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

# Configure Chainlit's data layer BEFORE importing chainlit
# To enable persistence: Set CHAINLIT_DATABASE_URL to your PostgreSQL connection string
# To disable persistence: Leave CHAINLIT_DATABASE_URL empty (default for POC)
# If persistence is enabled, run: ./scripts/create_chainlit_schema.sh [database_name]
import os
# Default: Disable data layer for POC (set CHAINLIT_DATABASE_URL in .env to enable)
if "CHAINLIT_DATABASE_URL" not in os.environ:
    os.environ["CHAINLIT_DATABASE_URL"] = ""
# Note: DATABASE_URL is used for knowledge base, CHAINLIT_DATABASE_URL is for Chainlit persistence

# Enable Guardian tools by default for Chainlit UI
# Force enable unless explicitly disabled in .env
# Set GUARDIAN_TOOLS_ENABLED=false in .env to disable if needed
current_value = os.environ.get("GUARDIAN_TOOLS_ENABLED", "").lower()
if current_value not in ("false", "0", "no", "off"):
    os.environ["GUARDIAN_TOOLS_ENABLED"] = "true"
else:
    # User explicitly disabled it - respect that
    os.environ["GUARDIAN_TOOLS_ENABLED"] = "false"

# NOW import chainlit and other modules
import chainlit as cl
import logging
from langchain_core.messages import HumanMessage

# Aggressively suppress Chainlit data layer errors and warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="chainlit.data")
warnings.filterwarnings("ignore", category=UserWarning, module="chainlit")

# Custom logging filter to suppress Chainlit database errors
class ChainlitDatabaseErrorFilter(logging.Filter):
    """Filter out Chainlit database errors when persistence is disabled."""
    def filter(self, record):
        msg = str(record.getMessage())
        # Suppress "Thread" table errors (various formats)
        if 'relation "Thread" does not exist' in msg or 'relation \'Thread\' does not exist' in msg:
            return False
        if 'UndefinedTableError' in msg:
            return False
        # Suppress ChainlitDataLayer errors
        if 'ChainlitDataLayer' in msg:
            if any(keyword in msg for keyword in ['does not exist', 'UndefinedTableError', 'create_step', 'update_step']):
                return False
        # Suppress "Task exception was never retrieved" for Chainlit data layer
        if 'Task exception was never retrieved' in msg:
            if 'ChainlitDataLayer' in msg or 'chainlit.data' in msg or 'chainlit/data' in msg:
                return False
        # Suppress "Database error" messages related to Thread table
        if 'Database error' in msg and ('Thread' in msg or 'UndefinedTableError' in msg):
            return False
        # Suppress "Error updating thread" or "Error while flushing" for Thread errors
        if any(phrase in msg for phrase in ['Error updating thread', 'Error while flushing']):
            if 'Thread' in msg or 'does not exist' in msg:
                return False
        return True

# Apply filter to root logger (catches all loggers)
_chainlit_db_filter = ChainlitDatabaseErrorFilter()
logging.getLogger().addFilter(_chainlit_db_filter)

# Also suppress at module level for chainlit.data and asyncpg
logging.getLogger("chainlit.data").setLevel(logging.CRITICAL)
logging.getLogger("chainlit.data.chainlit_data_layer").setLevel(logging.CRITICAL)
logging.getLogger("chainlit.data.utils").setLevel(logging.CRITICAL)
logging.getLogger("asyncpg").setLevel(logging.ERROR)  # Only show actual errors, not missing table warnings

# Suppress "Database error" messages from our own logger if they're Chainlit-related
logging.getLogger("__main__").addFilter(_chainlit_db_filter)

# Note: Some asyncio tracebacks may still appear in stderr (from Python's default exception handler)
# These are harmless - Chainlit works fine without persistence. The logging filter above
# suppresses all logged errors. Tracebacks are printed directly by asyncio and bypass logging.

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
    
    # Helper function to ensure step exists
    async def _ensure_step_exists():
        """Create step if it doesn't exist (for direct LLM calls that skip on_chain_start)."""
        if node_name not in active_steps:
            step = cl.Step(name=f"{emoji} {agent_display_name} Agent", type="tool")
            # step.language = "markdown"  # COMMENTED: Causes raw markdown display and horizontal scroll
            await step.send()
            active_steps[node_name] = step
    
    # Agent starts thinking/acting
    # Handle BOTH on_chain_start (for tool-calling) AND on_chat_model_start (for direct LLM calls)
    if event_type == "on_chain_start" or event_type == "on_chat_model_start":
        await _ensure_step_exists()
    
    # Agent streams tokens (typewriter effect)
    elif event_type == "on_chat_model_stream":
        # Create step lazily if it doesn't exist (for direct LLM calls that skip on_chain_start)
        await _ensure_step_exists()
        
        chunk = event.get("data", {}).get("chunk", {})
        if hasattr(chunk, 'content') and chunk.content:
            # Normalize content to string (chunk.content can be a list in LangChain)
            content = chunk.content
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text" and "text" in block:
                            text_parts.append(str(block["text"]))
                        elif "text" in block:
                            text_parts.append(str(block["text"]))
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = " ".join(text_parts).strip()
            elif not isinstance(content, str):
                content = str(content) if content else ""
            
            if isinstance(content, str) and content:
                await active_steps[node_name].stream_token(content)
    
    # Agent uses a tool (nested in agent step)
    elif event_type == "on_tool_start":
        await _ensure_step_exists()
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
        await _ensure_step_exists()
        tool_name = event.get("name", "unknown_tool")
        # For portfolio pacing, don't show raw output (Guardian formats it)
        if tool_name != "analyze_portfolio_pacing":
            # Show brief completion message for other tools
            await active_steps[node_name].stream_token(
                f"*✅ Tool `{tool_name}` completed*\n\n"
            )
    
    # Agent completes
    elif event_type == "on_chain_end" or event_type == "on_chat_model_end":
        if node_name in active_steps:
            # Step will auto-close, or we can explicitly finalize
            await active_steps[node_name].update()
    
    # Error handling
    elif event_type == "on_chain_error":
        await _ensure_step_exists()
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
        # step.language = "markdown"  # COMMENTED: Causes raw markdown display and horizontal scroll
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
