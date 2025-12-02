# AI Development Agent Handoff Document

**Last Updated**: December 1, 2025 (Latest: Portfolio pacing refactor, timezone fixes, CSV storage improvements)  
**Purpose**: Reference manual for architectural decisions, patterns, and critical implementation details

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Agent Configuration](#agent-configuration)
3. [Core Architectural Patterns (The "Golden Rules")](#core-architectural-patterns-the-golden-rules)
4. [Critical Implementation Details (Do Not Touch)](#critical-implementation-details-do-not-touch)
5. [Development Workflow](#development-workflow)
6. [Troubleshooting Playbook](#troubleshooting-playbook)
7. [Reference Implementation](#reference-implementation)

---

## System Overview

**Architecture**: LangGraph Supervisor Pattern  
**Model Standard**: `gemini-2.5-flash` (all agents)  
**Routing**: Structured Output (`RouteDecision`) - NO tools  
**State Management**: LangGraph `AgentState` TypedDict

**Vision**: See [`docs/vision/README.md`](docs/vision/README.md) for the strategic vision and progressive autonomy model that guides this implementation.

### Flow Diagram

```
User Question
    ↓
OrchestratorAgent.chat() → ALWAYS invokes graph
    ↓
Supervisor Node (structured output) → RouteDecision
    ↓
Conditional edges route to:
    - semantic_search (knowledge base)
    - guardian/specialist/optimizer/pathfinder (agents)
    - FINISH (simple questions)
    ↓
Node executes → Returns to supervisor
    ↓
Supervisor decides: FINISH or route again
```

### Key Components

- **Supervisor Node** (`src/agents/orchestrator/graph/supervisor.py`): Router using `RouteDecision` Pydantic model
- **Agent Nodes** (`src/agents/orchestrator/graph/nodes/`): Read `current_task_instruction` from state
- **State Schema** (`src/agents/orchestrator/graph/state.py`): Shared `AgentState` TypedDict
- **Semantic Search** (`src/agents/orchestrator/graph/nodes/semantic_search.py`): Tool/service, NOT an agent

---

## Agent Configuration

### Agent Roster

1. **🛡️ Guardian Agent**: Portfolio oversight, health monitoring, anomaly detection
   - Tool: `analyze_portfolio_pacing`
   - Config: `config/agents/guardian.yaml`

2. **🔧 Specialist Agent**: Deep diagnostic analysis, root cause identification
   - Config: `config/agents/specialist.yaml`

3. **🎯 Optimizer Agent**: Budget allocation, bid optimization, creative rotation
   - Config: `config/agents/optimizer.yaml`

4. **🧭 Pathfinder Agent**: Supply chain navigation, QPS optimization, SSP relationships
   - Config: `config/agents/pathfinder.yaml`

### Model Selection Strategy

**Standard**: `gemini-2.5-flash` for ALL agents

**Rationale**:
- Flash: ~1,000-4,000 RPM ✅ (survives parallel execution)
- Pro: ~60 RPM ❌ (crashes with 4 agents × 2 calls = 8-10 requests instantly)

**Escalation Path**:
1. Start with `gemini-2.5-flash` for all agents
2. Monitor Guardian behavior
3. If Guardian still calls tools unnecessarily → upgrade ONLY Guardian to `gemini-2.5-pro`
4. Don't pay "Pro Tax" until proven necessary

---

## Core Architectural Patterns (The "Golden Rules")

### Pattern 1: Routing - Structured Output (No Tools)

**Principle**: Supervisor uses structured output (`RouteDecision`) for routing. NO tools for routing.

**Implementation**:
```python
# ✅ CORRECT
structured_llm = llm.with_structured_output(RouteDecision)
decision = structured_llm.invoke(messages)
return {"next": decision.next, "current_task_instruction": decision.instructions}
```

**Why**: Tools add latency and break the architectural pattern. Supervisor IS the graph entry point.

### Pattern 2: Resilience - The "Canary" Pattern

**Principle**: Tools use `@tool` decorators with internal `safe_str` sanitizers. NO Pydantic schemas on tools.

**Why**: Pydantic schemas cause validation crashes when LLM sends lists instead of strings. Internal sanitization prevents crashes.

**Implementation**: See [Reference Implementation - Safe Tool Definition](#reference-implementation)

### Pattern 3: State-Based Communication

**Principle**: Read from `AgentState`, don't prop-drill through function signatures.

**Implementation**:
```python
# ✅ CORRECT: Read from state
def guardian_node(state: AgentState):
    instruction = state.get("current_task_instruction", "")
    user_question = state.get("user_question", "")
    # Use instruction and question
```

### Pattern 4: Prompt-Driven Reasoning

**Principle**: ALL decisions come from LLM reasoning guided by prompts. NO hardcoded logic.

**Rule**: If you find yourself writing `if "keyword" in text:`, STOP. Use prompts instead.

---

## Critical Implementation Details (Do Not Touch)

### Why We Removed Pydantic Schemas from Tools

**Problem**: LLMs (especially Gemini Flash) send lists (`['value']`) instead of strings (`"value"`). Pydantic's validation calls `.strip()` on lists, causing crashes.

**Solution**: Use `@tool` decorator WITHOUT Pydantic schemas. Implement internal sanitization with `safe_str()` functions.

**Files**:
- `src/tools/portfolio_pacing_tool.py` - Main tool function (185 lines)
- `src/tools/portfolio_pacing_helpers.py` - Helper functions (calculations, formatting, CSV)
- `src/tools/portfolio_pacing_loader.py` - Analyzer loading and client config
- `src/agents/specialists/guardian_agent.py` - Pydantic Model Guard (for input models, not tools)

### Why We Bypass LangChain Validation in `agent_loop.py`

**Problem**: LangChain's `StructuredTool` validates arguments via Pydantic BEFORE calling the function. When LLM passes lists, Pydantic's internal validation crashes.

**Solution**: Middleware normalization in `agent_loop.py` normalizes arguments BEFORE Pydantic validation occurs.

**File**: `src/utils/agent_loop.py` - `_normalize_tool_args()` function

### Why `semantic_search` is a Service, Not an Agent

**Design Decision**: `semantic_search` is a tool/service that adds results to `messages`, NOT `agent_responses`.

**Why**: `agent_responses` is semantically for agents only. Tools belong in `messages` for supervisor synthesis.

**Files**:
- `src/agents/orchestrator/graph/nodes/semantic_search.py` - Only adds to `messages`
- `src/agents/orchestrator/graph/supervisor.py` - Detects `semantic_search` results in `messages`, not `agent_responses`

**Loop Prevention**: Hardcoded check prevents routing back to `semantic_search` if it's already been called.

---

## Development Workflow

### How to Add a New Agent

1. **Create Agent Class** (`src/agents/specialists/{agent_name}_agent.py`)
   - Inherit from `BaseAgent`
   - Implement `analyze()` method
   - Load tools in `_load_tools()` if needed

2. **Create Graph Node** (`src/agents/orchestrator/graph/nodes/{agent_name}.py`)
   - Read `current_task_instruction` from `AgentState`
   - Call agent's `analyze()` method
   - Return to supervisor with `agent_responses` (NOT `messages`)

3. **Update Graph** (`src/agents/orchestrator/graph/graph.py`)
   - Add node to graph
   - Add conditional edge from supervisor
   - Update `RouteDecision` model if needed

4. **Update Supervisor Prompt** (`prompts/orchestrator/supervisor.txt`)
   - Add routing guidance for new agent

5. **Create Config** (`config/agents/{agent_name}.yaml`)
   - Set model to `gemini-2.5-flash`
   - Configure agent-specific settings

### How to Add a New Tool

**CRITICAL**: Follow the Canary Pattern. Copy from `portfolio_pacing_tool.py`.

1. **Create Tool Function** (`src/tools/{tool_name}.py`)
   - Use `@tool` decorator WITHOUT Pydantic schemas
   - Implement internal `safe_str()` sanitizers
   - Add explicit "WHEN NOT TO USE" section in description

2. **Add to Agent** (`src/agents/specialists/{agent}_agent.py`)
   - Import tool
   - Return from `_load_tools()` method

3. **Test**: Verify tool handles list inputs gracefully

**Reference**: See [Reference Implementation - Safe Tool Definition](#reference-implementation)

---

## Troubleshooting Playbook

### Issue: `AttributeError: 'list' object has no attribute 'strip'`

**Cause**: LLM sent `['value']` instead of `"value"`.

**Fix**: Already handled by Double-Ended Sanitation. Verify:
- [ ] Tool uses `@tool` decorator WITHOUT Pydantic schemas
- [ ] Tool function has `safe_str()` sanitizers
- [ ] Middleware normalization in `agent_loop.py` is active
- [ ] Pydantic validators (if any) handle lists BEFORE string operations

**Files to Check**:
- `src/utils/agent_loop.py` - Middleware normalization
- `src/tools/{tool_name}.py` - Tool sanitization
- `src/agents/specialists/{agent}_agent.py` - Pydantic Model Guard (if using input models)

### Issue: Agent calling tools unnecessarily

**Check**:
1. Tool description has "WHEN NOT TO USE" section?
2. Supervisor instruction injected into system prompt?
3. XML tags used for instruction injection?
4. No hardcoded keyword checks bypassing LLM reasoning?

**Fix**: Add/improve prompt guidance, don't add code checks.

### Issue: Duplicate agent responses

**Cause**: Agent nodes adding responses to both `messages` and `agent_responses`.

**Fix**: Only add to `agent_responses`. Streaming callback handles display.

**Files to Check**:
- `src/agents/orchestrator/graph/nodes/{agent}.py` - Should only add to `agent_responses`

### Issue: `semantic_search` infinite loop

**Cause**: Supervisor routing back to `semantic_search` after it already responded.

**Fix**: Hardcoded prevention check in supervisor (already implemented).

**File**: `src/agents/orchestrator/graph/supervisor.py` - Lines 143-149

### Issue: Module import errors after tool usage

**Cause**: Conditional imports inside methods.

**Fix**: Always import at module level (top of file), not conditionally inside methods.

**File**: `src/agents/specialists/guardian_agent.py` - `execute_agent_loop` import

### Issue: Chainlit async context error (Python 3.14+)

**Cause**: `sniffio` can't detect async library in Python 3.14.

**Fix**: Use `python run_chainlit.py` wrapper script which patches `sniffio` automatically.

### Issue: Chainlit Database Persistence Errors (RESOLVED - DISABLED)

**Status**: ✅ **RESOLVED** - Persistence disabled, all database operations patched

**Errors Previously Seen**:
```
asyncpg.exceptions.DataError: invalid input for query argument $11: 'json' (a boolean is required (got type str))
asyncpg.exceptions.InvalidTextRepresentationError: invalid input syntax for type json
asyncpg.exceptions.NotNullViolationError: null value in column "name" violates not-null constraint
asyncpg.exceptions.UndefinedTableError: relation "Element" does not exist
```

**Root Cause**: Chainlit's data layer has fundamental bugs incompatible with PostgreSQL strict typing.

**Solution Implemented**: 
- ✅ **Persistence DISABLED** - `CHAINLIT_DATABASE_URL=""` forced in `src/interface/chainlit/config.py`
- ✅ All database operations monkey-patched to no-ops (`create_step`, `update_step`, `get_thread`, `create_element`)
- ✅ Zero errors, clean console output
- ✅ App runs perfectly in "Ephemeral Mode" (chat history lost on refresh)

**Files**:
- `src/interface/chainlit/config.py` - Persistence disable and monkey-patches
- `docs/CHAINLIT_SQLITE_PERSISTENCE.md` - Future SQLite implementation guide

**Future Recommendation**: If persistence is needed, use **SQLite** instead of PostgreSQL (see `CHAINLIT_SQLITE_PERSISTENCE.md`).

---

## Reference Implementation

### Safe Tool Definition (Canary Pattern)

```python
from langchain_core.tools import tool

def _safe_str(value, default=""):
    """Safely convert any input to string, handling lists and None."""
    if value is None:
        return default
    if isinstance(value, list):
        if len(value) > 0:
            value = value[0]
        else:
            return default
    return str(value).strip() if value else default

@tool
def my_tool(account_id: str) -> str:
    """
    Tool description here.
    
    WHEN TO USE:
    - User explicitly asks for specific data
    
    WHEN NOT TO USE:
    - DO NOT use for introductions, greetings, or general conversation
    - DO NOT use when asked "who are you?" or role explanations
    """
    # Sanitize inputs
    account_id = _safe_str(account_id, "17")
    
    # Tool logic here
    return f"Result for account {account_id}"
```

**Key Points**:
- NO Pydantic schemas on `@tool` decorator
- Internal `_safe_str()` sanitization
- Explicit "WHEN NOT TO USE" in docstring

### Supervisor Node

```python
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.pydantic_v1 import BaseModel
from typing import Literal

class RouteDecision(BaseModel):
    next: Literal["semantic_search", "guardian", "specialist", "optimizer", "pathfinder", "FINISH"]
    instructions: str
    reasoning: str

def supervisor_node(state: AgentState, llm, supervisor_prompt, orchestrator_prompt):
    """Supervisor node using structured output for routing."""
    user_question = state.get("user_question", "")
    agent_responses = state.get("agent_responses", [])
    
    # Build context
    context = f"User Question: {user_question}\n\n"
    if agent_responses:
        context += "Agent Responses:\n"
        for r in agent_responses:
            context += f"- {r.get('agent', 'unknown')}: {r.get('response', '')[:200]}\n"
    
    # Route using structured output
    messages = [
        SystemMessage(content=supervisor_prompt),
        HumanMessage(content=f"{context}\n\nWhat should happen next?")
    ]
    
    structured_llm = llm.with_structured_output(RouteDecision)
    decision = structured_llm.invoke(messages)
    
    # Handle None decision (LLM failure)
    if decision is None:
        decision = RouteDecision(next="FINISH", instructions="", reasoning="LLM failed to provide routing decision.")
    
    # Generate response if FINISH
    if decision.next == "FINISH":
        response_messages = [
            SystemMessage(content=orchestrator_prompt or supervisor_prompt),
            HumanMessage(content=f"{context}\n\nProvide a helpful response to the user.")
        ]
        response = llm.invoke(response_messages)
        return {
            "agent_responses": agent_responses + [{"agent": "orchestrator", "response": response.content}],
            "next": "FINISH"
        }
    
    return {
        "current_task_instruction": decision.instructions,
        "next": decision.next
    }
```

**Key Points**:
- Uses `with_structured_output(RouteDecision)`
- Handles None decision gracefully
- Uses orchestrator prompt for FINISH responses

### Agent Node

```python
def guardian_node(state: AgentState, streaming_callback=None):
    """Guardian agent node."""
    instruction = state.get("current_task_instruction", "")
    user_question = state.get("user_question", "")
    
    # Get agent instance
    agent = get_agent("guardian")
    
    # Execute agent
    response = agent.analyze(
        question=user_question,
        context="",
        supervisor_instruction=instruction
    )
    
    # Emit streaming event
    if streaming_callback:
        streaming_callback("agent_response", response, {"agent": "guardian"})
    
    # Return to supervisor (ONLY agent_responses, NOT messages)
    return {
        "agent_responses": state.get("agent_responses", []) + [
            {"agent": "guardian", "response": response}
        ],
        "current_task_instruction": "",
        "next": ""
    }
```

**Key Points**:
- Reads from `AgentState`
- Only adds to `agent_responses` (NOT `messages`)
- Returns `"next": ""` to return to supervisor

### Middleware Normalization (`agent_loop.py`)

```python
def _normalize_tool_args(tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize tool arguments BEFORE Pydantic validation.
    
    Prevents crashes when LLM sends lists instead of strings.
    """
    normalized = {}
    for key, value in tool_args.items():
        if value is None:
            normalized[key] = value
        elif isinstance(value, list):
            # Extract first element if list
            normalized[key] = value[0] if len(value) > 0 else None
        elif isinstance(value, (str, int, float, bool)):
            normalized[key] = value
        else:
            normalized[key] = str(value) if value else None
    return normalized

# Apply BEFORE tool_func.invoke():
normalized_args = _normalize_tool_args(tool_args)
tool_result = tool_func.invoke(normalized_args)
```

**Key Points**:
- Runs BEFORE Pydantic validation
- Handles lists, None, and edge cases
- Prevents `.strip()` crashes

---

## Architectural Decision Records (ADRs)

### ADR 001: Robust Tool Execution Strategy

**Problem**: Tools crash when LLM sends lists (`['value']`) instead of strings (`"value"`). Pydantic validation calls `.strip()` on lists.

**Decision**: Implement **Two-Layer Defense**:
1. **Canary Pattern**: Tools use `@tool` WITHOUT Pydantic schemas, internal sanitization
2. **Middleware Normalization**: Normalize arguments BEFORE Pydantic validation

**Note**: Tool usage is controlled by prompt-driven reasoning. Agents reason about when tools are needed based on tool descriptions with "WHEN NOT TO USE" sections. No physical tool holstering is needed.

**Implementation**: See [Reference Implementation](#reference-implementation)

**Files**:
- `src/tools/portfolio_pacing_tool.py` - Canary Pattern
- `src/utils/agent_loop.py` - Middleware Normalization

### ADR 002: Routing via Structured Output (Not Tools)

**Problem**: Using tools for routing adds latency and breaks architectural pattern.

**Decision**: Supervisor uses structured output (`RouteDecision`) directly. NO tools for routing.

**Implementation**: See [Reference Implementation - Supervisor Node](#reference-implementation)

**Files**:
- `src/agents/orchestrator/graph/supervisor.py`
- `src/agents/orchestrator/graph/graph.py`

### ADR 003: State-Based Communication (Not Prop-Drilling)

**Problem**: Prop-drilling parameters through function signatures is brittle and unscalable.

**Decision**: Use LangGraph's shared state (`AgentState`) for all communication.

**Implementation**: See [Reference Implementation - Agent Node](#reference-implementation)

**Files**:
- `src/agents/orchestrator/graph/state.py`
- `src/agents/orchestrator/graph/nodes/*.py`

### ADR 004: Prompt-Driven Reasoning (Not Hardcoded Logic)

**Problem**: Hardcoded keyword checks (`if "keyword" in text`) are brittle and unscalable.

**Decision**: ALL decisions come from LLM reasoning guided by prompts. NO hardcoded logic.

**Implementation**: 
- Tool descriptions include "WHEN NOT TO USE" sections
- Supervisor instructions injected via XML tags (as guidance, not commands)
- System prompts guide LLM behavior
- Agents reason about tool usage based on clear descriptions

**Files**:
- `prompts/orchestrator/supervisor.txt`
- `config/prompts/{agent}/system.txt`
- `src/tools/*.py` - Tool descriptions with "WHEN NOT TO USE" sections

### ADR 005: Tools vs Agents - Semantic Distinction

**Problem**: `semantic_search` was incorrectly classified as an agent, causing routing confusion.

**Decision**: Tools/services add results to `messages`, NOT `agent_responses`. `agent_responses` is semantically for agents only.

**Implementation**: 
- `semantic_search` only adds to `messages`
- Supervisor detects `semantic_search` results in `messages`
- Hardcoded loop prevention for tools

**Files**:
- `src/agents/orchestrator/graph/nodes/semantic_search.py`
- `src/agents/orchestrator/graph/supervisor.py`

---

## Latest Session Learnings (December 2025)

### Portfolio Pacing Tool - Refactoring & Timezone Fixes (December 2025)

**Major Refactoring**: Split 894-line file into 3 manageable modules (all under 400 lines):
- `portfolio_pacing_tool.py` (185 lines): Main tool function
- `portfolio_pacing_helpers.py` (449 lines): Helper functions (calculations, formatting, CSV generation)
- `portfolio_pacing_loader.py` (185 lines): Analyzer loading and client config management

**Timezone Fix**: Fixed UTC vs PST mismatch when client config load fails:
- **Problem**: When `load_client_config()` import fails, `client_config` was `None`, causing Python to use PST dates while database query used UTC (no conversion).
- **Solution**: Explicit PST default when import fails: `client_config = {'timezone': 'PST', 'timezone_full': 'America/Los_Angeles'}`
- **Result**: Consistent PST timezone handling even when config file can't be loaded

**CSV Storage Fix**: Fixed `_GLOBAL_CSV_STORAGE` assignment error:
- **Problem**: Code was finding `torch.ops` module which has `_GLOBAL_CSV_STORAGE` attribute but it's not a dict (`_OpNamespace` object).
- **Solution**: Added type check: `if isinstance(storage, dict):` before assignment
- **Result**: Prevents errors when non-dict modules have this attribute

**Database Error Suppression**: Suppressed Chainlit Element table errors:
- **Problem**: Chainlit still tries to persist file elements even though persistence is disabled.
- **Solution**: Added `create_element` to no-op patch list in `config.py`
- **Result**: CSV files still work via message system, no database errors

**Files Modified**:
- `src/tools/portfolio_pacing_tool.py` - Refactored to use helpers and loader
- `src/tools/portfolio_pacing_helpers.py` - New helper module
- `src/tools/portfolio_pacing_loader.py` - New loader module
- `src/utils/agent_loop.py` - Fixed CSV storage type checking
- `src/interface/chainlit/config.py` - Added `create_element` patch

**Key Insights**: 
- Modular structure improves maintainability (no file exceeds 400 lines)
- Timezone consistency critical for accurate pacing calculations
- Client config file exists at `tools/campaign-portfolio-pacing/config/clients/tricoast media llc.json`

### Guardian Agent Output Formatting

**Change**: Updated Guardian agent to preserve tool output formatting instead of reformatting.

**Problem**: Agent was reformatting the beautifully structured tool output, losing emojis, sections, and visual separators.

**Solution**: Updated system prompt to:
1. **PRESERVE** tool output verbatim (with all formatting)
2. **ADD** brief context before tool output (1-2 sentences)
3. **ADD** strategic insights after tool output (2-3 bullet points)

**Files Modified**:
- `config/prompts/guardian_agent/system.txt` - Added "RESPONSE FORMATTING - CRITICAL INSTRUCTIONS" section

**Result**: Tool output is preserved exactly as formatted, with agent adding context and insights without rewriting.

### Chainlit Database Persistence (RESOLVED - DISABLED)

**Issue**: Persistent `asyncpg.exceptions.DataError` when Chainlit creates/updates Step records in PostgreSQL.

**Error Pattern**:
```
invalid input for query argument $11: 'json' (a boolean is required (got type str))
asyncpg.exceptions.InvalidTextRepresentationError: invalid input syntax for type json
asyncpg.exceptions.NotNullViolationError: null value in column "name" violates not-null constraint
asyncpg.exceptions.UndefinedTableError: relation "Element" does not exist
```

**Root Cause**: Chainlit's data layer has fundamental bugs:
- Passes raw strings to JSONB columns without proper JSON encoding
- Creates Step records without required fields
- Type mismatches between Chainlit's expectations and PostgreSQL strictness
- Attempts to persist file elements even when persistence is disabled

**Solution Implemented**: 
- ✅ **Persistence DISABLED** - Set `CHAINLIT_DATABASE_URL=""` in `src/interface/chainlit/config.py`
- ✅ All database operations monkey-patched to no-ops (`create_step`, `update_step`, `get_thread`, `create_element`)
- ✅ Zero errors, clean console output
- ✅ App runs perfectly in "Ephemeral Mode" (chat history lost on refresh)
- ✅ CSV file downloads still work via message system (no database persistence needed)

**Status**: ✅ **RESOLVED** - Persistence disabled, acceptable for POC

**Future Recommendation**: If persistence is needed, use **SQLite** instead of PostgreSQL:
- SQLite is permissive and handles Chainlit's data types gracefully
- No schema conflicts, no crashes
- Decouples "UI Memory" (SQLite) from "Agent Brain" (Postgres)
- See `docs/CHAINLIT_SQLITE_PERSISTENCE.md` for full implementation guide

**Related Files**:
- `docs/CHAINLIT_SQLITE_PERSISTENCE.md` - SQLite persistence guide
- `scripts/cleanup_chainlit_databases.sh` - Cleanup script for Postgres artifacts
- `src/interface/chainlit/config.py` - Persistence disable and monkey-patches

## Related Documentation

- **`docs/incidents/2025-11-29-guardian-loop.md`**: Detailed incident post-mortem
- **`docs/chainlit_ui_implementation_plan.md`**: Chainlit UI implementation details
- **`docs/chainlit_ui_tickets.md`**: Implementation ticket tracking

---

## Quick Reference

### File Locations

- Supervisor node: `src/agents/orchestrator/graph/supervisor.py`
- Guardian agent: `src/agents/specialists/guardian_agent.py`
- Guardian node: `src/agents/orchestrator/graph/nodes/guardian.py`
- State schema: `src/agents/orchestrator/graph/state.py`
- Graph definition: `src/agents/orchestrator/graph/graph.py`
- Agent loop: `src/utils/agent_loop.py`
- Tool example: `src/tools/portfolio_pacing_tool.py` (main function)
- Tool helpers: `src/tools/portfolio_pacing_helpers.py` (calculations, formatting)
- Tool loader: `src/tools/portfolio_pacing_loader.py` (analyzer loading)
- Supervisor prompt: `prompts/orchestrator/supervisor.txt`

### Key Patterns

- **Routing**: Structured output (`RouteDecision`) in supervisor
- **Instructions**: XML tags (`<supervisor_instruction>`) in agent prompts
- **Tool Usage**: "WHEN NOT TO USE" in tool descriptions
- **State Access**: Read from `AgentState` in nodes
- **Tool Safety**: Canary Pattern (no Pydantic schemas, internal sanitization)

### Anti-Patterns

- ❌ Hardcoded keyword checks (`if "keyword" in text`)
- ❌ Tool-calling for routing
- ❌ Special-casing edge cases in code
- ❌ Prop-drilling parameters
- ❌ Adding responses to both `messages` and `agent_responses`
- ❌ Conditional imports inside methods
- ❌ Pydantic schemas on `@tool` decorators

---

**Remember**: When in doubt, ask yourself: "Can this be solved with better prompts instead of code logic?" The answer is almost always yes.
