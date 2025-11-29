"""
Semantic search node for LangGraph.

Executes semantic search and formats response for the orchestrator.
"""
import logging
import json
from langchain_core.messages import AIMessage

from ..state import AgentState

logger = logging.getLogger(__name__)


def create_semantic_search_node(semantic_search_func, streaming_callback=None):
    """
    Create semantic search node function.
    
    Args:
        semantic_search_func: Function to execute semantic search
        streaming_callback: Optional callback for streaming events
        
    Returns:
        semantic_search_node function that takes state and returns updated state
    """
    def semantic_search_node(state: AgentState) -> AgentState:
        """Semantic search node."""
        try:
            instruction = state.get("current_task_instruction", "")
            user_question = state.get("user_question", "")
            context_id = state.get("context_id", "")
            
            # Use instruction if available, otherwise use original question
            query = instruction if instruction else user_question
            
            # Emit streaming event
            if streaming_callback:
                try:
                    streaming_callback("agent_call", "semantic_search", {"agent": "semantic_search"})
                except Exception as e:
                    logger.debug(f"Streaming callback error: {e}")
            
            # Execute semantic search
            search_result = semantic_search_func(query=query, chunk_types=None, limit=5)
            
            # Parse JSON result
            try:
                result_data = json.loads(search_result)
                if result_data.get("error"):
                    response = f"Error: {result_data.get('error')}"
                elif result_data.get("results"):
                    # Format results into readable response
                    results = result_data.get("results", [])
                    formatted_parts = []
                    for result in results[:5]:  # Limit to top 5
                        title = result.get("chunk_title", "Untitled")
                        content = result.get("content", "")[:500]  # Truncate long content
                        formatted_parts.append(f"**{title}**\n{content}")
                    
                    response = "\n\n".join(formatted_parts)
                    if not response:
                        response = "No relevant content found in knowledge base."
                else:
                    response = result_data.get("message", "No results found.")
            except (json.JSONDecodeError, ValueError):
                response = search_result
            
            # Emit response via streaming callback
            if streaming_callback:
                try:
                    streaming_callback("agent_response", response, {"agent": "semantic_search"})
                except Exception as e:
                    logger.debug(f"Streaming callback error: {e}")
            
            # Update state
            return {
                "messages": [AIMessage(content=response)],
                "agent_responses": state.get("agent_responses", []) + [{"agent": "semantic_search", "response": response}],
                "current_task_instruction": ""  # Clear after processing
            }
            
        except Exception as e:
            logger.error(f"Semantic search node error: {e}", exc_info=True)
            error_response = f"Error in semantic search: {str(e)}"
            return {
                "messages": [AIMessage(content=error_response)],
                "agent_responses": state.get("agent_responses", []) + [{"agent": "semantic_search", "response": error_response}],
                "current_task_instruction": ""
            }
    
    return semantic_search_node

