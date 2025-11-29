"""Base class for specialist agents in Agentic CRAG Launchpad."""

from typing import Dict, Any, Optional
import logging

from ..core.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class BaseSpecialistAgent(BaseAgent):
    """
    Base class for specialist agents that perform deep analysis.
    
    Specialist agents inherit from BaseAgent and provide domain-specific
    analysis capabilities. They are called by the OrchestratorAgent for
    complex queries requiring specialized expertise.
    """

    def __init__(self, config_path: str):
        """Initialize specialist agent with configuration."""
        super().__init__(config_path)
        self.specialist_type = self.__class__.__name__.replace('Agent', '').lower()

    def analyze(self, question: str, context: str) -> Dict[str, Any]:
        """
        Perform specialist analysis on a question with provided context.
        
        Args:
            question: The question to analyze
            context: Relevant context from knowledge base
            
        Returns:
            Analysis result dictionary
        """
        # Build prompt with context
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": self._build_user_prompt(question, context)}
        ]
        
        # Get LLM response
        response = self.llm.invoke(messages)
        answer = response.content if hasattr(response, 'content') else str(response)
        
        return {
            'answer': answer,
            'specialist_type': self.specialist_type,
            'question': question
        }

    def _get_system_prompt(self) -> str:
        """Get system prompt for this specialist."""
        # Default implementation - should be overridden
        return self.config.prompts.get('system', '')

    def _build_user_prompt(self, question: str, context: str) -> str:
        """Build user prompt with question and context."""
        # Default implementation - should be overridden
        user_template = self.config.prompts.get('user', '')
        return user_template.format(question=question, context=context)

