"""
Agent Calling Utilities

Functions for calling specialist agents.
"""
import logging
from typing import Optional, List, Dict
from ...core.search.semantic_search import search_knowledge_base
from .agent_utils import get_simulated_portfolio_context
from .prompts import build_agent_qa_prompt

logger = logging.getLogger(__name__)


def call_specialist_agent(
    agent_name: str,
    question: str,
    context_id: str,
    embedding_model,
    agent_registry_get_agent,
    conversation_history: Optional[List[Dict]] = None,
    supervisor_instruction: Optional[str] = None
) -> Optional[str]:
    """
    Call a specialist agent for Q&A analysis.

    Uses agent's analyze() method which supports tool calling.
    For agents with tools (like Guardian), skips simulated data.

    Args:
        agent_name: Name of the agent to call
        question: The question to analyze
        context_id: Knowledge base context ID
        embedding_model: Embedding model for semantic search
        agent_registry_get_agent: Function to get agent instance
        conversation_history: Optional recent conversation history for context

    Returns:
        Agent's response or None if failed
    """
    try:
        # Get the agent instance
        agent = agent_registry_get_agent(agent_name)
        if hasattr(agent, 'tools'):
            pass  # Agent has tools

        # Set knowledge base context
        if hasattr(agent, 'set_context'):
            agent.set_context(context_id)
        
        # Set streaming callback if agent supports it (for Guardian agent)
        # The streaming callback is passed via the graph's streaming_callback parameter
        # We need to get it from the calling context - for now, agents will emit via their own callbacks
        # The graph node will handle streaming events

        # Get semantic context for the question
        query_embedding = embedding_model.embed_query(question)
        semantic_results = search_knowledge_base(
            query_text=question,
            query_embedding=query_embedding,
            chunk_types=None,
            match_limit=10,
            context_id=context_id
        )

        # Format semantic results as knowledge base context
        kb_context = ""
        if semantic_results:
            kb_context = format_semantic_results_as_context(semantic_results, agent_name)
        else:
            logger.debug(f"No semantic context found for agent {agent_name}")

        # Build enhanced context with conversation history if available
        context_parts = []
        
        # Add conversation history context if available
        if conversation_history:
            recent_context = []
            for entry in conversation_history[-4:]:  # Last 2 exchanges (4 messages)
                role = entry.get('role', '')
                content = entry.get('content', '')
                if role == 'user':
                    recent_context.append(f"User: {content}")
                elif role == 'assistant':
                    recent_context.append(f"Assistant: {content}")
            
            if recent_context:
                context_parts.append("RECENT CONVERSATION CONTEXT:")
                context_parts.append("\n".join(recent_context))
                context_parts.append("")
                context_parts.append("Use this conversation history to understand references like 'this request', 'that question', 'him', etc.")
                context_parts.append("")
        
        # For Guardian agent specifically, add note about original question vs instruction
        # Guardian needs the original question for keyword detection in direct tool call path
        if agent_name == "guardian" and conversation_history:
            context_parts.append("NOTE: The question parameter contains the original user question.")
            context_parts.append("Use it for keyword detection (e.g., 'portfolio', 'lilly', 'eli lilly') to trigger direct tool calls.")
            context_parts.append("")

        # Check if agent has tools (like Guardian with portfolio pacing tool)
        agent_has_tools = hasattr(agent, 'tools') and agent.tools and len(agent.tools) > 0
        
        if agent_has_tools:
            # Agent has tools - let it use them, provide minimal context
            # Don't inject simulated data as it will interfere with tool usage
            if kb_context:
                context_parts.append(kb_context)
            else:
                context_parts.append("Use your tools to analyze the request.")
            context = "\n".join(context_parts).strip()
            logger.info(f"Agent {agent_name} has {len(agent.tools)} tool(s) - using tool-based analysis")
        else:
            # Agent doesn't have tools - use simulated data for demonstration
            simulated_data = get_simulated_portfolio_context(agent_name)
            context_parts.append(simulated_data)
            context_parts.append("")
            context_parts.append("---")
            context_parts.append("")
            context_parts.append("KNOWLEDGE BASE PROCEDURES AND BEST PRACTICES:")
            context_parts.append(kb_context if kb_context else "No specific KB context found, but agent can provide guidance based on general platform knowledge.")
            context = "\n".join(context_parts).strip()
            logger.info(f"Agent {agent_name} has no tools - using simulated data")

        # Call agent's analyze() method (which supports tool calling)
        # Pass supervisor instruction if available (for Guardian agent to follow supervisor guidance)
        if hasattr(agent, 'analyze'):
            # Check if analyze accepts supervisor_instruction parameter
            import inspect
            sig = inspect.signature(agent.analyze)
            if 'supervisor_instruction' in sig.parameters:
                result = agent.analyze(question, context, supervisor_instruction=supervisor_instruction)
            else:
                result = agent.analyze(question, context)
        else:
            result = agent.analyze(question, context)
        
        # Extract answer from result
        if isinstance(result, dict):
            answer = result.get('answer', '')
            # Log tool usage if available
            if result.get('tool_calls'):
                logger.info(f"Agent {agent_name} used {len(result.get('tool_calls', []))} tool(s)")
        else:
            answer = str(result)

        logger.info(f"Agent {agent_name} provided response")
        return answer

    except Exception as e:
        logger.warning(f"Failed to call agent {agent_name}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


def format_semantic_results_as_context(results: List[Dict], agent_type: str) -> str:
    """Format semantic search results as knowledge base context for agent analysis."""
    context_parts = []
    
    for result in results:
        chunk_type = result.get('chunk_type', 'unknown')
        chunk_title = result.get('chunk_title', 'Untitled')
        chunk_content = result.get('chunk_content', '')
        relevance = result.get('relevance_score', 0)
        
        context_parts.append(f"### {chunk_title} ({chunk_type}, relevance: {relevance:.2f})\n{chunk_content}\n")
    
    return "\n".join(context_parts)

