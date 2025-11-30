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
            
            # --- DYNAMIC TOOL BINDING (Tool Holster Pattern) ---
            # Trust the supervisor's explicit instruction - if it explicitly forbids tools,
            # holster them. Otherwise, let the agent decide (with tools available).
            # The supervisor will include directives like "STRICTLY FORBIDDEN from using tools"
            # or "text only" when tools should not be used.
            instruction_lower = instruction.lower()
            explicit_no_tools_directives = [
                "strictly forbidden from using tools",
                "do not use tools",
                "text only",
                "speak text only",
                "forbidden from using",
                "must not use tools"
            ]
            should_holster_tools = any(directive in instruction_lower for directive in explicit_no_tools_directives)
            
            logger.info(f"Guardian node - Instruction: '{instruction}' | Holster tools: {should_holster_tools}")
            if should_holster_tools:
                logger.info(f"✅ Tool Holster ACTIVE - tools will be disabled")
            else:
                logger.info(f"⚠️  Tool Holster INACTIVE - tools will be available")
            
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
            def guardian_streaming_wrapper(event_type, message, data=None):
                if data is None:
                    data = {}
                data["agent"] = "guardian"
                if streaming_callback:
                    streaming_callback(event_type, message, data)
            
            # Get agent instance and set streaming callback
            agent = get_agent_func("guardian")
            if agent and hasattr(agent, 'set_streaming_callback'):
                agent.set_streaming_callback(guardian_streaming_wrapper)
            
            # --- TOOL HOLSTER LOGIC ---
            # If supervisor explicitly forbade tools, run WITHOUT tools
            # Otherwise, run WITH tools (normal path - agent decides)
            if should_holster_tools:
                logger.info("Guardian: Running WITHOUT tools (Tool Holster - supervisor explicitly forbade tools)")
                # Run without tools using direct agent method
                if agent and hasattr(agent, 'analyze_without_tools'):
                    # For introductions, we don't need knowledge base context
                    result = agent.analyze_without_tools(
                        question=question_for_guardian,
                        context="No specific context needed for introduction.",
                        supervisor_instruction=instruction
                    )
                    response = result.get('answer', '') if isinstance(result, dict) else str(result)
                else:
                    # Fallback: call via standard path but force use_tools=False
                    response = call_specialist_agent_func(
                        agent_name="guardian",
                        question=question_for_guardian,
                        context_id=context_id,
                        embedding_model=embedding_model,
                        agent_registry_get_agent=get_agent_func,
                        conversation_history=conversation_history if conversation_history else None,
                        supervisor_instruction=instruction
                    )
            else:
                logger.info("Guardian: Running WITH tools (data request detected)")
                # Normal path: run WITH tools
            response = call_specialist_agent_func(
                agent_name="guardian",
                question=question_for_guardian,  # Pass original question for context
                context_id=context_id,
                embedding_model=embedding_model,
                agent_registry_get_agent=get_agent_func,
                conversation_history=conversation_history if conversation_history else None,
                supervisor_instruction=instruction  # Pass supervisor instruction from state
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

