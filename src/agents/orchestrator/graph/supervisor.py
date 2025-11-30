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
    next: Literal["semantic_search", "guardian", "specialist", "optimizer", "pathfinder", "canary", "FINISH"] = Field(
        description="The next node to route to: semantic_search (tool/service) for knowledge base queries, agent names for specialist routing, canary for testing, or FINISH if done."
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
            # Extract agent names (only actual agents, not tools/services)
            agents_called = []
            for r in agent_responses:
                agent_name = r.get("agent")  # Only look for "agent" key (tools don't belong in agent_responses)
                if agent_name:  # Only add non-None values
                    agents_called.append(agent_name)
            
            # Build context for routing decision
            context_parts = [f"User question: {user_message}"]
            
            # Check messages for semantic_search results (tools add to messages, not agent_responses)
            # semantic_search adds AIMessage to messages, so check for AIMessages that indicate semantic_search has been called
            messages = state.get("messages", [])
            # Since agents don't add to messages anymore (they use agent_responses),
            # any AIMessage in messages is from semantic_search tool
            from langchain_core.messages import AIMessage
            semantic_search_called = any(
                isinstance(msg, AIMessage) and msg.content 
                for msg in messages
            )
            
            if agent_responses:
                context_parts.append(f"\nPrevious agent responses ({len(agent_responses)} total):")
                for resp in agent_responses:
                    agent_name = resp.get("agent", "unknown")
                    response_preview = resp.get("response", "")[:200]  # Truncate for context
                    context_parts.append(f"- {agent_name} (agent): {response_preview}...")
            
            if semantic_search_called:
                context_parts.append(f"\nNote: semantic_search tool has been called (results in conversation history).")
            
            # Build messages for LLM routing decision
            # Add explicit warning if agents have already responded
            routing_guidance = ""
            if agents_called:
                routing_guidance = f"\n\n⚠️ CRITICAL: The following agents have already responded: {', '.join(agents_called)}\n"
                routing_guidance += "If the question is FULLY ANSWERED by these responses, you MUST route to FINISH.\n"
                routing_guidance += "Do NOT route back to the same agent unless the user is asking a NEW follow-up question.\n"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"""{'\n'.join(context_parts)}{routing_guidance}

Make a routing decision:
- **FIRST CHECK:** If agents have already responded AND the question is fully answered → FINISH (do NOT route back to the same agent)
- If semantic_search (tool) has responded and the question is answered → FINISH
- If the question requires specialized agent expertise AND no agent has responded yet → route to appropriate agent
- If the question is a simple fact you know → FINISH
- If an agent responded but the user is asking a NEW follow-up question → route to appropriate agent
- Otherwise → route to semantic_search (tool) or appropriate agent

**CRITICAL:** Do NOT route back to an agent that has already responded unless the user is asking a genuinely NEW question or requesting different/additional information.

IMPORTANT: semantic_search is a TOOL/SERVICE, not an agent. Refer to it as "semantic_search tool" or "semantic_search service" in your reasoning, never as "semantic_search agent".

Agents called: {', '.join(agents_called) if agents_called else 'none'}""")
            ]
            
            # Use structured output for routing decision
            structured_llm = llm.with_structured_output(RouteDecision)
            decision = structured_llm.invoke(messages)
            
            # CRITICAL FIX: Prevent routing back to same agent if they already responded
            # This prevents the tool from being called twice for the same question
            if decision.next in agents_called and decision.next != "semantic_search" and decision.next != "FINISH":
                # Agent already responded - force FINISH to prevent duplicate tool calls
                logger.warning(f"Supervisor tried to route back to {decision.next} which already responded. Forcing FINISH to prevent duplicate tool calls.")
                decision.next = "FINISH"
                decision.reasoning = f"The {decision.next} agent has already responded to this question. The question is fully answered."
                decision.instructions = ""
            
            # CRITICAL FIX: Prevent routing back to semantic_search if it's already been called
            # Check if semantic_search results are in messages (semantic_search adds AIMessage to messages)
            if decision.next == "semantic_search" and semantic_search_called:
                logger.warning("Supervisor tried to route back to semantic_search which already responded. Forcing FINISH to prevent duplicate tool calls.")
                decision.next = "FINISH"
                decision.reasoning = "The semantic_search tool has already provided results. The question is fully answered."
                decision.instructions = ""
            
            # Emit streaming event if callback available
            if streaming_callback:
                try:
                    streaming_callback("reasoning", decision.reasoning, {"routing": decision.next})
                except Exception as e:
                    logger.debug(f"Streaming callback error: {e}")
            
            # If routing to FINISH, check if any agent has already responded
            if decision.next == "FINISH":
                # Check if any agent has already responded - if so, don't generate new response
                # Filter out orchestrator responses to check for actual agent responses
                # Note: semantic_search is a tool and doesn't belong in agent_responses (results are in messages)
                actual_agent_responses = [
                    r for r in agent_responses 
                    if r.get("agent") != "orchestrator"
                ]
                has_agent_response = len(actual_agent_responses) > 0
                
                # CRITICAL: If any agent has responded, NEVER generate orchestrator response
                # This prevents duplicate responses from being shown
                if has_agent_response:
                    # Agent/service already responded - just route to FINISH, don't generate new response
                    # The orchestrator will extract and return the agent response directly
                    logger.info(f"✅ Supervisor: Routing to FINISH after agent response - SKIPPING orchestrator response generation. Agents that responded: {[r.get('agent') for r in actual_agent_responses]}")
                    # CRITICAL: Return state WITHOUT adding any messages or orchestrator response
                    # This prevents the orchestrator from echoing the agent's response
                    # DO NOT call streaming_callback - agent already streamed its response
                    # CRITICAL: MUST preserve agent_responses from state (LangGraph doesn't auto-preserve lists)
                    return {
                        "next": "FINISH",
                        "current_task_instruction": "",
                        "messages": [],  # Don't add new messages, use existing agent response
                        "agent_responses": agent_responses,  # PRESERVE existing agent responses
                        # DO NOT add orchestrator response to agent_responses - agent already responded
                    }
                
                # DOUBLE-CHECK: Make absolutely sure no agents have responded
                # This is a defensive check in case the first check somehow failed
                if len(actual_agent_responses) > 0:
                    logger.error(f"❌ BUG: Supervisor tried to generate orchestrator response but agents have responded! actual_agent_responses={actual_agent_responses}")
                    return {
                        "next": "FINISH",
                        "current_task_instruction": "",
                        "messages": [],
                        "agent_responses": agent_responses  # PRESERVE existing agent responses
                    }
                
                # Only generate response for simple questions that don't need agents or semantic_search
                # This is ONLY for questions the supervisor can answer directly (e.g., "how many agents do you have")
                # DOUBLE-CHECK: Make absolutely sure no agents have responded
                if len(actual_agent_responses) > 0:
                    # This should never happen, but defensive check
                    logger.error(f"❌ BUG: Supervisor tried to generate orchestrator response but agents have responded! actual_agent_responses={actual_agent_responses}")
                    return {
                        "next": "FINISH",
                        "current_task_instruction": "",
                        "messages": [],
                        "agent_responses": agent_responses  # PRESERVE existing agent responses
                    }
                
                logger.warning(f"⚠️ Supervisor: Generating orchestrator response - NO agents have responded yet. agent_responses={len(agent_responses)}, actual_agent_responses={len(actual_agent_responses)}")
                response_system_prompt = orchestrator_prompt if orchestrator_prompt else system_prompt
                
                # Generate actual response for simple questions
                # IMPORTANT: Do NOT include agent responses in the prompt - this prevents echoing
                # Also, do NOT include messages that might contain agent responses
                response_prompt = f"""Based on the user's question and your routing decision, provide a helpful, direct answer.

User question: {user_message}
Your reasoning: {decision.reasoning}

Provide a clear, concise answer to the user's question.

CRITICAL: This is a simple question that does NOT require any agent responses. Provide your own direct answer. Do NOT repeat or echo any agent responses."""
                
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
            # CRITICAL: MUST preserve agent_responses from state (LangGraph doesn't auto-preserve lists)
            return {
                "next": decision.next,
                "current_task_instruction": instructions if decision.next != "FINISH" else "",
                "messages": [],  # Supervisor doesn't add messages, agents do
                "agent_responses": agent_responses  # PRESERVE existing agent responses
            }
            
        except Exception as e:
            logger.error(f"Supervisor node error: {e}", exc_info=True)
            # Default to FINISH on error
            # CRITICAL: MUST preserve agent_responses from state (LangGraph doesn't auto-preserve lists)
            agent_responses = state.get("agent_responses", [])
            return {
                "next": "FINISH",
                "current_task_instruction": "",
                "messages": [],
                "agent_responses": agent_responses  # PRESERVE existing agent responses
            }
    
    return supervisor_node

