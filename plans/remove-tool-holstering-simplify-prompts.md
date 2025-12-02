# Remove Tool Holstering & Simplify Agent Prompts

**Date**: December 1, 2025  
**Status**: 📋 **Architectural Refactoring Plan**  
**Related Documentation**: 
- [`AI_HANDOFF.md`](../AI_HANDOFF.md) - Core architectural patterns
- [`docs/guides/TOOL_INSTRUCTIONS_ARCHITECTURE.md`](../docs/guides/TOOL_INSTRUCTIONS_ARCHITECTURE.md) - Tool instruction layers

---

## Overview

This plan removes the **Tool Holstering** pattern and simplifies agent prompts to rely on **prompt-driven reasoning** instead of hardcoded logic. This aligns with **Pattern 5** from AI_HANDOFF.md: "ALL decisions come from LLM reasoning guided by prompts. NO hardcoded logic."

Additionally, we'll make all agents respond concisely (like Guardian currently does) by simplifying their prompts and removing verbose introduction rules.

---

## Problem Statement

### Current Issues

1. **Architectural Inconsistency**: 
   - Pattern 5 says "NO hardcoded logic" but tool holstering uses hardcoded keyword matching
   - Contradicts the principle: "If you find yourself writing `if "keyword" in text:`, STOP. Use prompts instead."

2. **Maintenance Burden**:
   - Keyword lists to maintain (`explicit_no_tools_directives`)
   - Multiple code paths (`analyze_without_tools()` vs normal path)
   - Brittle (breaks if supervisor phrasing changes)

3. **Complexity**:
   - Tool holstering logic in `guardian.py` (lines 41-61, 95-131)
   - Separate `analyze_without_tools()` method
   - Verbose "don't use tools" rules in Guardian prompt

4. **Inconsistent Agent Responses**:
   - Guardian: Brief, concise
   - Specialist/Optimizer/Pathfinder: Verbose, detailed
   - No clear guidance on response length

---

## Solution: Prompt-Driven Reasoning

### Core Principle

**Trust the LLM to reason about tool usage** based on:
1. Clear tool descriptions with "WHEN NOT TO USE" sections
2. Good agent prompts that encourage reasoning
3. Supervisor instructions as guidance (not commands)

### Benefits

- ✅ **Simpler code**: One execution path, no conditional logic
- ✅ **Consistent architecture**: Prompt-driven, no hardcoded logic
- ✅ **Easier maintenance**: Update tool descriptions, not code
- ✅ **More reliable**: LLMs are good at following clear instructions
- ✅ **Consistent responses**: All agents brief and concise

---

## Implementation Checklist

### Phase 1: Remove Tool Holstering Code ✅

- [ ] Remove tool holstering logic from `src/agents/orchestrator/graph/nodes/guardian.py`
  - [ ] Remove lines 41-61 (keyword detection)
  - [ ] Remove lines 95-131 (conditional execution paths)
  - [ ] Simplify to single execution path: always call `call_specialist_agent_func()`
  
- [ ] Remove `analyze_without_tools()` method from `src/agents/specialists/guardian_agent.py`
  - [ ] Delete method (lines 190-228)
  - [ ] Remove any references to this method

- [ ] Update documentation
  - [ ] Remove tool holstering section from `docs/guides/TOOL_INSTRUCTIONS_ARCHITECTURE.md`
  - [ ] Update `AI_HANDOFF.md` to remove Pattern 2 (Tool Holster Pattern)
  - [ ] Update ADR 001 to remove tool holstering from Three-Layer Defense

### Phase 2: Simplify Guardian Prompt ✅

- [ ] Remove verbose "don't use tools" rules from `config/prompts/guardian_agent/system.txt`
  - [ ] Remove lines 47-53 (OPERATIONAL PROTOCOL section about never calling tools for introductions)
  - [ ] Remove lines 55-74 (MANDATORY REASONING PROTOCOL with introduction examples)
  - [ ] Remove lines 69-74 (INHIBITION RULE with introduction examples)
  
- [ ] Keep essential tool guidance
  - [ ] Keep tool description section (lines 32-39)
  - [ ] Keep "ONLY use this tool when..." guidance (line 39)
  - [ ] Simplify to: "Use tools only when live data is required. Follow the tool's 'WHEN NOT TO USE' guidance."

- [ ] Add concise response instruction
  - [ ] Add: "Provide concise, direct responses. Be brief and focused."

### Phase 3: Simplify Other Agent Prompts ✅

- [ ] Update `config/prompts/specialist_agent/system.txt`
  - [ ] Add: "Provide concise, actionable analysis that helps resolve specific issues."
  - [ ] Remove any verbose instructions

- [ ] Update `config/prompts/optimizer_agent/system.txt`
  - [ ] Add: "Provide concise, actionable optimization recommendations."
  - [ ] Remove any verbose instructions

- [ ] Update `config/prompts/pathfinder_agent/system.txt`
  - [ ] Add: "Provide concise strategic guidance on supply chain navigation."
  - [ ] Remove any verbose instructions

### Phase 4: Update Supervisor Prompt ✅

- [ ] Update `prompts/orchestrator/supervisor.txt`
  - [ ] Remove any references to "STRICTLY FORBIDDEN from using tools"
  - [ ] Simplify introduction instructions to: "Introduce yourself and explain your role."
  - [ ] Trust agents to reason about tool usage based on their prompts

### Phase 5: Verify Tool Descriptions ✅

- [ ] Verify `src/tools/portfolio_pacing_tool.py` has clear "WHEN NOT TO USE" section
  - [ ] Already present (lines 54-60) ✅
  - [ ] Ensure it's comprehensive and clear

- [ ] Document that tool descriptions are the source of truth for tool usage
  - [ ] Add note in `AI_HANDOFF.md` about trusting tool descriptions

---

## Detailed Changes

### 1. Remove Tool Holstering from `guardian.py`

**File**: `src/agents/orchestrator/graph/nodes/guardian.py`

**Current Code** (lines 41-61):
```python
# --- DYNAMIC TOOL BINDING (Tool Holster Pattern) ---
# Trust the supervisor's explicit instruction - if it explicitly forbids tools,
# holster them. Otherwise, let the agent decide (with tools available).
# The supervisor will include directives like "STRICTLY FORBIDDEN from using tools"
# or "text only" when tools should not be used.
instruction_lower = instruction.lower()
explicit_no_tools_directives = [
    "strictly forbidden from using tools",
    "do not use tools",
    "text only",
    "speak text only",
    "forbidden from using",
    "must not use tools"
]
should_holster_tools = any(directive in instruction_lower for directive in explicit_no_tools_directives)

logger.info(f"Guardian node - Instruction: '{instruction}' | Holster tools: {should_holster_tools}")
if should_holster_tools:
    logger.info(f"✅ Tool Holster ACTIVE - tools will be disabled")
else:
    logger.info(f"⚠️  Tool Holster INACTIVE - tools will be available")
```

**Replace With**:
```python
# Trust agent reasoning - tools are available, agent decides based on tool descriptions and prompts
logger.info(f"Guardian node - Instruction: '{instruction}'")
```

**Current Code** (lines 95-131):
```python
# --- TOOL HOLSTER LOGIC ---
# If supervisor explicitly forbade tools, run WITHOUT tools
# Otherwise, run WITH tools (normal path - agent decides)
if should_holster_tools:
    logger.info("Guardian: Running WITHOUT tools (Tool Holster - supervisor explicitly forbade tools)")
    # Run without tools using direct agent method
    if agent and hasattr(agent, 'analyze_without_tools'):
        # For introductions, we don't need knowledge base context
        result = agent.analyze_without_tools(
            question=question_for_guardian,
            context="No specific context needed for introduction.",
            supervisor_instruction=instruction
        )
        response = result.get('answer', '') if isinstance(result, dict) else str(result)
    else:
        # Fallback: call via standard path but force use_tools=False
        response = call_specialist_agent_func(
            agent_name="guardian",
            question=question_for_guardian,
            context_id=context_id,
            embedding_model=embedding_model,
            agent_registry_get_agent=get_agent_func,
            conversation_history=conversation_history if conversation_history else None,
            supervisor_instruction=instruction
        )
else:
    logger.info("Guardian: Running WITH tools (data request detected)")
    # Normal path: run WITH tools
response = call_specialist_agent_func(
    agent_name="guardian",
    question=question_for_guardian,  # Pass original question for context
    context_id=context_id,
    embedding_model=embedding_model,
    agent_registry_get_agent=get_agent_func,
    conversation_history=conversation_history if conversation_history else None,
    supervisor_instruction=instruction  # Pass supervisor instruction from state
)
```

**Replace With**:
```python
# Single execution path - agent decides tool usage based on prompts and tool descriptions
response = call_specialist_agent_func(
    agent_name="guardian",
    question=question_for_guardian,
    context_id=context_id,
    embedding_model=embedding_model,
    agent_registry_get_agent=get_agent_func,
    conversation_history=conversation_history if conversation_history else None,
    supervisor_instruction=instruction
)
```

### 2. Remove `analyze_without_tools()` Method

**File**: `src/agents/specialists/guardian_agent.py`

**Delete**: Lines 190-228 (entire `analyze_without_tools()` method)

**Reason**: No longer needed - agent will reason about tool usage based on prompts.

### 3. Simplify Guardian Prompt

**File**: `config/prompts/guardian_agent/system.txt`

**Remove**:
- Lines 41-53: OPERATIONAL PROTOCOL section
- Lines 55-74: MANDATORY REASONING PROTOCOL with introduction examples

**Keep**:
- Tool description (lines 32-39)
- "ONLY use this tool when..." (line 39)

**Add**:
```txt
TOOL USAGE GUIDANCE:
Use tools only when live data is explicitly required. The tool description includes clear "WHEN NOT TO USE" guidance - follow it. Trust your reasoning to determine when tools are needed.

RESPONSE STYLE:
Provide concise, direct responses. Be brief and focused. Avoid unnecessary verbosity.
```

### 4. Simplify Other Agent Prompts

**Files**: 
- `config/prompts/specialist_agent/system.txt`
- `config/prompts/optimizer_agent/system.txt`
- `config/prompts/pathfinder_agent/system.txt`

**Add to each** (at the end):
```txt
RESPONSE STYLE:
Provide concise, direct responses. Be brief and focused.
```

**Specialist**:
```txt
Provide concise, actionable analysis that helps resolve specific issues.
```

**Optimizer**:
```txt
Provide concise, actionable optimization recommendations.
```

**Pathfinder**:
```txt
Provide concise strategic guidance on supply chain navigation.
```

### 5. Update Supervisor Prompt

**File**: `prompts/orchestrator/supervisor.txt`

**Current** (lines 21-22):
```txt
- User: "guardian say hi" OR "guardian introduce yourself" OR any single-agent introduction
  → Route: guardian, Instruction: "Introduce yourself and explain your role. Focus on YOUR role only."
```

**Keep as-is** - no need for "STRICTLY FORBIDDEN" keywords. Trust agent reasoning.

---

## Testing Strategy

### Unit Tests

1. **Guardian Node**:
   - Verify single execution path (no conditional logic)
   - Verify `call_specialist_agent_func()` always called
   - Verify no references to `analyze_without_tools()`

2. **Guardian Agent**:
   - Verify `analyze_without_tools()` method removed
   - Verify `analyze()` method works normally

### Integration Tests

1. **Introduction Flow**:
   - User: "Have agents introduce themselves"
   - Verify agents respond concisely
   - Verify no tool calls made for introductions
   - Verify responses are brief (like Guardian currently)

2. **Tool Usage Flow**:
   - User: "How is my portfolio pacing?"
   - Verify Guardian calls `analyze_portfolio_pacing` tool
   - Verify tool is used appropriately

3. **Edge Cases**:
   - Ambiguous questions (should agent use tool?)
   - Questions that don't need tools (should agent reason correctly?)

### Manual Testing

1. **Test introductions**: Verify all agents respond concisely
2. **Test tool usage**: Verify tools are called when needed
3. **Test tool inhibition**: Verify tools are NOT called for greetings/introductions
4. **Monitor logs**: Verify no tool holstering messages appear

---

## Success Criteria

- [ ] Tool holstering code completely removed
- [ ] Single execution path in guardian node
- [ ] No `analyze_without_tools()` method
- [ ] All agents respond concisely (like Guardian)
- [ ] Agents correctly reason about tool usage (no unnecessary tool calls)
- [ ] No hardcoded keyword matching
- [ ] Architecture aligns with Pattern 5 (prompt-driven reasoning)
- [ ] Documentation updated to reflect changes

---

## Rollback Plan

If agents misuse tools after removing holstering:

1. **First**: Improve tool descriptions ("WHEN NOT TO USE" sections)
2. **Second**: Improve agent prompts (add clearer guidance)
3. **Third**: Add supervisor instruction guidance (not commands)
4. **Last resort**: Re-add minimal holstering (but try prompts first)

**Principle**: Fix prompts before adding code workarounds.

---

## Related Documentation Updates

### Files to Update

1. **`AI_HANDOFF.md`**:
   - Remove Pattern 2 (Tool Holster Pattern)
   - Update ADR 001 (remove tool holstering from Three-Layer Defense)
   - Add note about trusting tool descriptions

2. **`docs/guides/TOOL_INSTRUCTIONS_ARCHITECTURE.md`**:
   - Remove Layer 4 (Tool Holstering) section
   - Update to reflect prompt-driven approach

3. **`docs/features/PROACTIVE_NOTIFICATION_PANEL.md`**:
   - No changes needed (unrelated feature)

---

## Implementation Order

1. ✅ **Remove tool holstering code** (guardian.py, guardian_agent.py)
2. ✅ **Simplify Guardian prompt** (remove verbose rules)
3. ✅ **Simplify other agent prompts** (add concise response instructions)
4. ✅ **Update supervisor prompt** (remove "FORBIDDEN" references)
5. ✅ **Update documentation** (AI_HANDOFF.md, docs/guides/TOOL_INSTRUCTIONS_ARCHITECTURE.md)
6. ✅ **Test end-to-end** (introductions, tool usage, edge cases)
7. ✅ **Verify success criteria**

---

## Expected Outcomes

### Before (Current State)

- **Code**: ~90 lines of tool holstering logic
- **Complexity**: Multiple execution paths, keyword matching
- **Maintenance**: Keyword lists, separate methods
- **Responses**: Guardian brief, others verbose

### After (Target State)

- **Code**: Single execution path, ~10 lines
- **Complexity**: Simple, prompt-driven
- **Maintenance**: Update tool descriptions/prompts only
- **Responses**: All agents concise and consistent

### Benefits

- ✅ **Simpler**: Less code, easier to understand
- ✅ **Consistent**: Aligns with Pattern 5 (prompt-driven reasoning)
- ✅ **Maintainable**: Update prompts, not code
- ✅ **Reliable**: LLMs follow clear instructions well
- ✅ **Unified**: All agents respond consistently

---

**Last Updated**: December 1, 2025  
**Status**: 📋 Ready for Implementation

