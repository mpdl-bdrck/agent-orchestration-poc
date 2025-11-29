# Tool Instructions Architecture

## Overview

This document describes the two-layer architecture for tool documentation and execution guidance:

1. **System Prompt Toolkit** - Static reference with tool contracts (inputs/outputs)
2. **Execution Instructions** - Dynamic, contextual guidance loaded from markdown files

## Architecture

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
- `src/utils/agent_loop.py` injects instructions before tool execution
- Instructions are injected as a `HumanMessage` in the message chain

**Template Variables**:
- `{question}` - Current user question
- `{tool_name}` - Name of the tool
- `{account_id}` - Account ID being analyzed
- `{advertiser_filter}` - Advertiser filter if specified

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
1. Detects when a tool is about to be called
2. Loads execution instructions from markdown file
3. Injects instructions as a `HumanMessage` before tool execution
4. LLM sees instructions when processing tool results

## File Locations

### Utility Functions
- `src/utils/tool_instructions.py` - Core utilities for toolkit reference and execution instructions

### Agent Integration
- `src/agents/specialists/guardian_agent.py` - Example implementation with `_get_system_prompt()` override
- `src/utils/agent_loop.py` - Automatic instruction injection

### Execution Instructions
- `tools/campaign-portfolio-pacing/execution_instructions.md` - Example execution instructions

## Benefits

1. **Separation of Concerns**: Contracts vs. execution guidance
2. **Maintainable**: Markdown files alongside tool code
3. **Version Controlled**: Instructions tracked with tool changes
4. **Context-Aware**: Instructions adapt to question keywords
5. **Scalable**: Easy to add tools and instructions
6. **Developer-Friendly**: Clear structure for maintaining instructions

## Adding New Tools

### Step 1: Create Execution Instructions File

Create `tools/{tool_name}/execution_instructions.md` with:
- Context-aware guidance sections
- Keyword-based detection
- Example response patterns
- Template variables

### Step 2: Update Tool Path Mappings (Optional)

If your tool doesn't follow standard naming, add to `tool_path_mappings` in `load_execution_instructions()`:

```python
tool_path_mappings = {
    'your_tool_name': [
        project_root / 'tools' / 'your-tool' / 'execution_instructions.md',
    ],
}
```

### Step 3: Agent Auto-Generates Toolkit Reference

The agent will automatically generate toolkit reference from tool schemas when `_get_system_prompt()` is called.

## Maintenance

- **Toolkit Reference**: Auto-generated from tool schemas - no manual maintenance needed
- **Execution Instructions**: Maintained by developers in markdown files alongside tool code
- **Template Variables**: Updated automatically at runtime based on question and tool args

