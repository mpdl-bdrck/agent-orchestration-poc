# 🛑 Incident Post-Mortem: "The Guardian Loop"

**Date:** November 29, 2025  
**Duration:** ~4 Hours  
**Severity:** Critical (System Unusable)  
**Status:** ✅ RESOLVED

---

## Executive Summary

The Guardian Agent experienced a critical failure loop that prevented it from executing portfolio analysis tools. The agent would crash with `AttributeError: 'list' object has no attribute 'strip'` whenever it attempted to call its `analyze_portfolio_pacing` tool, despite multiple attempted fixes.

**Root Cause:** Multi-layer failure combining:
1. **Model Eagerness**: `gemini-2.5-flash` sending malformed input formats (`['17']` instead of `"17"`)
2. **Pydantic Validation**: Strict schema validation crashing before our defensive code could run
3. **Stale Caching**: Python bytecode cache preventing code updates from taking effect
4. **Missing Type Handling**: LLM result content being a `list` instead of `str` in tool call responses

**Resolution:** Implemented a three-layer defense architecture:
- **Layer 1**: Safe content extraction in `agent_loop.py` (handles list/string content)
- **Layer 2**: `@tool` decorator with `str` type hints (simple schema, internal sanitization)
- **Layer 3**: Recursive input sanitization inside tool functions

---

## Timeline of Failures & Fixes

### Stage 1: The Initial Crash ⚠️

**Symptom:**
```
AttributeError: 'list' object has no attribute 'strip'
```

**Root Cause:**
- Gemini model sent `account_id: ['17']` (list) instead of `account_id: "17"` (string)
- Pydantic validation attempted to call `.strip()` on the list before our defensive code could intercept it
- Crash occurred inside LangChain's `StructuredTool.invoke()` method

**Attempted Fixes:**
1. Added `_normalize_string_arg()` helper in tool function
2. Added `@field_validator(mode='before')` to Pydantic schema
3. Added `@model_validator(mode='before')` to Pydantic schema
4. Added middleware normalization in `agent_loop.py` before `tool_func.invoke()`

**Why Fixes Failed:**
- Pydantic validation runs **before** function code executes
- Middleware normalization happened **after** Pydantic had already seen the list
- LangChain's internal validation layer was inaccessible

**Final Fix:**
- Created `guardian_v2_tool.py` with `@tool` decorator (no Pydantic schema)
- Used `Any` type hints to bypass schema validation
- Implemented recursive `safe_str()` function inside tool to handle all input types

---

### Stage 2: The Infinite Loop 🔄

**Symptom:**
- Agent would retry the same tool call infinitely
- No error messages visible to user
- System appeared "hung"

**Root Cause:**
- Exception handler in `agent_loop.py` crashed because `logger` wasn't imported
- Error handling code itself raised `NameError: name 'logger' is not defined`
- Exception loop prevented proper error reporting

**Fix:**
```python
# Added to agent_loop.py
import logging
logger = logging.getLogger(__name__)
```

**Lesson:** Always verify imports in exception handlers are available.

---

### Stage 3: The Invisible Output 👻

**Symptom:**
- Tool executed successfully (no crash)
- Agent generated response text
- Response never appeared in CLI output

**Root Cause:**
- Hardcoded early exit in `guardian_agent.py` bypassed streaming callback
- Code path: `if 'hi' in question.lower(): return fallback_response`
- This skipped `execute_agent_loop()` which handles streaming events

**Fix:**
- Removed hardcoded early exit
- Forced all execution through `execute_agent_loop()` to ensure streaming events fire

**Lesson:** Never bypass the standard execution path with hardcoded shortcuts.

---

### Stage 4: The Zombie Code 💀

**Symptom:**
- Code changes had no effect
- Same error persisted despite multiple fixes
- Debug logs from new code never appeared

**Root Cause:**
- Python bytecode cache (`.pyc` files) containing stale code
- LangChain's `StructuredTool` regenerating schemas from cached imports
- File system caching preventing fresh imports

**Fix:**
- Created `guardian_v3_tool.py` (new file) to force fresh import
- Cleared all `__pycache__` directories
- Added unique log message (`*** V3 TOOL EXECUTING ***`) to verify execution

**Lesson:** When code changes don't take effect, suspect caching. Create new files to break cache.

---

### Stage 5: The Schema Rejection 🚫

**Symptom:**
```
400 Invalid argument provided to Gemini: 
* GenerateContentRequest.tools[0].function_declarations[0].parameters.properties[account_id].items: missing field.
```

**Root Cause:**
- `Union[str, List[str]]` type hint generated complex JSON schema
- Gemini API rejected schema because it saw `array` type but no `items` definition
- API validation failed before tool could execute

**Fix:**
- Changed type hints to simple `str` (for API schema generation)
- Kept internal `safe_str()` logic to handle lists at runtime
- Pattern: "Lie to the API, handle the truth in code"

**Lesson:** API schemas must be simple. Handle complexity internally.

---

### Stage 6: The Final Discovery 🔍

**Symptom:**
- Error persisted even after all tool fixes
- Stack trace showed crash in `agent_loop.py` line 71
- Error: `'list' object has no attribute 'strip'`

**Root Cause:**
- **NOT** in tool execution path
- **NOT** in Pydantic validation
- **IN** `agent_loop.py` line 71: `result.content.strip()`
- When Gemini returns tool calls, `result.content` is a **list** (`[]` or `[{"type": "text", ...}]`), not a string
- Code assumed `result.content` was always a string

**Fix:**
```python
def _safe_extract_content(result) -> str:
    """Safely extract content, handling both string and list formats."""
    if not hasattr(result, 'content'):
        return ""
    
    content = result.content
    
    if isinstance(content, str):
        return content.strip() if content else ""
    elif isinstance(content, list):
        # Extract text from Gemini's content block format
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                text_parts.append(block)
        return " ".join(text_parts).strip()
    else:
        return str(content) if content else ""
```

**Lesson:** Never assume LLM response formats. Always handle multiple content types.

---

## Root Cause Analysis

### Primary Root Cause

**The crash was NOT in tool execution or Pydantic validation.**

The crash was in `agent_loop.py` line 71, where code assumed `result.content` was always a string. When Gemini returns tool call responses, `result.content` can be:
- A string: `"Hello world"` (normal response)
- A list: `[]` (empty for tool calls) or `[{"type": "text", "text": "..."}]` (multi-modal format)

### Contributing Factors

1. **Model Eagerness**: `gemini-2.5-flash` is optimized for speed, not precision. It frequently sends malformed input formats.

2. **Architectural Mismatch**: Mixing strict engineering (Pydantic schemas) with loose models (Flash) created brittleness.

3. **Insufficient Defensive Programming**: Code assumed LLM outputs would always match expected formats.

4. **Cache Ghost**: Python's bytecode cache masked code changes, making debugging appear ineffective.

5. **Missing Type Guards**: No runtime type checking for LLM response content.

---

## The Final Architecture: Three-Layer Defense

### Layer 1: Safe Content Extraction (agent_loop.py)

**Purpose:** Handle LLM response content safely, regardless of format.

**Implementation:**
```python
def _safe_extract_content(result) -> str:
    """Safely extract content from LLM result, handling both string and list formats."""
    # Handles: str, list, dict (Gemini content blocks), None
    # Returns: Always a string (empty if no content)
```

**Location:** `src/utils/agent_loop.py` lines 26-63

**Why:** Gemini (and other LLMs) can return content as lists for tool call responses. This layer ensures we never crash on `.strip()`.

---

### Layer 2: Simple Tool Schema (@tool decorator)

**Purpose:** Generate simple JSON schemas that Gemini accepts, while handling complex inputs internally.

**Implementation:**
```python
@tool
def analyze_portfolio_pacing(
    account_id: str = "17",  # Simple str type hint (for API)
    advertiser_filter: Optional[str] = None
) -> str:
    # Internal sanitization handles lists/None/etc.
    clean_account = safe_str(account_id) or "17"
    # ... rest of logic ...
```

**Location:** `src/tools/guardian_v3_tool.py`

**Why:** 
- Simple `str` type hints generate clean JSON schemas (`{"type": "string"}`)
- Gemini API accepts these schemas without rejection
- Internal `safe_str()` handles runtime complexity (lists, None, etc.)

**Anti-Pattern to Avoid:**
```python
# ❌ DON'T DO THIS:
account_id: Union[str, List[str]]  # Generates complex schema Gemini rejects

# ✅ DO THIS:
account_id: str  # Simple schema, handle lists internally
```

---

### Layer 3: Recursive Input Sanitization (Inside Tool Functions)

**Purpose:** Defensively handle any input format the LLM might send.

**Implementation:**
```python
def safe_str(val: Any) -> str:
    """Recursively unwraps lists and ensures string output."""
    if val is None:
        return ""
    if isinstance(val, list):
        return safe_str(val[0]) if len(val) > 0 else ""
    return str(val).strip()
```

**Location:** Inside each tool function (e.g., `guardian_v3_tool.py`)

**Why:** Even with type hints, LLMs can send unexpected formats. This layer ensures we never crash.

---

## Golden Rules for Future Development

### Rule 1: The "Canary" Tool Pattern 🐤

**Never use `StructuredTool` or strict Pydantic schemas for `flash` models.**

**Do:**
- ✅ Use the simple `@tool` decorator
- ✅ Use `str` type hints (to generate simple schemas)
- ✅ Use a `safe_str()` helper inside the function to recursively unwrap lists/garbage

**Don't:**
- ❌ Use `StructuredTool` with explicit Pydantic schemas
- ❌ Use `Union[str, List[str]]` type hints (Gemini rejects these)
- ❌ Assume inputs will match type hints

**Example:**
```python
from langchain_core.tools import tool
from typing import Optional

@tool
def robust_tool(arg: str, optional_arg: Optional[str] = None) -> str:
    """Tool description."""
    # Internal sanitization
    def safe_str(val):
        if val is None:
            return ""
        if isinstance(val, list):
            return safe_str(val[0]) if len(val) > 0 else ""
        return str(val).strip()
    
    clean_arg = safe_str(arg)
    clean_optional = safe_str(optional_arg) if optional_arg else None
    
    # ... rest of logic ...
    return result
```

---

### Rule 2: The "Tool Holster" Pattern 🔫

**Don't rely on Prompt Engineering to stop eager models.**

**Problem:** `gemini-2.5-flash` ignores "Please don't use tools" instructions when it's eager to demonstrate capabilities.

**Solution:** Use the **Graph Node** to physically remove tools from the context.

**Implementation:**
```python
# In guardian.py node
def guardian_node(state: AgentState):
    instruction = state.get("current_task_instruction", "")
    
    # Check supervisor instruction for tool prohibition
    if "STRICTLY FORBIDDEN from using tools" in instruction or "text only" in instruction.lower():
        # Run WITHOUT tools (Tool Holster)
        response = guardian_agent.analyze_without_tools(
            question=state["user_question"],
            context=context,
            supervisor_instruction=instruction
        )
    else:
        # Run WITH tools (Tool Available)
        response = call_specialist_agent_func(
            agent_name="guardian",
            question=state["user_question"],
            # ... tools will be bound ...
        )
    
    return new_state
```

**Why:** Physical removal of tools is 100% effective. Prompt engineering is not.

---

### Rule 3: The "Sanitized Middleware" Pattern 🛡️

**Never trust LLM output formats.**

**Do:**
- ✅ Normalize tool arguments in `agent_loop.py` before execution
- ✅ Handle `result.content` being a List or String
- ✅ Add type guards for all LLM response fields

**Implementation:**
```python
# In agent_loop.py
def execute_agent_loop(...):
    # ...
    result = llm_with_tools.invoke(messages)
    
    # SAFE CONTENT CHECK - Handle both string and list content
    content_str = _safe_extract_content(result)  # ✅ Never crashes
    has_content = bool(content_str)
    
    # SAFE ARG NORMALIZATION - Handle lists before tool execution
    normalized_args = _normalize_tool_args(tool_args)  # ✅ Recursive unwrap
    # ...
```

**Why:** LLMs are non-deterministic. Defensive programming prevents crashes.

---

## File Locations Reference

### Critical Files Modified

1. **`src/utils/agent_loop.py`**
   - Added `_safe_extract_content()` function (lines 26-63)
   - Updated all `result.content` accesses to use safe extraction
   - Added trap logging for diagnostics

2. **`src/tools/guardian_v3_tool.py`** (NEW FILE)
   - Uses `@tool` decorator with `str` type hints
   - Implements `safe_str()` recursive sanitization
   - BeforeValidator pattern (though not needed after Layer 1 fix)

3. **`src/agents/specialists/guardian_agent.py`**
   - Fixed syntax error in fallback chain (lines 159-165)
   - Updated to import V3 tool
   - Added stack trace logging

4. **`src/agents/orchestrator/graph/nodes/guardian.py`**
   - Implements Tool Holster pattern
   - Conditionally binds tools based on supervisor instruction

### Diagnostic Files Created

- `src/tools/guardian_v2_tool.py` - Cache-busting intermediate version
- `src/tools/canary_tools.py` - Minimal test tool for isolation testing

---

## Testing Checklist

After implementing fixes, verify:

- [ ] Guardian can introduce itself WITHOUT calling tools
- [ ] Guardian can execute portfolio analysis WITH tools
- [ ] No crashes when LLM sends list inputs (`['17']`)
- [ ] No crashes when LLM returns list content (`[]` or `[{...}]`)
- [ ] Tool execution logs appear correctly
- [ ] Agent responses display in CLI
- [ ] No infinite retry loops
- [ ] Stack traces show correct error locations

---

## Prevention Checklist

Before deploying new agents or tools:

- [ ] Use `@tool` decorator (not `StructuredTool` with Pydantic)
- [ ] Use simple `str` type hints (not `Union[str, List[str]]`)
- [ ] Implement `safe_str()` helper inside tool functions
- [ ] Use `_safe_extract_content()` for all LLM response content
- [ ] Add trap logging for diagnostics
- [ ] Clear Python cache before testing (`find . -name "__pycache__" -exec rm -r {} +`)
- [ ] Test with both string and list inputs
- [ ] Verify tool holster pattern for inhibition scenarios

---

## Lessons Learned

### 1. **Never Assume LLM Output Formats**
LLMs are non-deterministic. Always handle multiple content types (string, list, dict, None).

### 2. **Cache Ghosts Are Real**
When code changes don't take effect, suspect Python bytecode cache. Create new files to break cache.

### 3. **Simple Schemas Win**
Complex type hints (`Union[str, List[str]]`) generate schemas that APIs reject. Use simple hints, handle complexity internally.

### 4. **Physical Removal > Prompt Engineering**
For inhibition, physically remove tools from context. Don't rely on prompts alone.

### 5. **Defensive Programming Saves Hours**
Add type guards, safe extractors, and recursive sanitization. The extra code prevents crashes.

### 6. **Stack Traces Are Your Friend**
When debugging, capture full stack traces. They reveal the actual crash location, not where you think it is.

### 7. **Isolation Testing Works**
The Canary Agent pattern helped isolate whether the issue was in core infrastructure or Guardian-specific code.

---

## Related Documentation

- **Architecture Decisions:** `AI_HANDOFF.md` - Documents the three-layer defense architecture
- **Performance Optimization:** `docs/performance_optimization_plan.md` - Parallel search implementation
- **Tool Development Guide:** `docs/tool_development_guide.md` (to be created)

---

## Sign-Off

**Incident Resolved:** ✅ November 29, 2025  
**System Status:** ✅ Stable  
**Prevention Measures:** ✅ Documented  
**Next Review:** When adding new agents or tools

---

**Remember:** The crash was NOT where we thought it was. Always follow the stack trace to the actual error location. 🎯

