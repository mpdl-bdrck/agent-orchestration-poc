# LangGraph Supervisor Pattern Implementation Plan

## Executive Summary

This document outlines the **complete replacement** of the Tool-Calling Pattern with a **LangGraph Supervisor (Router) Pattern** for multi-agent orchestration. This is a clean implementation that removes legacy code and addresses the "Recursive Intent" bug while enabling better state management, conditional routing, and scalable agent coordination.

**Timeline**: 1-2 weeks  
**Approach**: Clean implementation, no backward compatibility  
**Risk Level**: Low (clean slate implementation)  
**Code Quality**: All Python files ≤ 400 lines

---

## Table of Contents

1. [Current Architecture](#current-architecture)
2. [Target Architecture](#target-architecture)
3. [Migration Strategy](#migration-strategy)
4. [Implementation Tickets](#implementation-tickets)
5. [Code Structure](#code-structure)
6. [Testing Strategy](#testing-strategy)
7. [Rollout Plan](#rollout-plan)
8. [Success Metrics](#success-metrics)

---

## Current Architecture

### What We Have Now

```
User Question
    ↓
OrchestratorAgent.chat()
    ↓
_get_llm_response_with_tools()
    ↓
execute_agent_loop() [Tool Calling]
    ↓
LLM decides: call_specialist_agents tool
    ↓
_call_specialist_agents_tool()
    ↓
Loop through agents → call_specialist_agent()
    ↓
Each agent starts fresh (stateless)
    ↓
Return JSON string with responses
    ↓
Orchestrator synthesizes
```

### Current Problems

1. **Recursive Intent Bug**: User says "have your agents say hi" → Agent thinks it needs to coordinate other agents
2. **Context Loss**: Each agent call is stateless, no memory between calls
3. **State Management**: No shared state between orchestrator and agents
4. **Context Window Bloat**: Full conversation history passed to each agent
5. **Limited Control Flow**: Sequential only, no conditional routing or loops

---

## Target Architecture

### LangGraph Supervisor Pattern

```
User Question
    ↓
OrchestratorAgent.chat()
    ↓
[Decision Point]
    ├─→ Simple Query → Semantic Search Tool (keep current)
    └─→ Complex Query → LangGraph Supervisor Graph
                            ↓
                    Supervisor Node (Router)
                            ↓
            ┌───────────────┼───────────────┐
            │               │               │
        Guardian      Specialist      Optimizer
            │               │               │
            └───────────────┼───────────────┘
                            ↓
                    Supervisor (synthesis)
                            ↓
                    Return to User
```

### Key Improvements

1. **State Schema**: Shared state with `current_task_instruction` field
2. **Structured Routing**: Supervisor outputs structured routing decisions
3. **State Isolation**: Each agent node has access to shared state
4. **Conditional Edges**: Graph routes based on supervisor decisions
5. **Clear Boundaries**: Orchestrator routes, agents execute

---

## Implementation Strategy

### Phase 1: Foundation (Days 1-3)
- Add LangGraph dependency
- Create state schema
- Build basic graph structure
- Implement supervisor node
- Create agent node wrappers

### Phase 2: Integration (Days 4-5)
- Replace orchestrator tool-calling with graph
- Remove legacy `call_specialist_agents` tool
- Update streaming callbacks
- Integrate graph execution

### Phase 3: Cleanup & Testing (Days 6-7)
- Remove legacy code bloat
- Ensure all files ≤ 400 lines
- Comprehensive testing
- Documentation

---

## Implementation Tickets

> **Individual Ticket Files**: Each ticket has been extracted into a separate markdown file in [`docs/tickets/`](./tickets/). See the [Tickets README](./tickets/README.md) for an overview.

---

### Ticket 1: Add LangGraph Dependency and Basic Setup

**Ticket File**: [TICKET-01](./tickets/TICKET-01.md)  
**Priority**: High  
**Estimate**: 2 hours  
**Dependencies**: None

#### Tasks
- [ ] Add `langgraph>=0.0.20` to `requirements.txt`
- [ ] Install and verify LangGraph import works
- [ ] Create `src/agents/orchestrator/graph/` directory structure
- [ ] Create `src/agents/orchestrator/graph/nodes/` directory
- [ ] Add basic imports and setup
- [ ] Verify no existing code breaks

#### Acceptance Criteria
- [ ] LangGraph can be imported successfully
- [ ] Directory structure created
- [ ] No breaking changes to existing code (yet)

#### Files to Create
```
src/agents/orchestrator/graph/
├── __init__.py
├── state.py          # State schema
├── supervisor.py     # Supervisor node
└── graph.py          # Graph definition
```

---

### Ticket 2: Define State Schema

**Ticket File**: [TICKET-02](./tickets/TICKET-02.md)  
**Priority**: High  
**Estimate**: 3 hours  
**Dependencies**: Ticket 1

#### Tasks
- [ ] Create `AgentState` TypedDict with required fields
- [ ] Define message history field (append-only)
- [ ] Add `next` field for routing decisions
- [ ] Add `current_task_instruction` field (THE FIX)
- [ ] Add `context_id` and `agent_responses` fields
- [ ] Add type hints and documentation

#### Acceptance Criteria
- [ ] State schema compiles without errors
- [ ] All fields properly typed
- [ ] Documentation explains each field's purpose
- [ ] State can be instantiated with sample data

#### Code Structure
```python
# src/agents/orchestrator/graph/state.py
from typing import TypedDict, Annotated, List, Dict, Any
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """Shared state for LangGraph agent orchestration."""
    
    # Conversation history (append-only)
    messages: Annotated[List[BaseMessage], operator.add]
    
    # Routing decision from supervisor
    next: str  # "guardian" | "specialist" | "optimizer" | "pathfinder" | "FINISH"
    
    # THE FIX: Translated instruction for current agent
    # Prevents recursive intent bug
    current_task_instruction: str
    
    # Knowledge base context
    context_id: str
    
    # Accumulated agent responses
    agent_responses: List[Dict[str, Any]]
    
    # Original user question (for reference)
    user_question: str
```

---

### Ticket 3: Implement Supervisor Node with Structured Output

**Ticket File**: [TICKET-03](./tickets/TICKET-03.md)  
**Priority**: High  
**Estimate**: 4 hours  
**Dependencies**: Ticket 2

#### Tasks
- [ ] Create Pydantic model for routing decisions
- [ ] Implement supervisor node function
- [ ] Add structured output binding to LLM
- [ ] Implement instruction translation logic
- [ ] Handle "FINISH" decision
- [ ] Add logging and error handling

#### Acceptance Criteria
- [ ] Supervisor outputs valid routing decisions
- [ ] Instructions are properly translated (e.g., "have agents say hi" → "Introduce yourself")
- [ ] Structured output enforces valid agent names
- [ ] Handles edge cases (no agents needed, invalid input)

#### Code Structure
```python
# src/agents/orchestrator/graph/supervisor.py
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Literal
from .state import AgentState

class RouteDecision(BaseModel):
    """Structured routing decision from supervisor."""
    next: Literal["guardian", "specialist", "optimizer", "pathfinder", "FINISH"] = Field(
        description="The next agent to act, or FINISH if done."
    )
    instructions: str = Field(
        description="Specific, imperative instruction for the worker. "
                    "Translate user intent into direct command. "
                    "Example: User says 'Have agents say hi' -> 'Introduce yourself and your role.'"
    )
    reasoning: str = Field(
        description="Why this routing decision was made."
    )

def supervisor_node(state: AgentState) -> AgentState:
    """Router that decides next agent or FINISH."""
    # Implementation here
```

---

### Ticket 4: Create Agent Node Wrappers

**Ticket File**: [TICKET-04](./tickets/TICKET-04.md)  
**Priority**: High  
**Estimate**: 6 hours  
**Dependencies**: Ticket 2, Ticket 3

#### Tasks
- [ ] Create `guardian_node()` function
- [ ] Create `specialist_node()` function
- [ ] Create `optimizer_node()` function
- [ ] Create `pathfinder_node()` function
- [ ] Each node reads `current_task_instruction` instead of raw messages
- [ ] Each node appends response to `agent_responses`
- [ ] Each node clears `current_task_instruction` after processing
- [ ] Integrate with existing agent calling logic

#### Acceptance Criteria
- [ ] Each agent node can be called independently
- [ ] Nodes read instruction from state, not raw user prompt
- [ ] Responses are properly accumulated
- [ ] Existing agent logic is reused (no duplication)

#### Code Structure
```python
# src/agents/orchestrator/graph/nodes/guardian.py (≤400 lines, ~150 lines)
from ..state import AgentState
from ...agent_calling import call_specialist_agent
from langchain_core.messages import AIMessage

def guardian_node(state: AgentState) -> AgentState:
    """Guardian agent as a graph node."""
    instruction = state.get("current_task_instruction", "Assist the user.")
    
    # Call existing agent logic (simplified)
    response = call_specialist_agent(
        agent_name="guardian",
        question=instruction,  # Use instruction, not raw prompt
        context_id=state["context_id"],
        embedding_model=state.get("embedding_model"),
        agent_registry_get_agent=state.get("get_agent"),
        conversation_history=None  # State handles this
    )
    
    # Update state
    return {
        "messages": [AIMessage(content=response)],
        "agent_responses": state["agent_responses"] + [{"agent": "guardian", "response": response}],
        "current_task_instruction": ""  # Clear after processing
    }
```

---

### Ticket 5: Build Graph with Conditional Edges

**Ticket File**: [TICKET-05](./tickets/TICKET-05.md)  
**Priority**: High  
**Estimate**: 4 hours  
**Dependencies**: Ticket 3, Ticket 4

#### Tasks
- [ ] Create StateGraph instance
- [ ] Add supervisor node
- [ ] Add all agent nodes
- [ ] Implement routing function (`should_continue`)
- [ ] Add conditional edges from supervisor
- [ ] Add edges from agents back to supervisor
- [ ] Set entry point
- [ ] Compile graph

#### Acceptance Criteria
- [ ] Graph compiles without errors
- [ ] Routing logic works correctly
- [ ] Agents return to supervisor after execution
- [ ] FINISH condition properly terminates graph

#### Code Structure
```python
# src/agents/orchestrator/graph/graph.py
from langgraph.graph import StateGraph, END
from .state import AgentState
from .supervisor import supervisor_node
from .nodes import guardian_node, specialist_node, optimizer_node, pathfinder_node

def create_agent_graph() -> StateGraph:
    """Create the LangGraph supervisor graph."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("guardian", guardian_node)
    workflow.add_node("specialist", specialist_node)
    workflow.add_node("optimizer", optimizer_node)
    workflow.add_node("pathfinder", pathfinder_node)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Routing function
    def should_continue(state: AgentState) -> str:
        if state["next"] == "FINISH":
            return END
        return state["next"]
    
    # Conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "guardian": "guardian",
            "specialist": "specialist",
            "optimizer": "optimizer",
            "pathfinder": "pathfinder",
            END: END
        }
    )
    
    # Agents return to supervisor
    workflow.add_edge("guardian", "supervisor")
    workflow.add_edge("specialist", "supervisor")
    workflow.add_edge("optimizer", "supervisor")
    workflow.add_edge("pathfinder", "supervisor")
    
    return workflow.compile()
```

---

### Ticket 6: Replace Orchestrator Tool-Calling with Graph

**Ticket File**: [TICKET-06](./tickets/TICKET-06.md)  
**Priority**: High  
**Estimate**: 8 hours  
**Dependencies**: Ticket 5

#### Tasks
- [ ] Remove `call_specialist_agents` tool from `_create_chatbot_tools()`
- [ ] Remove `_call_specialist_agents_tool()` method
- [ ] Remove `_build_multi_agent_instruction()` method (no longer needed)
- [ ] Replace `_get_llm_response_with_tools()` with `_execute_graph()`
- [ ] Update `chat()` method to use graph instead of tool loop
- [ ] Handle graph state initialization
- [ ] Convert graph output to orchestrator response format
- [ ] Ensure orchestrator.py ≤ 400 lines (split if needed)

#### Acceptance Criteria
- [ ] All agent calls go through graph pattern
- [ ] No tool-calling pattern remains
- [ ] Graph state is properly initialized
- [ ] Responses are formatted correctly
- [ ] orchestrator.py ≤ 400 lines

#### Code Structure
```python
# src/agents/orchestrator/orchestrator.py
def chat(self, question: str, context_id: str) -> str:
    """Chat interface - now uses graph pattern."""
    self.set_context(context_id)
    
    # Initialize graph state
    initial_state = {
        "messages": [HumanMessage(content=question)],
        "next": "",
        "current_task_instruction": "",
        "context_id": context_id,
        "agent_responses": [],
        "user_question": question
    }
    
    # Execute graph
    final_state = self.graph.invoke(initial_state)
    
    # Extract and return response
    return self._extract_response_from_state(final_state)
```

---

### Ticket 7: Update Streaming Callbacks for Graph

**Ticket File**: [TICKET-07](./tickets/TICKET-07.md)  
**Priority**: High  
**Estimate**: 4 hours  
**Dependencies**: Ticket 6

#### Tasks
- [ ] Add streaming support to supervisor node
- [ ] Add streaming support to agent nodes
- [ ] Emit routing decisions as streaming events
- [ ] Emit agent responses as streaming events
- [ ] Maintain compatibility with existing streaming interface
- [ ] Test streaming output in CLI

#### Acceptance Criteria
- [ ] Routing decisions are streamed
- [ ] Agent responses are streamed
- [ ] CLI display works correctly
- [ ] No duplicate or missing events

---

### Ticket 8: Add Supervisor System Prompt

**Ticket File**: [TICKET-08](./tickets/TICKET-08.md)  
**Priority**: Medium  
**Estimate**: 3 hours  
**Dependencies**: Ticket 3

#### Tasks
- [ ] Create `prompts/orchestrator/supervisor.txt`
- [ ] Write clear instructions for routing decisions
- [ ] Include instruction translation guidelines
- [ ] Add examples of good routing decisions
- [ ] Test prompt with various queries

#### Acceptance Criteria
- [ ] Prompt produces consistent routing decisions
- [ ] Instructions are properly translated
- [ ] Handles edge cases correctly

#### Prompt Template
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

---

### Ticket 9: Unit Tests for Graph Components

**Ticket File**: [TICKET-09](./tickets/TICKET-09.md)  
**Priority**: High  
**Estimate**: 6 hours  
**Dependencies**: Ticket 5

#### Tasks
- [ ] Test state schema creation and updates
- [ ] Test supervisor routing decisions
- [ ] Test agent node execution
- [ ] Test graph compilation
- [ ] Test routing logic
- [ ] Test edge cases (FINISH, invalid routes)

#### Acceptance Criteria
- [ ] All graph components have unit tests
- [ ] Test coverage > 80%
- [ ] Tests pass consistently

---

### Ticket 10: Integration Tests for Graph Pattern

**Ticket File**: [TICKET-10](./tickets/TICKET-10.md)  
**Priority**: High  
**Estimate**: 4 hours  
**Dependencies**: Ticket 6

#### Tasks
- [ ] Test multi-agent introduction scenario
- [ ] Test single agent routing
- [ ] Test complex multi-step workflows
- [ ] Test state persistence across nodes
- [ ] Test error handling
- [ ] Compare output with expected results

#### Acceptance Criteria
- [ ] Graph produces correct results
- [ ] State is properly managed
- [ ] No regressions vs expected behavior

---

### Ticket 11: Remove Legacy Code and Enforce 400-Line Limit

**Ticket File**: [TICKET-11](./tickets/TICKET-11.md)  
**Priority**: High  
**Estimate**: 6 hours  
**Dependencies**: Ticket 6, Ticket 9, Ticket 10

#### Tasks
- [ ] Remove `execute_agent_loop()` from `utils/agent_loop.py` (or refactor if used elsewhere)
- [ ] Remove `_call_specialist_agents_tool()` method
- [ ] Remove `_build_multi_agent_instruction()` method
- [ ] Remove `call_specialist_agents` tool definition
- [ ] Audit all Python files for line count
- [ ] Split files exceeding 400 lines:
  - `orchestrator.py` → Split into orchestrator.py + orchestrator/chat.py + orchestrator/response.py
  - `agent_calling.py` → Split if needed
  - `supervisor.py` → Split into supervisor.py + supervisor/routing.py
  - Agent nodes → Ensure each ≤ 400 lines
- [ ] Update imports after splitting
- [ ] Verify all functionality still works

#### Acceptance Criteria
- [ ] No legacy tool-calling code remains
- [ ] All Python files ≤ 400 lines
- [ ] Code is well-organized and modular
- [ ] All imports work correctly
- [ ] No functionality lost

#### Files to Remove/Refactor
```
REMOVE:
- orchestrator.py: _call_specialist_agents_tool() method
- orchestrator.py: _build_multi_agent_instruction() method
- orchestrator.py: call_specialist_agents tool definition

SPLIT IF > 400 LINES:
- orchestrator.py → orchestrator/chat.py, orchestrator/response.py
- supervisor.py → supervisor/routing.py (if needed)
- agent_calling.py → agent_calling/core.py (if needed)
```

---

### Ticket 12: Performance Testing and Optimization

**Ticket File**: [TICKET-12](./tickets/TICKET-12.md)  
**Priority**: Medium  
**Estimate**: 4 hours  
**Dependencies**: Ticket 11

#### Tasks
- [ ] Benchmark graph performance
- [ ] Measure latency differences
- [ ] Measure context window usage
- [ ] Optimize if needed
- [ ] Document performance characteristics

#### Acceptance Criteria
- [ ] Performance is acceptable
- [ ] No significant regressions
- [ ] Metrics documented

---

### Ticket 13: Documentation and Migration Guide

**Ticket File**: [TICKET-13](./tickets/TICKET-13.md)  
**Priority**: Medium  
**Estimate**: 3 hours  
**Dependencies**: Ticket 11

#### Tasks
- [ ] Document new graph architecture
- [ ] Create migration guide for future changes
- [ ] Update README with graph pattern info
- [ ] Add code examples
- [ ] Document decision logic (when to use graph vs tool)

#### Acceptance Criteria
- [ ] Documentation is complete
- [ ] Examples are clear
- [ ] Migration path is documented

---

## Code Structure

### New Directory Structure

```
src/agents/orchestrator/
├── __init__.py
├── orchestrator.py          # Main orchestrator (≤400 lines, graph-based)
├── session.py              # Existing (reused, ≤400 lines)
├── graph/                   # LangGraph components (all ≤400 lines)
│   ├── __init__.py
│   ├── state.py            # State schema (~50 lines)
│   ├── supervisor.py       # Supervisor node (~200 lines)
│   ├── routing.py          # Routing logic (~150 lines, if supervisor.py > 400)
│   ├── graph.py            # Graph definition (~200 lines)
│   └── nodes/              # Agent nodes (each ≤400 lines)
│       ├── __init__.py
│       ├── guardian.py      # Guardian node (~150 lines)
│       ├── specialist.py    # Specialist node (~150 lines)
│       ├── optimizer.py     # Optimizer node (~150 lines)
│       └── pathfinder.py    # Pathfinder node (~150 lines)
├── chat/                    # Chat interface (if orchestrator.py > 400)
│   ├── __init__.py
│   ├── interface.py        # Chat method (~200 lines)
│   └── response.py         # Response extraction (~150 lines)
└── agent_calling.py         # Simplified, graph-integrated (~300 lines)
```

### Key Files (All ≤ 400 Lines)

1. **state.py**: Defines `AgentState` TypedDict (~50 lines)
2. **supervisor.py**: Router node that makes routing decisions (~200-400 lines)
3. **graph.py**: Graph definition and compilation (~200 lines)
4. **nodes/*.py**: Individual agent node implementations (~150 lines each)
5. **orchestrator.py**: Main orchestrator using graph (~300-400 lines)
6. **agent_calling.py**: Simplified agent calling logic (~300 lines)

### File Size Enforcement

- **Rule**: No Python file exceeds 400 lines
- **Strategy**: Split large files into focused modules
- **Pattern**: Extract logical components into separate files
- **Example**: If `supervisor.py` > 400 lines → Split into `supervisor.py` + `supervisor/routing.py`

---

## Testing Strategy

### Unit Tests

- **State Schema**: Test state creation, updates, type safety
- **Supervisor Node**: Test routing decisions, instruction translation
- **Agent Nodes**: Test individual node execution
- **Graph**: Test compilation, routing logic, edge cases

### Integration Tests

- **End-to-End**: Test full graph execution with real agents
- **Graph Execution**: Test graph execution paths
- **Streaming**: Test streaming callbacks through graph
- **State Management**: Test state persistence across nodes

### Regression Tests

- **API Compatibility**: Ensure public API remains stable
- **API Compatibility**: Ensure `chat()` method signature unchanged
- **CLI Compatibility**: Ensure CLI display works correctly

### Test Scenarios

1. **Multi-Agent Introduction**: "Have your agents introduce themselves"
2. **Single Agent Query**: "What is portfolio pacing?"
3. **Complex Workflow**: "Analyze portfolio, then optimize, then forecast"
4. **Error Handling**: Invalid routing, agent failures
5. **State Persistence**: Multi-turn conversations

---

## Implementation Plan

### Phase 1: Foundation (Days 1-3)
- **Day 1**: Tickets 1-2 (Setup, State Schema)
- **Day 2**: Tickets 3-4 (Supervisor, Agent Nodes)
- **Day 3**: Ticket 5 (Graph Definition) + Initial testing

### Phase 2: Integration (Days 4-5)
- **Day 4**: Ticket 6 (Replace Tool-Calling) + Ticket 7 (Streaming)
- **Day 5**: Ticket 8 (Supervisor Prompt) + Ticket 11 (Legacy Cleanup)

### Phase 3: Testing & Polish (Days 6-7)
- **Day 6**: Tickets 9-10 (Unit & Integration Tests)
- **Day 7**: Ticket 12 (Performance) + Ticket 13 (Documentation)

### Implementation Strategy

1. **Clean Implementation**: No feature flags, no gradual rollout
2. **Complete Replacement**: Remove all tool-calling code immediately
3. **Code Quality**: Enforce 400-line limit from start
4. **Testing**: Comprehensive tests before removing legacy code
5. **Documentation**: Update as we go

---

## Success Metrics

### Functional Metrics

- [ ] Recursive intent bug fixed (agents don't try to coordinate others)
- [ ] Multi-agent requests work correctly
- [ ] State persists across agent calls
- [ ] Routing decisions are accurate (>95%)

### Performance Metrics

- [ ] Latency: Graph pattern meets performance requirements
- [ ] Context window: More efficient state management
- [ ] Error rate: < 1% for graph pattern

### Quality Metrics

- [ ] Test coverage: > 80%
- [ ] Code review: All tickets reviewed
- [ ] Documentation: Complete and accurate

---

## Risks and Mitigation

### Risk 1: Complete Replacement Risk
- **Mitigation**: Comprehensive testing before removing legacy code
- **Impact**: Medium (mitigated by thorough testing)

### Risk 2: Performance Regression
- **Mitigation**: Benchmark early, optimize if needed
- **Impact**: Low (graph pattern should be more efficient)

### Risk 3: File Size Management
- **Mitigation**: Enforce 400-line limit from start, split proactively
- **Impact**: Low (clear rule, easy to enforce)

### Risk 4: Learning Curve
- **Mitigation**: Good documentation, code examples, code reviews
- **Impact**: Low (team can learn LangGraph)

---

## Dependencies

### External Dependencies
- `langgraph>=0.0.20` (new)
- Existing LangChain dependencies (unchanged)

### Internal Dependencies
- Existing agent calling logic (reused)
- Existing streaming callbacks (extended)
- Existing CLI display (compatible)

---

## Appendix

### Example: Multi-Agent Introduction Flow

```
1. User: "Have your agents introduce themselves"
2. Orchestrator detects multi-agent request → Use graph
3. Initialize state:
   - messages: [user_message]
   - next: ""
   - current_task_instruction: ""
   - user_question: "Have your agents introduce themselves"
4. Supervisor node:
   - Analyzes request
   - Routes to: "guardian"
   - Instruction: "Introduce yourself and explain your role"
5. Guardian node:
   - Reads instruction (not raw prompt!)
   - Executes: "Hello, I'm Guardian Agent..."
   - Returns to supervisor
6. Supervisor routes to: "specialist"
7. Specialist node: Introduces itself
8. ... (repeat for all agents)
9. Supervisor: next = "FINISH"
10. Graph ends, orchestrator synthesizes responses
```

### Example: Single Agent Query Flow

```
1. User: "What is portfolio pacing?"
2. Orchestrator → Graph execution
3. Supervisor routes to: "guardian"
4. Guardian node executes with instruction: "Explain portfolio pacing"
5. Supervisor: next = "FINISH"
6. Graph ends, response returned
```

---

## Questions and Decisions

### Decision 1: Clean Implementation vs Hybrid
**Decision**: Clean implementation, complete replacement  
**Rationale**: Simpler codebase, no legacy bloat, easier to maintain

### Decision 2: State Schema Design
**Decision**: TypedDict with Annotated fields  
**Rationale**: Type-safe, LangGraph-compatible, clear structure

### Decision 3: Instruction Translation
**Decision**: Supervisor translates, agents read instruction  
**Rationale**: Solves recursive intent bug, clear separation

### Decision 4: Agent Node Implementation
**Decision**: Reuse existing `call_specialist_agent()` logic, simplify  
**Rationale**: No duplication, cleaner integration with graph

### Decision 5: File Size Limit
**Decision**: Enforce 400-line maximum for all Python files  
**Rationale**: Better maintainability, easier code reviews, clearer structure

---

## Next Steps

1. **Review this plan** with team
2. **Prioritize tickets** based on business needs
3. **Assign tickets** to developers
4. **Set up project board** (GitHub Projects, Jira, etc.)
5. **Begin implementation** with Ticket 1

---

**Document Version**: 1.0  
**Last Updated**: 2024-12-XX  
**Author**: AI Assistant  
**Reviewers**: [To be assigned]

