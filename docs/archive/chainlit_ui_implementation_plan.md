# Chainlit UI Implementation Plan

**Created**: December 2025  
**Status**: Planning Phase  
**Purpose**: Implement production-ready Chainlit UI for Agent Orchestration POC

---

## Executive Summary

This document outlines the implementation plan for adding a Chainlit-based web UI to the Agent Orchestration POC. The UI will provide a "Main Chat vs. Sub-Process" view where users interact with the Orchestrator in the main chat, while sub-agents (Guardian, Specialist, Optimizer, Pathfinder) work in expandable steps.

**Key Principle**: The UI sits **outside** the graph and listens to `astream_events`. It acts like a specialized logger that draws UI elements instead of printing text. **No modifications to stable core logic** (`agent_loop.py`, `guardian_agent.py`, graph nodes).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Phase 1: Setup & Dependencies](#phase-1-setup--dependencies)
3. [Phase 2: Graph Initialization Module](#phase-2-graph-initialization-module)
4. [Phase 3: Chainlit App Implementation](#phase-3-chainlit-app-implementation)
5. [Phase 4: Implementation Details](#phase-4-implementation-details)
6. [Phase 5: Key Implementation Considerations](#phase-5-key-implementation-considerations)
7. [Phase 6: UI/UX Enhancements](#phase-6-uiux-enhancements)
8. [Phase 7: Testing Plan](#phase-7-testing-plan)
9. [Phase 8: File Structure](#phase-8-file-structure)
10. [Phase 9: Implementation Steps](#phase-9-implementation-steps-order)
11. [Phase 10: Key Differences from Consultant's Example](#phase-10-key-differences-from-consultants-example)
12. [Phase 11: Critical Success Factors](#phase-11-critical-success-factors)
13. [Phase 12: Rollout Strategy](#phase-12-rollout-strategy)
14. [Questions to Resolve](#questions-to-resolve)

---

## Architecture Overview

### The Event Listener Pattern

```
User Message
    ↓
Chainlit App (app.py)
    ↓
Graph.astream_events() ← Listens to all events
    ↓
Event Router:
    - Supervisor events → Main Chat Window
    - Sub-agent events → Expandable Steps
    - Tool events → Nested in Agent Steps
```

### Visual Layout

```
┌─────────────────────────────────────────┐
│ Main Chat Window                        │
│                                         │
│ 👤 User: "How is my portfolio?"         │
│ 🧠 Orchestrator: "I'll ask the          │
│    Guardian to analyze..."              │
│                                         │
│ [Expandable Step] 🛡️ Guardian Agent    │
│   └─ Thinking...                        │
│   └─ 🛠️ Running Tool: analyze_portfolio │
│   └─ Response: "Portfolio is healthy"  │
│                                         │
│ 🧠 Orchestrator: "The Guardian reports  │
│    that your portfolio is healthy."    │
└─────────────────────────────────────────┘
```

---

## Phase 1: Setup & Dependencies

### 1.1 Install Chainlit

```bash
pip install chainlit
```

### 1.2 Update requirements.txt

Add to `requirements.txt`:
```
chainlit>=1.0.0
```

### 1.3 Create Entry Point

Create `app.py` in project root (same level as `src/`)

---

## Phase 2: Graph Initialization Module

### 2.1 Create Graph Factory Function

**File**: `src/interface/chainlit/graph_factory.py`

**Purpose**: Centralize graph initialization logic so `app.py` can reuse it without duplicating OrchestratorAgent initialization.

**Function Signature**:
```python
def create_chainlit_graph(
    context_id: str = "bedrock_kb",
    config_path: str = None,
    streaming_callback: Callable = None
) -> CompiledGraph:
    """
    Create and initialize LangGraph workflow for Chainlit.
    
    Args:
        context_id: Knowledge base context identifier
        config_path: Path to orchestrator config file
        streaming_callback: Optional callback (usually None for Chainlit)
    
    Returns:
        Compiled LangGraph workflow ready for astream_events()
    """
```

**Dependencies Needed**:
1. **LLM instance** - From config (gemini-2.5-flash)
2. **Supervisor prompt** - Load from `prompts/orchestrator/supervisor.txt`
3. **Orchestrator prompt** - Built from system prompt + knowledge base context
4. **call_specialist_agent** - Function from `src/agents/orchestrator/agent_calling.py`
5. **semantic_search_func** - From OrchestratorAgent's `_semantic_search_tool` method
6. **embedding_model** - For semantic search (sentence-transformers)
7. **get_agent** - Function from `src/agents/__init__.py`
8. **Streaming callback** - Optional (None for Chainlit, events handle display)

**Implementation Approach**:
- Create a minimal OrchestratorAgent instance to extract dependencies
- Or extract initialization logic into a shared function
- Reuse existing `create_agent_graph()` from `src/agents/orchestrator/graph/graph.py`

---

## Phase 3: Chainlit App Implementation

### 3.1 Node Name Mapping

**Critical**: Map node names correctly based on actual graph structure:

- **Supervisor node** = `"supervisor"` (NOT "orchestrator")
- **Sub-agents** = `["guardian", "specialist", "optimizer", "pathfinder", "canary"]`
- **Semantic search** = `"semantic_search"` (tool/service, can be step or main chat)
- **Main chat** = Supervisor responses (when routing to FINISH or synthesizing)

### 3.2 Event Type Mapping

From `astream_events(version="v1")`, we need to handle:

| Event Type | Meaning | UI Action |
|------------|---------|-----------|
| `on_chain_start` | Node starts executing | Create step for sub-agents |
| `on_chain_end` | Node completes | Finalize step |
| `on_chat_model_start` | LLM starts generating | Show "thinking..." in step |
| `on_chat_model_stream` | LLM streams tokens | Typewriter effect in step/main chat |
| `on_tool_start` | Tool execution begins | Log tool name in agent step |
| `on_tool_end` | Tool execution completes | Optional: show result summary |
| `on_chain_error` | Error occurred | Show error in step/main chat |

### 3.3 State Management

**Per-Session State**:
- `graph`: Compiled graph instance
- `history`: Conversation history (list of messages)
- `context_id`: Knowledge base context (default: "bedrock_kb")
- `active_steps`: Dict tracking open Chainlit steps `{node_name: cl.Step}`

**Graph State** (passed to `astream_events`):
```python
{
    "messages": [HumanMessage(content=user_message)],
    "next": "",
    "current_task_instruction": "",
    "context_id": context_id,
    "agent_responses": [],
    "user_question": user_message
}
```

---

## Phase 4: Implementation Details

### 4.1 Graph Initialization Function

**File**: `src/interface/chainlit/graph_factory.py`

```python
"""
Graph factory for Chainlit UI.

Creates and initializes LangGraph workflow with all dependencies.
"""
from pathlib import Path
from typing import Callable, Optional
from langchain_core.messages import HumanMessage

from src.agents.orchestrator import OrchestratorAgent
from src.agents.orchestrator.graph.graph import create_agent_graph
from src.agents.orchestrator.agent_calling import call_specialist_agent
from src.agents import get_agent

def create_chainlit_graph(
    context_id: str = "bedrock_kb",
    config_path: Optional[str] = None,
    streaming_callback: Optional[Callable] = None
):
    """
    Create and initialize LangGraph workflow for Chainlit.
    
    This function extracts all dependencies needed for graph creation
    by initializing an OrchestratorAgent instance, then uses those
    dependencies to create the graph.
    
    Args:
        context_id: Knowledge base context identifier
        config_path: Path to orchestrator config file (default: config/orchestrator.yaml)
        streaming_callback: Optional callback (None for Chainlit - events handle display)
    
    Returns:
        Compiled LangGraph workflow ready for astream_events()
    """
    # 1. Initialize OrchestratorAgent to get dependencies
    if config_path is None:
        config_path = str(Path("config/orchestrator.yaml"))
    
    orchestrator = OrchestratorAgent(config_path=config_path)
    
    # 2. Set context to load knowledge base
    orchestrator.set_context(context_id)
    
    # 3. Load supervisor prompt
    supervisor_prompt_path = Path("prompts/orchestrator/supervisor.txt")
    if supervisor_prompt_path.exists():
        supervisor_prompt = supervisor_prompt_path.read_text()
    else:
        # Fallback prompt
        supervisor_prompt = """You are the Orchestrator Agent..."""
    
    # 4. Build orchestrator prompt with context
    orchestrator_prompt = orchestrator._build_system_prompt_with_context()
    
    # 5. Extract dependencies
    llm = orchestrator.llm
    embedding_model = orchestrator.embedding_model
    semantic_search_func = orchestrator._semantic_search_tool
    
    # 6. Create graph using existing function
    graph = create_agent_graph(
        llm=llm,
        supervisor_prompt=supervisor_prompt,
        call_specialist_agent_func=call_specialist_agent,
        semantic_search_func=semantic_search_func,
        embedding_model=embedding_model,
        get_agent_func=get_agent,
        orchestrator_prompt=orchestrator_prompt,
        streaming_callback=streaming_callback  # None for Chainlit
    )
    
    return graph
```

### 4.2 Chainlit App Structure

**File**: `app.py` (project root)

```python
"""
Chainlit UI for Agent Orchestration POC.

Provides web-based interface with main chat and expandable agent steps.
"""
import chainlit as cl
from langchain_core.messages import HumanMessage
from src.interface.chainlit.graph_factory import create_chainlit_graph

# Node name constants
SUB_AGENTS = ["guardian", "specialist", "optimizer", "pathfinder", "canary"]
SEMANTIC_SEARCH_NODE = "semantic_search"
SUPERVISOR_NODE = "supervisor"

# Agent emoji mapping
AGENT_EMOJIS = {
    "guardian": "🛡️",
    "specialist": "🔧",
    "optimizer": "🎯",
    "pathfinder": "🧭",
    "canary": "🐤",
    "semantic_search": "🔍"
}

@cl.on_chat_start
async def start():
    """Initialize session when user starts chat."""
    # Initialize session state
    context_id = cl.user_session.get("context_id", "bedrock_kb")
    
    # Create graph for this session
    try:
        graph = create_chainlit_graph(context_id=context_id)
        cl.user_session.set("graph", graph)
        cl.user_session.set("history", [])
        cl.user_session.set("context_id", context_id)
        
        await cl.Message(
            content="👋 **Bedrock Orchestrator Online.**\n\n"
                   "I can analyze portfolios, troubleshoot issues, and optimize campaigns. "
                   "How can I help?"
        ).send()
    except Exception as e:
        await cl.Message(
            content=f"❌ **Error initializing orchestrator:** {str(e)}\n\n"
                   "Please check your configuration and try again."
        ).send()

@cl.on_message
async def main(message: cl.Message):
    """Handle user message and stream graph events."""
    # 1. Get graph and history from session
    graph = cl.user_session.get("graph")
    if not graph:
        await cl.Message(content="❌ Graph not initialized. Please refresh the page.").send()
        return
    
    history = cl.user_session.get("history", [])
    context_id = cl.user_session.get("context_id", "bedrock_kb")
    
    # 2. Prepare initial state for graph
    initial_state = {
        "messages": [HumanMessage(content=message.content)],
        "next": "",
        "current_task_instruction": "",
        "context_id": context_id,
        "agent_responses": [],
        "user_question": message.content
    }
    
    # 3. Track active UI steps
    active_steps = {}
    
    # 4. Start the Supervisor's Main Message (empty at first)
    main_msg = cl.Message(content="")
    await main_msg.send()
    
    # 5. Stream graph events
    try:
        async for event in graph.astream_events(initial_state, version="v1"):
            event_type = event.get("event")
            node_name = event.get("metadata", {}).get("langgraph_node", "")
            
            # --- SUB-AGENT ACTIVITY (Expandable Steps) ---
            if node_name in SUB_AGENTS:
                await _handle_sub_agent_event(
                    event_type, event, node_name, active_steps
                )
            
            # --- SEMANTIC SEARCH (Can be step or main chat) ---
            elif node_name == SEMANTIC_SEARCH_NODE:
                await _handle_semantic_search_event(
                    event_type, event, active_steps
                )
            
            # --- SUPERVISOR ACTIVITY (Main Chat) ---
            elif node_name == SUPERVISOR_NODE:
                await _handle_supervisor_event(
                    event_type, event, main_msg
                )
    
    except Exception as e:
        await cl.Message(
            content=f"❌ **Error during execution:** {str(e)}"
        ).send()
        return
    
    # 6. Finalize main message
    await main_msg.update()
    
    # 7. Update history for next turn
    history.append(HumanMessage(content=message.content))
    # Add final response to history (extract from final state if needed)
    cl.user_session.set("history", history)

async def _handle_sub_agent_event(event_type, event, node_name, active_steps):
    """Handle events from sub-agents (Guardian, Specialist, etc.)."""
    emoji = AGENT_EMOJIS.get(node_name, "🤖")
    agent_display_name = node_name.title()
    
    # Agent starts thinking/acting
    if event_type == "on_chain_start":
        # Create expandable step
        step = cl.Step(name=f"{emoji} {agent_display_name} Agent", type="tool")
        step.language = "markdown"
        await step.send()
        active_steps[node_name] = step
    
    # Agent streams tokens (typewriter effect)
    elif event_type == "on_chat_model_stream":
        if node_name in active_steps:
            chunk = event.get("data", {}).get("chunk", {})
            if hasattr(chunk, 'content'):
                await active_steps[node_name].stream_token(chunk.content)
    
    # Agent uses a tool (nested in agent step)
    elif event_type == "on_tool_start":
        if node_name in active_steps:
            tool_name = event.get("name", "unknown_tool")
            # Hide raw output for portfolio pacing tool
            if tool_name == "analyze_portfolio_pacing":
                await active_steps[node_name].stream_token(
                    f"\n\n*🛠️ Running Tool: `{tool_name}`...*\n\n"
                )
            else:
                await active_steps[node_name].stream_token(
                    f"\n\n*🛠️ Running Tool: `{tool_name}`...*\n\n"
                )
    
    # Agent completes
    elif event_type == "on_chain_end":
        if node_name in active_steps:
            # Step will auto-close, or we can explicitly finalize
            pass

async def _handle_semantic_search_event(event_type, event, active_steps):
    """Handle semantic search events."""
    # Decide: show as step or inline in main chat?
    # For now, show as step for consistency
    if event_type == "on_chain_start":
        step = cl.Step(name="🔍 Semantic Search", type="tool")
        step.language = "markdown"
        await step.send()
        active_steps["semantic_search"] = step
    
    elif event_type == "on_tool_start":
        if "semantic_search" in active_steps:
            query = event.get("data", {}).get("input", {}).get("query", "")
            await active_steps["semantic_search"].stream_token(
                f"*Searching knowledge base for: `{query}`...*\n\n"
            )

async def _handle_supervisor_event(event_type, event, main_msg):
    """Handle supervisor/orchestrator events (main chat)."""
    # Supervisor streams reasoning or final response
    if event_type == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk", {})
        if hasattr(chunk, 'content'):
            await main_msg.stream_token(chunk.content)
```

### 4.3 Event Routing Logic

**Decision Tree**:
```
Event Received
    ↓
What node? (langgraph_node metadata)
    ↓
├─ supervisor → Main Chat Window
├─ guardian/specialist/optimizer/pathfinder/canary → Expandable Step
├─ semantic_search → Expandable Step (or main chat, TBD)
└─ unknown → Log and continue
```

---

## Phase 5: Key Implementation Considerations

### 5.1 Context ID Handling

**Options**:
1. **Default**: Use `"bedrock_kb"` as default
2. **Settings Sidebar**: Allow user to change via Chainlit settings
3. **URL Parameter**: Support `?context_id=xyz` in URL
4. **Per-Message**: Allow context switching mid-conversation

**Recommendation**: Start with default, add settings sidebar later.

### 5.2 Streaming Callback vs Events

**Current State**: CLI uses `streaming_callback` parameter for real-time updates.

**Chainlit Approach**: Use `astream_events` exclusively. Pass `streaming_callback=None` when creating graph.

**Consideration**: Some existing code might emit events via callback. We need to ensure `astream_events` captures all necessary information.

### 5.3 Tool Output Handling

**Portfolio Pacing Tool**:
- Hide raw tool output (Guardian formats it)
- Show tool execution indicator: "🛠️ Running Tool: analyze_portfolio_pacing..."
- Guardian's formatted response appears in Guardian's step

**Semantic Search**:
- Show search query
- Show result count
- Optionally show top results (if not too verbose)

**Other Tools**:
- Show tool name and key arguments
- Show completion status
- Hide verbose output unless debugging

### 5.4 Error Handling

**Graph Initialization Failures**:
- Show error message in Chainlit
- Allow retry
- Log error details

**Event Streaming Errors**:
- Catch exceptions in event loop
- Show error in appropriate step/main chat
- Continue processing if possible

**Agent Execution Errors**:
- Show error in agent's step
- Don't crash entire UI
- Allow user to retry

---

## Phase 6: UI/UX Enhancements

### 6.1 Agent Step Display

**Visual Design**:
- **Header**: Emoji + Agent Name (e.g., "🛡️ Guardian Agent")
- **Collapsed by default**: User clicks to expand
- **Content**: 
  - Thinking process (if visible)
  - Tool calls (inline)
  - Final response

**Step States**:
- **Running**: Show spinner/animation
- **Completed**: Show checkmark
- **Error**: Show error icon and message

### 6.2 Main Chat Display

**Content**:
- Supervisor reasoning (routing decisions)
- Final synthesized responses
- Clean, conversational format

**Formatting**:
- Markdown support
- Code blocks for technical content
- Lists and tables where appropriate

### 6.3 Tool Call Visualization

**Within Agent Steps**:
```
🛡️ Guardian Agent
  └─ Thinking about portfolio analysis...
  └─ 🛠️ Running Tool: analyze_portfolio_pacing
      └─ Parameters: account_id=17, advertiser_filter=None
  └─ Analyzing results...
  └─ Portfolio is healthy. 92.3% budget utilized...
```

**Visual Indicators**:
- Tool icon (🛠️) for tool calls
- Loading spinner during execution
- Success/error indicators

---

## Phase 7: Testing Plan

### 7.1 Basic Flow Tests

- [ ] **Simple Question**: "How many agents do you have?"
  - Expected: Supervisor responds directly in main chat
  - No agent steps should appear

- [ ] **Portfolio Question**: "How is my portfolio doing?"
  - Expected: 
    - Supervisor reasoning in main chat
    - Guardian agent step appears (expandable)
    - Tool call visible in Guardian step
    - Guardian response in Guardian step
    - Supervisor synthesis in main chat

- [ ] **Multi-Agent Intro**: "Have all agents introduce themselves"
  - Expected:
    - Supervisor reasoning in main chat
    - All 4 agent steps appear (Guardian, Specialist, Optimizer, Pathfinder)
    - Each agent responds in its own step
    - Supervisor finalizes in main chat

- [ ] **Tool Usage**: Portfolio pacing tool execution
  - Expected:
    - Tool call visible in Guardian step
    - Raw tool output hidden
    - Formatted Guardian response visible

### 7.2 Edge Cases

- [ ] **Error Handling**: Graph initialization failure
  - Expected: Error message shown, user can retry

- [ ] **Long Operations**: Portfolio analysis takes time
  - Expected: Loading indicators, progress updates

- [ ] **Multiple Requests**: User sends multiple messages quickly
  - Expected: Each handled independently, no state mixing

- [ ] **Context Switching**: User changes context_id mid-conversation
  - Expected: New graph initialized, history preserved or reset

### 7.3 Comparison with CLI

- [ ] **Functionality Parity**: All CLI features work in Chainlit
- [ ] **Better UX**: Expandable steps improve clarity
- [ ] **No Regression**: Core logic unchanged, same behavior

---

## Phase 8: File Structure

```
agent_orchestration_poc/
├── app.py                                    # NEW: Chainlit entry point
├── src/
│   ├── interface/
│   │   ├── chainlit/                         # NEW: Chainlit-specific code
│   │   │   ├── __init__.py
│   │   │   └── graph_factory.py             # Graph initialization helper
│   │   └── cli/                              # Existing CLI (keep as-is)
│   │       ├── main.py
│   │       └── display.py
│   └── ...                                   # Existing code (unchanged)
├── requirements.txt                          # UPDATE: Add chainlit
├── docs/
│   └── chainlit_ui_implementation_plan.md   # This document
└── ...                                       # Other files unchanged
```

---

## Phase 9: Implementation Steps (Order)

### Step 1: Create Graph Factory
**File**: `src/interface/chainlit/graph_factory.py`
- Extract graph initialization logic
- Reuse OrchestratorAgent dependencies
- Test graph creation independently

### Step 2: Create Basic Chainlit App
**File**: `app.py`
- Minimal implementation
- Supervisor streaming to main chat
- Basic event routing

### Step 3: Implement Event Routing
**File**: `app.py` (update)
- Supervisor → main chat
- Sub-agents → expandable steps
- Test with single agent call

### Step 4: Add Tool Call Handling
**File**: `app.py` (update)
- Show tool calls within agent steps
- Handle portfolio pacing tool (hide raw output)
- Handle semantic search

### Step 5: Polish UI
**File**: `app.py` (update)
- Add emojis and formatting
- Improve error handling
- Add loading states

### Step 6: Test All Scenarios
- Run through all test cases
- Compare with CLI behavior
- Fix any discrepancies

### Step 7: Documentation
- Update README with Chainlit instructions
- Add screenshots/demos
- Document any differences from CLI

---

## Phase 10: Key Differences from Consultant's Example

### 10.1 Node Name Mapping

**Consultant's Example**:
```python
ORCHESTRATOR = "orchestrator"
```

**Our Graph**:
```python
SUPERVISOR_NODE = "supervisor"  # Actual node name in graph
```

**Fix**: Use `"supervisor"` not `"orchestrator"` when checking `node_name`.

### 10.2 Graph Import

**Consultant's Example**:
```python
from src.graph import workflow  # Direct import
```

**Our Structure**:
- Graph is created dynamically via `create_agent_graph()`
- Needs dependencies (LLM, prompts, functions)
- Created per-session with context_id

**Fix**: Create `graph_factory.py` to handle initialization.

### 10.3 Context Management

**Consultant's Example**:
- No explicit context_id handling

**Our Requirements**:
- Graph needs `context_id` in state
- Knowledge base context loaded per session
- Context affects orchestrator prompt

**Fix**: Store `context_id` in Chainlit session, pass to graph state.

### 10.4 Streaming Callback

**Consultant's Example**:
- No mention of streaming_callback

**Our Code**:
- Graph creation accepts `streaming_callback` parameter
- CLI uses it for real-time updates
- Chainlit should use `None` (events handle display)

**Fix**: Pass `streaming_callback=None` when creating graph for Chainlit.

### 10.5 Event Structure

**Consultant's Example**:
- Uses `event["data"]["chunk"].content` directly

**Our Events**:
- May need to handle different event structures
- Check for `hasattr(chunk, 'content')` vs direct access
- Handle both string and object content

**Fix**: Add defensive checks for event data structure.

---

## Phase 11: Critical Success Factors

### 11.1 No Core Logic Changes

**Principle**: Don't modify `agent_loop.py`, `guardian_agent.py`, or graph nodes.

**Why**: Core logic is stable and tested. UI should be a thin layer on top.

**How**: Use `astream_events` exclusively. Don't add new callbacks or modify existing ones.

### 11.2 Event-Driven Architecture

**Principle**: Use `astream_events` exclusively for UI updates.

**Why**: Clean separation of concerns. UI listens, doesn't control.

**How**: All UI updates triggered by events, not direct function calls.

### 11.3 State Preservation

**Principle**: Maintain conversation history correctly.

**Why**: Multi-turn conversations need context.

**How**: 
- Store history in Chainlit session
- Pass to graph state correctly
- Update after each turn

### 11.4 Error Resilience

**Principle**: Handle failures gracefully without breaking UI.

**Why**: Better user experience, easier debugging.

**How**:
- Try-catch around event streaming
- Show errors in appropriate places
- Allow retry/recovery

### 11.5 Performance

**Principle**: Ensure streaming is smooth and responsive.

**Why**: User experience depends on responsiveness.

**How**:
- Stream tokens as they arrive
- Don't block on long operations
- Show loading indicators

---

## Phase 12: Rollout Strategy

### Phase A: Basic Implementation (Week 1)
- [ ] Graph factory created
- [ ] Basic Chainlit app with supervisor streaming
- [ ] Single agent (Guardian) working

### Phase B: All Agents (Week 1-2)
- [ ] All sub-agents show as steps
- [ ] Multi-agent flows working
- [ ] Basic error handling

### Phase C: Tool Visualization (Week 2)
- [ ] Tool calls visible in steps
- [ ] Portfolio pacing tool handled correctly
- [ ] Semantic search integrated

### Phase D: Polish (Week 2-3)
- [ ] UI/UX improvements
- [ ] Error handling refined
- [ ] Loading states and indicators

### Phase E: Testing & Documentation (Week 3)
- [ ] Comprehensive testing
- [ ] Documentation updated
- [ ] README with Chainlit instructions

---

## Questions to Resolve

### Q1: Semantic Search Display
**Question**: Should semantic_search appear as an expandable step or inline in main chat?

**Options**:
- **Option A**: Expandable step (consistent with agents)
- **Option B**: Inline in main chat (it's a tool, not an agent)
- **Option C**: Configurable (user preference)

**Recommendation**: Start with Option A (expandable step) for consistency. Can change later based on feedback.

### Q2: Context ID Selection
**Question**: How should users select/change context_id?

**Options**:
- **Option A**: Settings sidebar in Chainlit
- **Option B**: URL parameter (`?context_id=xyz`)
- **Option C**: Per-message context switching
- **Option D**: Default only (hardcoded)

**Recommendation**: Start with Option D (default: "bedrock_kb"), add Option A later.

### Q3: CLI vs Chainlit
**Question**: Should we keep CLI alongside Chainlit or migrate fully?

**Options**:
- **Option A**: Keep both (CLI for dev/debugging, Chainlit for users)
- **Option B**: Migrate fully to Chainlit
- **Option C**: Make CLI optional/deprecated

**Recommendation**: Option A - Keep both. CLI is useful for development and debugging.

### Q4: AWS SSO Authentication
**Question**: How to handle AWS SSO authentication in Chainlit?

**Options**:
- **Option A**: Same as CLI (check at startup, show error if not authenticated)
- **Option B**: Chainlit-specific auth flow
- **Option C**: Skip auth check (assume already authenticated)

**Recommendation**: Option A - Check at startup, show clear error if not authenticated. Users can authenticate in terminal before starting Chainlit.

### Q5: Tool Output Verbosity
**Question**: How much tool output should be shown?

**Options**:
- **Option A**: Hide all raw tool output (agents format it)
- **Option B**: Show tool output in collapsed section
- **Option C**: Configurable verbosity

**Recommendation**: Option A for portfolio pacing (Guardian formats it), Option B for other tools (show but collapsed).

---

## Implementation Checklist

### Setup
- [ ] Install Chainlit: `pip install chainlit`
- [ ] Add to requirements.txt
- [ ] Create `src/interface/chainlit/` directory
- [ ] Create `src/interface/chainlit/__init__.py`

### Graph Factory
- [ ] Create `src/interface/chainlit/graph_factory.py`
- [ ] Implement `create_chainlit_graph()` function
- [ ] Test graph creation independently
- [ ] Handle all dependencies correctly

### Chainlit App
- [ ] Create `app.py` in project root
- [ ] Implement `@cl.on_chat_start` handler
- [ ] Implement `@cl.on_message` handler
- [ ] Implement event routing functions
- [ ] Add error handling

### Event Handling
- [ ] Handle supervisor events → main chat
- [ ] Handle sub-agent events → expandable steps
- [ ] Handle tool events → nested in steps
- [ ] Handle semantic search events

### UI Polish
- [ ] Add agent emojis
- [ ] Format messages with markdown
- [ ] Add loading states
- [ ] Improve error messages

### Testing
- [ ] Test simple questions
- [ ] Test portfolio analysis
- [ ] Test multi-agent flows
- [ ] Test error scenarios
- [ ] Compare with CLI behavior

### Documentation
- [ ] Update README with Chainlit instructions
- [ ] Add screenshots/demos
- [ ] Document differences from CLI
- [ ] Add troubleshooting guide

---

## Running Chainlit

Once implemented, run with:

```bash
# Development mode (auto-reload)
chainlit run app.py -w

# Production mode
chainlit run app.py
```

The UI will be available at `http://localhost:8000` (default port).

---

## Next Steps

1. **Review this plan** with the team
2. **Create graph_factory.py** - Extract graph initialization logic
3. **Create basic app.py** - Minimal Chainlit app with supervisor streaming
4. **Iteratively add features** - Agent steps, tool handling, polish
5. **Test thoroughly** - Compare with CLI behavior
6. **Document** - Update README and add usage instructions

---

## References

- **Consultant's Guidance**: Provided in user query (December 2025)
- **Chainlit Documentation**: https://docs.chainlit.io
- **LangGraph Events**: https://langchain-ai.github.io/langgraph/how-tos/streaming/
- **Current Graph Structure**: `src/agents/orchestrator/graph/graph.py`
- **Current CLI Implementation**: `src/interface/cli/main.py`

---

**Last Updated**: December 2025  
**Status**: Ready for Implementation

