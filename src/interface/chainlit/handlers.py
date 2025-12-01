"""
Chainlit Decorators and Main Message Handler.

Contains all Chainlit decorator functions (@cl.set_starters, @cl.on_chat_start, @cl.on_message).
"""
import logging

from .config import (
    cl,
    HumanMessage,
    logger,
    create_chainlit_graph,
    SUPERVISOR_NODE,
    SUB_AGENTS,
    SEMANTIC_SEARCH_NODE
)
from .event_handlers import (
    _handle_agent_message_event,
    _handle_semantic_search_event
)
# CSV is handled in event_handlers.py on_chat_model_end - no need to import here

logger = logging.getLogger(__name__)


@cl.set_starters
async def set_starters():
    """Define starter buttons for common actions."""
    return [
        cl.Starter(
            label="Agent Team Introduction",
            message="Have all your agents say hi and explain their roles.",
        ),
        cl.Starter(
            label="Campaign Portfolio Health",
            message="How is my portfolio pacing right now?",
        ),
        cl.Starter(
            label="What are Supply Deals?",
            message="What are 'Supply Deals' in the Bedrock platform?",
        )
    ]


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
        cl.user_session.set("active_messages", {})  # Changed from active_steps
        
        # Avatar registration (Chainlit 1.1.300+)
        # Chainlit automatically loads avatars from /public/avatars/ directory
        # File naming: lowercase, hyphenated (e.g., "Guardian" -> "guardian.png")
        # No need to register programmatically - Chainlit auto-discovers them
        # Ensure avatars exist in public/avatars/ directory with correct naming
        # Use debug level to reduce console noise (this runs on every browser tab/reload)
        logger.debug("✅ Avatar system: Chainlit will auto-load avatars from /public/avatars/")
        logger.debug("   Avatars should be named: orchestrator.png, guardian.png, specialist.png, etc.")
        
        # NOTE: No welcome message - this keeps the chat 'empty' so Starter buttons stay visible
    except Exception as e:
        logger.error(f"Failed to initialize Chainlit session: {e}", exc_info=True)
        await cl.Message(
            content=f"❌ **Error initializing orchestrator:** {str(e)}\n\n"
                   "Please check your configuration and try again.",
            author="System"
        ).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle user message and stream graph events."""
    try:
        # 1. Get graph and history from session
        graph = cl.user_session.get("graph")
        if not graph:
            await cl.Message(
                content="❌ Graph not initialized. Please refresh the page.",
                author="System"
            ).send()
            return
        
        history = cl.user_session.get("history", [])
        context_id = cl.user_session.get("context_id", "bedrock_kb")
        active_messages = cl.user_session.get("active_messages", {})
        
        # Clear active messages for new turn (each agent gets a fresh message bubble)
        active_messages.clear()
        cl.user_session.set("active_messages", active_messages)
        
        # 2. Prepare initial state for graph
        initial_state = {
            "messages": [HumanMessage(content=message.content)],
            "next": "",
            "current_task_instruction": "",
            "context_id": context_id,
            "agent_responses": [],
            "user_question": message.content
        }
        
        # Create Chainlit streaming callback for tool usage messages
        # This captures tool_call events from agent_loop.py that LangGraph doesn't capture
        # Store tool calls in session - we'll display them when agent message is created
        tool_calls_queue = cl.user_session.get("tool_calls_queue", [])
        
        def chainlit_streaming_callback(event_type: str, message: str, data: dict = None):
            """Handle streaming events from agents (tool calls, etc.) that LangGraph doesn't capture."""
            if event_type == "tool_call":
                tool_name = data.get("tool", message) if data else message
                # Store tool call info - we'll display it when agent message is created
                tool_calls_queue.append({
                    "tool_name": tool_name,
                    "agent": data.get("agent", "unknown") if data else "unknown"
                })
                logger.info(f"🔧 Tool call queued: {tool_name} for agent {data.get('agent', 'unknown') if data else 'unknown'}")
                # Update session
                cl.user_session.set("tool_calls_queue", tool_calls_queue)
        
        # Store callback and queue in session so nodes can access them
        cl.user_session.set("streaming_callback", chainlit_streaming_callback)
        cl.user_session.set("tool_calls_queue", tool_calls_queue)
        
        # 3. Stream graph events - create messages on-demand as agents speak
        try:
            async for event in graph.astream_events(initial_state, version="v1"):
                event_type = event.get("event")
                node_name = event.get("metadata", {}).get("langgraph_node", "")
                
                # DEBUG: Log all events to understand what LangGraph emits
                # This helps diagnose why tool_start events might not be showing
                if event_type in ["on_tool_start", "on_tool_end", "on_chain_start", "on_chain_end", "on_chat_model_start"]:
                    tool_name = event.get("name", event.get("data", {}).get("name", "N/A"))
                    logger.debug(f"🔍 LangGraph Event: {event_type} | Node: {node_name} | Tool/Name: {tool_name} | Event keys: {list(event.keys())}")
                
                # Check if this event comes from a known agent (Orchestrator OR Sub-agents)
                if node_name in SUB_AGENTS or node_name == SUPERVISOR_NODE:
                    await _handle_agent_message_event(
                        event_type, event, node_name, active_messages
                    )
                    
                    # After handling event, check if we need to display queued tool calls
                    # This handles the case where tool call happened before message bubble was created
                    if node_name in active_messages and node_name in SUB_AGENTS:
                        tool_calls_queue = cl.user_session.get("tool_calls_queue", [])
                        if tool_calls_queue:
                            msg = active_messages[node_name]
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
                            if displayed_tools:
                                remaining_tools = [tc for tc in tool_calls_queue if tc not in displayed_tools]
                                cl.user_session.set("tool_calls_queue", remaining_tools)
                                logger.info(f"✅ Displayed {len(displayed_tools)} queued tool call(s) for {node_name}")
                
                # --- SEMANTIC SEARCH (Keep as step, nested under orchestrator message) ---
                elif node_name == SEMANTIC_SEARCH_NODE:
                    # Find the orchestrator's active message to nest the step under it
                    orchestrator_msg = active_messages.get(SUPERVISOR_NODE)
                    await _handle_semantic_search_event(
                        event_type, event, orchestrator_msg
                    )
        
        except Exception as e:
            logger.error(f"Error during event streaming: {e}", exc_info=True)
            await cl.Message(
                content=f"❌ **Error during execution:** {str(e)}",
                author="System"
            ).send()
            return
        
        # 4. Finalize all active messages (CSV sent via Late Arrival pattern in on_chat_model_end)
        logger.info(f"🔍 Finalizing messages for nodes: {list(active_messages.keys())}")
        
        # NOTE: CSV is sent in on_chat_model_end handler (event_handlers.py)
        # No need to send it again here - that was causing duplicates
        
        # Update all messages normally (CSV sent separately)
        for msg in active_messages.values():
            if msg:
                await msg.update()
        
        # 5. Update history for next turn
        history.append(HumanMessage(content=message.content))
        cl.user_session.set("history", history)
        cl.user_session.set("active_messages", active_messages)
        
    except Exception as e:
        logger.error(f"Error during Chainlit message handling: {e}", exc_info=True)
        await cl.Message(
            content=f"❌ **Error during execution:** {str(e)}",
            author="System"
        ).send()

