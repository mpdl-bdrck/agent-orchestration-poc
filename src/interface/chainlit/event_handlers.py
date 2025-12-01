"""
Event Handlers for Chainlit UI.

Handles LangGraph events and creates appropriate UI elements (messages, bubbles, etc.).
"""
import json
import logging

import chainlit as cl

from .config import (
    SUPERVISOR_NODE,
    SUB_AGENTS,
    SEMANTIC_SEARCH_NODE,
    AGENT_EMOJIS,
    AGENT_DISPLAY_NAMES,
    logger
)
from .csv_manager import (
    retrieve_csv_all_methods,
    send_csv_as_message,
    store_csv_in_session,
    clear_csv_storage
)

logger = logging.getLogger(__name__)


async def _handle_agent_message_event(event_type, event, node_name, active_messages):
    """Handle events from agents (Orchestrator, Guardian, Specialist, etc.) - creates chat bubbles."""
    emoji = AGENT_EMOJIS.get(node_name, "🤖")
    agent_display_name = AGENT_DISPLAY_NAMES.get(node_name, node_name.title())
    
    # Helper function to ensure message exists
    async def _ensure_message_exists():
        """Create message bubble if it doesn't exist (for direct LLM calls that skip on_chat_model_start)."""
        if node_name not in active_messages:
            # Show "Calling [Agent] Agent..." status for sub-agents
            if node_name in SUB_AGENTS:
                status_msg = cl.Message(
                    content=f"*Calling {agent_display_name} Agent...*",
                    author="System"
                )
                await status_msg.send()
            
            msg = cl.Message(
                content="",
                author=agent_display_name
            )
            await msg.send()
            active_messages[node_name] = msg
            
            # Check for queued tool calls and display them immediately
            tool_calls_queue = cl.user_session.get("tool_calls_queue", [])
            if tool_calls_queue:
                displayed_tools = []
                for tool_call in tool_calls_queue:
                    tool_agent = tool_call.get("agent", "unknown")
                    if tool_agent == node_name or tool_agent == "unknown":
                        tool_name = tool_call.get("tool_name", "unknown")
                        if tool_name == "analyze_portfolio_pacing":
                            await msg.stream_token(f"\n\n🛠️ *Running portfolio analysis...*\n\n")
                        else:
                            await msg.stream_token(f"\n\n🛠️ *Running tool: `{tool_name}`...*\n\n")
                        displayed_tools.append(tool_call)
                # Remove displayed tools from queue
                remaining_tools = [tc for tc in tool_calls_queue if tc not in displayed_tools]
                cl.user_session.set("tool_calls_queue", remaining_tools)
    
    # 0. DETECT CHAIN START (create message bubble early for tool calls)
    if event_type == "on_chain_start" and node_name in SUB_AGENTS:
        # Create message bubble early so tool calls can be displayed
        if node_name not in active_messages:
            await _ensure_message_exists()
    
    # 1. DETECT START OF SPEECH
    if event_type == "on_chat_model_start":
        # Skip Orchestrator - it will be created lazily on first token to prevent empty bubbles
        if node_name == SUPERVISOR_NODE:
            return  # Don't create empty bubble for Orchestrator when it routes
        
        # Ensure message exists (might have been created on on_chain_start)
        await _ensure_message_exists()
    
    # 2. STREAM TOKENS
    elif event_type == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk", {})
        
        # Extract content - MINIMAL processing, let Chainlit handle rendering naturally
        # NO normalization - that was causing excessive spacing!
        content = None
        if hasattr(chunk, 'content') and chunk.content:
            if isinstance(chunk.content, list):
                # Only handle list case - simple join, no normalization
                content = "".join(
                    str(block.get("text", block) if isinstance(block, dict) else block)
                    for block in chunk.content
                )
            else:
                # Pass through strings and other types directly
                content = chunk.content
        
        # STRICT CHECK: Only create Orchestrator message if we have actual content
        if node_name == SUPERVISOR_NODE:
            if content:  # Only act if chunk has text
                # Create bubble ONLY if we have text AND it doesn't exist
                if node_name not in active_messages:
                    msg = cl.Message(
                        content="",
                        author=agent_display_name
                    )
                    await msg.send()
                    active_messages[node_name] = msg
                
                # Stream the content
                await active_messages[node_name].stream_token(content)
        else:
            # Create message lazily for other agents if it doesn't exist
            await _ensure_message_exists()
            
            if node_name in active_messages and content:
                await active_messages[node_name].stream_token(content)
    
    # 3. HANDLE TOOLS (Show as inline text in agent's message, or as standalone steps)
    elif event_type == "on_tool_start":
        await _ensure_message_exists()
        if node_name in active_messages:
            tool_name = event.get("name", "unknown_tool")
            # Show tool execution as inline text in the agent's message
            # For portfolio pacing, show minimal info (Guardian will format the results)
            if tool_name == "analyze_portfolio_pacing":
                await active_messages[node_name].stream_token(
                    f"\n\n🛠️ *Running portfolio analysis...*\n\n"
                )
            else:
                await active_messages[node_name].stream_token(
                    f"\n\n🛠️ *Running tool: `{tool_name}`...*\n\n"
                )
    
    elif event_type == "on_tool_end":
        await _ensure_message_exists()
        if node_name in active_messages:
            tool_name = event.get("name", "unknown_tool")
            
            # Try to extract CSV from tool output if available
            tool_output = event.get("data", {}).get("output", "")
            if tool_name == "analyze_portfolio_pacing" and tool_output:
                try:
                    parsed = json.loads(tool_output)
                    if isinstance(parsed, dict) and "csv" in parsed:
                        csv_data = parsed.get("csv")
                        csv_filename = parsed.get("filename")
                        if csv_data and csv_filename:
                            # Store CSV in session for later retrieval
                            store_csv_in_session(csv_data, csv_filename, tool_name, node_name)
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
            
            # For portfolio pacing, don't show completion (Guardian formats the results)
            if tool_name != "analyze_portfolio_pacing":
                await active_messages[node_name].stream_token(
                    f"✅ *Tool `{tool_name}` completed*\n\n"
                )
    
    # 4. END OF SPEECH (Commit the message)
    elif event_type == "on_chat_model_end":
        if node_name in active_messages:
            msg = active_messages[node_name]
            
            # SOLUTION: "Late Arrival" Pattern - Send CSV as a NEW message (not updating existing)
            # This bypasses Chainlit's flaky msg.update(elements=[...]) behavior
            # CRITICAL: Only retrieve CSV for Guardian agent (portfolio pacing tool)
            if node_name == "guardian":
                csv_data, csv_filename = retrieve_csv_all_methods(node_name)
                
                # Send CSV as a NEW message (Late Arrival Pattern)
                if csv_data and csv_filename:
                    await send_csv_as_message(csv_data, csv_filename)
                    clear_csv_storage(node_name)  # Clear only for this node
            
            # Update the original message normally (without CSV)
            try:
                await msg.update()
            except Exception as e:
                logger.error(f"Failed to update message: {e}", exc_info=True)
            
            # Keep message in active_messages - don't delete, so user can see full conversation
    
    # Error handling
    elif event_type == "on_chain_error":
        await _ensure_message_exists()
        if node_name in active_messages:
            error = event.get("data", {}).get("error", "Unknown error")
            await active_messages[node_name].stream_token(
                f"\n\n❌ **Error:** {str(error)}\n\n"
            )
            await active_messages[node_name].update()


async def _handle_semantic_search_event(event_type, event, orchestrator_msg):
    """Handle semantic search events - show as standalone status message."""
    # Semantic search is a custom node (not a tool), so use on_chain_start instead of on_tool_start
    if event_type == "on_chain_start":
        # Create standalone status message (like "Calling X Agent...")
        status_msg = cl.Message(
            content=f"*Searching Knowledge Base...*",
            author="System"
        )
        await status_msg.send()

