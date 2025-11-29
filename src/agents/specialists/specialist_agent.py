"""
Specialist Agent - Issue Resolution Expert

The Specialist Agent provides diagnostic analysis and issue resolution for the
Bedrock DSP platform.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from ..base_specialist import BaseSpecialistAgent
from ...utils.observability import trace_agent

logger = logging.getLogger(__name__)


class SpecialistAgent(BaseSpecialistAgent):
    """
    Specialist Agent for issue resolution and diagnostics.
    
    Responsibilities:
    - Deep diagnostic analysis on campaigns, line items, and supply deals
    - Root cause identification
    - Targeted fixes and solutions
    - Issue resolution verification
    """

    def __init__(self, config_path: str = None):
        """
        Initialize the Specialist Agent.

        Args:
            config_path: Path to agent configuration YAML file
        """
        if config_path is None:
            from pathlib import Path
            package_dir = Path(__file__).parent.parent.parent
            config_path = str(package_dir / "config" / "specialist_agent.yaml")
        super().__init__(config_path)

    @trace_agent("specialist")
    def analyze(self, question: str, context: str) -> Dict[str, Any]:
        """
        Perform Specialist analysis on a question with provided context.
        
        Args:
            question: The question to analyze
            context: Relevant context from knowledge base
            
        Returns:
            Analysis result dictionary
        """
        return super().analyze(question, context)
    
    def __call__(self, state: Any) -> str:
        """
        Execute Specialist analysis (required by BaseAgent interface).
        
        Args:
            state: Can be a question string or dict with 'question' and 'context'
            
        Returns:
            Analysis result as string
        """
        if isinstance(state, str):
            question = state
            context = ""
        elif isinstance(state, dict):
            question = state.get('question', '')
            context = state.get('context', '')
        else:
            question = str(state)
            context = ""
        
        result = self.analyze(question, context)
        return result.get('answer', str(result))

