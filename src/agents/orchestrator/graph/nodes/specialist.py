"""
Specialist agent node for LangGraph.

Reads instruction from state and executes Specialist agent logic.
"""
import logging
from langchain_core.messages import AIMessage

from ..state import AgentState

logger = logging.getLogger(__name__)


def create_specialist_node(call_specialist_agent_func, embedding_model, get_agent_func, streaming_callback=None):
    """
    Create specialist node function.
    
    Args:
        call_specialist_agent_func: Function to call specialist agents
        embedding_model: Embedding model for semantic search
        get_agent_func: Function to get agent instances
        streaming_callback: Optional callback for streaming events
        
    Returns:
        specialist_node function that takes state and returns updated state
    """
    def specialist_node(state: AgentState) -> AgentState:
        """Specialist agent as a graph node."""
        try:
            instruction = state.get("current_task_instruction", "Assist the user.")
            context_id = state.get("context_id", "")
            
            if streaming_callback:
                try:
                    streaming_callback("agent_call", "specialist", {"agent": "specialist"})
                except Exception:
                    pass
            
            response = call_specialist_agent_func(
                agent_name="specialist",
                question=instruction,
                context_id=context_id,
                embedding_model=embedding_model,
                agent_registry_get_agent=get_agent_func,
                conversation_history=None
            )
            
            if not response:
                response = "No response from Specialist agent."
            
            if streaming_callback:
                try:
                    streaming_callback("agent_response", response, {"agent": "specialist"})
                except Exception:
                    pass
            
            return {
                "messages": [AIMessage(content=response)],
                "agent_responses": state.get("agent_responses", []) + [{"agent": "specialist", "response": response}],
                "current_task_instruction": ""
            }
            
        except Exception as e:
            logger.error(f"Specialist node error: {e}", exc_info=True)
            error_response = f"Error in Specialist agent: {str(e)}"
            return {
                "messages": [AIMessage(content=error_response)],
                "agent_responses": state.get("agent_responses", []) + [{"agent": "specialist", "response": error_response}],
                "current_task_instruction": ""
            }
    
    return specialist_node

