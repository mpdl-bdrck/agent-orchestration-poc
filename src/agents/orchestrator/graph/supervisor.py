"""
Supervisor node for LangGraph agent orchestration.

The supervisor acts as a router, making decisions about which agent should
handle the current request and translating user intent into clear instructions.
"""
import logging
from typing import Literal
try:
    from pydantic import BaseModel, Field
except ImportError:
    from pydantic.v1 import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from .state import AgentState

logger = logging.getLogger(__name__)


class RouteDecision(BaseModel):
    """Structured routing decision from supervisor."""
    next: Literal["semantic_search", "guardian", "specialist", "optimizer", "pathfinder", "FINISH"] = Field(
        description="The next node to route to: semantic_search for knowledge base queries, agent names for specialist routing, or FINISH if done."
    )
    instructions: str = Field(
        description="Specific, imperative instruction for the worker. "
                    "Translate user intent into direct command. "
                    "Example: User says 'Have agents say hi' -> 'Introduce yourself and your role.'"
    )
    reasoning: str = Field(
        description="Why this routing decision was made."
    )


def create_supervisor_node(llm, system_prompt: str, orchestrator_prompt: str = None, streaming_callback=None):
    """
    Create supervisor node function with LLM and system prompt.
    
    Args:
        llm: LLM instance for making routing decisions
        system_prompt: System prompt for the supervisor (routing decisions)
        orchestrator_prompt: System prompt for the orchestrator (used for FINISH responses)
        streaming_callback: Optional callback for streaming events
        
    Returns:
        supervisor_node function that takes state and returns updated state
    """
    def supervisor_node(state: AgentState) -> AgentState:
        """
        Router that decides next agent or FINISH.
        
        Reads the current conversation state and makes a routing decision,
        translating user intent into clear instructions for the selected agent.
        """
        try:
            # Prioritize user_question from state (original question) over messages
            # Messages may contain AI responses, so we want the original user question
            user_message = state.get("user_question", "")
            
            # Fallback: extract from messages if user_question not set
            if not user_message:
                for msg in reversed(state["messages"]):
                    if hasattr(msg, 'content') and msg.content:
                        # Only use HumanMessage, not AI responses
                        msg_type = type(msg).__name__
                        if msg_type == 'HumanMessage':
                            user_message = msg.content
                            break
            
            # Check if we've already routed to agents
            agent_responses = state.get("agent_responses", [])
            agents_called = [r.get("agent") for r in agent_responses]
            
            # Build context for routing decision
            context_parts = [f"User question: {user_message}"]
            
            if agent_responses:
                context_parts.append(f"\nPrevious responses ({len(agent_responses)} total):")
                for resp in agent_responses:
                    agent_name = resp.get("agent", "unknown")
                    response_preview = resp.get("response", "")[:200]  # Truncate for context
                    context_parts.append(f"- {agent_name}: {response_preview}...")
            
            # Build messages for LLM routing decision
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"""{'\n'.join(context_parts)}

Make a routing decision:
- If semantic_search has responded and the question is answered → FINISH
- If agents have responded and the question is answered → FINISH
- If the question requires specialized agent expertise → route to appropriate agent
- If the question is a simple fact you know → FINISH
- Otherwise → route to semantic_search or appropriate agent

Agents called so far: {', '.join(agents_called) if agents_called else 'none'}""")
            ]
            
            # Use structured output for routing decision
            structured_llm = llm.with_structured_output(RouteDecision)
            decision = structured_llm.invoke(messages)
            
            # Emit streaming event if callback available
            if streaming_callback:
                try:
                    streaming_callback("reasoning", decision.reasoning, {"routing": decision.next})
                except Exception as e:
                    logger.debug(f"Streaming callback error: {e}")
            
            # If routing to FINISH, generate a response first
            if decision.next == "FINISH":
                # Use orchestrator prompt for responses (has introduction info), fallback to supervisor prompt
                response_system_prompt = orchestrator_prompt if orchestrator_prompt else system_prompt
                
                # Generate actual response for simple questions
                response_prompt = f"""Based on the user's question and your routing decision, provide a helpful, direct answer.

User question: {user_message}
Your reasoning: {decision.reasoning}

Provide a clear, concise answer to the user's question."""
                
                response_messages = [
                    SystemMessage(content=response_system_prompt),
                    HumanMessage(content=response_prompt)
                ]
                
                response = llm.invoke(response_messages)
                response_content = response.content if hasattr(response, 'content') else str(response)
                
                # Emit response via streaming callback
                if streaming_callback:
                    try:
                        streaming_callback("agent_response", response_content, {"agent": "orchestrator"})
                    except Exception as e:
                        logger.debug(f"Streaming callback error: {e}")
                
                # Add response to state
                from langchain_core.messages import AIMessage
                return {
                    "next": "FINISH",
                    "current_task_instruction": "",
                    "messages": [AIMessage(content=response_content)],
                    "agent_responses": state.get("agent_responses", []) + [{"agent": "orchestrator", "response": response_content}]
                }
            
            # Use the instructions from the LLM's routing decision
            instructions = decision.instructions
            
            # Update state with routing decision
            return {
                "next": decision.next,
                "current_task_instruction": instructions if decision.next != "FINISH" else "",
                "messages": []  # Supervisor doesn't add messages, agents do
            }
            
        except Exception as e:
            logger.error(f"Supervisor node error: {e}", exc_info=True)
            # Default to FINISH on error
            return {
                "next": "FINISH",
                "current_task_instruction": "",
                "messages": []
            }
    
    return supervisor_node

