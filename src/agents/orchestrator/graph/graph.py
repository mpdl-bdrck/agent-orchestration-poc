"""
LangGraph definition for supervisor pattern orchestration.

Creates and compiles the StateGraph with supervisor and agent nodes.
"""
from langgraph.graph import StateGraph, END
from typing import Callable, Any

from .state import AgentState
from .supervisor import create_supervisor_node
from .nodes.guardian import create_guardian_node
from .nodes.specialist import create_specialist_node
from .nodes.optimizer import create_optimizer_node
from .nodes.pathfinder import create_pathfinder_node
from .nodes.canary import create_canary_node
from .nodes.semantic_search import create_semantic_search_node


def create_agent_graph(
    llm,
    supervisor_prompt: str,
    call_specialist_agent_func: Callable,
    semantic_search_func: Callable,
    embedding_model: Any,
    get_agent_func: Callable,
    orchestrator_prompt: str = None,
    streaming_callback: Callable = None
):
    """
    Create the LangGraph supervisor graph.
    
    Args:
        llm: LLM instance for supervisor routing decisions
        supervisor_prompt: System prompt for supervisor
        call_specialist_agent_func: Function to call specialist agents
        semantic_search_func: Function to execute semantic search
        embedding_model: Embedding model for semantic search
        get_agent_func: Function to get agent instances
        orchestrator_prompt: System prompt for orchestrator (used for FINISH responses)
        streaming_callback: Optional callback for streaming events
        
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create node functions
    supervisor = create_supervisor_node(llm, supervisor_prompt, orchestrator_prompt, streaming_callback)
    semantic_search = create_semantic_search_node(semantic_search_func, streaming_callback)
    guardian = create_guardian_node(call_specialist_agent_func, embedding_model, get_agent_func, streaming_callback)
    specialist = create_specialist_node(call_specialist_agent_func, embedding_model, get_agent_func, streaming_callback)
    optimizer = create_optimizer_node(call_specialist_agent_func, embedding_model, get_agent_func, streaming_callback)
    pathfinder = create_pathfinder_node(call_specialist_agent_func, embedding_model, get_agent_func, streaming_callback)
    canary = create_canary_node(call_specialist_agent_func, embedding_model, get_agent_func, streaming_callback)
    
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor)
    workflow.add_node("semantic_search", semantic_search)
    workflow.add_node("guardian", guardian)
    workflow.add_node("specialist", specialist)
    workflow.add_node("optimizer", optimizer)
    workflow.add_node("pathfinder", pathfinder)
    workflow.add_node("canary", canary)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Routing function
    def should_continue(state: AgentState) -> str:
        """Determine next node based on supervisor's routing decision."""
        next_node = state.get("next", "")
        if next_node == "FINISH" or not next_node:
            return END
        return next_node
    
    # Conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "semantic_search": "semantic_search",
            "guardian": "guardian",
            "specialist": "specialist",
            "optimizer": "optimizer",
            "pathfinder": "pathfinder",
            "canary": "canary",
            END: END
        }
    )
    
    # All nodes return to supervisor after execution
    workflow.add_edge("semantic_search", "supervisor")
    workflow.add_edge("guardian", "supervisor")
    workflow.add_edge("specialist", "supervisor")
    workflow.add_edge("optimizer", "supervisor")
    workflow.add_edge("pathfinder", "supervisor")
    workflow.add_edge("canary", "supervisor")
    
    # Compile and return
    return workflow.compile()

