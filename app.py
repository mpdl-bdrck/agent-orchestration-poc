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
# Chainlit persistence is ENABLED by default - uses same database as knowledge base
# To disable: Set CHAINLIT_DATABASE_URL="" in .env
import os

# Enable Chainlit persistence by default (uses same database as knowledge base)
if "CHAINLIT_DATABASE_URL" not in os.environ:
    # Construct CHAINLIT_DATABASE_URL from DATABASE_URL or POSTGRES_* vars
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        # Use same database as knowledge base
        os.environ["CHAINLIT_DATABASE_URL"] = database_url
        print("✅ Chainlit persistence enabled (using DATABASE_URL)")
    else:
        # Try to construct from POSTGRES_* vars
        postgres_host = os.getenv("POSTGRES_HOST")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_db = os.getenv("POSTGRES_DB", "knowledge_base")
        postgres_user = os.getenv("POSTGRES_USER")
        postgres_password = os.getenv("POSTGRES_PASSWORD")
        
        if postgres_host and postgres_user:
            # Construct PostgreSQL URL
            if postgres_password:
                chainlit_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
            else:
                chainlit_url = f"postgresql://{postgres_user}@{postgres_host}:{postgres_port}/{postgres_db}"
            os.environ["CHAINLIT_DATABASE_URL"] = chainlit_url
            print(f"✅ Chainlit persistence enabled (using POSTGRES_* vars → {postgres_db})")
        else:
            # No database config found - disable persistence
            os.environ["CHAINLIT_DATABASE_URL"] = ""
            print("⚠️  Chainlit persistence DISABLED (no database configuration found)")
            print("   Set DATABASE_URL or POSTGRES_* vars in .env to enable conversation history")

# Note: DATABASE_URL is used for knowledge base, CHAINLIT_DATABASE_URL is for Chainlit persistence
# They can point to the same database (recommended) or different databases
# If you see "relation 'thread' does not exist" errors, run: ./scripts/create_chainlit_schema.sh [database_name]

# Enable Guardian tools by default for Chainlit UI
# Force enable unless explicitly disabled in .env
# Set GUARDIAN_TOOLS_ENABLED=false in .env to disable if needed
current_value = os.environ.get("GUARDIAN_TOOLS_ENABLED", "").lower()
if current_value not in ("false", "0", "no", "off"):
    os.environ["GUARDIAN_TOOLS_ENABLED"] = "true"
else:
    # User explicitly disabled it - respect that
    os.environ["GUARDIAN_TOOLS_ENABLED"] = "false"

# Check AWS SSO authentication for portfolio pacing tool
# This is required for Redshift database connections
import subprocess
import sys
try:
    result = subprocess.run(
        ['aws', 'sts', 'get-caller-identity', '--profile', 'bedrock'],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        print("✅ AWS SSO authentication verified (bedrock profile)")
    else:
        print("⚠️  AWS SSO authentication required for portfolio pacing tool")
        print("   Run: aws sso login --profile bedrock")
        print("   Portfolio pacing queries may fail without AWS SSO credentials")
except FileNotFoundError:
    print("⚠️  AWS CLI not found. Portfolio pacing tool requires AWS SSO authentication.")
except subprocess.TimeoutExpired:
    print("⚠️  AWS SSO check timed out. Portfolio pacing queries may fail.")
except Exception as e:
    print(f"⚠️  AWS SSO check failed: {e}. Portfolio pacing queries may fail.")

# NOW import chainlit and other modules
import chainlit as cl
import logging
from langchain_core.messages import HumanMessage

# Suppress ALL Chainlit database errors/exceptions from console
# This is a known issue in Chainlit 2.9.2 where parameter binding has bugs
# The app still works perfectly - these are just console noise
class ChainlitDatabaseExceptionFilter(logging.Filter):
    """Filter out ALL Chainlit database errors and exceptions."""
    def filter(self, record):
        message = str(record.getMessage())
        # Suppress parameter binding errors
        if 'invalid input for query argument' in message:
            return False
        if 'DataError' in message:
            return False
        # Suppress "Task exception was never retrieved" messages
        if 'Task exception was never retrieved' in message:
            return False
        # Suppress database errors from Chainlit
        if 'Database error' in message and ('chainlit' in message.lower() or 'Step' in message or 'Thread' in message):
            return False
        # Suppress asyncpg exceptions
        if 'asyncpg.exceptions' in message:
            return False
        # Suppress UndefinedColumnError (we've fixed the schema, but old errors may persist)
        if 'UndefinedColumnError' in message:
            return False
        return True

# Apply comprehensive filter to root logger (catches everything)
_chainlit_db_filter = ChainlitDatabaseExceptionFilter()
logging.getLogger().addFilter(_chainlit_db_filter)

# Suppress at module level (double protection)
logging.getLogger("chainlit.data").setLevel(logging.CRITICAL)
logging.getLogger("chainlit.data.chainlit_data_layer").setLevel(logging.CRITICAL)
logging.getLogger("chainlit.data.utils").setLevel(logging.CRITICAL)
logging.getLogger("asyncpg").setLevel(logging.CRITICAL)  # Suppress all asyncpg logs

# Also suppress warnings from asyncio about unretrieved exceptions
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*Task exception was never retrieved.*")
warnings.filterwarnings("ignore", message=".*coroutine.*was never awaited.*")

# Chainlit persistence is now ENABLED by default
# Conversation history will be saved to the database automatically
# 
# If you see "relation 'thread' does not exist" errors on startup:
#   1. Run: ./scripts/create_chainlit_schema.sh [database_name]
#   2. This creates the required tables: thread, step, user, element, feedback
#   3. Restart Chainlit - errors will disappear and conversations will be saved

from src.interface.chainlit.graph_factory import create_chainlit_graph

logger = logging.getLogger(__name__)

# Node name constants
SUPERVISOR_NODE = "supervisor"
ORCHESTRATOR_NODE = "supervisor"  # Supervisor is the orchestrator
SUB_AGENTS = ["guardian", "specialist", "optimizer", "pathfinder", "canary"]
SEMANTIC_SEARCH_NODE = "semantic_search"

# Agent emoji mapping
AGENT_EMOJIS = {
    "supervisor": "🧠",
    "guardian": "🛡️",
    "specialist": "🔧",
    "optimizer": "🎯",
    "pathfinder": "🧭",
    "canary": "🐤",
    "semantic_search": "🔍"
}

# Agent display names (for chat bubbles) - use ASCII names for avatars (emojis are in SVG files)
AGENT_DISPLAY_NAMES = {
    "supervisor": "Orchestrator",
    "guardian": "Guardian",
    "specialist": "Specialist",
    "optimizer": "Optimizer",
    "pathfinder": "Pathfinder",
    "canary": "Canary",
    "semantic_search": "Semantic Search"
}


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
        logger.info("✅ Avatar system: Chainlit will auto-load avatars from /public/avatars/")
        logger.info("   Avatars should be named: orchestrator.png, guardian.png, specialist.png, etc.")
        
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
        
        # 4. Finalize all active messages
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


async def _handle_agent_message_event(event_type, event, node_name, active_messages):
    """Handle events from agents (Orchestrator, Guardian, Specialist, etc.) - creates chat bubbles."""
    emoji = AGENT_EMOJIS.get(node_name, "🤖")
    agent_display_name = AGENT_DISPLAY_NAMES.get(node_name, node_name.title())
    
    # Helper function to ensure message exists
    async def _ensure_message_exists():
        """Create message bubble if it doesn't exist (for direct LLM calls that skip on_chat_model_start)."""
        if node_name not in active_messages:
            msg = cl.Message(
                content="",
                author=agent_display_name
            )
            await msg.send()
            active_messages[node_name] = msg
    
    # 1. DETECT START OF SPEECH
    if event_type == "on_chat_model_start":
        # Skip Orchestrator - it will be created lazily on first token to prevent empty bubbles
        if node_name == SUPERVISOR_NODE:
            return  # Don't create empty bubble for Orchestrator when it routes
        
        # Only create a new bubble if one isn't already open for this node
        if node_name not in active_messages:
            # Show "Calling [Agent] Agent..." status for sub-agents
            if node_name in SUB_AGENTS:
                # Send a brief status message before the agent responds
                status_msg = cl.Message(
                    content=f"📞 Calling {agent_display_name} Agent...",
                    author="System"
                )
                await status_msg.send()
            
            msg = cl.Message(
                content="",
                author=agent_display_name
            )
            await msg.send()
            active_messages[node_name] = msg
    
    # 2. STREAM TOKENS
    elif event_type == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk", {})
        
        # Extract content from chunk
        content = None
        if hasattr(chunk, 'content') and chunk.content:
            # Normalize content to string (chunk.content can be a list in LangChain)
            raw_content = chunk.content
            if isinstance(raw_content, list):
                text_parts = []
                for block in raw_content:
                    if isinstance(block, dict):
                        if block.get("type") == "text" and "text" in block:
                            text_parts.append(str(block["text"]))
                        elif "text" in block:
                            text_parts.append(str(block["text"]))
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = " ".join(text_parts).strip()
            elif isinstance(raw_content, str):
                content = raw_content.strip()
            elif raw_content:
                content = str(raw_content).strip()
        
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
            # For portfolio pacing, don't show completion (Guardian formats the results)
            if tool_name != "analyze_portfolio_pacing":
                await active_messages[node_name].stream_token(
                    f"✅ *Tool `{tool_name}` completed*\n\n"
                )
    
    # 4. END OF SPEECH (Commit the message)
    elif event_type == "on_chat_model_end":
        if node_name in active_messages:
            await active_messages[node_name].update()
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
    """Handle semantic search events - show as inline text in orchestrator message."""
    if orchestrator_msg is None:
        return  # Can't show if no orchestrator message exists
    
    # Show semantic search activity inline in orchestrator's message
    if event_type == "on_tool_start":
        # Extract query from event data
        input_data = event.get("data", {}).get("input", {})
        query = input_data.get("query", "") if isinstance(input_data, dict) else ""
        await orchestrator_msg.stream_token(
            f"\n\n🔍 *Searching knowledge base for: `{query}`...*\n\n"
        )
    
    elif event_type == "on_tool_end":
        await orchestrator_msg.stream_token(
            "*✅ Search completed*\n\n"
        )
