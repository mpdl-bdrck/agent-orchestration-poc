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
            label="Team Introduction",
            message="Have all your agents say hi and explain their roles.",
        ),
        cl.Starter(
            label="Portfolio Health",
            message="How is my portfolio pacing right now?",
        ),
        cl.Starter(
            label="Knowledge Base",
            message="What are 'Supply Deals' in the Bedrock platform?",
        ),
        cl.Starter(
            label="Optimization",
            message="How can I optimize my bid strategy for better ROAS?",
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
        
        # 3. Stream graph events - create messages on-demand as agents speak
        try:
            async for event in graph.astream_events(initial_state, version="v1"):
                event_type = event.get("event")
                node_name = event.get("metadata", {}).get("langgraph_node", "")
                
                # Check if this event comes from a known agent (Orchestrator OR Sub-agents)
                if node_name in SUB_AGENTS or node_name == SUPERVISOR_NODE:
                    await _handle_agent_message_event(
                        event_type, event, node_name, active_messages
                    )
                
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

