# TICKET-04: Create Agent Node Wrappers

**Status**: 🟢 Done  
**Priority**: High  
**Estimate**: 6 hours  
**Assignee**: _Unassigned_  
**Sprint**: Phase 1 - Foundation

**Dependencies**: [TICKET-02](./TICKET-02.md), [TICKET-03](./TICKET-03.md)  
**Blocks**: [TICKET-05](./TICKET-05.md)

**Related**: [Migration Plan](../langgraph_migration_plan.md#ticket-4-create-agent-node-wrappers)

---

## Description

Create graph node wrappers for each specialist agent (Guardian, Specialist, Optimizer, Pathfinder). Each node reads the `current_task_instruction` from state instead of the raw user prompt, preventing the recursive intent bug.

## Tasks

- [ ] Create `guardian_node()` function
- [ ] Create `specialist_node()` function
- [ ] Create `optimizer_node()` function
- [ ] Create `pathfinder_node()` function
- [ ] Each node reads `current_task_instruction` instead of raw messages
- [ ] Each node appends response to `agent_responses`
- [ ] Each node clears `current_task_instruction` after processing
- [ ] Integrate with existing agent calling logic
- [ ] Ensure each file ≤ 400 lines

## Acceptance Criteria

- [ ] Each agent node can be called independently
- [ ] Nodes read instruction from state, not raw user prompt
- [ ] Responses are properly accumulated
- [ ] Existing agent logic is reused (no duplication)
- [ ] Each node file ≤ 400 lines

## Files to Create

- `src/agents/orchestrator/graph/nodes/guardian.py` (~150 lines)
- `src/agents/orchestrator/graph/nodes/specialist.py` (~150 lines)
- `src/agents/orchestrator/graph/nodes/optimizer.py` (~150 lines)
- `src/agents/orchestrator/graph/nodes/pathfinder.py` (~150 lines)

## Code Structure

```python
# src/agents/orchestrator/graph/nodes/guardian.py (≤400 lines, ~150 lines)
from ..state import AgentState
from ...agent_calling import call_specialist_agent
from langchain_core.messages import AIMessage

def guardian_node(state: AgentState) -> AgentState:
    """Guardian agent as a graph node."""
    instruction = state.get("current_task_instruction", "Assist the user.")
    
    # Call existing agent logic (simplified)
    response = call_specialist_agent(
        agent_name="guardian",
        question=instruction,  # Use instruction, not raw prompt
        context_id=state["context_id"],
        embedding_model=state.get("embedding_model"),
        agent_registry_get_agent=state.get("get_agent"),
        conversation_history=None  # State handles this
    )
    
    # Update state
    return {
        "messages": [AIMessage(content=response)],
        "agent_responses": state["agent_responses"] + [{"agent": "guardian", "response": response}],
        "current_task_instruction": ""  # Clear after processing
    }
```

## Testing

- [ ] Test each node independently
- [ ] Test instruction reading from state
- [ ] Test response accumulation
- [ ] Test state updates
- [ ] Test integration with existing agent logic

## Notes

These nodes are thin wrappers around existing agent calling logic. The key innovation is reading `current_task_instruction` instead of the raw user prompt.

---

**Created**: 2024-12-XX  
**Last Updated**: 2024-12-XX

