"""
Response Synthesis

Functions for synthesizing multiple agent responses into coherent answers.
"""
import logging
from typing import List, Dict
from langchain_core.messages import SystemMessage, HumanMessage

from .agent_utils import get_agent_emoji

logger = logging.getLogger(__name__)


def synthesize_agent_responses(
    question: str,
    agent_responses: List[Dict],
    llm
) -> str:
    """
    Synthesize multiple agent responses into a coherent answer.
    
    Now includes individual agent responses for transparency.

    Args:
        question: Original user question
        agent_responses: List of {'agent': name, 'response': text} dicts
        llm: LLM instance for synthesis

    Returns:
        Synthesized response with individual agent outputs
    """
    if len(agent_responses) == 1:
        # Single agent response - show it clearly with correct emoji
        agent_info = agent_responses[0]
        emoji = get_agent_emoji(agent_info['agent'])
        agent_name = agent_info['agent'].replace('_', ' ').title()
        return f"{emoji} **{agent_name} Analysis:**\n\n{agent_info['response']}"

    # Multiple agent responses - show individual responses then synthesize
    response_parts = []
    
    # First, show individual agent responses with emojis
    response_parts.append("**Specialist Agent Responses:**\n\n")
    
    for i, agent_resp in enumerate(agent_responses, 1):
        agent_name = agent_resp['agent'].replace('_', ' ').title()
        agent_response = agent_resp['response'].strip()
        emoji = get_agent_emoji(agent_resp['agent'])
        
        response_parts.append(f"**{i}. {emoji} {agent_name}:**\n\n")
        # Show full response (don't truncate - users want to see agent analysis)
        response_parts.append(f"{agent_response}\n\n")
    
    response_parts.append("---\n\n")
    
    # Now synthesize them
    response_parts.append("🧠 **Orchestrator Synthesis:**\n\n")
    
    synthesis_prompt = f"""
Please synthesize the following specialist analyses into a coherent answer for this question:

Question: {question}

Agent Analyses:
"""

    for i, agent_resp in enumerate(agent_responses, 1):
        synthesis_prompt += f"\n{i}. {agent_resp['agent'].replace('_', ' ').title()}:\n{agent_resp['response'][:500]}..."

    synthesis_prompt += "\n\nProvide a unified, well-structured answer that combines insights from all these analyses."

    try:
        # Use the LLM to synthesize responses
        messages = [
            SystemMessage(content="You are a synthesis expert. Combine multiple specialist analyses into coherent, insightful answers."),
            HumanMessage(content=synthesis_prompt)
        ]

        response = llm.invoke(messages)
        synthesized_answer = response.content

        response_parts.append(synthesized_answer)

        # Add attribution
        agent_names = [resp['agent'].replace('_', ' ') for resp in agent_responses]
        attribution = f"\n\n*Analysis synthesized from: {', '.join(agent_names)}*"
        response_parts.append(attribution)

        return "\n".join(response_parts)

    except Exception as e:
        logger.warning(f"Synthesis failed: {e}, falling back to first response")
        # Fallback: return the first agent's response
        agent_info = agent_responses[0]
        emoji = get_agent_emoji(agent_info['agent'])
        agent_name = agent_info['agent'].replace('_', ' ').title()
        return f"{emoji} **{agent_name} Analysis:**\n\n{agent_info['response']}"

