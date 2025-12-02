# Tool Instructions Architecture

## Overview

This document describes the **multi-layer architecture** for tool documentation, execution guidance, and runtime control:

1. **System Prompt Toolkit** - Static reference with tool contracts (inputs/outputs)
2. **Execution Instructions** - Dynamic, contextual guidance loaded from markdown files
3. **Account Defaults Injection** - Runtime injection of agent-specific defaults (Guardian-specific)
4. **Supervisor Instructions** - Runtime guidance injected via XML tags

---

## Architecture Layers

### Layer 1: System Prompt Toolkit (Static Reference)

**Purpose**: Provide a tool registry with contracts so agents know what tools exist and their schemas.

**Location**: Auto-generated and appended to agent system prompts

**Content**:
- Tool name and general purpose
- Input schema (from Pydantic model)
- Output schema description
- General use cases

**Implementation**:
- `src/utils/tool_instructions.py::build_toolkit_reference()` generates this from tool schemas
- Agents override `_get_system_prompt()` to append toolkit reference
- Cached after first generation (`_toolkit_reference` attribute)

**Example Output**:
```markdown
## AVAILABLE TOOLS

### analyze_portfolio_pacing
**Purpose**: Analyze portfolio pacing and generate dashboard-style insights.

**Input Schema**:
- **account_id** (str, default: "17"): Account ID to analyze
- **advertiser_filter** (str, default: None (optional)): Optional advertiser name filter
- **campaign_start** (str, default: None (optional)): Campaign start date
- **campaign_end** (str, default: None (optional)): Campaign end date
- **campaign_budget** (float, default: None (optional)): Total campaign budget

**Output Schema**:
Returns JSON with analysis results and insights.

**Use When**:
- Portfolio health questions
- Budget utilization queries
- Pacing analysis requests
```

---

### Layer 2: Execution Instructions (Dynamic, Contextual)

**Purpose**: Provide granular, context-aware instructions when a tool is about to be called.

**Location**: Markdown files alongside tool code

**File Structure**:
```
tools/
  campaign-portfolio-pacing/
    execution_instructions.md  # Maintained by devs
    src/
      campaign_analyzer.py
```

**Content**: Context-aware guidance with template variables

**Implementation**:
- `src/utils/tool_instructions.py::load_execution_instructions()` loads from markdown
- `src/utils/agent_loop.py` injects instructions **BEFORE** tool execution (lines 157-183)
- Instructions are injected as a `HumanMessage` in the message chain

**Timing**: 
- Instructions are injected **BEFORE** tool execution
- LLM sees instructions when processing tool results
- This allows LLM to interpret tool output according to guidance

**Message Format**:
```python
instructions_msg = HumanMessage(
    content=f"TOOL EXECUTION GUIDANCE for {tool_name}:\n\n{execution_instructions}\n\nUse this guidance when interpreting the tool results."
)
messages.append(instructions_msg)
```

**Template Variables**:
- `{question}` - Current user question
- `{tool_name}` - Name of the tool
- `{account_id}` - Account ID being analyzed (from tool_args)
- `{advertiser_filter}` - Advertiser filter if specified (from tool_args)
- `{arg_name}` - Any tool argument name (automatically replaced from tool_args)

**Keyword-Based Section Extraction**:
- Instructions file can have multiple sections (marked with `###`)
- System matches question keywords to section headers
- Only relevant sections are extracted and injected
- Keywords checked: `['trend', 'risk', 'calculate', 'average', 'pacing', 'budget']`
- If no match found, entire file content is used

**Example** (`tools/campaign-portfolio-pacing/execution_instructions.md`):
```markdown
### When user asks for calculations

**Keywords**: "average", "calculate", "compute", "sum"

**Focus Areas**:
- Use `daily_trend` data for calculations
- Show work step-by-step with specific dates and amounts

**Example Response Pattern**:
- "To calculate the average over last {N} days:"
- "Step 1: Sum the spend for dates {dates}: {amounts} = {total}"
```

**Error Handling**:
- If instruction file is missing: Silent failure (logs debug message)
- If template variable missing: Variable remains as `{variable_name}` in output
- If file parsing fails: Returns `None`, no instructions injected

---

### Layer 3: Account Defaults Injection (Runtime, Agent-Specific)

**Purpose**: Inject agent-specific default values into system prompt at runtime.

**Location**: Agent-specific implementation (currently Guardian only)

**Implementation**:
- `src/agents/specialists/guardian_agent.py::analyze()` (lines 277-286)
- Extracts account info from question using `_extract_account_info()`
- Injects defaults into system prompt before tool execution

**Example**:
```python
system_prompt_with_defaults = f"""
{system_prompt}

IMPORTANT: When calling analyze_portfolio_pacing tool, use these default values:
- account_id: "17" (Tricoast Media LLC)
- advertiser_filter: None

Only override these if the user explicitly specifies a different account or advertiser.
"""
```

**When Used**:
- Only for Guardian agent
- Only when tools are available and enabled
- Injected into system prompt before `execute_agent_loop()` is called

---

### Layer 4: Supervisor Instructions (Runtime Guidance)

**Purpose**: Inject runtime guidance from supervisor into agent prompts.

**Location**: `src/agents/specialists/guardian_agent.py::analyze()` (line 273)

**Implementation**:
- Supervisor instruction passed via `supervisor_instruction` parameter
- Injected into system prompt via `_get_system_prompt(supervisor_instruction=supervisor_instruction)`
- Wrapped in XML tags: `<supervisor_instruction>...</supervisor_instruction>`

**Example**:
```python
system_prompt = self._get_system_prompt(supervisor_instruction=supervisor_instruction)
```

**Format**:
- XML tags: `<supervisor_instruction>...</supervisor_instruction>`
- Can contain specific task instructions
- Can contain context about why agent was called

---

## Complete Flow Diagram

```
User Question
    ↓
Supervisor Node (Structured Output)
    ↓
RouteDecision with instruction
    ↓
Guardian Node
    ↓
Build System Prompt
    ├─ Base prompt
    ├─ Toolkit reference (Layer 1)
    ├─ Account defaults (Layer 3)
    └─ Supervisor instruction (Layer 4)
        ↓
    Execute Agent Loop
        ↓
    LLM decides to call tool
        ↓
    Load Execution Instructions (Layer 2)
    ├─ Read markdown file
    ├─ Replace template variables
    ├─ Extract relevant sections
    └─ Inject as HumanMessage BEFORE tool execution
        ↓
    Execute Tool
        ↓
    LLM processes tool result WITH instructions
        ↓
    Return formatted response
```

---

## Implementation Details

### 1. Building Toolkit Reference

```python
from src.utils.tool_instructions import build_toolkit_reference

# In agent's _get_system_prompt() method
if self.tools and not self._toolkit_reference:
    self._toolkit_reference = build_toolkit_reference(self.tools)

if self._toolkit_reference:
    return f"{base_prompt}\n\n{self._toolkit_reference}"
```

### 2. Loading Execution Instructions

```python
from src.utils.tool_instructions import load_execution_instructions

execution_instructions = load_execution_instructions(
    tool_name="analyze_portfolio_pacing",
    question="What is the average spend over the last 3 days?",
    tool_args={"account_id": "17"},
    conversation_history=None
)
```

### 3. Injecting Instructions in Agent Loop

The `execute_agent_loop` function in `src/utils/agent_loop.py` automatically:
1. Detects when a tool is about to be called (line 155)
2. Loads execution instructions from markdown file (lines 158-173)
3. Injects instructions as a `HumanMessage` **BEFORE** tool execution (lines 175-180)
4. LLM sees instructions when processing tool results

**Code Location**: `src/utils/agent_loop.py` lines 157-183

### 4. Account Defaults Injection

**Location**: `src/agents/specialists/guardian_agent.py::analyze()` (lines 277-286)

```python
# Extract account info from question
account_info = self._extract_account_info(question)

# Inject account defaults into system prompt
system_prompt_with_defaults = f"""
{system_prompt}

IMPORTANT: When calling analyze_portfolio_pacing tool, use these default values:
- account_id: "{account_info['account_id']}" (Tricoast Media LLC)
- advertiser_filter: {f'"{account_info["advertiser_filter"]}"' if account_info['advertiser_filter'] else 'None'}

Only override these if the user explicitly specifies a different account or advertiser.
"""
```

---

## File Locations

### Utility Functions
- `src/utils/tool_instructions.py` - Core utilities for toolkit reference and execution instructions
  - `build_toolkit_reference()` - Generates static toolkit reference
  - `load_execution_instructions()` - Loads and processes dynamic instructions

### Agent Integration
- `src/agents/specialists/guardian_agent.py` - Example implementation
  - `_get_system_prompt()` - Appends toolkit reference
  - `analyze()` - Handles account defaults injection
- `src/utils/agent_loop.py` - Automatic instruction injection (lines 157-183)

### Execution Instructions
- `tools/campaign-portfolio-pacing/execution_instructions.md` - Example execution instructions

---

## Benefits

1. **Separation of Concerns**: Contracts vs. execution guidance vs. runtime control
2. **Maintainable**: Markdown files alongside tool code
3. **Version Controlled**: Instructions tracked with tool changes
4. **Context-Aware**: Instructions adapt to question keywords
5. **Scalable**: Easy to add tools and instructions
6. **Developer-Friendly**: Clear structure for maintaining instructions
7. **Flexible**: Multiple layers allow fine-grained control

---

## Adding New Tools

### Step 1: Create Execution Instructions File

Create `tools/{tool_name}/execution_instructions.md` with:
- Context-aware guidance sections (marked with `###`)
- Keyword-based detection in section headers
- Example response patterns
- Template variables (e.g., `{question}`, `{tool_name}`, `{arg_name}`)

**Example Structure**:
```markdown
### When user asks for calculations

**Keywords**: "average", "calculate", "compute", "sum"

**Focus Areas**:
- Use specific data fields for calculations
- Show work step-by-step

**Example Response Pattern**:
- "To calculate {metric}:"
- "Step 1: {calculation}"
```

### Step 2: Update Tool Path Mappings (Optional)

If your tool doesn't follow standard naming, add to `tool_path_mappings` in `load_execution_instructions()`:

```python
tool_path_mappings = {
    'your_tool_name': [
        project_root / 'tools' / 'your-tool' / 'execution_instructions.md',
    ],
}
```

**File**: `src/utils/tool_instructions.py` (lines 130-136)

### Step 3: Agent Auto-Generates Toolkit Reference

The agent will automatically generate toolkit reference from tool schemas when `_get_system_prompt()` is called.

---

## Maintenance

- **Toolkit Reference**: Auto-generated from tool schemas - no manual maintenance needed
- **Execution Instructions**: Maintained by developers in markdown files alongside tool code
- **Template Variables**: Updated automatically at runtime based on question and tool args
- **Account Defaults**: Agent-specific, maintained in agent code

---

## Error Handling

### Execution Instructions
- **File Missing**: Silent failure, logs debug message, no instructions injected
- **Template Variable Missing**: Variable remains as `{variable_name}` in output
- **File Parsing Error**: Returns `None`, no instructions injected

### Account Defaults
- **Extraction Fails**: Uses default values from `_extract_account_info()`
- **No Account Info**: Defaults to account_id="17", advertiser_filter=None

---

## Related Documentation

- **Tool Development Guide**: See `AI_HANDOFF.md` ADR-001 (Robust Tool Execution Strategy)
- **Canary Pattern**: See `src/tools/portfolio_pacing_tool.py` (Example implementation)

---

**Last Updated**: December 1, 2025
