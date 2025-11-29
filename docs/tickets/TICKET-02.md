# TICKET-02: Define State Schema

**Status**: 🟢 Done  
**Priority**: High  
**Estimate**: 3 hours  
**Assignee**: _Unassigned_  
**Sprint**: Phase 1 - Foundation

**Dependencies**: [TICKET-01](./TICKET-01.md)  
**Blocks**: [TICKET-03](./TICKET-03.md), [TICKET-04](./TICKET-04.md)

**Related**: [Migration Plan](../langgraph_migration_plan.md#ticket-2-define-state-schema)

---

## Description

Create the `AgentState` TypedDict that defines the shared state schema for LangGraph agent orchestration. This state schema includes the `current_task_instruction` field that fixes the recursive intent bug.

## Tasks

- [ ] Create `AgentState` TypedDict with required fields
- [ ] Define message history field (append-only)
- [ ] Add `next` field for routing decisions
- [ ] Add `current_task_instruction` field (THE FIX)
- [ ] Add `context_id` and `agent_responses` fields
- [ ] Add type hints and documentation

## Acceptance Criteria

- [ ] State schema compiles without errors
- [ ] All fields properly typed
- [ ] Documentation explains each field's purpose
- [ ] State can be instantiated with sample data

## Files to Create

- `src/agents/orchestrator/graph/state.py` (~50 lines)

## Code Structure

```python
# src/agents/orchestrator/graph/state.py
from typing import TypedDict, Annotated, List, Dict, Any
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """Shared state for LangGraph agent orchestration."""
    
    # Conversation history (append-only)
    messages: Annotated[List[BaseMessage], operator.add]
    
    # Routing decision from supervisor
    next: str  # "guardian" | "specialist" | "optimizer" | "pathfinder" | "FINISH"
    
    # THE FIX: Translated instruction for current agent
    # Prevents recursive intent bug
    current_task_instruction: str
    
    # Knowledge base context
    context_id: str
    
    # Accumulated agent responses
    agent_responses: List[Dict[str, Any]]
    
    # Original user question (for reference)
    user_question: str
```

## Testing

- [ ] Test state creation with sample data
- [ ] Test type checking
- [ ] Test append-only behavior for messages field
- [ ] Verify all fields are accessible

## Notes

The `current_task_instruction` field is critical - it prevents agents from seeing the raw user prompt and getting confused about coordinating other agents.

---

**Created**: 2024-12-XX  
**Last Updated**: 2024-12-XX

