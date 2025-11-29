"""
Orchestrator Agent Module

Split from orchestrator.py for better maintainability.
"""
from .orchestrator import OrchestratorAgent
from .session import SessionHistory

# For backward compatibility - import from old location
import sys
from pathlib import Path

# Add old orchestrator.py location to path temporarily for imports
_old_orchestrator_path = Path(__file__).parent.parent
if str(_old_orchestrator_path) not in sys.path:
    sys.path.insert(0, str(_old_orchestrator_path))

__all__ = ['OrchestratorAgent', 'SessionHistory']

