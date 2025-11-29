# TICKET-08: Add Supervisor System Prompt

**Status**: 🟢 Done  
**Priority**: Medium  
**Estimate**: 3 hours  
**Assignee**: _Unassigned_  
**Sprint**: Phase 2 - Integration

**Dependencies**: [TICKET-03](./TICKET-03.md)  
**Blocks**: None

**Related**: [Migration Plan](../langgraph_migration_plan.md#ticket-8-add-supervisor-system-prompt)

---

## Description

Create a comprehensive system prompt for the supervisor that guides it in making routing decisions and translating user intent into clear instructions for agents.

## Tasks

- [ ] Create `prompts/orchestrator/supervisor.txt`
- [ ] Write clear instructions for routing decisions
- [ ] Include instruction translation guidelines
- [ ] Add examples of good routing decisions
- [ ] Test prompt with various queries

## Acceptance Criteria

- [ ] Prompt produces consistent routing decisions
- [ ] Instructions are properly translated
- [ ] Handles edge cases correctly

## Files to Create

- `prompts/orchestrator/supervisor.txt`

## Prompt Template

```markdown
You are the Supervisor, responsible for routing queries to specialist agents.

AVAILABLE AGENTS:
- guardian: Portfolio oversight, monitoring, anomaly detection
- specialist: Technical troubleshooting, detailed analysis
- optimizer: Performance optimization, recommendations
- pathfinder: Forecasting, planning, strategy

ROUTING RULES:
1. Route to appropriate agent(s) based on question domain
2. Translate user intent into clear, imperative instructions
3. For multi-agent requests, route to each agent sequentially
4. Use FINISH when no more agents are needed

INSTRUCTION TRANSLATION:
- User: "Have agents introduce themselves" 
  → Instruction: "Introduce yourself and explain your role"
- User: "Analyze my portfolio" 
  → Instruction: "Analyze portfolio health and provide insights"
```

## Testing

- [ ] Test routing decisions with various queries
- [ ] Test instruction translation
- [ ] Test edge cases
- [ ] Verify consistency

## Notes

The supervisor prompt is critical for good routing decisions and instruction translation.

---

**Created**: 2024-12-XX  
**Last Updated**: 2024-12-XX

