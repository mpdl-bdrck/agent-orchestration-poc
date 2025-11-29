# TICKET-03: Implement Supervisor Node with Structured Output

**Status**: 🟢 Done  
**Priority**: High  
**Estimate**: 4 hours  
**Assignee**: _Unassigned_  
**Sprint**: Phase 1 - Foundation

**Dependencies**: [TICKET-02](./TICKET-02.md)  
**Blocks**: [TICKET-04](./TICKET-04.md), [TICKET-05](./TICKET-05.md), [TICKET-08](./TICKET-08.md)

**Related**: [Migration Plan](../langgraph_migration_plan.md#ticket-3-implement-supervisor-node-with-structured-output)

---

## Description

Implement the supervisor node that acts as the router for the graph. The supervisor uses structured output to make routing decisions and translates user intent into clear instructions for agents.

## Tasks

- [ ] Create Pydantic model for routing decisions
- [ ] Implement supervisor node function
- [ ] Add structured output binding to LLM
- [ ] Implement instruction translation logic
- [ ] Handle "FINISH" decision
- [ ] Add logging and error handling
- [ ] Ensure file ≤ 400 lines (split to `routing.py` if needed)

## Acceptance Criteria

- [ ] Supervisor outputs valid routing decisions
- [ ] Instructions are properly translated (e.g., "have agents say hi" → "Introduce yourself")
- [ ] Structured output enforces valid agent names
- [ ] Handles edge cases (no agents needed, invalid input)
- [ ] File size ≤ 400 lines

## Files to Create

- `src/agents/orchestrator/graph/supervisor.py` (~200-400 lines)
- `src/agents/orchestrator/graph/routing.py` (~150 lines, if supervisor.py > 400 lines)

## Code Structure

```python
# src/agents/orchestrator/graph/supervisor.py (≤400 lines)
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Literal
from .state import AgentState
from .routing import translate_user_intent  # If supervisor.py > 400 lines

class RouteDecision(BaseModel):
    """Structured routing decision from supervisor."""
    next: Literal["guardian", "specialist", "optimizer", "pathfinder", "FINISH"] = Field(
        description="The next agent to act, or FINISH if done."
    )
    instructions: str = Field(
        description="Specific, imperative instruction for the worker. "
                    "Translate user intent into direct command. "
                    "Example: User says 'Have agents say hi' -> 'Introduce yourself and your role.'"
    )
    reasoning: str = Field(
        description="Why this routing decision was made."
    )

def supervisor_node(state: AgentState) -> AgentState:
    """Router that decides next agent or FINISH."""
    # Implementation here (~200 lines)
    # If exceeds 400 lines, extract routing logic to supervisor/routing.py
```

## Testing

- [ ] Test routing decisions for various queries
- [ ] Test instruction translation
- [ ] Test FINISH condition
- [ ] Test error handling
- [ ] Test structured output validation

## Notes

The supervisor is the "brain" of the graph - it makes all routing decisions. Instruction translation is critical to prevent the recursive intent bug.

---

**Created**: 2024-12-XX  
**Last Updated**: 2024-12-XX

