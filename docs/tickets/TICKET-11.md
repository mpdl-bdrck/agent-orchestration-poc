# TICKET-11: Remove Legacy Code and Enforce 400-Line Limit

**Status**: 🟢 Done  
**Priority**: High  
**Estimate**: 6 hours  
**Assignee**: _Unassigned_  
**Sprint**: Phase 2 - Integration

**Dependencies**: [TICKET-06](./TICKET-06.md), [TICKET-09](./TICKET-09.md), [TICKET-10](./TICKET-10.md)  
**Blocks**: [TICKET-12](./TICKET-12.md), [TICKET-13](./TICKET-13.md)

**Related**: [Migration Plan](../langgraph_migration_plan.md#ticket-11-remove-legacy-code-and-enforce-400-line-limit)

---

## Description

Remove all legacy tool-calling code and enforce the 400-line limit for all Python files. Split any files that exceed this limit into focused modules.

## Tasks

- [ ] Remove `execute_agent_loop()` from `utils/agent_loop.py` (or refactor if used elsewhere)
- [ ] Remove `_call_specialist_agents_tool()` method
- [ ] Remove `_build_multi_agent_instruction()` method
- [ ] Remove `call_specialist_agents` tool definition
- [ ] Audit all Python files for line count
- [ ] Split files exceeding 400 lines:
  - `orchestrator.py` → Split into orchestrator.py + orchestrator/chat.py + orchestrator/response.py
  - `agent_calling.py` → Split if needed
  - `supervisor.py` → Split into supervisor.py + supervisor/routing.py
  - Agent nodes → Ensure each ≤ 400 lines
- [ ] Update imports after splitting
- [ ] Verify all functionality still works

## Acceptance Criteria

- [ ] No legacy tool-calling code remains
- [ ] All Python files ≤ 400 lines
- [ ] Code is well-organized and modular
- [ ] All imports work correctly
- [ ] No functionality lost

## Files to Remove

- `orchestrator.py`: `_call_specialist_agents_tool()` method
- `orchestrator.py`: `_build_multi_agent_instruction()` method
- `orchestrator.py`: `call_specialist_agents` tool definition

## Files to Split (if > 400 lines)

- `orchestrator.py` → `orchestrator/chat.py`, `orchestrator/response.py`
- `supervisor.py` → `supervisor/routing.py` (if needed)
- `agent_calling.py` → `agent_calling/core.py` (if needed)

## Testing

- [ ] Verify all imports work
- [ ] Run all tests
- [ ] Verify functionality unchanged
- [ ] Check file line counts

## Notes

This ticket cleans up the codebase and enforces code quality standards.

---

**Created**: 2024-12-XX  
**Last Updated**: 2024-12-XX

