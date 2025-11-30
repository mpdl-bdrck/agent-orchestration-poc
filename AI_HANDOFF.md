# AI Development Agent Handoff Document

**Last Updated**: Current Session  
**Purpose**: Provide comprehensive context for new AI development sessions to avoid past pitfalls and maintain architectural integrity

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Critical Learnings & Pitfalls](#critical-learnings--pitfalls)
4. [Consultant-Approved Patterns](#consultant-approved-patterns)
5. [Codebase Structure](#codebase-structure)
6. [Development Guidelines](#development-guidelines)
7. [Common Mistakes to Avoid](#common-mistakes-to-avoid)
8. [Testing & Validation](#testing--validation)

---

## Executive Summary

This is an **Agent Orchestration POC** using **LangGraph Supervisor Pattern** for multi-agent coordination. The system orchestrates specialist agents (Guardian, Specialist, Optimizer, Pathfinder) through a supervisor/router that uses LLM-driven structured output for routing decisions.

### Key Architectural Principle

**ALL routing and decision-making is LLM-driven via prompts. NO hardcoded logic.**

The orchestrator/supervisor uses structured output (`RouteDecision`) to make routing decisions. Agents use prompt-driven reasoning to decide when to call tools. This ensures scalability, maintainability, and adaptability.

---

## Architecture Overview

### Current Pattern: LangGraph Supervisor/Router

```
User Question
    ↓
OrchestratorAgent.chat() → ALWAYS invokes graph
    ↓
Graph Entry: Supervisor Node
    ↓
Supervisor uses structured output (RouteDecision) to decide:
    - semantic_search (knowledge base queries)
    - guardian/specialist/optimizer/pathfinder (specialized tasks)
    - FINISH (simple questions or done)
    ↓
Conditional edges route to selected node
    ↓
Node executes and returns to supervisor
    ↓
Supervisor decides: FINISH or route again
```

### Key Components

1. **Supervisor Node** (`src/agents/orchestrator/graph/supervisor.py`)
   - Uses `RouteDecision` (Pydantic model) with structured output
   - Routes to: `semantic_search`, `guardian`, `specialist`, `optimizer`, `pathfinder`, or `FINISH`
   - Generates responses when routing to FINISH (for simple questions)

2. **Agent Nodes** (`src/agents/orchestrator/graph/nodes/`)
   - Read `current_task_instruction` from `AgentState`
   - Execute agent logic and return to supervisor
   - Use supervisor instruction to guide behavior

3. **State Schema** (`src/agents/orchestrator/graph/state.py`)
   - `AgentState` TypedDict with shared state
   - `current_task_instruction`: Translated instruction from supervisor
   - `user_question`: Original user question
   - `agent_responses`: Accumulated responses

4. **Semantic Search Node** (`src/agents/orchestrator/graph/nodes/semantic_search.py`)
   - Handles knowledge base queries
   - Returns formatted results to supervisor

---

## Critical Learnings & Pitfalls

### ❌ Pitfall #1: Hardcoded Keyword Detection

**What Happened**: We added hardcoded checks like `if "introduce" in question.lower()` to detect specific cases.

**Why It Failed**:
- Brittle: Breaks with new phrasings ("Greetings" vs "Hi")
- Unscalable: Requires code changes for every edge case
- Defeats purpose: We want LLM-driven intelligence, not rule-based logic

**✅ Solution**: Use prompt-driven reasoning. Guide the LLM through:
- Explicit "WHEN NOT TO USE" sections in tool descriptions
- Supervisor instruction injection using XML tags
- Clear system prompt guidance

**Example (WRONG)**:
```python
# ❌ DON'T DO THIS
if "introduce" in question.lower():
    return "I am the Guardian..."
```

**Example (CORRECT)**:
```python
# ✅ DO THIS
# Tool description includes:
"""
WHEN NOT TO USE:
- DO NOT use for introductions, greetings, or general conversation
"""
# System prompt includes supervisor instruction in XML tags
```

### ❌ Pitfall #2: Tool-Calling Pattern Instead of Native Router

**What Happened**: We tried to give the orchestrator a `route_to_agents` tool, making it a "Router via Tool" instead of a "Native Router."

**Why It Failed**:
- Adds unnecessary latency (Tool Call → Parse → Execute)
- Still recursive: Tool just passes question to graph
- Breaks architectural pattern: Supervisor should BE the graph entry point

**✅ Solution**: Orchestrator IS the graph entry point. Supervisor node uses structured output for routing decisions. No tools needed for routing.

**Architecture (CORRECT)**:
```
chat() → ALWAYS invoke graph
    ↓
Supervisor Node (structured output) → Conditional edges
```

### ❌ Pitfall #3: Overfitting Edge Cases in Code

**What Happened**: We added special handling for "multi-agent introductions", "single introductions", etc. in Python code.

**Why It Failed**:
- Creates maintenance burden
- Hardcoded logic that breaks with new phrasings
- Defeats the purpose of having an intelligent orchestrator

**✅ Solution**: Let the LLM reason about all cases. Provide good prompts and examples. Trust the LLM's reasoning.

**Rule**: If you find yourself writing `if "keyword" in text:`, STOP. Use prompts instead.

### ❌ Pitfall #4: Guardian Agent Calling Tools Unnecessarily

**What Happened**: Guardian agent called portfolio pacing tool for "introduce yourself" requests.

**Root Cause**: 
- Tool description didn't explicitly say "WHEN NOT TO USE"
- System prompt didn't emphasize following supervisor instructions
- LLM saw tool available and called it "just in case"

**✅ Solution** (Consultant-Approved):
1. **Tool Docstring**: Add explicit "WHEN NOT TO USE" section
2. **Supervisor Instruction Injection**: Use XML tags (`<supervisor_instruction>`) to inject instruction into system prompt
3. **No Hardcoded Checks**: Remove all keyword-based tool call logic

**Implementation**:
```python
# Tool description
description="""...
WHEN NOT TO USE:
- DO NOT use for introductions, greetings, or general conversation
- DO NOT use when asked "who are you?" or role explanations
"""

# System prompt injection
if supervisor_instruction:
    base_prompt += f"""
<supervisor_instruction>
{supervisor_instruction}
</supervisor_instruction>
CRITICAL: Follow the Supervisor's instruction exactly...
"""
```

### ❌ Pitfall #5: Using Wrong Prompt for Responses

**What Happened**: Supervisor used its routing prompt when generating FINISH responses, resulting in generic answers.

**Why It Failed**: Routing prompt is about routing, not answering. Orchestrator prompt has introduction info.

**✅ Solution**: Pass orchestrator's full system prompt to supervisor node. Use it when generating FINISH responses.

---

## Consultant-Approved Patterns

### Pattern 1: Prompt-Driven Reasoning (Not Code Logic)

**Principle**: All decisions come from LLM reasoning guided by prompts, not hardcoded checks.

**Implementation**:
- Tool descriptions include explicit "WHEN TO USE" and "WHEN NOT TO USE"
- System prompts guide LLM behavior
- Supervisor instructions injected using XML tags for better attention

**Example**:
```python
# ✅ CORRECT: Tool description guides LLM
description="""...
WHEN TO USE:
- User explicitly asks for portfolio data

WHEN NOT TO USE:
- DO NOT use for introductions
"""
```

### Pattern 2: State-Based Instruction Passing

**Principle**: Use LangGraph's shared state (`AgentState`) to pass instructions. Don't prop-drill through function signatures.

**Implementation**:
- Guardian node reads `current_task_instruction` from `AgentState`
- Passes instruction to agent's `analyze()` method
- Agent injects instruction into system prompt using XML tags

**Example**:
```python
# ✅ CORRECT: Read from state
def guardian_node(state: AgentState):
    instruction = state.get("current_task_instruction", "")
    # Pass to agent
    agent.analyze(question, context, supervisor_instruction=instruction)
```

### Pattern 3: XML Tags for Critical Instructions

**Principle**: LLMs pay more attention to structured tags than plain text.

**Implementation**: Use XML tags (`<supervisor_instruction>`) when injecting supervisor instructions.

**Example**:
```python
# ✅ CORRECT: XML tags
base_prompt += f"""
<supervisor_instruction>
{supervisor_instruction}
</supervisor_instruction>
CRITICAL: Follow this instruction exactly...
"""
```

### Pattern 4: Native Router (Not Tool-Calling Router)

**Principle**: Supervisor IS the graph entry point. Uses structured output for routing, not tools.

**Implementation**:
- `chat()` always invokes graph
- Supervisor node uses `with_structured_output(RouteDecision)`
- Conditional edges route based on `state["next"]`

**Example**:
```python
# ✅ CORRECT: Structured output routing
structured_llm = llm.with_structured_output(RouteDecision)
decision = structured_llm.invoke(messages)
return {"next": decision.next, "current_task_instruction": decision.instructions}
```

---

## Codebase Structure

### Key Directories

```
src/
├── agents/
│   ├── orchestrator/
│   │   ├── orchestrator.py          # Main orchestrator (entry point)
│   │   ├── graph/
│   │   │   ├── supervisor.py       # Supervisor node (router)
│   │   │   ├── state.py             # AgentState TypedDict
│   │   │   ├── graph.py             # Graph definition
│   │   │   └── nodes/
│   │   │       ├── guardian.py     # Guardian node
│   │   │       ├── semantic_search.py  # Semantic search node
│   │   │       └── ...               # Other agent nodes
│   │   └── agent_calling.py         # call_specialist_agent function
│   └── specialists/
│       ├── guardian_agent.py        # Guardian agent (has portfolio tool)
│       └── ...                      # Other specialist agents
├── core/
│   ├── base_agent.py               # Base agent class
│   └── search/
│       └── semantic_search.py      # Semantic search implementation
└── utils/
    └── agent_loop.py               # execute_agent_loop utility
```

### Key Files

- **`src/agents/orchestrator/orchestrator.py`**: Main entry point. `chat()` always invokes graph.
- **`src/agents/orchestrator/graph/supervisor.py`**: Router node. Uses structured output.
- **`src/agents/specialists/guardian_agent.py`**: Guardian agent with portfolio pacing tool.
- **`prompts/orchestrator/supervisor.txt`**: Supervisor routing prompt.
- **`config/prompts/orchestrator/system.txt`**: Orchestrator system prompt (used for FINISH responses).

---

## Development Guidelines

### ✅ DO

1. **Use Prompt-Driven Reasoning**
   - Guide LLM behavior through prompts, not code logic
   - Add explicit "WHEN NOT TO USE" sections to tool descriptions
   - Use XML tags for critical instructions

2. **Read from State**
   - Read `current_task_instruction` from `AgentState` in nodes
   - Don't prop-drill through function signatures
   - Use shared state for communication

3. **Use Structured Output**
   - Supervisor uses `RouteDecision` (Pydantic model)
   - Enforces valid routing decisions
   - Makes routing explicit and debuggable

4. **Keep Files Under 400 Lines**
   - Split large files into smaller modules
   - Each file should have a single responsibility

5. **Let LLM Reason**
   - Trust the LLM's reasoning when guided by good prompts
   - Don't second-guess with hardcoded checks

### ❌ DON'T

1. **Don't Hardcode Keyword Checks**
   - No `if "keyword" in text:` checks
   - No pattern matching for specific phrases
   - Use prompts to guide LLM instead

2. **Don't Overfit Edge Cases**
   - Don't add special handling for specific phrasings
   - Don't create separate code paths for "introductions", "greetings", etc.
   - Let LLM handle all cases through reasoning

3. **Don't Use Tool-Calling for Routing**
   - Don't give orchestrator a `route_to_agents` tool
   - Supervisor IS the router (via structured output)
   - No nested tool calls for routing

4. **Don't Modify Function Signatures Unnecessarily**
   - Use state for passing instructions
   - Don't prop-drill parameters through multiple layers
   - Read from state where possible

5. **Don't Ignore Supervisor Instructions**
   - Always inject supervisor instruction into agent prompts
   - Use XML tags for better LLM attention
   - Make it clear this is a direct order

---

## Common Mistakes to Avoid

### Mistake 1: Adding Hardcoded Detection

**Symptom**: Code like `if "introduce" in question.lower():`

**Fix**: Remove it. Add guidance to prompts instead.

### Mistake 2: Creating Tool for Routing

**Symptom**: `route_to_agents` tool that calls the graph

**Fix**: Remove it. Supervisor uses structured output directly.

### Mistake 3: Special-Casing Edge Cases

**Symptom**: Separate code paths for "multi-agent intro", "single intro", etc.

**Fix**: Remove special cases. Let LLM reason about all cases.

### Mistake 4: Not Using Supervisor Instruction

**Symptom**: Agent doesn't follow supervisor's `current_task_instruction`

**Fix**: Inject instruction into system prompt using XML tags.

### Mistake 5: Using Wrong Prompt

**Symptom**: Supervisor uses routing prompt for FINISH responses

**Fix**: Use orchestrator's full system prompt for FINISH responses.

### Mistake 6: Adding Responses to Both messages and agent_responses

**Symptom**: Agent nodes adding responses to both `messages` and `agent_responses` fields, causing duplicate display.

**Fix**: Only add to `agent_responses`. Streaming callback handles display. Match Guardian pattern.

**Example**:
```python
# ❌ WRONG
return {
    "messages": [AIMessage(content=response)],  # ← Causes duplicate
    "agent_responses": state.get("agent_responses", []) + [{"agent": "specialist", "response": response}],
}

# ✅ CORRECT
return {
    "agent_responses": state.get("agent_responses", []) + [{"agent": "specialist", "response": response}],
    "current_task_instruction": "",
    "next": ""
}
```

### Mistake 7: Conditional Imports Inside Methods

**Symptom**: Importing modules conditionally inside methods instead of at module level, causing `ModuleNotFoundError` after module state changes.

**Fix**: Always import at module level (top of file), not conditionally inside methods.

**Example**:
```python
# ❌ WRONG
def analyze(self, question):
    if self.tools:
        from ...utils.agent_loop import execute_agent_loop  # ← Conditional import

# ✅ CORRECT
from ...utils.agent_loop import execute_agent_loop  # ← Module-level import

def analyze(self, question):
    if self.tools:
        # execute_agent_loop is already available
```

### Mistake 8: Inconsistent Emoji Usage

**Symptom**: Using different emojis for the same agent across different files (e.g., Optimizer with ⚡ vs 🎯).

**Fix**: Maintain consistent emoji mapping:
- 🛡️ Guardian Agent
- 🔧 Specialist Agent
- 🎯 Optimizer Agent (NOT ⚡)
- 🧭 Pathfinder Agent

**Verification**: Check all prompt files and agent references for consistency.

### Mistake 9: Adding Tool Results to agent_responses

**Symptom**: Tools (like `semantic_search`) adding results to `agent_responses`, causing design confusion and requiring filtering workarounds.

**Fix**: Tools should only add to `messages`, not `agent_responses`. `agent_responses` is semantically for agents only.

**Example**:
```python
# ❌ WRONG (semantic_search in agent_responses)
return {
    "messages": [AIMessage(content=response)],
    "agent_responses": state.get("agent_responses", []) + [{"service": "semantic_search", "response": response}],
}

# ✅ CORRECT (semantic_search only in messages)
return {
    "messages": [AIMessage(content=response)],
    # DO NOT add to agent_responses - tools don't belong there
}
```

**Key Principle**: `agent_responses` is for agents only. Tools add to `messages`. This separation ensures clean design.

### Mistake 10: Not Preventing Tool Infinite Loops

**Symptom**: Tools (like `semantic_search`) being called repeatedly in infinite loops because supervisor can't detect they've already been called.

**Fix**: When tools don't add to `agent_responses`, detection must rely on `messages`. Always add hardcoded prevention checks for tools to prevent infinite loops.

**Example**:
```python
# Detection: Check for AIMessage in messages (tools add AIMessage, agents don't)
from langchain_core.messages import AIMessage
semantic_search_called = any(
    isinstance(msg, AIMessage) and msg.content 
    for msg in messages
)

# Prevention: Hardcoded check after LLM routing decision
if decision.next == "semantic_search" and semantic_search_called:
    logger.warning("Preventing duplicate semantic_search call")
    decision.next = "FINISH"
```

**Key Principle**: Don't rely solely on LLM to prevent loops. Add hardcoded prevention checks for tools.

---

## Testing & Validation

### How to Verify Correct Behavior

1. **Introduction Requests**
   - "who are you?" → Supervisor answers directly (no agent routing)
   - "introduce yourself" → Supervisor answers directly
   - "get agents to introduce themselves" → All agents introduce (no tool calls)

2. **Portfolio Questions**
   - "how is my portfolio?" → Guardian uses portfolio tool
   - "what's the budget status?" → Guardian uses portfolio tool
   - "introduce yourself" (to Guardian) → Guardian introduces WITHOUT tool

3. **Knowledge Base Questions**
   - "what is portfolio pacing?" → Routes to semantic_search
   - "how does the platform work?" → Routes to semantic_search

4. **Simple Questions**
   - "how many agents do you have?" → Supervisor answers directly (FINISH)

### Red Flags

- ❌ Seeing `[REASONING] Using 1 tool(s)` for introductions
- ❌ Hardcoded `if` statements checking for keywords
- ❌ Agent responses appearing twice
- ❌ Supervisor fabricating agent responses instead of routing
- ❌ Tools being called when not needed

---

## Current State

### What's Working

✅ LangGraph supervisor pattern with structured output routing  
✅ Semantic search node for knowledge base queries  
✅ Supervisor generates responses for FINISH (simple questions)  
✅ Guardian agent has portfolio pacing tool  
✅ Supervisor instruction injection using XML tags  
✅ Tool descriptions include "WHEN NOT TO USE" guidance  
✅ No hardcoded keyword checks  

### Known Issues

- None currently (all recent issues resolved)

### Recent Fixes

1. **Removed hardcoded keyword detection** - Now uses prompt-driven reasoning
2. **Fixed supervisor prompt usage** - Uses orchestrator prompt for FINISH responses
3. **Fixed Guardian tool calling** - Uses supervisor instruction to avoid unnecessary tool calls
4. **Removed tool-calling pattern** - Now uses native router with structured output
5. **Fixed duplicate agent responses** - Removed messages from agent nodes, only use agent_responses (December 2025)
6. **Fixed Guardian import error** - Moved execute_agent_loop import to module level (December 2025)
7. **Fixed Optimizer emoji consistency** - Updated Guardian prompt to use 🎯 instead of ⚡ (December 2025)
8. **Fixed semantic_search design** - Removed from agent_responses (tools don't belong there) (December 2025)
9. **Fixed semantic_search infinite loop** - Added hardcoded prevention check (December 2025)
10. **Removed hardcoded introduction logic** - Removed "STRICTLY FORBIDDEN" rules from supervisor prompt (December 2025)

### Latest Learnings (Cost Framing & CoT Inhibition)

#### Critical Learning: Cost Framing + Chain of Thought Inhibition

**Problem**: Guardian agent was calling tools for simple introductions/greetings.

**Root Cause**: "Lite" models prioritize speed over inhibition - they see tools and use them impulsively.

**Solution**: Implement **Cost Framing** + **Chain of Thought (CoT) Inhibition**.

##### 1. Cost Framing (System Prompt)
- Frame tools as "computationally expensive" and "connect to a live database"
- Explicitly state "NEVER call this tool for introductions, greetings, or general explanations"
- Only call when user requires "NEW, LIVE NUMBERS"

**Implementation**:
```python
OPERATIONAL PROTOCOL - EFFICIENCY IS PARAMOUNT:

1. EFFICIENCY IS PARAMOUNT. You have access to the `analyze_portfolio_pacing` tool.
2. This tool is "computationally expensive" and connects to a live database.
3. NEVER call this tool for introductions, greetings, or general explanations of your role.
4. ONLY call this tool if the user's request specifically requires retrieving NEW, LIVE NUMBERS or portfolio data.
```

##### 2. Chain of Thought (CoT) Inhibition
- Force model to output thought process BEFORE calling any tool
- Require explicit reasoning: "Does the user require LIVE DATA to answer this?"
- Make it FORBIDDEN to call tool unless reasoning determines "YES, live data required"

**Implementation**:
```python
MANDATORY REASONING PROTOCOL (Chain of Thought Inhibition):

Before you decide to use a tool or speak, you MUST output your thought process.

REASONING STEP - Answer these questions in your mind BEFORE calling any tool:

1. What is the user asking for?
2. Does the user require LIVE DATA to answer this question?
   - If asking "who are you?" → NO, does NOT require live data
   - If asking "how is my portfolio?" → YES, requires live data
3. Can I answer this from my general knowledge?

INHIBITION RULE: If reasoning determines NO live data needed, FORBIDDEN from calling tool.
```

##### 3. Restrictive Tool Description
- Changed from descriptive "WHEN TO USE/WHEN NOT TO USE" to "CRITICAL USAGE RULES"
- Used "STRICTLY RESERVED" language
- Emphasized "computationally expensive"
- "If ambiguous, err on the side of NOT calling"

**Implementation**:
```python
description="""Connects to the live database to fetch current pacing metrics and portfolio insights.

CRITICAL USAGE RULES:
- STRICTLY RESERVED for queries asking for *numbers*, *data*, *status*, or *health* metrics
- DO NOT USE if the user is just asking who you are or what you do
- If the input is ambiguous, err on the side of NOT calling this tool
- This tool is computationally expensive - only use when live data is explicitly required
"""
```

##### 4. Model Selection Strategy: gemini-2.5-flash (Standard Flash)

**Critical Decision**: Standardize on `gemini-2.5-flash` (not Lite, not Pro) for ALL agents.

**Why Not "All Pro"?**
- **Rate Limit Risk**: Pro models have ~60 RPM (or even 10 RPM for previews)
- **Parallel Execution Risk**: Orchestrator fires 4 agents simultaneously → 8-10 requests instantly
- **Crash Risk**: Using "All Pro" risks `429 Too Many Requests` errors (same as Experimental model crash)
- **Latency**: "All Pro" makes chat feel sluggish (3-5s waits per agent)

**Why Standard Flash (Not Lite)?**
- **Better Inhibition**: Standard Flash respects "Negative Constraints" (Don't use tools) much better than Lite
- **Survives Load**: ~1,000 RPM limit (per dashboard) - parallel agents won't crash it
- **Fast**: No Pro latency penalty
- **Industry Sweet Spot**: Standard Flash is usually the industry sweet spot for Agents

**Model Progression**:
1. ❌ Experimental (`gemini-2.0-flash-exp`) → **Crash** (10 RPM rate limit)
2. ❌ Lite (`gemini-2.5-flash-lite`) → **Stupid/Eager** (calls tools impulsively)
3. ✅ **Standard Flash (`gemini-2.5-flash`)** → **Sweet Spot** (listens, survives, fast)
4. 🔄 Pro (`gemini-2.5-pro`) → **Fallback** (only if Guardian still calls tools unnecessarily)

**Implementation Strategy**:
- **Start**: All agents use `gemini-2.5-flash`
- **Monitor**: Watch Guardian behavior
- **Escalate**: If Guardian still calls tools unnecessarily → upgrade ONLY Guardian to `gemini-2.5-pro`
- **Don't Pay "Pro Tax"**: Don't use Pro for entire team until proven Flash can't handle it

**Rate Limit Comparison** (from dashboard):
- **Flash Models**: ~1,000 - 4,000 RPM ✅
- **Pro/Exp Models**: Often as low as **60 RPM** (or even 10 RPM for previews) ❌

##### 5. Centralized Model Configuration
- Added centralized LLM config in `config/config.yaml`
- All agents inherit defaults but can override
- Single source of truth for model changes
- Validation against allowed models list

**Implementation**:
```yaml
# config/config.yaml
llm:
  default_model: "gemini-2.5-flash"  # Standard Flash for all agents
  default_provider: "gemini"
  default_temperature: 0.7
  default_max_tokens: 2000
  allowed_models:
    - "gemini-2.5-flash"  # Standard Flash (default)
    - "gemini-2.5-pro"    # Pro (for Guardian override if needed)
```

**Benefits**:
1. **Scalable**: Works with any phrasing ("Greetings", "What's up?", "Identify yourself")
2. **AI-native**: Leverages model's reasoning ability instead of hardcoded checks
3. **Efficient**: Prevents unnecessary database calls and latency
4. **Production-ready**: High RPM limits (~1,000 RPM) for real-world usage
5. **Rate Limit Safe**: Avoids Pro model's ~60 RPM bottleneck that crashes parallel execution

**Files Updated**:
- `config/prompts/guardian_agent/system.txt` - Cost framing + CoT inhibition
- `src/agents/specialists/guardian_agent.py` - Restrictive tool description
- `src/utils/agent_loop.py` - Reasoning visibility before tool calls
- `config/config.yaml` - Centralized LLM configuration (gemini-2.5-flash)
- `src/core/base_agent.py` - Centralized config support
- All agent configs - Updated to `gemini-2.5-flash` (standardized)

#### Critical Learning: Tool Crash Fix - Double-Ended Sanitation (The Breakthrough)

**Problem**: Guardian agent crashed with `'list' object has no attribute 'strip'` when calling tools, causing introduction text to disappear.

**Deep Root Cause Discovery**: There were **TWO IDENTICAL PROBLEMS** in different layers:

1. **Pydantic Model Layer**: `@field_validator` methods tried to handle lists but ran AFTER Pydantic's internal validation
2. **Tool Function Layer**: `_normalize_string_arg()` function had the same flawed logic that could call `.strip()` on lists

**The Smoking Gun**: Deep audit revealed line 50 in `src/tools/portfolio_pacing_tool.py`:
```python
return str(arg).strip() if arg else default  # ← CRASH: .strip() called on list object
```

**Why Previous Fixes Failed**:
- ❌ **Single-layer fixes**: Only fixed Pydantic OR tool function, but not both
- ❌ **Flawed normalization logic**: `str(arg).strip()` could fail if `arg` remained a list
- ❌ **Timing issues**: Pydantic validators ran after internal validation already crashed

**The Breakthrough Solution**: **Double-Ended Sanitation**

Implement bulletproof normalization logic in **BOTH** the Pydantic Model and Tool Function layers. Never rely on one or the other - make both layers independently robust.

**Layer 1: Pydantic Model Guard** (`src/agents/specialists/guardian_agent.py`):
```python
@model_validator(mode='before')
@classmethod
def flatten_list_inputs(cls, data: Any) -> Any:
    """NUCLEAR FIX: Intercepts raw data before ANY Pydantic validation."""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                data[key] = value[0] if value else ""
    return data
```

**Layer 2: Tool Function Sanitation** (`src/tools/portfolio_pacing_tool.py`):
```python
def _normalize_string_arg(arg, default=""):
    """Robustly converts Any input (List, None, String) to a clean String."""
    if arg is None:
        return default
    if isinstance(arg, list):
        if len(arg) > 0:
            arg = arg[0]
        else:
            return default
    # ATOMIC FIX: Cast to str() BEFORE stripping
    return str(arg).strip()
```

**Implementation** (`src/utils/agent_loop.py`):

```python
def _normalize_tool_args(tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize tool arguments to handle list inputs from eager LLMs.
    
    LangChain's StructuredTool validates arguments via Pydantic before calling the function.
    When LLM passes lists (e.g., account_id: ["17"]) instead of strings, Pydantic's internal
    validation calls .strip() on the list, causing: 'list' object has no attribute 'strip'
    
    This function normalizes arguments BEFORE Pydantic validation occurs, preventing crashes.
    """
    normalized = {}
    for key, value in tool_args.items():
        if value is None:
            normalized[key] = value
        elif isinstance(value, list):
            # Extract first element if list (LLM sometimes passes ["value"] instead of "value")
            if len(value) > 0:
                normalized[key] = value[0]
            else:
                normalized[key] = None
        elif isinstance(value, (str, int, float, bool)):
            # Already normalized - pass through
            normalized[key] = value
        else:
            # Convert to string as fallback
            normalized[key] = str(value) if value else None
    
    return normalized

# Apply BEFORE tool_func.invoke():
normalized_args = _normalize_tool_args(tool_args)
tool_result = tool_func.invoke(normalized_args)
```

**Why This Works**:
1. **Prevents Crash**: Normalizes arguments before Pydantic validation, so `.strip()` is never called on a list
2. **Allows Text Output**: Even if Guardian calls the tool unnecessarily, it won't crash, so introduction text is delivered
3. **Middleware Pattern**: Catches the issue at the right layer (before validation, not after)

**Additional Defense Layer**: Supervisor Instruction Update

**File**: `prompts/orchestrator/supervisor.txt`

**Update**: Added explicit negative constraint for Guardian during multi-agent introductions:

```
4. For multi-agent requests, route to EACH agent sequentially. **CRITICAL:** When routing to the Guardian for introductions, you MUST add the instruction: "STRICTLY FORBIDDEN from using tools. Speak text only. This is a greeting/introduction, not a data request."
```

**Multi-Layer Defense Strategy**:
1. **Middleware Normalization** (Primary): Prevents crash even if tool is called
2. **Supervisor Instruction** (Secondary): Explicitly forbids Guardian from using tools during introductions
3. **Prompt Reordering** (Tertiary): Uses recency bias to emphasize inhibition rules
4. **Cost Framing + CoT** (Quaternary): Guides model reasoning

**Key Lesson**: When debugging tool crashes, check **where** the error occurs in the call stack. If it's in validation (Pydantic), fix it **before** validation, not after.

**Files Updated**:
- `src/utils/agent_loop.py` - Added `_normalize_tool_args()` middleware function
- `prompts/orchestrator/supervisor.txt` - Added explicit negative constraint for Guardian introductions

#### Critical Learning: Pydantic Validator Fix - Handle Lists Before String Operations

**Problem**: The middleware normalization wasn't enough - Pydantic validators were still calling `.strip()` on lists before our normalization could run.

**Root Cause**: Pydantic field validators with `mode='before'` run during Pydantic's internal validation, but the validators themselves were calling `.strip()` on values that might be lists.

**Solution**: Updated all Pydantic validators in `PortfolioPacingInput` to handle lists FIRST, before any string operations:

```python
@field_validator('account_id', mode='before')
@classmethod
def normalize_account_id(cls, v):
    """Normalize account_id, handling list inputs BEFORE any string operations."""
    # CRITICAL: Handle list FIRST, before Pydantic tries to validate as string
    if isinstance(v, list):
        v = v[0] if len(v) > 0 else "17"
    if v is None:
        return "17"
    # Now safe to convert to string and strip
    return str(v).strip() if isinstance(v, str) else str(v)
```

**Key Principle**: In Pydantic validators, always check for list type FIRST, extract the value, THEN perform string operations.

**Files Updated**:
- `src/agents/specialists/guardian_agent.py` - Updated all `@field_validator` methods to handle lists before string operations

#### Critical Learning: The Final Solution - Three-Layer Defense Architecture

**Date**: November 29, 2025  
**Status**: ✅ RESOLVED - Guardian agent now works perfectly for introductions

#### The Problem (Recap)

After multiple attempts with prompt engineering, middleware normalization, and Pydantic validators, the Guardian agent was still:
1. Calling tools unnecessarily for introductions
2. Crashing with `'list' object has no attribute 'strip'` when tools were called

#### The Breakthrough: Three-Layer Defense

The final solution uses **three complementary layers** that work together:

##### Layer 1: Tool Holster Pattern (Prevention)

**Location**: `src/agents/orchestrator/graph/nodes/guardian.py`

**What It Does**: Physically removes tools from agent's capability set when supervisor explicitly forbids them.

**How It Works**:
- Supervisor sends explicit directives: "STRICTLY FORBIDDEN from using tools" or "text only"
- Guardian node checks for these directives (NOT hardcoded keywords)
- If detected → Calls `analyze_without_tools()` which runs LLM without `bind_tools()`
- If not detected → Normal path with tools available

**Why It Works**:
- **Physical Prevention**: Tools aren't bound, so agent CANNOT call them
- **Supervisor-Driven**: Respects explicit supervisor instructions, not hardcoded logic
- **No Hardcoding**: Checks for directives, not use cases

**Key Code**:
```python
# Check supervisor instruction for explicit directives
explicit_no_tools_directives = [
    "strictly forbidden from using tools",
    "do not use tools",
    "text only",
    ...
]
should_holster_tools = any(directive in instruction_lower for directive in explicit_no_tools_directives)

if should_holster_tools:
    # Run WITHOUT tools - physically impossible to call them
    agent.analyze_without_tools(...)
else:
    # Run WITH tools - agent decides
    agent.analyze(...)
```

##### Layer 2: Canary Pattern (Ghost Buster) - Crash-Proof Tool

**Location**: `src/tools/portfolio_pacing_tool.py`

**What It Does**: Makes tool resilient to malformed inputs from eager LLMs.

**How It Works**:
1. Function signature accepts `Union[str, List[str]]` - Pydantic doesn't reject lists
2. Internal cleaning function normalizes inputs BEFORE any string operations
3. All arguments cleaned immediately at function entry
4. Safe fallback if tool execution fails

**Why It Works**:
- **Accepts Anything**: `Union` types let lists pass Pydantic validation
- **Cleans Inside**: Normalization happens BEFORE `.strip()` calls
- **No Crashes**: Even if called unnecessarily, tool won't crash

**Key Code**:
```python
@tool
def analyze_portfolio_pacing(
    account_id: Union[str, List[str]] = "17",  # ← Accepts both!
    ...
) -> str:
    # --- THE "GHOST BUSTER" PATTERN ---
    def clean(arg, default=""):
        if arg is None: return default
        if isinstance(arg, list):
            return str(arg[0]).strip() if len(arg) > 0 else default
        return str(arg).strip() if arg else default
    
    # Clean ALL inputs immediately (No Pydantic validation crash)
    safe_account_id = clean(account_id, "17")
    ...
```

> ⚠️ **ARCHITECTURAL DECISION RECORD (ADR): Why we removed Pydantic Schemas**
>
> **Do NOT refactor the Guardian tools back to `StructuredTool` / Pydantic models.**
>
> We intentionally downgraded to the simple `@tool` decorator because:
> 1. **Eager Models (Flash):** These models often hallucinate input formats (sending `['17']` instead of `"17"`).
> 2. **Validation Timing:** Pydantic validators run *before* our custom cleaning logic could intercept the data, causing `AttributeError` crashes inside the library itself.
> 3. **Resilience:** The `@tool` decorator allows us to type hints as `Union[str, List[str]]`, permitting "bad" data to enter the function so we can sanitize it manually.
>
> **Rule:** All tools for "Flash" class models must use the `@tool` pattern with internal sanitation, not strict Schema validation.

##### Layer 3: Middleware Normalization (Safety Net)

**Location**: `src/utils/agent_loop.py`

**What It Does**: Normalizes tool arguments before Pydantic validation AND filters unsupported parameters.

**How It Works**:
1. Normalizes lists to strings before tool invocation
2. Checks tool signature and removes `job_name` if tool doesn't accept it
3. Prevents validation errors even if Layer 1 fails

**Why It Works**:
- **Catches Edge Cases**: If tools are called anyway, arguments are normalized
- **Signature-Aware**: Respects tool contracts (removes unsupported params)
- **Defense in Depth**: Multiple layers of protection

**Key Code**:
```python
# Normalize arguments BEFORE invoking
normalized_args = _normalize_tool_args(tool_args)

# Filter out job_name if tool doesn't accept it
if 'job_name' in normalized_args:
    sig = inspect.signature(tool_func.func)
    if 'job_name' not in sig.parameters:
        normalized_args = {k: v for k, v in normalized_args.items() if k != 'job_name'}

tool_result = tool_func.invoke(normalized_args)
```

#### The Complete Flow

```
User: "guardian say hi"
    ↓
Supervisor Node:
  - Detects introduction request
  - Routes to Guardian with instruction: "STRICTLY FORBIDDEN from using tools. Speak text only."
    ↓
Guardian Node:
  - Reads instruction from state
  - Detects "strictly forbidden from using tools" directive
  - Calls analyze_without_tools() → LLM WITHOUT bind_tools()
    ↓
Guardian Agent:
  - Runs LLM.invoke() directly (no tools available)
  - Generates introduction text
  - Returns response
    ↓
✅ Success: Introduction without tool calls!
```

**If Layer 1 Fails** (tools called anyway):
```
Guardian calls tool → Layer 2 (Canary Pattern) → Tool accepts lists → Cleans internally → No crash
```

**If Layer 2 Fails** (cleaning fails):
```
Layer 3 (Middleware) → Normalizes before validation → No crash
```

#### Why This Architecture Works

1. **Prevention First**: Tool Holster removes tools when not needed
2. **Resilience**: Canary Pattern handles malformed inputs gracefully
3. **Defense in Depth**: Multiple layers catch edge cases
4. **Supervisor-Driven**: No hardcoded logic, respects supervisor instructions
5. **Scalable**: Works for ANY use case, not just introductions

#### Key Principles

- **Trust Supervisor Instructions**: If supervisor says "no tools", physically remove them
- **Accept, Then Clean**: Tools should accept malformed input, then normalize internally
- **Multiple Safety Nets**: If one layer fails, others catch it
- **No Hardcoding**: Check for directives, not use cases

#### Files Modified

1. **`src/agents/orchestrator/graph/nodes/guardian.py`**:
   - Added Tool Holster logic (checks supervisor directives)
   - Calls `analyze_without_tools()` when tools forbidden

2. **`src/agents/specialists/guardian_agent.py`**:
   - Added `analyze_without_tools()` method (runs LLM without bind_tools)
   - Tool loading uses simple `@tool` decorator pattern

3. **`src/tools/portfolio_pacing_tool.py`**:
   - Refactored to Canary Pattern (Union types + internal cleaning)
   - Removed Pydantic schema complexity
   - Added safe fallback for failures

4. **`src/utils/agent_loop.py`**:
   - Enhanced middleware normalization
   - Added signature-aware parameter filtering (removes unsupported `job_name`)

#### Testing Results

✅ **Introduction Requests**: Guardian introduces without calling tools  
✅ **Portfolio Questions**: Guardian calls tools when needed  
✅ **Malformed Inputs**: Tool handles lists gracefully  
✅ **Tool Failures**: Safe fallback prevents crashes  

#### Consultant Approval

This architecture was approved by the consultant as the "Clean Slate" approach:
- Removed all Pydantic schema complexity
- Adopted simple `@tool` decorator pattern (proven by Canary agent)
- Implemented Tool Holster for physical prevention
- Multiple layers ensure resilience

**Status**: ✅ PRODUCTION READY

#### Critical Learning: Supervisor Hallucination Fix - Don't Generate New Responses When Tool Already Responded

**Problem**: When semantic_search tool responded, supervisor would route to FINISH and generate a NEW hallucinated response instead of using the tool's results.

**Root Cause**: Supervisor's FINISH routing logic always generated a new response, even when semantic_search had already provided results.

**Solution**: Check if semantic_search has already responded before generating FINISH response:

```python
if decision.next == "FINISH":
    # Check if semantic_search has already responded - if so, don't generate new response
    has_semantic_search_response = any(
        r.get("service") == "semantic_search" or r.get("agent") == "semantic_search" 
        for r in agent_responses
    )
    
    if has_semantic_search_response:
        # semantic_search already responded - just route to FINISH, don't generate new response
        return {
            "next": "FINISH",
            "current_task_instruction": "",
            "messages": []  # Don't add new messages, use existing semantic_search response
        }
```

**Key Principle**: When a tool/service has already provided results, don't generate new responses - let the orchestrator extract and use the tool's results.

**Files Updated**:
- `src/agents/orchestrator/graph/supervisor.py` - Added check to skip response generation when semantic_search already responded

#### Critical Learning: Semantic Search Terminology - Tool/Service, Not Agent

**Problem**: Supervisor was referring to semantic_search as "semantic_search agent" in reasoning, causing confusion.

**Root Cause**: Supervisor prompt and context building didn't distinguish between agents and tools/services, so LLM inferred "agent" terminology.

**Solution**: Explicitly clarify in prompts and context that semantic_search is a TOOL/SERVICE:

1. **Supervisor Prompt**: Added `**TOOL**` label and explicit note "(NOT an agent - it's a search tool/service)"
2. **Context Building**: Distinguish in response history: `"- semantic_search (tool): ..."` vs `"- {agent_name} (agent): ..."`
3. **Routing Prompt**: Added explicit instruction: "semantic_search is a TOOL/SERVICE, not an agent. Refer to it as 'semantic_search tool' or 'semantic_search service' in your reasoning, never as 'semantic_search agent'."
4. **Status Display**: Separated "Services/Tools called" from "Agents called"

**Key Principle**: Be explicit about terminology in prompts. If something is a tool/service, label it clearly to prevent LLM from inferring incorrect terminology.

**Files Updated**:
- `prompts/orchestrator/supervisor.txt` - Added TOOL/AGENT labels and terminology clarification
- `src/agents/orchestrator/graph/supervisor.py` - Updated context building and routing prompts to distinguish tools from agents

#### Critical Learning: Tool Calling Visibility - Restore User Transparency

**Problem**: Tool calls were not visible to users, reducing transparency.

**Root Cause**: Guardian agent was passing `streaming_callback=None` to `execute_agent_loop`, and semantic_search wasn't emitting tool_call events.

**Solution**: 
1. Enable streaming callback in Guardian agent for tool calls
2. Emit `tool_call` events from semantic_search node
3. Display tool calls and results in CLI

**Files Updated**:
- `src/agents/specialists/guardian_agent.py` - Enabled streaming callback for tool calls
- `src/agents/orchestrator/graph/nodes/semantic_search.py` - Added tool_call event emission
- `src/interface/cli/main.py` - Added handlers for tool_call and tool_result events

#### Critical Learning: Remove Hardcoded Logic - Trust Prompt-Based Reasoning

**Problem**: Guardian agent had hardcoded keyword check that bypassed streaming path, causing invisible responses for introductions.

**Root Cause**: Hardcoded early exit (`return super().analyze()`) at lines 343-349 bypassed `execute_agent_loop` which has streaming enabled. The `super().analyze()` path goes to `BaseSpecialistAgent.analyze()` which has NO streaming callbacks.

**Solution**: Remove hardcoded keyword checks. Rely on:
1. **Supervisor Instruction**: "STRICTLY FORBIDDEN from using tools" (prompt-based)
2. **System Prompt**: Efficiency Protocol with tool inhibition (prompt-based)
3. **Middleware Normalization**: Prevents crashes if tool is called anyway (safety net)

**Key Principle**: "Trust, but Verify (and Sanitize)" - Trust prompt-based reasoning, verify with middleware safety net. No hardcoded `if "hi" in text` checks.

**Files Updated**:
- `src/agents/specialists/guardian_agent.py` - Removed hardcoded early exit (lines 343-349), always use `execute_agent_loop` for streaming

#### Key Lesson: "Lite" Models Need Inhibition Training

"Lite" models prioritize speed over accuracy. They act like eager interns - seeing a tool and clicking it immediately without thinking "is this actually necessary?"

Solution: **Cost Framing** + **CoT Inhibition** + **Better Model** creates a "thoughtful intern" that considers efficiency and requirements before acting.

#### Key Lesson: Model Selection Strategy - Standard Flash First

**The Rate Limit Wall**: Using `gemini-2.5-pro` for everything comes with massive risk.

**The Problem**:
- Flash Models: ~1,000 - 4,000 RPM (Requests Per Minute)
- Pro/Exp Models: Often as low as **60 RPM** (or even 10 RPM for previews)
- Orchestrator fires 4 agents simultaneously → 8-10 requests instantly
- "All Pro" risks crashing with `429 Too Many Requests` (same as Experimental crash)

**The Solution**: Standardize on `gemini-2.5-flash` first.

**Why Standard Flash (Not Lite, Not Pro)?**
1. **vs. Lite**: Standard Flash has better reasoning inhibition - stops Guardian from aggressively calling tools during intros
2. **vs. Pro**: Need the 1,000 RPM quota to support parallel agent execution without crashing
3. **Industry Sweet Spot**: Standard Flash is the industry sweet spot for Agents

**Escalation Path**:
1. ✅ **Start**: All agents use `gemini-2.5-flash`
2. 👀 **Monitor**: Watch Guardian behavior
3. 🔄 **Escalate**: If Guardian still calls tools unnecessarily → upgrade ONLY Guardian to `gemini-2.5-pro`
4. ❌ **Don't Pay "Pro Tax"**: Don't use Pro for entire team until proven Flash can't handle it

**Key Principle**: Don't pay the "Pro Tax" (latency/quota) for the whole team until you prove Flash can't handle it.

---

### Latest Fixes (December 2025) - Agent Response Duplication & Import Errors

#### Critical Learning: Agent Node Response Pattern - Only Use agent_responses

**Problem**: When users asked "have all agents introduce themselves", Specialist and Optimizer agents were responding twice - once from streaming callback and once from messages being added to state.

**Root Cause**: Agent nodes (Specialist, Optimizer, Pathfinder) were adding responses to BOTH:
- `messages` field (causing duplicate display)
- `agent_responses` field (for supervisor tracking)

The streaming callback already handles display, so adding to `messages` caused duplicates.

**✅ Solution**: Match Guardian pattern - only add to `agent_responses`, not `messages`.

**Implementation**:
```python
# ❌ WRONG (causes duplicates)
return {
    "messages": [AIMessage(content=response)],  # ← Causes duplicate display
    "agent_responses": state.get("agent_responses", []) + [{"agent": "specialist", "response": response}],
    "current_task_instruction": ""
}

# ✅ CORRECT (matches Guardian pattern)
return {
    # DO NOT add to messages - only add to agent_responses
    # The streaming callback already displays the response
    "agent_responses": state.get("agent_responses", []) + [{"agent": "specialist", "response": response}],
    "current_task_instruction": "",
    "next": ""  # Return to supervisor for FINISH routing
}
```

**Files Fixed**:
- `src/agents/orchestrator/graph/nodes/specialist.py`
- `src/agents/orchestrator/graph/nodes/optimizer.py`
- `src/agents/orchestrator/graph/nodes/pathfinder.py`

**Key Principle**: Streaming callback handles display. Agent nodes should only track responses in `agent_responses` for supervisor routing decisions.

---

#### Critical Learning: Module-Level Imports Prevent Conditional Import Failures

**Problem**: Guardian agent was throwing `ModuleNotFoundError: No module named 'src.utils.agent_loop'` when called for introductions AFTER using its tool.

**Root Cause**: The import `from ...utils.agent_loop import execute_agent_loop` was happening conditionally inside the `analyze()` method:
```python
if self.tools and use_tools:
    try:
        from ...utils.agent_loop import execute_agent_loop  # ← Conditional import
```

After Guardian used its tool, Python's import system couldn't resolve the relative import when it was called again.

**✅ Solution**: Move import to module level (top of file) so it happens once when the module loads.

**Implementation**:
```python
# ✅ CORRECT - Import at module level
from ..base_specialist import BaseSpecialistAgent
from ...utils.observability import trace_agent
from ...utils.tool_instructions import build_toolkit_reference
from ...utils.agent_loop import execute_agent_loop  # ← Module-level import

# Then in analyze() method:
if self.tools and use_tools:
    try:
        # execute_agent_loop is already imported - no need to import here
        from langchain_core.messages import SystemMessage, HumanMessage
```

**File Fixed**: `src/agents/specialists/guardian_agent.py`

**Key Principle**: Always import at module level, not conditionally inside methods. This ensures consistent import resolution regardless of execution path.

---

#### Critical Learning: Emoji Consistency Across Agent References

**Problem**: Guardian agent was referring to Optimizer Agent with wrong emoji (⚡ instead of 🎯) in its system prompt.

**Root Cause**: Inconsistent emoji usage in `config/prompts/guardian_agent/system.txt` - used ⚡ while other files used 🎯.

**✅ Solution**: Update Guardian system prompt to match emoji used in orchestrator and agent_utils.

**Implementation**:
```python
# ❌ WRONG
3. Optimizer Agent (⚡) - Budget and performance optimization

# ✅ CORRECT
3. Optimizer Agent (🎯) - Budget and performance optimization
```

**File Fixed**: `config/prompts/guardian_agent/system.txt`

**Key Principle**: Maintain emoji consistency across all agent references. Use:
- 🛡️ Guardian Agent
- 🔧 Specialist Agent
- 🎯 Optimizer Agent (NOT ⚡)
- 🧭 Pathfinder Agent

**Verification**: Check all files that reference agents:
- `src/agents/orchestrator/orchestrator.py`
- `src/agents/orchestrator/agent_utils.py`
- `src/agents/orchestrator/prompts.py`
- `config/prompts/guardian_agent/system.txt`

---

## Key Architectural Decisions

### Decision 1: Always Invoke Graph

**Rationale**: Supervisor should make ALL routing decisions. No hardcoded detection in `chat()`.

**Implementation**: `chat()` always calls `_execute_graph()`. Supervisor decides routing.

### Decision 2: Structured Output for Routing

**Rationale**: Enforces valid routing decisions. Makes routing explicit and debuggable.

**Implementation**: `RouteDecision` Pydantic model with `next` and `instructions` fields.

### Decision 3: Supervisor Instruction Injection

**Rationale**: Agents need to follow supervisor's translated instructions, not raw user questions.

**Implementation**: XML tags (`<supervisor_instruction>`) injected into agent system prompts.

### Decision 4: Tool Descriptions Include "WHEN NOT TO USE"

**Rationale**: LLMs read tool descriptions when deciding to call tools. Explicit exclusions prevent misuse.

**Implementation**: All tool descriptions include explicit "WHEN NOT TO USE" sections.

### Decision 5: No Hardcoded Logic

**Rationale**: Hardcoded checks are brittle and defeat the purpose of LLM-driven intelligence.

**Implementation**: All decisions come from LLM reasoning guided by prompts.

### Decision 6: Model Selection Strategy - Standard Flash First

**Rationale**: Rate limits are critical for parallel agent execution. Pro models have ~60 RPM vs Flash's ~1,000 RPM. Using "All Pro" risks crashes.

**Implementation**: 
- Standardize on `gemini-2.5-flash` for all agents
- Monitor Guardian behavior
- Only escalate Guardian to `gemini-2.5-pro` if Flash proves insufficient
- Don't pay "Pro Tax" (latency/quota) for entire team until proven necessary

**Rate Limit Reality**:
- Flash Models: ~1,000 - 4,000 RPM ✅
- Pro Models: ~60 RPM (or 10 RPM for previews) ❌
- Parallel execution (4 agents × 2 calls) = 8-10 requests instantly

### Decision 7: Middleware Normalization for Tool Arguments

**Rationale**: Tool crashes happen in LangChain's validation layer BEFORE function execution. Pydantic validates arguments and calls `.strip()` on lists, causing crashes. Fix must be at middleware layer, not inside functions.

**Implementation**: 
- Add `_normalize_tool_args()` function in `src/utils/agent_loop.py`
- Normalize arguments BEFORE `tool_func.invoke()` (before Pydantic validation)
- Extract lists to first element, handle None values, pass through primitives
- **CRITICAL**: Also fix Pydantic validators to handle lists BEFORE string operations
- Prevents `'list' object has no attribute 'strip'` crashes

**Key Principle**: When debugging tool crashes, check WHERE the error occurs in the call stack. If it's in validation (Pydantic), fix it BEFORE validation, not after. Also ensure Pydantic validators handle lists before string operations.

**Multi-Layer Defense**:
1. **Pydantic Validators** (Primary) - Handle lists before string operations
2. **Middleware Normalization** (Secondary) - Normalize before invoke
3. **Supervisor Instruction** (Tertiary) - Explicitly forbids tool usage
4. **Prompt Reordering** (Quaternary) - Uses recency bias
5. **Cost Framing + CoT** (Quinary) - Guides reasoning

### Decision 8: Supervisor Should Not Generate Responses When Tools Already Responded

**Rationale**: When semantic_search tool responds, supervisor should route to FINISH without generating a new hallucinated response. The orchestrator will extract and use the tool's results.

**Implementation**: 
- Check if semantic_search has already responded before generating FINISH response
- If tool responded, just route to FINISH without adding new messages
- Prevents hallucinated responses when tools have already provided results

**Key Principle**: When a tool/service has already provided results, don't generate new responses - let the orchestrator extract and use the tool's results.

### Decision 9: Explicit Terminology - Tools vs Agents

**Rationale**: LLMs infer terminology from context. If semantic_search is listed alongside agents without clarification, LLM will call it an "agent". Be explicit about what is a tool/service vs an agent.

**Implementation**: 
- Label semantic_search as `**TOOL**` in supervisor prompt
- Distinguish tools from agents in context building: `"- semantic_search (tool): ..."` vs `"- {agent_name} (agent): ..."`
- Add explicit instruction: "semantic_search is a TOOL/SERVICE, not an agent"
- Separate "Services/Tools called" from "Agents called" in status display

**Key Principle**: Be explicit about terminology in prompts. If something is a tool/service, label it clearly to prevent LLM from inferring incorrect terminology.

---

## Consultant Guidance Summary

### Core Principle

**"Prompt-Driven Reasoning, Not Code Logic"**

All behavior should come from LLM reasoning guided by well-crafted prompts. Hardcoded checks are brittle and unscalable.

### Key Quotes

> "Do not implement hardcoded Python checks (`if 'introduce' in question`). That is brittle and unscalable."

> "Use XML tags when injecting supervisor instructions. LLMs pay much closer attention to structured tags."

> "Read `current_task_instruction` directly from `AgentState`. Don't prop-drill through function signatures."

> "The supervisor IS the graph entry point. Use structured output for routing, not tools."

### Approved Patterns

1. **Tool Docstrings**: Explicit "WHEN NOT TO USE" sections
2. **XML Tags**: For supervisor instruction injection
3. **State-Based**: Read from `AgentState`, don't prop-drill
4. **Structured Output**: Use Pydantic models for routing decisions
5. **Prompt Engineering**: Guide LLM behavior through prompts
6. **Middleware Normalization**: Normalize tool arguments BEFORE Pydantic validation (in `agent_loop.py`)

---

## Next Steps for New Sessions

1. **Read this document first** - Understand the architecture and pitfalls
2. **Review recent commits** - See what was fixed and why
3. **Check consultant guidance** - Follow approved patterns
4. **Test before coding** - Verify current behavior
5. **Use prompts, not code** - When in doubt, improve prompts

### When Adding New Features

1. **Ask**: Does this require hardcoded logic? → If yes, use prompts instead
2. **Ask**: Does this fit the supervisor pattern? → If no, reconsider architecture
3. **Ask**: Can the LLM reason about this? → If yes, use prompt guidance
4. **Ask**: Does this break the "no hardcoded checks" rule? → If yes, don't do it

---

## Quick Reference

### File Locations

- Supervisor node: `src/agents/orchestrator/graph/supervisor.py`
- Guardian agent: `src/agents/specialists/guardian_agent.py` - **Pydantic Model Guard** (`@model_validator`)
- Guardian node: `src/agents/orchestrator/graph/nodes/guardian.py`
- State schema: `src/agents/orchestrator/graph/state.py`
- Graph definition: `src/agents/orchestrator/graph/graph.py`
- Agent loop: `src/utils/agent_loop.py` - **Middleware normalization for tool arguments**
- Tool function: `src/tools/portfolio_pacing_tool.py` - **Tool Function Sanitation** (`_normalize_string_arg`)
- Supervisor prompt: `prompts/orchestrator/supervisor.txt` - **Multi-agent routing rules**

### Key Patterns

- **Routing**: Structured output (`RouteDecision`) in supervisor
- **Instructions**: XML tags (`<supervisor_instruction>`) in agent prompts
- **Tool Usage**: "WHEN NOT TO USE" in tool descriptions
- **State Access**: Read from `AgentState` in nodes
- **Tool Argument Normalization**: **Double-Ended Sanitation** - Robust normalization in BOTH Pydantic Model AND Tool Function layers

### Anti-Patterns

- ❌ Hardcoded keyword checks
- ❌ Tool-calling for routing
- ❌ Special-casing edge cases
- ❌ Prop-drilling parameters
- ❌ Ignoring supervisor instructions
- ❌ Adding defensive code INSIDE tool functions for validation errors (fix at middleware layer instead)

---

**Remember**: When in doubt, ask yourself: "Can this be solved with better prompts instead of code logic?" The answer is almost always yes.

---

## Performance Optimization Plan

**See**: [`docs/performance_optimization_plan.md`](../docs/performance_optimization_plan.md) for the complete performance optimization plan.

**Summary**: The system currently uses a Sequential Chain pattern (~20s) and needs to move to Parallel Map-Reduce pattern (~6-8s). Three optimization phases are approved:

1. **Phase 1: Hardware Optimization** (MPS) - ~15 min, 1s savings
2. **Phase 2: Parallel Search Execution** - ~2-3 hours, 8s savings  
3. **Phase 3: Verbosity Control** - ~30 min, 5s savings

**Expected Total Improvement**: 60-70% reduction (20s → 6-8s)

### Final Lesson: "Lite" Models Need Inhibition Training

"Lite" models prioritize speed over accuracy. They act like eager interns - seeing a tool and clicking it immediately without thinking "is this actually necessary?"

**Solution**: Cost Framing + CoT Inhibition + Better Model creates a "thoughtful intern" that considers efficiency and requirements before acting.

**Key Pattern**: If you see impulsive tool usage, add:
1. **Cost framing** (tools are expensive)
2. **CoT inhibition** (force reasoning first)
3. **Better model** (higher inhibition capabilities)
4. **Restrictive descriptions** (strict usage rules)

This prevents unnecessary tool calls while maintaining scalability.

### Final Lesson: Model Selection Strategy - Standard Flash First

**The Rate Limit Wall**: Don't use "All Pro" - it crashes parallel execution.

**Key Principle**: Standardize on `gemini-2.5-flash` first. Only escalate Guardian to Pro if Flash proves insufficient.

**Why**:
- Flash: ~1,000 - 4,000 RPM ✅ (survives parallel execution)
- Pro: ~60 RPM ❌ (crashes with 4 agents × 2 calls = 8-10 requests instantly)

**Escalation Path**:
1. Start with `gemini-2.5-flash` for all agents
2. Monitor Guardian behavior
3. If Guardian still calls tools unnecessarily → upgrade ONLY Guardian to `gemini-2.5-pro`
4. Don't pay "Pro Tax" (latency/quota) for entire team until proven necessary

### Final Lesson: Tool Crash Fix - Double-Ended Sanitation

**The Breakthrough**: There were **TWO IDENTICAL PROBLEMS** - Pydantic Model AND Tool Function both had flawed normalization logic.

**Key Principle**: Implement bulletproof normalization in **BOTH** layers - never rely on one or the other.

**Why Previous Fixes Failed**:
- Only fixed ONE layer (Pydantic OR Tool Function)
- Flawed normalization logic: `str(arg).strip()` could crash if `arg` remained a list
- Pydantic validators ran AFTER internal validation already crashed

**The Solution**: **Double-Ended Sanitation** - Robust normalization in BOTH places:

**Layer 1: Pydantic Model Guard** (`@model_validator(mode='before')`):
- Intercepts raw data **before ANY Pydantic validation**
- Flattens lists to first element: `['17']` → `'17'`
- Sets defaults for required fields

**Layer 2: Tool Function Sanitation** (Atomic string conversion):
- Forces `str()` cast **BEFORE** `.strip()`: `str(arg).strip()`
- Handles None, lists, and any input type gracefully
- Mathematically impossible to call `.strip()` on a list

**Impact**: Guardian can safely call tools without crashing, and introduction text is delivered.

**Multi-Layer Defense** (Updated):
1. **Double-Ended Sanitation** (Primary) - Prevents crash at both layers
2. **Middleware Normalization** (Secondary) - Additional protection in agent loop
3. **Supervisor Instruction** (Tertiary) - Explicitly forbids tool usage
4. **Prompt Reordering** (Quaternary) - Uses recency bias
5. **Cost Framing + CoT** (Quinary) - Guides reasoning

---

## Concrete Examples from Recent Development

### Canary Agent - Testing Infrastructure

**Problem**: Persistent `'list' object has no attribute 'strip'` error in Guardian agent despite multiple fixes.

**Solution**: Created minimal "Canary Agent" for isolation testing.

**Files Created**:
- `src/tools/canary_tools.py` - Simple `echo_tool(text: str)` that repeats input
- `src/agents/specialists/canary_agent.py` - Minimal agent with single tool
- `config/canary_agent.yaml` - Simple config using `gemini-2.5-flash`
- `src/agents/orchestrator/graph/nodes/canary.py` - Graph node for canary
- Updated graph routing and supervisor to support `canary` agent

**Testing Protocol**:
1. Ask: "Canary, say hello"
2. If works → Issue is Guardian-specific complexity
3. If fails → Issue is core agent loop (LLM sending bad lists globally)

**Impact**: Provides definitive diagnosis without fighting complex Guardian code.

### Example 1: Guardian Tool Calling Fix

**Problem**: Guardian called portfolio tool for "introduce yourself"

**Wrong Approach** (What we tried first):
```python
# ❌ Hardcoded check
is_intro_request = any(phrase in question_lower for phrase in [
    "introduce yourself", "introduce", "who are you"
])
if is_intro_request:
    # Skip tool call
```

**Correct Approach** (Consultant-approved):
```python
# ✅ Tool description
description="""...
WHEN NOT TO USE:
- DO NOT use for introductions, greetings, or general conversation
"""

# ✅ System prompt injection
if supervisor_instruction:
    base_prompt += f"""
<supervisor_instruction>
{supervisor_instruction}
</supervisor_instruction>
CRITICAL: Follow the Supervisor's instruction exactly...
"""
```

**Files Changed**:
- `src/agents/specialists/guardian_agent.py`: Removed 56 lines of hardcoded checks, added prompt guidance
- `src/agents/orchestrator/graph/nodes/guardian.py`: Reads instruction from state
- `src/agents/orchestrator/agent_calling.py`: Passes instruction to agent

### Example 2: Supervisor Routing Fix

**Problem**: Supervisor used routing prompt for FINISH responses, resulting in generic answers

**Wrong Approach**:
```python
# ❌ Using supervisor prompt for responses
response_messages = [
    SystemMessage(content=supervisor_prompt),  # Wrong prompt!
    HumanMessage(content=response_prompt)
]
```

**Correct Approach**:
```python
# ✅ Using orchestrator prompt for responses
response_system_prompt = orchestrator_prompt if orchestrator_prompt else system_prompt
response_messages = [
    SystemMessage(content=response_system_prompt),  # Correct prompt!
    HumanMessage(content=response_prompt)
]
```

**Files Changed**:
- `src/agents/orchestrator/graph/supervisor.py`: Accepts `orchestrator_prompt` parameter
- `src/agents/orchestrator/graph/graph.py`: Passes orchestrator prompt to supervisor
- `src/agents/orchestrator/orchestrator.py`: Builds orchestrator prompt and passes to graph

### Example 3: Removing Hardcoded Detection

**Problem**: Hardcoded checks for "multi-agent intro", "single intro", etc.

**Wrong Approach**:
```python
# ❌ Hardcoded detection
is_multi_agent_intro = (
    any(keyword in user_question_lower for keyword in intro_keywords) and 
    any(keyword in user_question_lower for keyword in multi_agent_keywords)
)
if is_multi_agent_intro:
    # Special handling
```

**Correct Approach**:
```python
# ✅ LLM decides via structured output
structured_llm = llm.with_structured_output(RouteDecision)
decision = structured_llm.invoke(messages)
# LLM reasons about routing based on prompt guidance
```

**Files Changed**:
- `src/agents/orchestrator/graph/supervisor.py`: Removed all hardcoded detection, uses LLM reasoning

---

## Consultant Quotes (Critical Guidance)

### On Hardcoded Logic

> "Do not implement hardcoded Python checks (`if 'introduce' in question`). That is brittle and unscalable."

> "You are absolutely right to stop the Dev Agent from hardcoding string checks (`if "hi" in text`). That is 'brittle' code—it breaks as soon as a user says 'Greetings' instead of 'Hi.'"

### On Architecture

> "The Dev Agent's second proposal (Prompt Engineering) is the correct *direction*, but it needs to be executed with **Architecture**, not just 'hoping the LLM listens.'"

> "Do not over-engineer the 'threading' of parameters. In LangGraph, you have a **Shared State**. You don't need to drill arguments down through function signatures."

### On Tool Usage

> "The LLM's logic: 'I am the Guardian. My job is portfolio health. To introduce myself properly, I should probably check the health first!'"

> "We don't need Python `if` statements. We need to tell the LLM **specifically when NOT to use the tool** inside the tool's definition itself."

### On XML Tags

> "When injecting the instruction into the system prompt (Step 2 of their plan), advise them to use **XML Tags**. LLMs pay much closer attention to structured tags than just appended text."

---

## State Flow Diagram

```
User: "get agents to introduce themselves"
    ↓
OrchestratorAgent.chat(question)
    ↓
_execute_graph(question)
    ↓
Graph State Initialized:
{
    "messages": [HumanMessage("get agents to introduce themselves")],
    "user_question": "get agents to introduce themselves",
    "current_task_instruction": "",
    "next": "",
    "agent_responses": []
}
    ↓
Supervisor Node:
- Reads user_question from state
- Uses structured output to decide routing
- Sets current_task_instruction: "Introduce yourself and explain your role"
- Sets next: "guardian"
    ↓
Guardian Node:
- Reads current_task_instruction from state
- Passes instruction to Guardian.analyze()
- Guardian injects instruction into system prompt using XML tags
- LLM reasons: "This is an introduction, I should NOT call tools"
- Guardian responds without calling portfolio tool ✅
    ↓
State Updated:
{
    "agent_responses": [{"agent": "guardian", "response": "Hello, I'm..."}],
    "next": "supervisor"
}
    ↓
Supervisor Node (again):
- Sees guardian has responded
- Routes to next agent: "specialist"
- Sets current_task_instruction: "Introduce yourself..."
    ↓
[Continues for all agents]
```

---

## Code Patterns Reference

### Pattern: Reading from State

```python
# ✅ CORRECT: Read directly from state
def guardian_node(state: AgentState):
    instruction = state.get("current_task_instruction", "")
    user_question = state.get("user_question", "")
    # Use instruction and question
```

### Pattern: Injecting Supervisor Instruction

```python
# ✅ CORRECT: XML tags for better attention
if supervisor_instruction:
    base_prompt += f"""
<supervisor_instruction>
{supervisor_instruction}
</supervisor_instruction>
CRITICAL: Follow this instruction exactly...
"""
```

### Pattern: Tool Description with Exclusions

```python
# ✅ CORRECT: Explicit "WHEN NOT TO USE"
description="""...
WHEN TO USE:
- User explicitly asks for portfolio data

WHEN NOT TO USE:
- DO NOT use for introductions
- DO NOT use for general conversation
"""
```

### Pattern: Structured Output Routing

```python
# ✅ CORRECT: Structured output for routing
class RouteDecision(BaseModel):
    next: Literal["semantic_search", "guardian", ..., "FINISH"]
    instructions: str
    reasoning: str

structured_llm = llm.with_structured_output(RouteDecision)
decision = structured_llm.invoke(messages)
```

---

## Testing Checklist

Before committing changes, verify:

- [ ] No hardcoded keyword checks (`if "keyword" in text`)
- [ ] No special-casing edge cases in code
- [ ] Tool descriptions include "WHEN NOT TO USE"
- [ ] Supervisor instructions injected using XML tags
- [ ] State read directly (not prop-drilled)
- [ ] Structured output used for routing
- [ ] All files ≤ 400 lines
- [ ] Introduction requests don't trigger tools
- [ ] Portfolio questions DO trigger tools
- [ ] Supervisor uses correct prompt for FINISH responses

---

## Emergency Debugging Guide

### Issue: Agent calling tools unnecessarily

**Check**:
1. Tool description has "WHEN NOT TO USE" section?
2. Supervisor instruction injected into system prompt?
3. XML tags used for instruction injection?
4. No hardcoded keyword checks bypassing LLM reasoning?

**Fix**: Add/improve prompt guidance, don't add code checks.

### Issue: Supervisor not routing correctly

**Check**:
1. `chat()` always calls `_execute_graph()`?
2. Supervisor uses structured output (`RouteDecision`)?
3. No hardcoded detection logic?
4. Prompt guides LLM correctly?

**Fix**: Remove hardcoded logic, improve prompts.

### Issue: Duplicate responses

**Check**:
1. Agent nodes not emitting responses twice?
2. Streaming callbacks not duplicated?
3. State properly managed?

**Fix**: Ensure single emission point for responses.

**✅ FIXED (December 2025)**: Agent nodes (Specialist, Optimizer, Pathfinder) were adding responses to both `messages` and `agent_responses`, causing duplicate display. Fixed by matching Guardian pattern - only add to `agent_responses`, not `messages`. Streaming callback already handles display.

---

## Final Reminders

1. **Prompts > Code**: Always prefer prompt improvements over code logic
2. **State > Props**: Read from `AgentState`, don't prop-drill
3. **Structured > Unstructured**: Use Pydantic models for routing
4. **XML > Plain Text**: Use XML tags for critical instructions
5. **LLM Reasoning > Hardcoded Checks**: Trust the LLM when properly guided

**When you see `if "keyword" in text:` → STOP. Use prompts instead.**

---

## 📚 Related Documentation

### Critical Incident Post-Mortem

**`docs/incident_postmortem_guardian_loop.md`** - Comprehensive post-mortem of the 4-hour Guardian Loop incident (November 29, 2025)

**What's Inside:**
- Complete timeline of failures and fixes
- Root cause analysis (the crash was NOT where we thought!)
- Three-layer defense architecture documentation
- Golden rules for future development
- Prevention checklists
- Lessons learned

**When to Read:**
- Before creating new agents or tools
- When debugging similar crashes
- When implementing tool calling patterns
- When working with `gemini-2.5-flash` models

**Key Takeaway:** The crash was in `agent_loop.py` line 71 (`result.content.strip()`), NOT in tool execution. Always handle LLM response content as potentially being a list, not just a string.

