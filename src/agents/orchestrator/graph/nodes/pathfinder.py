"""
Pathfinder agent node for LangGraph.

Reads instruction from state and executes Pathfinder agent logic.
"""
import logging
from langchain_core.messages import AIMessage

from ..state import AgentState

logger = logging.getLogger(__name__)


def create_pathfinder_node(call_specialist_agent_func, embedding_model, get_agent_func, streaming_callback=None):
    """
    Create pathfinder node function.
    
    Args:
        call_specialist_agent_func: Function to call specialist agents
        embedding_model: Embedding model for semantic search
        get_agent_func: Function to get agent instances
        streaming_callback: Optional callback for streaming events
        
    Returns:
        pathfinder_node function that takes state and returns updated state
    """
    def pathfinder_node(state: AgentState) -> AgentState:
        """Pathfinder agent as a graph node."""
        try:
            instruction = state.get("current_task_instruction", "Assist the user.")
            context_id = state.get("context_id", "")
            
            if streaming_callback:
                try:
                    streaming_callback("agent_call", "pathfinder", {"agent": "pathfinder"})
                except Exception:
                    pass
            
            response = call_specialist_agent_func(
                agent_name="pathfinder",
                question=instruction,
                context_id=context_id,
                embedding_model=embedding_model,
                agent_registry_get_agent=get_agent_func,
                conversation_history=None
            )
            
            if not response:
                response = "No response from Pathfinder agent."
            
            if streaming_callback:
                try:
                    streaming_callback("agent_response", response, {"agent": "pathfinder"})
                except Exception:
                    pass
            
            return {
                "messages": [AIMessage(content=response)],
                "agent_responses": state.get("agent_responses", []) + [{"agent": "pathfinder", "response": response}],
                "current_task_instruction": ""
            }
            
        except Exception as e:
            logger.error(f"Pathfinder node error: {e}", exc_info=True)
            error_response = f"Error in Pathfinder agent: {str(e)}"
            return {
                "messages": [AIMessage(content=error_response)],
                "agent_responses": state.get("agent_responses", []) + [{"agent": "pathfinder", "response": error_response}],
                "current_task_instruction": ""
            }
    
    return pathfinder_node

