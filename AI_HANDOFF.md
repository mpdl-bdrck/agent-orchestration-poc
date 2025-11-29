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
- Guardian agent: `src/agents/specialists/guardian_agent.py`
- Guardian node: `src/agents/orchestrator/graph/nodes/guardian.py`
- State schema: `src/agents/orchestrator/graph/state.py`
- Graph definition: `src/agents/orchestrator/graph/graph.py`

### Key Patterns

- **Routing**: Structured output (`RouteDecision`) in supervisor
- **Instructions**: XML tags (`<supervisor_instruction>`) in agent prompts
- **Tool Usage**: "WHEN NOT TO USE" in tool descriptions
- **State Access**: Read from `AgentState` in nodes

### Anti-Patterns

- ❌ Hardcoded keyword checks
- ❌ Tool-calling for routing
- ❌ Special-casing edge cases
- ❌ Prop-drilling parameters
- ❌ Ignoring supervisor instructions

---

**Remember**: When in doubt, ask yourself: "Can this be solved with better prompts instead of code logic?" The answer is almost always yes.

---

## Concrete Examples from Recent Development

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

---

## Final Reminders

1. **Prompts > Code**: Always prefer prompt improvements over code logic
2. **State > Props**: Read from `AgentState`, don't prop-drill
3. **Structured > Unstructured**: Use Pydantic models for routing
4. **XML > Plain Text**: Use XML tags for critical instructions
5. **LLM Reasoning > Hardcoded Checks**: Trust the LLM when properly guided

**When you see `if "keyword" in text:` → STOP. Use prompts instead.**

