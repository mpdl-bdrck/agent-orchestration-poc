"""
Agent Utilities

Helper functions for agent selection, emoji mapping, and agent calling.
"""
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


def get_agent_emoji(agent_name: str) -> str:
    """
    Get emoji for agent type.
    
    Args:
        agent_name: Agent name (case-insensitive)
        
    Returns:
        Emoji string
    """
    # Normalize agent name
    agent_lower = agent_name.lower().strip()
    
    emoji_map = {
        'guardian': '🛡️',      # Shield for protection/oversight
        'specialist': '🔧',     # Wrench for fixing issues
        'optimizer': '🎯',      # Target for precision optimization
        'pathfinder': '🧭',     # Compass for navigation
        # Legacy agents (for backward compatibility)
        'character_analyzer': '👥',
        'theme_analyzer': '🎭',
        'causality_analyzer': '⚖️',
        'setting_analyzer': '🏗️',
        'object_analyzer': '📦',
        'force_analyzer': '💪',
        'visual_description_analyzer': '👁️',
        'narrative_style_analyzer': '📖'
    }
    
    return emoji_map.get(agent_lower, '🧠')


def select_relevant_agents(question: str) -> List[str]:
    """
    Select relevant specialist agents based on question content.
    
    Args:
        question: User question
        
    Returns:
        List of agent names
    """
    question_lower = question.lower()
    relevant_agents = []
    
    # Guardian Agent: Portfolio oversight, monitoring, anomaly detection
    guardian_keywords = [
        'portfolio', 'health', 'status', 'overview', 'summary',
        'monitoring', 'anomaly', 'alert', 'oversight', 'guardian',
        'lilly', 'eli lilly', 'tricoast', 'account', 'campaign',
        'budget', 'spend', 'pacing', 'performance'
    ]
    if any(keyword in question_lower for keyword in guardian_keywords):
        relevant_agents.append('guardian')
    
    # Specialist Agent: Technical troubleshooting, detailed analysis
    specialist_keywords = [
        'issue', 'problem', 'error', 'bug', 'fix', 'troubleshoot',
        'why', 'how', 'technical', 'detailed', 'deep dive', 'investigate'
    ]
    if any(keyword in question_lower for keyword in specialist_keywords):
        relevant_agents.append('specialist')
    
    # Optimizer Agent: Performance optimization, recommendations
    optimizer_keywords = [
        'optimize', 'improve', 'better', 'recommend', 'suggestion',
        'efficiency', 'performance', 'tune', 'adjust', 'optimization'
    ]
    if any(keyword in question_lower for keyword in optimizer_keywords):
        relevant_agents.append('optimizer')
    
    # Pathfinder Agent: Forecasting, planning, navigation
    pathfinder_keywords = [
        'forecast', 'predict', 'plan', 'strategy', 'roadmap',
        'future', 'next', 'path', 'direction', 'guide', 'navigate'
    ]
    if any(keyword in question_lower for keyword in pathfinder_keywords):
        relevant_agents.append('pathfinder')
    
    # Default to Guardian if no agents selected
    if not relevant_agents:
        relevant_agents.append('guardian')
    
    return relevant_agents


def get_simulated_portfolio_context(agent_name: str) -> str:
    """
    Get simulated portfolio context for agents without tools.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        Simulated context string
    """
    if agent_name.lower() == 'guardian':
        return """Portfolio Overview (Simulated Data):
- Account: Tricoast Media LLC (ID: 17)
- Advertiser: Eli Lilly
- Total Budget: $466,000
- Spent: $205,722 (44.15%)
- Campaigns: 28 active campaigns
- Date Range: 2025-11-01 to 2025-11-28
- Status: On track, slight pacing adjustment recommended"""
    
    return "No specific context available for this agent."

