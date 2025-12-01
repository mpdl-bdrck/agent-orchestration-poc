"""
Guardian agent node for LangGraph.

Reads instruction from state and executes Guardian agent logic.
"""
import logging
from langchain_core.messages import AIMessage

from ..state import AgentState

logger = logging.getLogger(__name__)


def create_guardian_node(call_specialist_agent_func, embedding_model, get_agent_func, streaming_callback=None):
    """
    Create guardian node function.
    
    Args:
        call_specialist_agent_func: Function to call specialist agents
        embedding_model: Embedding model for semantic search
        get_agent_func: Function to get agent instances
        streaming_callback: Optional callback for streaming events
        
    Returns:
        guardian_node function that takes state and returns updated state
    """
    def guardian_node(state: AgentState) -> AgentState:
        """Guardian agent as a graph node."""
        try:
            # Read instruction from state (translated instruction)
            instruction = state.get("current_task_instruction", "Assist the user.")
            context_id = state.get("context_id", "")
            user_question = state.get("user_question", "")  # Get original user question
            
            # For Guardian agent, we need to pass the ORIGINAL user question
            # because Guardian's direct tool call path checks for keywords in the question
            # (e.g., "portfolio", "lilly", "eli lilly") to trigger portfolio pacing tool
            # The translated instruction may not contain these keywords
            question_for_guardian = user_question if user_question else instruction
            
            # Trust agent reasoning - tools are available, agent decides based on tool descriptions and prompts
            logger.info(f"Guardian node - Instruction: '{instruction}'")
            
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
            
            # Emit streaming event
            if streaming_callback:
                try:
                    streaming_callback("agent_call", "guardian", {"agent": "guardian"})
                except Exception as e:
                    logger.debug(f"Streaming callback error: {e}")
            
            # Set streaming callback on Guardian agent so it can emit responses
            # Create a wrapper callback that ensures agent name is included
            # Also check session for Chainlit callback (for tool usage messages)
            def guardian_streaming_wrapper(event_type, message, data=None):
                if data is None:
                    data = {}
                data["agent"] = "guardian"
                # Use graph callback if available
                if streaming_callback:
                    streaming_callback(event_type, message, data)
                # Also check Chainlit session callback (for tool calls from agent_loop)
                try:
                    import chainlit as cl
                    chainlit_callback = cl.user_session.get("streaming_callback")
                    if chainlit_callback:
                        chainlit_callback(event_type, message, data)
                except Exception:
                    pass  # Not in Chainlit context or callback not set
            
            # Get agent instance and set streaming callback
            agent = get_agent_func("guardian")
            if agent and hasattr(agent, 'set_streaming_callback'):
                agent.set_streaming_callback(guardian_streaming_wrapper)
            
            # Single execution path - agent decides tool usage based on prompts and tool descriptions
            response = call_specialist_agent_func(
                agent_name="guardian",
                question=question_for_guardian,
                context_id=context_id,
                embedding_model=embedding_model,
                agent_registry_get_agent=get_agent_func,
                conversation_history=conversation_history if conversation_history else None,
                supervisor_instruction=instruction
            )
            
            if not response:
                response = "No response from Guardian agent."
            
            # NOTE: Do NOT emit agent_response here - the Guardian agent already emits
            # via its own streaming_callback in guardian_agent.py. Emitting here causes duplicates.
            
            # Update state
            # CRITICAL: Set next="" to return to supervisor so it can route to FINISH
            # CRITICAL: Do NOT add to messages - agent already streamed via callback
            # Supervisor can see response via agent_responses, no need to add to messages
            # Adding to messages causes duplicate display (Guardian response + Orchestrator echo)
            return {
                # DO NOT add to messages - only add to agent_responses
                # The Canary node follows this pattern correctly - Guardian should match it
                "agent_responses": state.get("agent_responses", []) + [{"agent": "guardian", "response": response}],
                "current_task_instruction": "",  # Clear after processing
                "next": ""  # Return to supervisor for FINISH routing
            }
            
        except Exception as e:
            logger.error(f"Guardian node error: {e}", exc_info=True)
            error_response = f"Error in Guardian agent: {str(e)}"
            return {
                # DO NOT add to messages - only add to agent_responses (prevents duplicates)
                "agent_responses": state.get("agent_responses", []) + [{"agent": "guardian", "response": error_response}],
                "current_task_instruction": ""
            }
    
    return guardian_node

