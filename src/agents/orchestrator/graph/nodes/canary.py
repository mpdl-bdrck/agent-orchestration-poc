"""
Canary agent node for LangGraph.

Minimal test node for isolating agent loop issues.
"""
import logging
from langchain_core.messages import AIMessage

from ..state import AgentState

logger = logging.getLogger(__name__)


def create_canary_node(call_specialist_agent_func, embedding_model, get_agent_func, streaming_callback=None):
    """
    Create canary node function.

    Args:
        call_specialist_agent_func: Function to call specialist agents
        embedding_model: Embedding model for semantic search
        get_agent_func: Function to get agent instances
        streaming_callback: Optional callback for streaming events

    Returns:
        canary_node function that takes state and returns updated state
    """
    def canary_node(state: AgentState) -> AgentState:
        """Canary agent as a graph node."""
        try:
            # Read instruction from state (translated instruction)
            instruction = state.get("current_task_instruction", "Test the canary.")
            context_id = state.get("context_id", "")
            user_question = state.get("user_question", "")

            # For Canary, use the instruction directly
            question_for_canary = instruction

            # Convert state messages to conversation history format
            conversation_history = []
            for msg in state.get("messages", []):
                if hasattr(msg, 'content') and msg.content:
                    # Check message type using LangChain message class names
                    msg_type = type(msg).__name__
                    if msg_type == 'HumanMessage':
                        conversation_history.append({'role': 'user', 'content': msg.content})
                    elif msg_type == 'AIMessage':
                        conversation_history.append({'role': 'assistant', 'content': msg.content})

            logger.info(f"Executing Canary agent with instruction: {instruction}")

            # Emit streaming event
            if streaming_callback:
                try:
                    streaming_callback("agent_call", "canary", {"agent": "canary"})
                except Exception as e:
                    logger.debug(f"Streaming callback error: {e}")

            # Set streaming callback on Canary agent so it can emit responses
            def canary_streaming_wrapper(event_type, message, data=None):
                if data is None:
                    data = {}
                data["agent"] = "canary"
                if streaming_callback:
                    streaming_callback(event_type, message, data)

            # Get agent instance and set streaming callback
            agent = get_agent_func("canary")
            if agent and hasattr(agent, 'set_streaming_callback'):
                agent.set_streaming_callback(canary_streaming_wrapper)

            # Call specialist agent function
            result = call_specialist_agent_func(
                agent_name="canary",
                question=question_for_canary,
                context_id=context_id,
                embedding_model=embedding_model,
                agent_registry_get_agent=get_agent_func,
                conversation_history=conversation_history
            )

            # Handle result - call_specialist_agent returns a string, not a dict
            if result is None:
                response_text = "CANARY ERROR: No response from agent"
            elif isinstance(result, str):
                response_text = result
            elif isinstance(result, dict):
                response_text = result.get("response", str(result))
            else:
                response_text = str(result)

            if not response_text:
                response_text = "No response from Canary agent."

            # Update state with result - add to agent_responses only
            # NOTE: Canary agent emits via its own streaming_callback
            # Supervisor can see the response via agent_responses, no need to add to messages
            return {
                "agent_responses": state.get("agent_responses", []) + [
                    {
                        "agent": "canary",
                        "response": response_text,
                        "context_id": context_id
                    }
                ],
                "current_task_instruction": "",  # Clear after processing
                "next": ""  # Clear next to return to supervisor
            }

        except Exception as e:
            logger.error(f"Canary agent execution failed: {e}", exc_info=True)

            # Return error state
            new_state = state.copy()
            new_state["agent_responses"] = state.get("agent_responses", []) + [
                {
                    "agent": "canary",
                    "response": f"CANARY ERROR: {str(e)}",
                    "context_id": state.get("context_id", "")
                }
            ]
            new_state["next"] = ""

            return new_state

    return canary_node
