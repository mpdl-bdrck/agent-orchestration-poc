# Incident Post-Mortem: Guardian Loop (November 29, 2025)

**Duration**: ~4 hours  
**Status**: ✅ RESOLVED  
**Root Cause**: Tool crash in validation layer, not execution layer

## Timeline

### Initial Problem
Guardian agent crashed with `'list' object has no attribute 'strip'` when calling tools, causing introduction text to disappear.

### Attempted Fixes (Chronological)

1. **Prompt Engineering** - Added "WHEN NOT TO USE" sections
   - Result: Still called tools
   
2. **Middleware Normalization** - Added `_normalize_tool_args()` in `agent_loop.py`
   - Result: Partial success, but crashes still occurred
   
3. **Pydantic Validator Fix** - Updated validators to handle lists before string operations
   - Result: Still had edge cases
   
4. **Double-Ended Sanitation** - Fixed both Pydantic Model AND Tool Function layers
   - Result: Crashes stopped, but tools still called unnecessarily
   
5. **Tool Holster Pattern** - Physically remove tools when supervisor forbids them
   - Result: ✅ SUCCESS - Complete solution

## Root Cause Analysis

The crash was in **LangChain's validation layer** (`agent_loop.py` line 71: `result.content.strip()`), NOT in tool execution. The LLM was sending lists (`['value']`) instead of strings (`"value"`), and Pydantic's internal validation called `.strip()` on the list before our normalization could run.

## The Three-Layer Defense Architecture

### Layer 1: Tool Holster Pattern (Prevention)
- Physically removes tools from agent's capability set
- Supervisor-driven, not hardcoded
- **File**: `src/agents/orchestrator/graph/nodes/guardian.py`

### Layer 2: Canary Pattern (Crash-Proof Tool)
- Removed Pydantic schemas from tools
- Internal sanitization with `safe_str()` functions
- **File**: `src/tools/portfolio_pacing_tool.py`

### Layer 3: Middleware Normalization (Safety Net)
- Normalizes arguments before Pydantic validation
- Handles lists, None, and edge cases
- **File**: `src/utils/agent_loop.py`

## Key Lessons

1. **Check WHERE the error occurs** - If it's in validation, fix BEFORE validation
2. **Multi-layer defense** - Never rely on a single fix
3. **Physical prevention** - Removing tools is more reliable than hoping LLM won't call them
4. **Double-Ended Sanitation** - Fix both Pydantic Model AND Tool Function layers

## Prevention Checklist

- [ ] Tools use `@tool` decorator without Pydantic schemas
- [ ] Tool functions have internal `safe_str()` sanitizers
- [ ] Middleware normalizes arguments before validation
- [ ] Pydantic validators handle lists BEFORE string operations
- [ ] Supervisor can physically remove tools when needed

