# TICKET-06: Replace Orchestrator Tool-Calling with Graph

**Status**: 🟢 Done  
**Priority**: High  
**Estimate**: 8 hours  
**Assignee**: _Unassigned_  
**Sprint**: Phase 2 - Integration

**Dependencies**: [TICKET-05](./TICKET-05.md)  
**Blocks**: [TICKET-07](./TICKET-07.md), [TICKET-10](./TICKET-10.md), [TICKET-11](./TICKET-11.md)

**Related**: [Migration Plan](../langgraph_migration_plan.md#ticket-6-replace-orchestrator-tool-calling-with-graph)

---

## Description

Replace the tool-calling pattern in the orchestrator with graph execution. This removes the `call_specialist_agents` tool and `execute_agent_loop` usage, replacing it with direct graph invocation.

## Tasks

- [ ] Remove `call_specialist_agents` tool from `_create_chatbot_tools()`
- [ ] Remove `_call_specialist_agents_tool()` method
- [ ] Remove `_build_multi_agent_instruction()` method (no longer needed)
- [ ] Replace `_get_llm_response_with_tools()` with `_execute_graph()`
- [ ] Update `chat()` method to use graph instead of tool loop
- [ ] Handle graph state initialization
- [ ] Convert graph output to orchestrator response format
- [ ] Ensure orchestrator.py ≤ 400 lines (split if needed)

## Acceptance Criteria

- [ ] All agent calls go through graph pattern
- [ ] No tool-calling pattern remains
- [ ] Graph state is properly initialized
- [ ] Responses are formatted correctly
- [ ] orchestrator.py ≤ 400 lines

## Files to Modify

- `src/agents/orchestrator/orchestrator.py` - Replace tool-calling with graph
- `src/agents/orchestrator/chat/interface.py` - If orchestrator.py > 400 lines
- `src/agents/orchestrator/chat/response.py` - If orchestrator.py > 400 lines

## Code Structure

```python
# src/agents/orchestrator/orchestrator.py
def chat(self, question: str, context_id: str) -> str:
    """Chat interface - now uses graph pattern."""
    self.set_context(context_id)
    
    # Initialize graph state
    initial_state = {
        "messages": [HumanMessage(content=question)],
        "next": "",
        "current_task_instruction": "",
        "context_id": context_id,
        "agent_responses": [],
        "user_question": question
    }
    
    # Execute graph
    final_state = self.graph.invoke(initial_state)
    
    # Extract and return response
    return self._extract_response_from_state(final_state)
```

## Testing

- [ ] Test graph execution from orchestrator
- [ ] Test state initialization
- [ ] Test response extraction
- [ ] Test error handling
- [ ] Verify no tool-calling code remains

## Notes

This is the critical integration ticket. All agent calls now go through the graph instead of tools.

---

**Created**: 2024-12-XX  
**Last Updated**: 2024-12-XX

