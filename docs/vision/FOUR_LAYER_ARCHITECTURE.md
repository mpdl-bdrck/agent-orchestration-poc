# Four-Layer Architecture
## The Foundation for Autonomous Intelligence

> **Core Principle**: Separate coordination (Orchestrator), intelligence (specialist agents), tool integration (LangGraph), and capabilities (tools) for maximum flexibility and reusability.

---

## The Architecture Stack

**The Four Architectural Layers:**
1. **Level 3: Orchestrator Agent** (Coordination)
2. **Level 2: Specialist Agents** (Intelligence)
3. **Level 1: LangGraph Tool Integration** (Tool System)
4. **Level 0: Tools** (Capabilities)

**With:**
- Human supervision (oversight and governance)
- Data infrastructure (databases and APIs)

---

## Complete Stack Diagram

```
┌────────────────────────────────────────────────┐
│  EXTERNAL SUPERVISION                          │
│  • Human Operators (oversight and governance)   │
│  • Set policies and boundaries                 │
│  • Review edge cases and anomalies             │
│  • Approve high-risk changes                   │
│  • Strategic oversight                         │
└────────────────┬───────────────────────────────┘
                 │ Supervises
┌────────────────┴───────────────────────────────┐
│  Level 3: ORCHESTRATOR AGENT (Coordination Layer)│
│  • Central supervisor and intelligent router   │
│  • Routes user questions to specialist agents  │
│  • Handles knowledge base semantic search      │
│  • Answers simple questions directly            │
│  • Coordinates multi-agent workflows           │
│  • Synthesizes responses from multiple agents  │
└────────────────┬───────────────────────────────┘
                 │ Routes to
┌────────────────┴───────────────────────────────┐
│  Level 2: SPECIALIST AGENTS (Intelligence Layer)│
│  • Guardian Agent (portfolio oversight)        │
│  • Specialist Agent (diagnostics & fixes)      │
│  • Optimizer Agent (budget & bid mgmt)         │
│  • Pathfinder Agent (supply chain navigation)  │
│                                                │
│  Capabilities:                                 │
│  • Autonomous decision-making                  │
│  • Pattern learning and adaptation             │
│  • Context and memory maintenance              │
│  • Natural language reasoning                  │
│  • Agent-to-agent communication                │
└────────────────┬───────────────────────────────┘
                 │ Uses
┌────────────────┴───────────────────────────────┐
│  Level 1: LANGGRAPH TOOL INTEGRATION            │
│  • Tool registry and discovery                 │
│  • Standardized function calls                 │
│  • Request/response formatting                 │
│  • Error handling and retry logic              │
│                                                │
│  Characteristics:                              │
│  • Stateless and protocol-only                 │
│  • No intelligence or decisions                │
│  • Agent-agnostic communication                │
└────────────────┬───────────────────────────────┘
                 │ Invokes
┌────────────────┴───────────────────────────────┐
│  Level 0: TOOLS & KNOWLEDGE BASE               │
│                                                │
│  Diagnostic Tools:                             │
│  • flag_deals_for_debugging()                  │
│  • generate_debug_report()                     │
│  • detect_geo_conflicts()                      │
│  • analyze_creative_issues()                   │
│  • recommend_inventory_expansion()             │
│  • analyze_buyer_behavior()                    │
│  • diagnose_ctv_issues()                       │
│                                                │
│  Optimization Tools (Phase 2):                 │
│  • adjust_budget(), adjust_bid_price()         │
│  • pause_line_item(), reallocate_budget()      │
│                                                │
│  Supply Chain Tools (Phase 2):                 │
│  • adjust_qps(), enable_disable_deal()         │
│  • update_floor_price(), request_traffic()     │
│                                                │
│  Analytics & Reporting Tools (Phase 2):        │
│  • pull_performance_metrics()                  │
│  • detect_anomalies()                          │
│  • generate_insights_summary()                 │
│                                                │
│  Knowledge Base:                               │
│  • Troubleshooting patterns & procedures       │
│  • Diagnostic rules (validated + expanding)    │
│  • Industry best practices                     │
│  • Business context and guidelines             │
│                                                │
│  System of Record:                             │
│  • Action logs and outcomes                    │
│  • Pattern success rates                       │
│  • Client-specific learnings                   │
│                                                │
│  Characteristics:                              │
│  • Pure functions, stateless                   │
│  • No agent-specific logic                     │
│  • Reusable across all agents                  │
│  • Agent-agnostic                              │
└────────────────────────────────────────────────┘
```

---

## Why This Architecture?

### **1. Decoupling = Flexibility**

**Agent changes don't affect tools**:
- Upgrade Guardian Agent → Tools still work
- Add new Optimizer Agent → Reuses existing tools
- Swap Claude for GPT-4 → Tools unchanged

**Tool changes don't affect agents**:
- Improve geo_conflict_detector → All agents benefit
- Add new diagnostic tool → All agents can use it
- Optimize performance → Transparent to agents

**LangGraph Tool Integration standardizes everything**:
- Agents don't know implementation details
- Tools don't know which agent called them
- Clean separation of concerns

---

### **2. Tool Reusability**

**Same tool, multiple agents, different purposes**:

| Tool | Guardian Use | Specialist Use | Optimizer Use | Pathfinder Use |
|------|--------------|----------------|---------------|----------------|
| **flag_deals** | Monitor portfolio health | Find specific issues | Find budget opportunities | Identify QPS issues |
| **debug_report** | Aggregate metrics | Diagnose root causes | Validate changes | Verify deal status |
| **geo_detector** | Detect portfolio patterns | Fix specific conflicts | Understand delivery drops | Coordinate SSP targeting |
| **buyer_analyzer** | System-wide insights | Provide diagnostic context | Target high-value buyers | Negotiate deal terms |

**Build once, use everywhere** - Maximum ROI on tool development.

---

### **3. Progressive Complexity**

**Phase 1**: Simple stack
```
Orchestrator Agent
    ↓ Routes via LangGraph
Guardian Agent
    ↓ Uses LangGraph Tool Integration
Diagnostic Tools (7)
```

**Phase 2**: Add layers without disruption
```
Orchestrator Agent
    ↓ Routes via LangGraph
Guardian ←→ Specialist ←→ Optimizer ←→ Pathfinder
    ↓           ↓                ↓         ↓
LangGraph Tool Integration
    ↓           ↓                ↓         ↓
Diagnostic  Optimization    Supply    Navigation
  Tools        Tools        Tools      Tools
```

**No rewrites** - Just additions. Foundation remains stable.

---

## Information Flow

### Diagnostic Flow (Read-Only, Phase 1)

```
1. User Question
   ↓
2. Orchestrator Agent
   ↓ "I need to route this portfolio question"
   
3. Supervisor Node (LangGraph)
   ↓ RouteDecision: "guardian"
   
4. Guardian Agent
   ↓ "I need to check deal health"
   
5. LangGraph Tool Integration
   ↓ "Here are available tools: flag_deals, debug_report, etc."
   
6. Guardian Decision
   ↓ "I'll call flag_deals first"
   
7. Tool Execution via LangGraph
   ↓ Queries database, calls BidSwitch API
   
8. Tool Returns Result
   ↓ Returns structured result
   
9. Guardian Agent
   ↓ Interprets result: "Deal 12345 needs attention"
   
10. Guardian → LangGraph Tool Integration → debug_report tool
    ↓ Gets detailed diagnosis
    
11. Guardian → Orchestrator
    ↓ Returns response to supervisor
    
12. Orchestrator → User
    ↓ Synthesizes and presents answer
```

---

### Action Flow (Write Operations, Phase 2)

```
1. User Question
   ↓
2. Orchestrator Agent
   ↓ "I need to route this optimization question"
   
3. Supervisor Node (LangGraph)
   ↓ RouteDecision: "optimizer"
   
4. Optimizer Agent
   ↓ "I want to pause line item 789"
   
5. Policy Engine
   ↓ "Check if allowed: Spend is $75K > $10K limit"
   
6. Policy Decision
   ↓ "Requires approval"
   
7. Approval Workflow
   ↓ Request sent to Slack with context
   
8. Human
   ↓ Reviews, clicks ✅ Approve
   
9. Optimizer Agent
   ↓ "Approval received, executing"
   
10. LangGraph Tool Integration
    ↓ call_tool("pause_line_item", params)
    
11. Tool Execution
    ↓ Updates database, pauses line item
    
12. Tool Returns Success
    ↓ Returns success confirmation
    
13. Optimizer Agent
    ↓ Logs to SoR, schedules verification
    
14. Optimizer → Orchestrator
    ↓ Returns response to supervisor
    
15. Orchestrator → User
    ↓ Synthesizes and presents answer
    
16. Guardian Agent (24h later)
    ↓ Verifies outcome, updates success rate
```

---

## Agent Responsibilities

### Orchestrator Agent (The Central Supervisor)

**Primary Role**: Intelligent routing, coordination, and conversational interface

**Responsibilities**:
- Receives all user inputs and questions
- Analyzes question intent and context
- Routes to appropriate specialist agents or tools
- Handles knowledge base semantic search queries
- Answers simple questions directly
- Synthesizes multi-agent responses
- Maintains conversation context
- Coordinates complex multi-agent workflows

**Routing Logic**:
- Portfolio/pacing questions → Guardian Agent
- Technical troubleshooting → Specialist Agent
- Performance optimization → Optimizer Agent
- Supply chain/SSP questions → Pathfinder Agent
- Knowledge base queries → Semantic Search tool
- Simple/system questions → Direct answer (FINISH)

**Architecture Position**: Sits above specialist agents, coordinates their execution via LangGraph supervisor pattern

**Does NOT**:
- Execute specialist tasks (delegates to appropriate agents)
- Access tools directly (specialist agents use tools)
- Make business decisions (specialist agents make domain decisions)

**Why**: Separation allows Orchestrator to focus on coordination and routing while specialist agents handle domain expertise.

---

### Guardian Agent (The Portfolio Overseer)

**Primary Role**: System-wide monitoring, anomaly detection, and coordination

**Responsibilities**:
- Continuously monitors all campaigns, line items, and supply deals across the entire DSP portfolio
- Detects anomalies and performance issues using pattern recognition and statistical analysis
- Aggregates performance metrics across geos, exchanges, creatives, and audiences
- Delegates specific issues to specialized agents (Specialist, Optimizer, Pathfinder)
- Generates insights summaries and alerts for human oversight
- Maintains situational awareness of the entire programmatic ecosystem

**Does NOT**:
- Take optimization actions (delegates to Optimizer Agent)
- Negotiate with SSPs (delegates to Pathfinder Agent)
- Diagnose individual issues (delegates to Specialist Agent)

**Why**: Separation allows Guardian to maintain big-picture awareness while specialized agents handle execution.

---

### Specialist Agent (The Issue Resolution Expert)

**Primary Role**: Diagnose and resolve specific campaign and supply deal issues

**Responsibilities**:
- Responds to Guardian's delegated issue alerts
- Conducts deep diagnostic analysis on individual campaigns, line items, and supply deals
- Identifies root causes using hierarchical investigation (Campaign → Line Item → Supply Deal)
- Executes targeted fixes within policy boundaries (progressive autonomy stages)
- Verifies outcomes 24-48 hours post-intervention
- Builds pattern expertise through System of Record learning

**Listens to**: Guardian Agent (delegated alerts)
**Coordinates with**: Optimizer Agent (for budget context), Pathfinder Agent (for supply issues)
**Reports to**: Humans (for approvals and outcome verification)

---

### Optimizer Agent (The Performance Manager)

**Primary Role**: Campaign performance optimization and budget management

**Responsibilities**:
- Budget allocation and reallocation
- Bid price adjustments
- Line item pause/resume
- Creative rotation optimization

**Listens to**: Guardian Agent diagnostics, Specialist Agent findings
**Coordinates with**: Pathfinder Agent (for deal-level changes)
**Reports to**: Humans (for approvals and FYI)

---

### Pathfinder Agent (The Supply Chain Navigator)

**Primary Role**: Supply path optimization and SSP relationship management

**Responsibilities**:
- QPS limit adjustments
- Deal activation/deactivation
- Floor price coordination
- Traffic allocation optimization

**Listens to**: Guardian Agent diagnostics, Specialist Agent findings
**Coordinates with**: Optimizer Agent (for budget-informed decisions)
**Interfaces with**: SSP APIs (BidSwitch, etc.)

---

## LangGraph Tool Integration's Critical Role

### Not Just an API

**LangGraph Tool Integration provides**:
1. **Tool Discovery**: Agents discover tools through LangGraph's tool binding system
2. **Standardization**: All tools follow same request/response format
3. **Versioning**: Tools can be upgraded without agent changes
4. **Error Handling**: Centralized retry and fallback logic
5. **Authentication**: Per-agent permissions and rate limiting
6. **Audit Trail**: All tool invocations logged

**Example - Agent discovers tools**:
```python
# Guardian discovers tools through LangGraph tool binding
# Tools are bound to the LLM instance, making them available for tool calling
llm_with_tools = llm.bind_tools(tools)

# LangGraph automatically makes tools available for the agent to call
# Agent can dynamically call appropriate tools based on tool descriptions
result = execute_agent_loop(
    llm_with_tools=llm_with_tools,
    messages=messages,
    tools=tools,
    ...
)
```

---

## Tool Design Principles

### Pure Functions

**Tools should be**:
- Stateless (same input → same output)
- No side effects (except database writes/API calls)
- No agent-specific logic
- Focused on single responsibility

**Bad (agent-specific)**:
```python
def flag_deals_for_guardian():
    # Hardcoded for Guardian Agent
    ...
```

**Good (agent-agnostic)**:
```python
def flag_deals_for_debugging(
    lookback_days=7,
    limit=10,
    focus_metric="sell_through_rate"
):
    # Any agent can use with different parameters
    ...
```

---

### Tool Output Standards

**All tools return structured JSON**:
```json
{
  "status": "SUCCESS",
  "data": {...},
  "metadata": {
    "execution_time_ms": 847,
    "api_calls_made": 3,
    "cached": false
  },
  "errors": []  // Empty if successful
}
```

**Benefits**:
- Agents can rely on consistent structure
- Error handling standardized
- Performance monitoring built-in

---

## Agent Communication (Phase 2)

### Message Queue Architecture

```
Guardian Agent
    ↓ Publishes task
Message Queue (RabbitMQ/SQS)
    ↓ Routes to appropriate agent
Optimizer Agent / Pathfinder Agent
    ↓ Picks up task
    ↓ Executes via LangGraph Tool Integration
    ↓ Publishes completion
Message Queue
    ↓ Routes back to Guardian
Guardian Agent
    ↓ Receives confirmation, schedules verification
```

**Why message queue?**:
- Asynchronous (agents don't block each other)
- Decoupled (agents don't need to know about each other)
- Scalable (add more agents without coordination)
- Reliable (messages persisted, retry logic)

---

## Scaling the Architecture

### Adding New Agents (Future)

**Want to add a "Fraud Detection Agent"?**

```
1. Build agent logic (intelligence)
2. Register agent with message queue
3. Agent discovers tools via LangGraph Tool Integration (no hardcoding)
4. Agent uses existing diagnostic tools
5. Agent publishes findings to message queue
6. Other agents can react to fraud alerts

No changes to:
- Existing agents (Guardian, Optimization, Supply Path)
- LangGraph Tool Integration (tools automatically available)
- Tools (agent-agnostic, work for all)
```

**Result**: Ecosystem grows organically without disruption.

---

### Adding New Tools

**Want to add "predictive_deal_failure" tool?**

```
1. Build tool function (capability)
2. Register with LangGraph Tool Integration (bind to LLM)
3. All agents automatically discover it
4. Guardian can start using it immediately

No changes to:
- Agents (they discover tools dynamically)
- Other tools (independent)
- Message queue (agents coordinate same way)
```

**Result**: Capabilities expand without architectural changes.

---

## Why This Wins

### vs. Monolithic Design

**Monolithic** (what NOT to do):
```python
class CampaignOptimizer:
    """Everything in one system"""
    def monitor_and_optimize():
        # Monitoring logic
        # Diagnostic logic
        # Optimization logic
        # SSP coordination logic
        # All coupled together
```

**Problems**:
- Can't upgrade one part without testing everything
- Can't reuse logic across different use cases
- Scaling requires duplicating everything
- One bug can break the entire system

---

### **Four-Layer**

**Separated** with clean interfaces:
```
Agents (can swap Claude for GPT-4, no tool changes)
   ↕️ LangGraph Tool Integration (standardized protocol)
Tools (can optimize without touching agents)
```

**Advantages**:
- Upgrade agents independently
- Improve tools without agent changes
- Add new agents using existing tools
- Each layer tested independently
- Failures contained (tool fails ≠ agent fails)

---

## Real-World Benefit

### Same Tools, Different Agents

**Example: flag_deals_for_debugging tool**

**Guardian Agent** (Phase 1):
```python
# Every 15 min
# Tool called via LangGraph tool integration
result = execute_agent_loop(
    llm_with_tools=llm.bind_tools([flag_deals_tool]),
    messages=messages,
    tools=[flag_deals_tool],
    ...
)
# LLM decides to call flag_deals with {"days": 7, "limit": 10}
# Find deals needing attention
```

**Optimizer Agent** (Phase 2):
```python
# Daily
# Tool called via LangGraph tool integration
result = execute_agent_loop(
    llm_with_tools=llm.bind_tools([flag_deals_tool]),
    messages=messages,
    tools=[flag_deals_tool],
    ...
)
# LLM decides to call flag_deals with {"days": 30, "metric": "cpa_over_target", "limit": 20}
# Find budget reallocation opportunities
```

**Pathfinder Agent** (Phase 2):
```python
# Hourly
# Tool called via LangGraph tool integration
result = execute_agent_loop(
    llm_with_tools=llm.bind_tools([flag_deals_tool]),
    messages=messages,
    tools=[flag_deals_tool],
    ...
)
# LLM decides to call flag_deals with {"days": 1, "metric": "qps_utilization", "limit": 5}
# Find QPS optimization candidates
```

**Future Fraud Agent**:
```python
# Continuous
# Tool called via LangGraph tool integration
result = execute_agent_loop(
    llm_with_tools=llm.bind_tools([flag_deals_tool]),
    messages=messages,
    tools=[flag_deals_tool],
    ...
)
# LLM decides to call flag_deals with {"days": 1, "metric": "suspicious_traffic_patterns", "limit": 50}
# Find potential fraud
```

**One tool, four use cases, no code duplication!**

---

## The Complete Stack

### Phase 1 Stack (Simplified)

```
Humans
    ↕️
Orchestrator Agent (Supervisor/Router)
    ↕️ Routes via LangGraph
Guardian Agent
    ↕️
LangGraph Tool Integration
    ↕️
Diagnostic Tools (Python)
    ↕️
Databases & APIs
    ↕️
PostgreSQL, BidSwitch, etc.
```

**Clean, focused, proven pattern**

---

### Phase 2 Stack (Expanded)

```
Humans (Oversight & Approval)
    ↕️
┌──────────────────────────────────────────┐
│ Agent Ecosystem                          │
│  • Guardian ←→ Specialist ←→ Optimizer ←→ Pathfinder │
│          ↕️              ↕️       ↕️         ↕️       │
│                Message Coordination              │
│          ↕️              ↕️       ↕️         ↕️       │
│    Message Queue (coordination)          │
└──────────────┬───────────────────────────┘
               ↕️
┌──────────────┴───────────────────────────┐
│ LangGraph Tool Integration                │
│  • Tool registry and discovery           │
│  • Standardized function calls           │
│  • Request/response formatting           │
└──────────────┬───────────────────────────┘
               ↕️
┌──────────────┴───────────────────────────┐
│ Tool Ecosystem                           │
│  • Diagnostic (7)                        │
│  • Optimization (5)                      │
│  • Supply Chain (6)                      │
│  • Analytics & Reporting (3)             │
│  • Knowledge Base (context)              │
│  • System of Record (learning)           │
└──────────────┬───────────────────────────┘
               ↕️
Data Layer (PostgreSQL, Redshift, BidSwitch, SSP APIs)
```

**Same architecture, expanded capabilities**

---

## Benefits of This Architecture

### **1. Future-Proof**
Add agents, add tools, swap components - architecture remains stable

### **2. Testable**
Each layer tested independently with clear interfaces

### **3. Debuggable**
LangGraph Tool Integration logs all calls, easy to trace issues through stack

### **4. Scalable**
Add capacity at any layer without affecting others

### **5. Maintainable**
Clear boundaries, focused responsibilities, reusable components

---

**This is the foundation that makes the entire agentic vision possible.**

---

## Related Documentation

- [Progressive Autonomy](PROGRESSIVE_AUTONOMY.md)
- [System of Record](SYSTEM_OF_RECORD.md)
- [Agentic Vision Overview](README.md)

