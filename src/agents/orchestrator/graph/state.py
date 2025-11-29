"""
State schema for LangGraph agent orchestration.

Defines the shared state that flows through the graph, including conversation
history, routing decisions, and agent responses.
"""
from typing import TypedDict, Annotated, List, Dict, Any
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """
    Shared state for LangGraph agent orchestration.
    
    This state is passed between nodes in the graph and accumulates information
    as the graph executes. The `current_task_instruction` field is critical - it
    prevents the recursive intent bug by providing translated instructions to
    agents instead of the raw user prompt.
    """
    
    # Conversation history (append-only)
    # Messages are accumulated as the graph executes
    messages: Annotated[List[BaseMessage], operator.add]
    
    # Routing decision from supervisor
    # Values: "guardian" | "specialist" | "optimizer" | "pathfinder" | "FINISH"
    next: str
    
    # THE FIX: Translated instruction for current agent
    # Prevents recursive intent bug by providing clear, direct instructions
    # instead of the raw user prompt that might confuse agents
    current_task_instruction: str
    
    # Knowledge base context ID
    context_id: str
    
    # Accumulated agent responses
    # Format: [{"agent": "guardian", "response": "..."}, ...]
    agent_responses: List[Dict[str, Any]]
    
    # Original user question (for reference)
    # Used by supervisor for context when making routing decisions
    user_question: str

