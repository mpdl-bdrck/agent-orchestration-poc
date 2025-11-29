"""
Response Formatting

Functions for formatting tool usage and other display elements.
"""
from typing import List, Dict
from .agent_utils import get_agent_emoji


def format_tool_usage(tool_names: List[str], last_agent_calls: List[Dict] = None) -> str:
    """
    Format tool usage for display, including agent calls.

    Args:
        tool_names: List of tool names used
        last_agent_calls: List of agent calls made

    Returns:
        Formatted tool usage string
    """
    parts = []
    
    # Show semantic search tool
    if 'semantic_search' in tool_names:
        parts.append("🔍 Semantic Search: semantic_search")
    
    # Show specialist agents if they were called
    if last_agent_calls:
        agent_display_parts = []
        for agent_call in last_agent_calls:
            agent_name = agent_call.get('agent', 'unknown')
            # Ensure lowercase for emoji lookup (agent_name might be capitalized)
            agent_name_lower = agent_name.lower() if agent_name else 'unknown'
            emoji = get_agent_emoji(agent_name_lower)
            display_name = agent_name.replace('_', ' ').title()
            agent_display_parts.append(f"{emoji} {display_name}")
        
        if agent_display_parts:
            # Use agent-specific emojis (already included in agent_display_parts)
            parts.append(f"**Specialist Agents**: {' | '.join(agent_display_parts)}")
    
    # Any other tools (shouldn't happen, but handle gracefully)
    other_tools = [t for t in tool_names if t != 'semantic_search']
    if other_tools:
        parts.append(f"🔧 Other: {', '.join(other_tools)}")

    if parts:
        return f"🔧 **Tools Used**: {' | '.join(parts)}"
    return ""

