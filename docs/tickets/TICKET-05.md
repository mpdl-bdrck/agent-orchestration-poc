# TICKET-05: Build Graph with Conditional Edges

**Status**: 🟢 Done  
**Priority**: High  
**Estimate**: 4 hours  
**Assignee**: _Unassigned_  
**Sprint**: Phase 1 - Foundation

**Dependencies**: [TICKET-03](./TICKET-03.md), [TICKET-04](./TICKET-04.md)  
**Blocks**: [TICKET-06](./TICKET-06.md), [TICKET-09](./TICKET-09.md)

**Related**: [Migration Plan](../langgraph_migration_plan.md#ticket-5-build-graph-with-conditional-edges)

---

## Description

Create the LangGraph StateGraph with all nodes and conditional edges. This ties together the supervisor and agent nodes into a working graph that can route queries appropriately.

## Tasks

- [ ] Create StateGraph instance
- [ ] Add supervisor node
- [ ] Add all agent nodes
- [ ] Implement routing function (`should_continue`)
- [ ] Add conditional edges from supervisor
- [ ] Add edges from agents back to supervisor
- [ ] Set entry point
- [ ] Compile graph
- [ ] Ensure file ≤ 400 lines

## Acceptance Criteria

- [ ] Graph compiles without errors
- [ ] Routing logic works correctly
- [ ] Agents return to supervisor after execution
- [ ] FINISH condition properly terminates graph
- [ ] File size ≤ 400 lines

## Files to Create

- `src/agents/orchestrator/graph/graph.py` (~200 lines)

## Code Structure

```python
# src/agents/orchestrator/graph/graph.py (~200 lines)
from langgraph.graph import StateGraph, END
from .state import AgentState
from .supervisor import supervisor_node
from .nodes import guardian_node, specialist_node, optimizer_node, pathfinder_node

def create_agent_graph() -> StateGraph:
    """Create the LangGraph supervisor graph."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("guardian", guardian_node)
    workflow.add_node("specialist", specialist_node)
    workflow.add_node("optimizer", optimizer_node)
    workflow.add_node("pathfinder", pathfinder_node)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Routing function
    def should_continue(state: AgentState) -> str:
        if state["next"] == "FINISH":
            return END
        return state["next"]
    
    # Conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "guardian": "guardian",
            "specialist": "specialist",
            "optimizer": "optimizer",
            "pathfinder": "pathfinder",
            END: END
        }
    )
    
    # Agents return to supervisor
    workflow.add_edge("guardian", "supervisor")
    workflow.add_edge("specialist", "supervisor")
    workflow.add_edge("optimizer", "supervisor")
    workflow.add_edge("pathfinder", "supervisor")
    
    return workflow.compile()
```

## Testing

- [ ] Test graph compilation
- [ ] Test routing to each agent
- [ ] Test FINISH condition
- [ ] Test agent return to supervisor
- [ ] Test error handling

## Notes

This is where everything comes together. The graph defines the execution flow and routing logic.

---

**Created**: 2024-12-XX  
**Last Updated**: 2024-12-XX

