"""
Optimizer Agent - Performance Manager

The Optimizer Agent provides budget and bid management, and performance optimization
for the Bedrock DSP platform.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from ..base_specialist import BaseSpecialistAgent
from ...utils.observability import trace_agent

logger = logging.getLogger(__name__)


class OptimizerAgent(BaseSpecialistAgent):
    """
    Optimizer Agent for performance optimization.
    
    Responsibilities:
    - Budget allocation and reallocation
    - Bid price adjustments
    - Line item pause/resume
    - Creative rotation optimization
    - Performance improvement strategies
    """

    def __init__(self, config_path: str = None):
        """
        Initialize the Optimizer Agent.

        Args:
            config_path: Path to agent configuration YAML file
        """
        if config_path is None:
            from pathlib import Path
            package_dir = Path(__file__).parent.parent.parent
            config_path = str(package_dir / "config" / "optimizer_agent.yaml")
        super().__init__(config_path)

    @trace_agent("optimizer")
    def analyze(self, question: str, context: str) -> Dict[str, Any]:
        """
        Perform Optimizer analysis on a question with provided context.
        
        Args:
            question: The question to analyze
            context: Relevant context from knowledge base
            
        Returns:
            Analysis result dictionary
        """
        return super().analyze(question, context)
    
    def __call__(self, state: Any) -> str:
        """
        Execute Optimizer analysis (required by BaseAgent interface).
        
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

