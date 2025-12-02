"""
Chainlit UI Configuration and Setup.

Handles all setup, patches, constants, and configuration for the Chainlit interface.
This module must be imported FIRST before any other chainlit modules to apply patches.
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
# DISABLED: Chainlit's database persistence is fundamentally broken (see docs/guides/CHAINLIT_SQLITE_PERSISTENCE.md)
# Chainlit has bugs: InvalidTextRepresentationError, NotNullViolationError, DataError
# These errors flood the console and make debugging impossible
# SOLUTION: Disable persistence entirely - we're building an Agent System, not a Chat History System

# GLOBAL CSV STORAGE - accessible without imports
# This is a fallback mechanism for CSV data that bypasses module import issues
_GLOBAL_CSV_STORAGE = {}

# FORCE DISABLE Chainlit database persistence
os.environ["CHAINLIT_DATABASE_URL"] = ""
print("ℹ️  Chainlit persistence DISABLED (Chainlit's database layer has critical bugs)")
print("   Chat history will not persist across sessions (acceptable for POC)")
print("   See docs/guides/CHAINLIT_SQLITE_PERSISTENCE.md for details")

# Enable Guardian tools by default for Chainlit UI
# Force enable unless explicitly disabled in .env
# Set GUARDIAN_TOOLS_ENABLED=false in .env to disable if needed
current_value = os.environ.get("GUARDIAN_TOOLS_ENABLED", "").lower()
if current_value not in ("false", "0", "no", "off"):
    os.environ["GUARDIAN_TOOLS_ENABLED"] = "true"
else:
    # User explicitly disabled it - respect that
    os.environ["GUARDIAN_TOOLS_ENABLED"] = "false"

# Notification Panel feature flag
# Disabled by default - set NOTIFICATION_PANEL_ENABLED=true to enable
notification_panel_value = os.environ.get("NOTIFICATION_PANEL_ENABLED", "").lower()
if notification_panel_value in ("true", "1", "yes", "on"):
    os.environ["NOTIFICATION_PANEL_ENABLED"] = "true"
else:
    os.environ["NOTIFICATION_PANEL_ENABLED"] = "false"

# Check AWS SSO authentication for portfolio pacing tool
# This is required for Redshift database connections
import subprocess
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
        print("🔑 Running: aws sso login --profile bedrock")
        # Automatically trigger AWS SSO login
        login_result = subprocess.run(
            ['aws', 'sso', 'login', '--profile', 'bedrock'],
            timeout=60  # SSO login can take time (browser popup)
        )
        if login_result.returncode == 0:
            # Verify login was successful
            verify_result = subprocess.run(
                ['aws', 'sts', 'get-caller-identity', '--profile', 'bedrock'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if verify_result.returncode == 0:
                print("✅ AWS SSO authentication successful")
            else:
                print("⚠️  AWS SSO login completed but verification failed")
                print("   Portfolio pacing queries may fail without AWS SSO credentials")
        else:
            print("⚠️  AWS SSO login failed or was cancelled")
            print("   Portfolio pacing queries may fail without AWS SSO credentials")
except FileNotFoundError:
    print("⚠️  AWS CLI not found. Portfolio pacing tool requires AWS SSO authentication.")
except subprocess.TimeoutExpired:
    print("⚠️  AWS SSO check/login timed out. Portfolio pacing queries may fail.")
except Exception as e:
    print(f"⚠️  AWS SSO check failed: {e}. Portfolio pacing queries may fail.")

# NOW import chainlit and other modules
# No need for error suppression - persistence is disabled, so no database errors will occur
import logging
import warnings

# Suppress harmless asyncio warnings about unretrieved exceptions
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*Task exception was never retrieved.*")

import chainlit as cl
from langchain_core.messages import HumanMessage

# NUCLEAR: Monkey-patch Chainlit's data layer to completely disable database operations
# This prevents Chainlit from even attempting to connect to the database
try:
    from chainlit.data import chainlit_data_layer
    
    # Store original methods
    _original_create_step = chainlit_data_layer.ChainlitDataLayer.create_step
    _original_update_step = chainlit_data_layer.ChainlitDataLayer.update_step
    _original_get_thread = chainlit_data_layer.ChainlitDataLayer.get_thread
    _original_create_element = chainlit_data_layer.ChainlitDataLayer.create_element
    
    # Replace with no-op methods that return immediately
    async def _noop_create_step(self, *args, **kwargs):
        """No-op: Chainlit persistence disabled"""
        return None
    
    async def _noop_update_step(self, *args, **kwargs):
        """No-op: Chainlit persistence disabled"""
        return None
    
    async def _noop_get_thread(self, *args, **kwargs):
        """No-op: Chainlit persistence disabled"""
        return None
    
    async def _noop_create_element(self, *args, **kwargs):
        """No-op: Chainlit persistence disabled - prevents Element table errors"""
        return None
    
    # Apply patches
    chainlit_data_layer.ChainlitDataLayer.create_step = _noop_create_step
    chainlit_data_layer.ChainlitDataLayer.update_step = _noop_update_step
    chainlit_data_layer.ChainlitDataLayer.get_thread = _noop_get_thread
    chainlit_data_layer.ChainlitDataLayer.create_element = _noop_create_element
    
    print("✅ Chainlit data layer patched - all database operations disabled")
except Exception as e:
    print(f"⚠️  Warning: Could not patch Chainlit data layer: {e}")
    print("   Database errors may still occur")

# Chainlit persistence is DISABLED - no database errors will occur
# Chat history is ephemeral (lost on refresh) which is acceptable for this POC

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

__all__ = [
    'cl',
    'HumanMessage',
    'logger',
    'create_chainlit_graph',
    'SUPERVISOR_NODE',
    'ORCHESTRATOR_NODE',
    'SUB_AGENTS',
    'SEMANTIC_SEARCH_NODE',
    'AGENT_EMOJIS',
    'AGENT_DISPLAY_NAMES',
    '_GLOBAL_CSV_STORAGE',
]

