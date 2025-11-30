"""
Chainlit UI for Agent Orchestration POC.

Provides web-based interface with main chat and expandable agent steps.
"""
import sys
import os

# CRITICAL: Patch sniffio BEFORE importing chainlit (Python 3.14+ compatibility)
# This must happen before ANY async libraries are imported
if sys.version_info >= (3, 14):
    try:
        import sniffio._impl
        
        # Store original function
        _original_current_async_library = sniffio._impl.current_async_library
        
        def _patched_current_async_library():
            """Patched version that falls back to 'asyncio' if detection fails."""
            try:
                return _original_current_async_library()
            except sniffio._impl.AsyncLibraryNotFoundError:
                return "asyncio"
            except Exception:
                return "asyncio"
        
        # Patch the internal implementation
        sniffio._impl.current_async_library = _patched_current_async_library
        
        # Also patch the public API
        try:
            import sniffio
            sniffio.current_async_library = _patched_current_async_library
        except Exception:
            pass
    except Exception:
        pass  # If patching fails, continue anyway

# Apply nest_asyncio for reentrant event loops
try:
    import nest_asyncio
    nest_asyncio.apply()
except Exception:
    pass

# NOW import chainlit and other modules
import chainlit as cl
import logging
from langchain_core.messages import HumanMessage

from src.interface.chainlit.graph_factory import create_chainlit_graph

logger = logging.getLogger(__name__)

# Node name constants
SUPERVISOR_NODE = "supervisor"
SUB_AGENTS = ["guardian", "specialist", "optimizer", "pathfinder", "canary"]
SEMANTIC_SEARCH_NODE = "semantic_search"

# Agent emoji mapping
AGENT_EMOJIS = {
    "guardian": "🛡️",
    "specialist": "🔧",
    "optimizer": "🎯",
    "pathfinder": "🧭",
    "canary": "🐤",
    "semantic_search": "🔍"
}


@cl.on_chat_start
async def start():
    """Initialize session when user starts chat."""
    try:
        # Initialize session state
        context_id = cl.user_session.get("context_id", "bedrock_kb")
        
        # Create graph for this session
        graph = create_chainlit_graph(context_id=context_id)
        cl.user_session.set("graph", graph)
        cl.user_session.set("history", [])
        cl.user_session.set("context_id", context_id)
        cl.user_session.set("active_steps", {})
        
        await cl.Message(
            content="👋 **Bedrock Orchestrator Online.**\n\n"
                   "I can analyze portfolios, troubleshoot issues, and optimize campaigns. "
                   "How can I help?"
        ).send()
    except Exception as e:
        logger.error(f"Failed to initialize Chainlit session: {e}", exc_info=True)
        await cl.Message(
            content=f"❌ **Error initializing orchestrator:** {str(e)}\n\n"
                   "Please check your configuration and try again."
        ).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle user message and stream graph events."""
    try:
        # 1. Get graph and history from session
        graph = cl.user_session.get("graph")
        if not graph:
            await cl.Message(content="❌ Graph not initialized. Please refresh the page.").send()
            return
        
        history = cl.user_session.get("history", [])
        context_id = cl.user_session.get("context_id", "bedrock_kb")
        active_steps = cl.user_session.get("active_steps", {})
        
        # Clear active steps for new message
        active_steps.clear()
        cl.user_session.set("active_steps", active_steps)
        
        # 2. Prepare initial state for graph
        initial_state = {
            "messages": [HumanMessage(content=message.content)],
            "next": "",
            "current_task_instruction": "",
            "context_id": context_id,
            "agent_responses": [],
            "user_question": message.content
        }
        
        # 3. Start the Supervisor's Main Message (empty at first)
        main_msg = cl.Message(content="")
        await main_msg.send()
        
        # 4. Stream graph events
        try:
            async for event in graph.astream_events(initial_state, version="v1"):
                event_type = event.get("event")
                node_name = event.get("metadata", {}).get("langgraph_node", "")
                
                # --- SUB-AGENT ACTIVITY (Expandable Steps) ---
                if node_name in SUB_AGENTS:
                    await _handle_sub_agent_event(
                        event_type, event, node_name, active_steps
                    )
                
                # --- SEMANTIC SEARCH (Expandable Step) ---
                elif node_name == SEMANTIC_SEARCH_NODE:
                    await _handle_semantic_search_event(
                        event_type, event, active_steps
                    )
                
                # --- SUPERVISOR ACTIVITY (Main Chat) ---
                elif node_name == SUPERVISOR_NODE:
                    await _handle_supervisor_event(
                        event_type, event, main_msg
                    )
        
        except Exception as e:
            logger.error(f"Error during event streaming: {e}", exc_info=True)
            await cl.Message(
                content=f"❌ **Error during execution:** {str(e)}"
            ).send()
            return
        
        # 5. Finalize main message
        await main_msg.update()
        
        # 6. Update history for next turn
        history.append(HumanMessage(content=message.content))
        cl.user_session.set("history", history)
        cl.user_session.set("active_steps", active_steps)
        
    except Exception as e:
        logger.error(f"Error during Chainlit message handling: {e}", exc_info=True)
        await cl.Message(
            content=f"❌ **Error during execution:** {str(e)}"
        ).send()


async def _handle_sub_agent_event(event_type, event, node_name, active_steps):
    """Handle events from sub-agents (Guardian, Specialist, etc.)."""
    emoji = AGENT_EMOJIS.get(node_name, "🤖")
    agent_display_name = node_name.title()
    
    # Agent starts thinking/acting
    if event_type == "on_chain_start":
        # Create expandable step
        step = cl.Step(name=f"{emoji} {agent_display_name} Agent", type="tool")
        step.language = "markdown"
        await step.send()
        active_steps[node_name] = step
    
    # Agent streams tokens (typewriter effect)
    elif event_type == "on_chat_model_stream":
        if node_name in active_steps:
            chunk = event.get("data", {}).get("chunk", {})
            if hasattr(chunk, 'content') and chunk.content:
                await active_steps[node_name].stream_token(chunk.content)
    
    # Agent uses a tool (nested in agent step)
    elif event_type == "on_tool_start":
        if node_name in active_steps:
            tool_name = event.get("name", "unknown_tool")
            # Hide raw output for portfolio pacing tool
            if tool_name == "analyze_portfolio_pacing":
                await active_steps[node_name].stream_token(
                    f"\n\n*🛠️ Running Tool: `{tool_name}`...*\n\n"
                )
            else:
                await active_steps[node_name].stream_token(
                    f"\n\n*🛠️ Running Tool: `{tool_name}`...*\n\n"
                )
    
    # Tool execution completes
    elif event_type == "on_tool_end":
        if node_name in active_steps:
            tool_name = event.get("name", "unknown_tool")
            # For portfolio pacing, don't show raw output (Guardian formats it)
            if tool_name != "analyze_portfolio_pacing":
                # Show brief completion message for other tools
                await active_steps[node_name].stream_token(
                    f"*✅ Tool `{tool_name}` completed*\n\n"
                )
    
    # Agent completes
    elif event_type == "on_chain_end":
        if node_name in active_steps:
            # Step will auto-close, or we can explicitly finalize
            await active_steps[node_name].update()
    
    # Error handling
    elif event_type == "on_chain_error":
        if node_name in active_steps:
            error = event.get("data", {}).get("error", "Unknown error")
            await active_steps[node_name].stream_token(
                f"\n\n❌ **Error:** {str(error)}\n\n"
            )
            await active_steps[node_name].update()


async def _handle_semantic_search_event(event_type, event, active_steps):
    """Handle semantic search events."""
    # Show as expandable step for consistency
    if event_type == "on_chain_start":
        step = cl.Step(name="🔍 Semantic Search", type="tool")
        step.language = "markdown"
        await step.send()
        active_steps["semantic_search"] = step
    
    elif event_type == "on_tool_start":
        if "semantic_search" in active_steps:
            # Extract query from event data
            input_data = event.get("data", {}).get("input", {})
            query = input_data.get("query", "") if isinstance(input_data, dict) else ""
            await active_steps["semantic_search"].stream_token(
                f"*Searching knowledge base for: `{query}`...*\n\n"
            )
    
    elif event_type == "on_tool_end":
        if "semantic_search" in active_steps:
            await active_steps["semantic_search"].stream_token(
                "*✅ Search completed*\n\n"
            )
            await active_steps["semantic_search"].update()
    
    elif event_type == "on_chain_end":
        if "semantic_search" in active_steps:
            await active_steps["semantic_search"].update()
    
    elif event_type == "on_chain_error":
        if "semantic_search" in active_steps:
            error = event.get("data", {}).get("error", "Unknown error")
            await active_steps["semantic_search"].stream_token(
                f"\n\n❌ **Error:** {str(error)}\n\n"
            )
            await active_steps["semantic_search"].update()


async def _handle_supervisor_event(event_type, event, main_msg):
    """Handle supervisor/orchestrator events (main chat)."""
    # Supervisor streams reasoning or final response
    if event_type == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk", {})
        if hasattr(chunk, 'content') and chunk.content:
            await main_msg.stream_token(chunk.content)
    
    # Error handling
    elif event_type == "on_chain_error":
        error = event.get("data", {}).get("error", "Unknown error")
        await main_msg.stream_token(
            f"\n\n❌ **Error:** {str(error)}\n\n"
        )
