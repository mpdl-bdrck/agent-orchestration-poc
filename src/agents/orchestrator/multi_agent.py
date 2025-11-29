"""
Multi-Agent Discussion Handling

Functions for orchestrating multi-agent discussions.
"""
import logging
from typing import List, Dict
from .agent_utils import select_relevant_agents, get_agent_emoji
from .synthesis import synthesize_agent_responses
from .agent_calling import call_specialist_agent
from .formatting import format_tool_usage

logger = logging.getLogger(__name__)


def should_use_multi_agent_discussion(question: str) -> bool:
    """
    Determine if a question warrants multi-agent discussion.

    Multi-agent discussion is appropriate for:
    - Questions matching Bedrock platform domain keywords (always use agents)
    - Complex questions requiring multiple perspectives
    - Questions with "how", "why", "analyze" requiring deep analysis

    Args:
        question: User's question

    Returns:
        True if multi-agent discussion should be used
    """
    question_lower = question.lower()

    # Exclusion patterns - don't use multi-agent for simple corrections/clarifications
    exclusion_patterns = [
        'you got to be kidding',
        'you are kidding',
        'just',
        'simply',
        'only',
        'that\'s wrong',
        'that is wrong',
        'no that\'s',
        'actually',
        'correction:',
        'i meant'
    ]
    
    # If question contains exclusion patterns, prefer tool-based approach
    if any(pattern in question_lower for pattern in exclusion_patterns):
        return False

    # PRIORITY 1: If domain-specific keywords are detected, always use agents
    relevant_agents = select_relevant_agents(question)
    if relevant_agents:
        return True  # Always use agents when domain matches

    # PRIORITY 2: Keywords that suggest deep analysis needed
    deep_analysis_keywords = [
        'analyze', 'analysis', 'how does', 'how is', 'why', 'explain how',
        'relationship between', 'connection', 'how are',
        'comprehensive', 'detailed analysis', 'deep dive',
        'compare', 'contrast', 'difference between'
    ]

    # Check for analysis keywords
    if any(keyword in question_lower for keyword in deep_analysis_keywords):
        return True

    # Check question length (longer questions often need deeper analysis)
    if len(question.split()) > 12:
        # Additional check: if it's just a long correction, don't use multi-agent
        if not any(excl in question_lower for excl in exclusion_patterns):
            return True

    return False


def handle_multi_agent_discussion(
    question: str,
    context_id: str,
    embedding_model,
    agent_registry_get_agent,
    llm,
    emit_streaming_event
) -> tuple[str, List[Dict]]:
    """
    Handle a question using direct agent orchestration.

    Args:
        question: User's question requiring multi-agent analysis
        context_id: Knowledge base context ID
        embedding_model: Embedding model for semantic search
        agent_registry_get_agent: Function to get agent instance
        llm: LLM instance for synthesis
        emit_streaming_event: Function to emit streaming events
        format_tool_usage: Function to format tool usage display

    Returns:
        Formatted discussion results
    """
    try:
        # Determine which agents to involve based on question content
        relevant_agents = select_relevant_agents(question)

        if not relevant_agents:
            return None, []  # Signal to use tool-based approach

        # Orchestrate direct agent calls
        agent_responses = []
        last_agent_calls = []
        for agent_name in relevant_agents:
            try:
                emit_streaming_event("agent_call", f"Calling {agent_name} agent...", {'agent': agent_name})
                agent_response = call_specialist_agent(
                    agent_name=agent_name,
                    question=question,
                    context_id=context_id,
                    embedding_model=embedding_model,
                    agent_registry_get_agent=agent_registry_get_agent
                )
                if agent_response:
                    agent_responses.append({
                        'agent': agent_name,
                        'response': agent_response
                    })
                    last_agent_calls.append({
                        'agent': agent_name,
                        'response': agent_response
                    })
                    emit_streaming_event("agent_response", f"{agent_name} completed", {'agent': agent_name})
            except Exception as e:
                logger.warning(f"Agent {agent_name} failed: {e}")
                emit_streaming_event("status", f"⚠️ {agent_name} failed: {str(e)}")
                continue

        if not agent_responses:
            return None, []  # Signal to use tool-based approach

        # Show orchestrator's decision-making process
        agent_names_display = [agent.replace('_', ' ').title() for agent in relevant_agents]
        agent_emojis = [get_agent_emoji(agent) for agent in relevant_agents]
        agent_list = [f"{emoji} {name}" for emoji, name in zip(agent_emojis, agent_names_display)]
        
        orchestrator_decision = f"""
🧠 **Orchestrator Decision:**

Based on the question analysis, I'm engaging the following specialist agents:
{', '.join(agent_list)}

Reasoning:
- Question domain matches: {', '.join(agent_names_display)}
- These agents will provide specialized analysis from their respective domains
- Their responses will be synthesized into a comprehensive answer

---
        """.strip()

        # Synthesize responses into coherent answer
        synthesized_response = synthesize_agent_responses(question, agent_responses, llm)

        # Combine orchestrator decision with synthesized response
        full_response = f"{orchestrator_decision}\n\n{synthesized_response}"

        # Add tool usage indicator (semantic search was used by agents, plus agent calls)
        tool_display = format_tool_usage(['semantic_search'], last_agent_calls)
        if tool_display:
            full_response = f"{full_response}\n\n{tool_display}"

        return full_response, last_agent_calls

    except Exception as e:
        logger.error(f"Multi-agent discussion failed: {e}, falling back to tool-based approach")
        return None, []  # Signal to use tool-based approach

