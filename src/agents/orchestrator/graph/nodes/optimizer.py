"""
Optimizer agent node for LangGraph.

Reads instruction from state and executes Optimizer agent logic.
"""
import logging
from langchain_core.messages import AIMessage

from ..state import AgentState

logger = logging.getLogger(__name__)


def create_optimizer_node(call_specialist_agent_func, embedding_model, get_agent_func, streaming_callback=None):
    """
    Create optimizer node function.
    
    Args:
        call_specialist_agent_func: Function to call specialist agents
        embedding_model: Embedding model for semantic search
        get_agent_func: Function to get agent instances
        streaming_callback: Optional callback for streaming events
        
    Returns:
        optimizer_node function that takes state and returns updated state
    """
    def optimizer_node(state: AgentState) -> AgentState:
        """Optimizer agent as a graph node."""
        try:
            instruction = state.get("current_task_instruction", "Assist the user.")
            context_id = state.get("context_id", "")
            
            if streaming_callback:
                try:
                    streaming_callback("agent_call", "optimizer", {"agent": "optimizer"})
                except Exception:
                    pass
            
            response = call_specialist_agent_func(
                agent_name="optimizer",
                question=instruction,
                context_id=context_id,
                embedding_model=embedding_model,
                agent_registry_get_agent=get_agent_func,
                conversation_history=None
            )
            
            if not response:
                response = "No response from Optimizer agent."
            
            if streaming_callback:
                try:
                    streaming_callback("agent_response", response, {"agent": "optimizer"})
                except Exception:
                    pass
            
            return {
                "messages": [AIMessage(content=response)],
                "agent_responses": state.get("agent_responses", []) + [{"agent": "optimizer", "response": response}],
                "current_task_instruction": ""
            }
            
        except Exception as e:
            logger.error(f"Optimizer node error: {e}", exc_info=True)
            error_response = f"Error in Optimizer agent: {str(e)}"
            return {
                "messages": [AIMessage(content=error_response)],
                "agent_responses": state.get("agent_responses", []) + [{"agent": "optimizer", "response": error_response}],
                "current_task_instruction": ""
            }
    
    return optimizer_node

