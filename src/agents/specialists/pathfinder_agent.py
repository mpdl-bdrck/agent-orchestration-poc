"""
Pathfinder Agent - Supply Chain Navigator

The Pathfinder Agent provides supply path optimization and SSP relationship
management for the Bedrock DSP platform.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from ..base_specialist import BaseSpecialistAgent
from ...utils.observability import trace_agent

logger = logging.getLogger(__name__)


class PathfinderAgent(BaseSpecialistAgent):
    """
    Pathfinder Agent for supply chain navigation.
    
    Responsibilities:
    - QPS limit adjustments
    - Deal activation/deactivation
    - Floor price coordination
    - Traffic allocation optimization
    - SSP relationship management
    """

    def __init__(self, config_path: str = None):
        """
        Initialize the Pathfinder Agent.

        Args:
            config_path: Path to agent configuration YAML file
        """
        if config_path is None:
            from pathlib import Path
            package_dir = Path(__file__).parent.parent.parent
            config_path = str(package_dir / "config" / "pathfinder_agent.yaml")
        super().__init__(config_path)

    @trace_agent("pathfinder")
    def analyze(self, question: str, context: str) -> Dict[str, Any]:
        """
        Perform Pathfinder analysis on a question with provided context.
        
        Args:
            question: The question to analyze
            context: Relevant context from knowledge base
            
        Returns:
            Analysis result dictionary
        """
        return super().analyze(question, context)
    
    def __call__(self, state: Any) -> str:
        """
        Execute Pathfinder analysis (required by BaseAgent interface).
        
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

