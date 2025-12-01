"""
Chainlit UI Entry Point - Agent Orchestration POC

This is a minimal entry point that imports and wires together all Chainlit components.
All actual logic is in src/interface/chainlit/ modules.
"""
# CRITICAL: Import config FIRST to apply all patches and setup
# This must happen before any other chainlit imports
from src.interface.chainlit.config import *  # noqa: F403, F401

# Import handlers (contains all Chainlit decorators)
from src.interface.chainlit.handlers import (  # noqa: F401
    set_starters,
    start,
    main
)

# Import event handlers (for potential direct access if needed)
from src.interface.chainlit.event_handlers import (  # noqa: F401
    _handle_agent_message_event,
    _handle_semantic_search_event
)

# Re-export for Chainlit (Chainlit looks for these decorators in app.py)
__all__ = [
    'set_starters',
    'start',
    'main',
]
