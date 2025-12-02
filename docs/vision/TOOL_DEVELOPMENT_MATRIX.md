# BEDROCK AGENTIC TOOLS - DEVELOPMENT MATRIX
## Comprehensive Tool Registry: POC → Production Path

**Purpose:** Central reference for all tools across development stages, agent assignments, categories, and progressive autonomy applicability

**Date:** November 18, 2025
**Status:** Master Planning Document

---

## AGENT ROLES & TOOL ACCESS PATTERNS

### Orchestrator Agent (Central Supervisor)

**Primary Role**: Intelligent routing, coordination, and conversational interface

**Responsibilities**:
- Routes user questions to appropriate specialist agents
- Handles knowledge base semantic search queries
- Answers simple questions directly
- Coordinates multi-agent workflows
- Synthesizes responses from multiple agents

**Tool Access**: 
- Semantic Search tool (for knowledge base queries)
- Does NOT access specialist tools directly (delegates to specialist agents)

**Architecture Position**: Coordination layer above specialist agents

---

### Guardian Agent (Portfolio Overseer)

**Primary Role**: System-wide monitoring, anomaly detection, and coordination

**Responsibilities**:
- Monitors all campaigns, line items, and supply deals across the DSP portfolio
- Detects anomalies and performance issues using pattern recognition
- Aggregates performance metrics across geos, exchanges, creatives, and audiences
- Delegates specific issues to specialized agents (Specialist, Optimizer, Pathfinder)
- Generates insights summaries and alerts for human oversight

**Autonomy Limit**: Stage 1-2 (Alert and Recommend only)

---

### Specialist Agent (Individual Diagnostician)

**Primary Role**: Diagnose and resolve specific campaign and supply deal issues

**Responsibilities**:
- Responds to Guardian's delegated issue alerts
- Conducts deep diagnostic analysis on individual campaigns, line items, and supply deals
- Identifies root causes using hierarchical investigation (Campaign → Line Item → Supply Deal)
- Executes targeted fixes within policy boundaries (progressive autonomy stages)
- Builds pattern expertise through System of Record learning

**Autonomy Path**: Stage 1-4 (Alert → Recommend → Approve → Autonomous)

---

### Optimizer Agent (Performance Manager)

**Primary Role**: Campaign performance optimization and budget management

**Responsibilities**:
- Budget allocation and reallocation
- Bid price adjustments
- Line item pause/resume
- Creative rotation optimization

**Autonomy Limit**: Stage 1-3 (Approval-based action)

---

### Pathfinder Agent (Supply Chain Navigator)

**Primary Role**: Supply path optimization and SSP relationship management

**Responsibilities**:
- QPS limit adjustments
- Deal activation/deactivation
- Floor price coordination
- Traffic allocation optimization

**Autonomy Limit**: Stage 1-3 (Approval-based action)

---

## THE COMPREHENSIVE TOOL DEVELOPMENT MATRIX

### Master Tool Registry

| Tool Name | Dev Stage | Category | Primary Agent | Secondary Agent(s) | Autonomy Stages | POC Location | Integration Status | Priority |
|-----------|-----------|----------|---------------|-------------------|----------------|--------------|------------|----------|
| **campaign_analysis** | ✅ POC Ready | Diagnostic | Specialist | Guardian | Stage 1-4 | `tools/campaign-analysis/` | 🟡 Integration Needed | 🔴 P0 |
| **deal_debugging** | ✅ POC Ready | Diagnostic | Specialist | - | Stage 1-4 | `tools/deal-debugging/` | 🟡 Integration Needed | 🔴 P0 |
| **flag_deals_for_debugging** | 📋 Specified | Discovery | Guardian | Specialist | Stage 1-2 | `tools/deal-flagger/` | ⚪ Not Started | 🔴 P0 |
| **generate_debug_report** | 📋 Specified | Diagnostic | Specialist | - | Stage 1-2 | `tools/quick-debug-report/` | ⚪ Not Started | 🔴 P0 |
| **detect_geo_conflicts** | 📋 Specified | Diagnostic | Specialist | - | Stage 2-4 | `tools/geo-conflict-detector/` | ⚪ Not Started | 🟠 P1 |
| **analyze_creative_issues** | 📋 Specified | Diagnostic | Specialist | - | Stage 2-3 | `tools/creative-analyzer/` | ⚪ Not Started | 🟠 P1 |
| **recommend_inventory_expansion** | 📋 Specified | Optimization | Optimizer | Guardian | Stage 1-2 | `tools/allowlist-recommender/` | ⚪ Not Started | 🟡 P2 |
| **analyze_buyer_behavior** | 📋 Specified | Analytics | Guardian | Specialist | Stage 1 only | `tools/buyer-seat-analyzer/` | ⚪ Not Started | 🟡 P2 |
| **diagnose_ctv_issues** | 🔮 Planned | Diagnostic | Specialist | - | Stage 2-4 | `tools/ctv-diagnostics/` | ⚪ Future | 🟢 P3 |
| **get_campaigns** | ✅ Production Ready | Data Access | Guardian | Specialist | Stage 1-4 | N/A (Production) | ✅ Production | 🔴 P0 |
| **get_line_items** | ✅ Production Ready | Data Access | Guardian | Specialist | Stage 1-4 | N/A (Production) | ✅ Production | 🔴 P0 |
| **bidswitch_list_deals** | ✅ Production Ready | Data Access | Guardian | Pathfinder | Stage 1-4 | N/A (Production) | ✅ Production | 🔴 P0 |
| **change_log** | ✅ Production Ready | System | Guardian | Specialist | Stage 2-4 | N/A (Production) | ✅ Production | 🔴 P0 |
| **list_creatives** | ✅ Production Ready | Data Access | Guardian | Specialist | Stage 1-4 | N/A (Production) | ✅ Production | 🔴 P0 |
| **list_curation_packages** | ✅ Production Ready | Data Access | Guardian | Specialist | Stage 1-4 | N/A (Production) | ✅ Production | 🔴 P0 |
| **overview_report** | ✅ Production Ready | Analytics | Guardian | Specialist | Stage 1-4 | N/A (Production) | ✅ Production | 🔴 P0 |
| **adjust_budget** | 🔮 Planned | Action | Optimizer | - | Stage 3-4 | TBD | ⚪ Phase 2 | 🟡 P2 |
| **pause_line_item** | 🔮 Planned | Action | Optimizer | Guardian | Stage 3-4 | TBD | ⚪ Phase 2 | 🟡 P2 |
| **reallocate_budget** | 🔮 Planned | Action | Optimizer | - | Stage 4 only | TBD | ⚪ Phase 2 | 🟡 P2 |
| **adjust_qps_limit** | 🔮 Planned | Action | Pathfinder | Guardian | Stage 3-4 | TBD | ⚪ Phase 2 | 🟡 P2 |
| **enable_disable_deal** | 🔮 Planned | Action | Pathfinder | Guardian | Stage 3-4 | TBD | ⚪ Phase 2 | 🟡 P2 |
| **update_floor_price** | 🔮 Planned | Action | Pathfinder | - | Stage 4 only | TBD | ⚪ Phase 2 | 🟢 P3 |
| **request_traffic_increase** | 🔮 Planned | Action | Pathfinder | - | Stage 3-4 | TBD | ⚪ Phase 2 | 🟢 P3 |
| **create_campaign** | ✅ Production Ready | Action | Optimizer | - | Stage 3-4 | N/A (Production) | ✅ Production | 🟡 P2 |
| **create_line_item** | ✅ Production Ready | Action | Optimizer | - | Stage 3-4 | N/A (Production) | ✅ Production | 🟡 P2 |

---

## COLUMN DEFINITIONS

### Dev Stage
- **✅ POC Ready**: Tool fully implemented and tested in POC repo, ready for production integration
- **✅ Production Ready**: Tool already in production, agents can use now
- **📋 Specified**: Complete specification exists (in `plans/deal_debugging_plan.md`), ready to build
- **🔮 Planned**: Conceptual only, needs specification before build

### Category
- **Discovery**: Identify entities/issues needing attention (flag deals, find underperformers)
- **Data Access**: Query platform data (campaigns, line items, deals, packages)
- **Diagnostic**: Deep analysis of specific issues (geo conflicts, creative problems)
- **Analytics**: System-wide analysis and pattern detection (buyer behavior, performance trends)
- **Optimization**: Recommend improvements (inventory expansion, budget allocation)
- **Action**: Execute changes to platform (create, pause, adjust)
- **System**: Infrastructure tools (change_log, monitoring)

### Primary Agent
- **Guardian**: Monitoring, diagnosis, validated fixes
- **Optimization**: Budget management, performance optimization
- **Supply Path**: SSP coordination, QPS management, traffic allocation
- **Insight**: System-wide analysis, strategic alerts (Stage 1-2 only, no autonomous actions)

### Autonomy Stages
- **Stage 1**: Diagnosis & Alert (tool provides data for alerts)
- **Stage 2**: Recommendation & Logging (tool suggests fixes, tracks outcomes)
- **Stage 3**: Approval-Based Action (tool executes with human approval)
- **Stage 4**: Autonomous Action (tool executes within policy boundaries)
- **Stage 1 only**: Analytics tools that should never progress to autonomous action

### Integration Status
- **✅ Production**: Live in production, agents can use now
- **🟡 Integration Needed**: POC tool ready, needs integration
- **⚪ Not Started**: Needs development (specified or planned)
- **⚪ Phase 2**: Deferred to Phase 2
- **⚪ Future**: Long-term roadmap item

### Priority
- **🔴 P0**: Critical for Guardian Agent Phase 1 (Stage 1-2)
- **🟠 P1**: High value for Guardian Agent enhancement
- **🟡 P2**: Phase 2 (multi-agent ecosystem)
- **🟢 P3**: Future optimization/advanced features

---

## DEVELOPMENT PATH VISUALIZATION

### Phase 1: Guardian Agent Foundation (P0 Tools)

```
POC Development          Production Integration           Agent Usage
────────────────         ───────────────           ───────────

[campaign_analysis] ──► [Integration] ──► Guardian Stage 1-4
     ✅ Ready                🟡 Needed

[deal_debugging] ──────► [Integration] ──► Guardian Stage 1-4
     ✅ Ready                🟡 Needed

[flag_deals] ──────────► [Build in POC] ──► [Integration] ──► Guardian Stage 1-2
                              📋 Spec'd         🟡 Needed

[debug_report] ────────► [Build in POC] ──► [Integration] ──► Guardian Stage 1-2
                              📋 Spec'd         🟡 Needed

[get_campaigns] ────────────────────────────────────► Guardian Stage 1-4
                         ✅ Already in Production

[get_line_items] ───────────────────────────────────► Guardian Stage 1-4
                         ✅ Already in Production

[change_log] ───────────────────────────────────────► Guardian Stage 2-4
                         ✅ Already in Production            (System of Record)
```

### Phase 2: Multi-Agent Ecosystem (P1-P2 Tools)

```
[detect_geo_conflicts] ──► [Build] ──► [Integration] ──► Guardian Stage 2-4
         📋 Spec'd

[analyze_creative] ──────► [Build] ──► [Integration] ──► Guardian Stage 2-3
         📋 Spec'd

[allowlist_recommend] ───► [Build] ──► [Integration] ──► Optimization Stage 1-2
         📋 Spec'd

[buyer_analyzer] ────────► [Build] ──► [Integration] ──► Insight Stage 1
         📋 Spec'd

[adjust_budget] ─────────────────────► [Specify] ──► [Integration] ──► Optimization Stage 3-4
         🔮 Planned

[create_campaign] ──────────────────────────────────────────► Optimization Stage 3-4
                              ✅ Already in Production
```

---

## TOOL-TO-AGENT MAPPING MATRIX

### Guardian Agent Tool Portfolio

| Tool | Category | Stage 1 | Stage 2 | Stage 3 | Stage 4 | Priority |
|------|----------|---------|---------|---------|---------|----------|
| **get_campaigns** | Data Access | ✅ Monitor | ✅ Monitor | ✅ Monitor | ✅ Monitor | 🔴 P0 |
| **get_line_items** | Data Access | ✅ Analyze | ✅ Analyze | ✅ Analyze | ✅ Analyze | 🔴 P0 |
| **bidswitch_list_deals** | Data Access | ✅ Discover | ✅ Discover | ✅ Discover | ✅ Discover | 🔴 P0 |
| **campaign_analysis** | Diagnostic | ✅ Alert | ✅ Recommend | ✅ Approve | ✅ Execute | 🔴 P0 |
| **deal_debugging** | Diagnostic | ✅ Alert | ✅ Recommend | ✅ Approve | ✅ Execute | 🔴 P0 |
| **flag_deals_for_debugging** | Discovery | ✅ Identify | ✅ Prioritize | - | - | 🔴 P0 |
| **generate_debug_report** | Diagnostic | ✅ Alert | ✅ Recommend | - | - | 🔴 P0 |
| **detect_geo_conflicts** | Diagnostic | - | ✅ Detect | ✅ Fix (approved) | ✅ Fix (auto) | 🟠 P1 |
| **analyze_creative_issues** | Diagnostic | - | ✅ Detect | ✅ Escalate (approved) | - | 🟠 P1 |
| **change_log** | System | - | ✅ Track | ✅ Track | ✅ Track | 🔴 P0 |
| **list_creatives** | Data Access | ✅ View | ✅ View | ✅ View | ✅ View | 🔴 P0 |

**Guardian's Progression:**
- **Stage 1**: Uses 7 tools (6 data/discovery + 1 diagnostic for alerts)
- **Stage 2**: Uses 9 tools (adds change_log for SoR + specialized diagnostics)
- **Stage 3**: Uses 10 tools (adds approval-based fix execution)
- **Stage 4**: Uses 10 tools (autonomous fix execution within policy)

---

### Optimization Agent Tool Portfolio

| Tool | Category | Stage 1 | Stage 2 | Stage 3 | Stage 4 | Priority |
|------|----------|---------|---------|---------|---------|----------|
| **get_campaigns** | Data Access | ✅ Monitor | ✅ Monitor | ✅ Monitor | ✅ Monitor | 🔴 P0 |
| **overview_report** | Analytics | ✅ Analyze | ✅ Analyze | ✅ Analyze | ✅ Analyze | 🔴 P0 |
| **flag_deals_for_debugging** | Discovery | ✅ Identify | ✅ Prioritize | - | - | 🔴 P0 |
| **recommend_inventory_expansion** | Optimization | ✅ Suggest | ✅ Model | - | - | 🟡 P2 |
| **adjust_budget** | Action | - | - | ✅ Execute (approved) | ✅ Execute (auto) | 🟡 P2 |
| **pause_line_item** | Action | - | - | ✅ Execute (approved) | ✅ Execute (auto) | 🟡 P2 |
| **reallocate_budget** | Action | - | - | - | ✅ Execute (auto) | 🟡 P2 |
| **create_campaign** | Action | - | - | ✅ Execute (approved) | ✅ Execute (auto) | 🟡 P2 |
| **create_line_item** | Action | - | - | ✅ Execute (approved) | ✅ Execute (auto) | 🟡 P2 |
| **change_log** | System | - | ✅ Track | ✅ Track | ✅ Track | 🔴 P0 |

**Optimization's Progression:**
- **Stage 1**: Uses 4 tools (data access + discovery for opportunity identification)
- **Stage 2**: Uses 5 tools (adds change_log for learning + optimization recommendations)
- **Stage 3**: Uses 9 tools (adds action tools with approval requirement)
- **Stage 4**: Uses 9 tools (autonomous action execution for validated patterns)

---

### Supply Path Agent Tool Portfolio

| Tool | Category | Stage 1 | Stage 2 | Stage 3 | Stage 4 | Priority |
|------|----------|---------|---------|---------|---------|----------|
| **bidswitch_list_deals** | Data Access | ✅ Monitor | ✅ Monitor | ✅ Monitor | ✅ Monitor | 🔴 P0 |
| **deal_debugging** | Diagnostic | ✅ Context | ✅ Context | ✅ Context | ✅ Context | 🔴 P0 |
| **detect_geo_conflicts** | Diagnostic | - | ✅ Coordinate | ✅ Coordinate | ✅ Coordinate | 🟠 P1 |
| **adjust_qps_limit** | Action | - | - | ✅ Execute (approved) | ✅ Execute (auto) | 🟡 P2 |
| **enable_disable_deal** | Action | - | - | ✅ Execute (approved) | ✅ Execute (auto) | 🟡 P2 |
| **update_floor_price** | Action | - | - | - | ✅ Execute (auto) | 🟢 P3 |
| **request_traffic_increase** | Action | - | - | ✅ Request (approved) | ✅ Request (auto) | 🟢 P3 |
| **change_log** | System | - | ✅ Track | ✅ Track | ✅ Track | 🔴 P0 |

**Supply Path's Progression:**
- **Stage 1**: Uses 2 tools (data access for monitoring QPS/traffic)
- **Stage 2**: Uses 4 tools (adds change_log + geo coordination)
- **Stage 3**: Uses 6 tools (adds action tools with approval)
- **Stage 4**: Uses 7 tools (autonomous QPS/traffic optimization)

---

### Insight Agent Tool Portfolio

| Tool | Category | Stage 1 | Stage 2 | Notes |
|------|----------|---------|---------|-------|
| **get_campaigns** | Data Access | ✅ Aggregate | ✅ Aggregate | System-wide view |
| **overview_report** | Analytics | ✅ Analyze | ✅ Analyze | Performance patterns |
| **analyze_buyer_behavior** | Analytics | ✅ Profile | ✅ Profile | Buyer patterns |
| **flag_deals_for_debugging** | Discovery | ✅ Context | ✅ Context | Portfolio view |

**Insight's Constraint:**
- **Stage 1-2 ONLY**: Provides analysis and alerts, NEVER progresses to autonomous action
- **Rationale**: Strategic insights require human judgment, not algorithmic fixes
- **Role**: Context provider for other agents, strategic alerting for humans

---

## DEVELOPMENT SEQUENCING STRATEGY

### Phase 1A: Guardian Agent Stage 1

**Objective:** Operational monitoring with alerts

**Tools Required:**
1. ✅ `get_campaigns` (Production - ready)
2. ✅ `get_line_items` (Production - ready)
3. ✅ `bidswitch_list_deals` (Production - ready)
4. 🟡 `campaign_analysis` (POC ready → needs integration)
5. 🟡 `deal_debugging` (POC ready → needs integration)

**Work Items:**
- [ ] Integrate `campaign_analysis` tool
- [ ] Integrate `deal_debugging` tool
- [ ] Guardian Agent orchestration logic
- [ ] Slack integration
- [ ] Testing on live campaigns

**Success Criteria:** Guardian alerts humans about campaign/deal issues every 15 minutes

---

### Phase 1B: Guardian Agent Stage 2

**Objective:** Recommendations + System of Record learning

**Tools Required:**
1. All Phase 1A tools
2. ✅ `change_log` (Production - ready)
3. ⚪ `flag_deals_for_debugging` (build from spec)
4. ⚪ `generate_debug_report` (build from spec)

**Work Items:**
- [ ] Build `flag_deals_for_debugging` in POC
- [ ] Integrate flagger tool
- [ ] Build `generate_debug_report` in POC
- [ ] Integrate reporter tool
- [ ] Implement SoR with `change_log` integration
- [ ] Slack recommendation interface
- [ ] Testing + validation

**Success Criteria:** Guardian recommends fixes, tracks human actions via change_log, builds success rates

---

### Phase 1C: Guardian Agent Stages 3-4

**Objective:** Approval-based → Autonomous fixes

**Tools Required:**
1. All Phase 1A-B tools
2. ⚪ `detect_geo_conflicts` (build from spec)
3. ⚪ `analyze_creative_issues` (build from spec)
4. Action tools TBD (Phase 2 planning)

**Work Items:**
- [ ] Build `detect_geo_conflicts` in POC
- [ ] Integrate tool
- [ ] Build `analyze_creative_issues` in POC
- [ ] Integrate tool
- [ ] Approval workflow implementation
- [ ] Policy boundary validation
- [ ] Stage 3 testing (20+ actions for validation)
- [ ] Stage 4 autonomous execution (once ≥90% success rate achieved)

**Success Criteria:** Guardian executes validated fixes autonomously for patterns with ≥90% success rates

---

### Phase 2: Multi-Agent Ecosystem

**Objective:** Optimization + Supply Path + Insight agents

**Tools Required:**
1. All Guardian tools
2. ⚪ `recommend_inventory_expansion` (build from spec)
3. ⚪ `analyze_buyer_behavior` (build from spec)
4. ⚪ Action tools (specify + build)

**Success Criteria:** 3-4 agents coordinating via message queue, 80%+ autonomous action rate

---

## TOOL MIGRATION CHECKLIST

### POC → Production Integration Process

For each POC tool becoming a production tool:

**Step 1: POC Validation** ✅
- [ ] Tool fully implemented in POC repo
- [ ] Unit tests passing (≥80% coverage)
- [ ] Integration tests with real data
- [ ] Agent-ready JSON output validated
- [ ] Documentation complete

**Step 2: Integration Development** 🟡
- [ ] Create tool specification
- [ ] Integrate tool with LangGraph Tool Integration
- [ ] Parameter validation
- [ ] Error handling standardized
- [ ] Authentication/authorization configured

**Step 3: Production Integration Testing** 🟡
- [ ] Tool callable by agents via LangGraph
- [ ] Parameter passing validated
- [ ] Return format matches schema
- [ ] Error cases handled gracefully
- [ ] Performance acceptable (<5s for diagnostics, <30s for analytics)

**Step 4: Agent Integration** 🟡
- [ ] Agent code updated to use tool
- [ ] Tool invocation patterns documented
- [ ] Progressive autonomy stages defined
- [ ] Policy boundaries configured
- [ ] Monitoring/alerting set up

**Step 5: Production Deployment** ⚪
- [ ] Tool deployed to production
- [ ] POC tool retired (or kept as reference implementation)
- [ ] Documentation updated
- [ ] Team trained on new tool
- [ ] Monitoring dashboard configured

---

## TOOL CATEGORIES

| Category | Purpose | Characteristics | Examples |
|----------|---------|------------------|----------|
| **Discovery** | Identify entities/issues needing attention | Fast (<5s), high volume, scoring algorithms | `flag_deals_for_debugging`, `bidswitch_list_deals` |
| **Data Access** | Query platform data | Lightweight (<2s), standardized outputs, all stages | `get_campaigns`, `get_line_items` |
| **Diagnostic** | Deep analysis of specific issues | Heavier (5-30s), confidence scoring, root cause analysis | `campaign_analysis`, `deal_debugging` |
| **Analytics** | System-wide analysis and patterns | Aggregate (30-120s), trend detection, insights only | `analyze_buyer_behavior`, `overview_report` |
| **Optimization** | Recommend improvements | Modeling (10-60s), impact projections, recommendations only | `recommend_inventory_expansion` |
| **Action** | Execute changes to platform | Write operations, policy validation, audit logging | `adjust_budget`, `pause_line_item` |
| **System** | Infrastructure and tracking | Support tools, high reliability, all stages | `change_log`

---

## PROGRESSIVE AUTONOMY GATES

### Tool Requirements by Stage

**Stage 1 (Diagnosis & Alert):**
- ✅ Discovery tools (identify issues)
- ✅ Data access tools (gather context)
- ✅ Diagnostic tools (analyze issues)
- ❌ No action tools
- ❌ No change_log needed yet

**Stage 2 (Recommendation & Logging):**
- ✅ All Stage 1 tools
- ✅ System tools (change_log for SoR)
- ✅ Optimization tools (for recommendations)
- ✅ Specialized diagnostic tools (pattern-specific)
- ❌ No action tools yet

**Stage 3 (Approval-Based Action):**
- ✅ All Stage 1-2 tools
- ✅ Action tools (with approval gate)
- ✅ Policy validation tools
- ✅ 20+ validated actions in SoR (per pattern)
- ✅ ≥70% success rate proven

**Stage 4 (Autonomous Action):**
- ✅ All Stage 1-3 tools
- ✅ Action tools (policy-bounded execution)
- ✅ 30+ total actions validated (Stage 2+3)
- ✅ ≥90% success rate proven
- ✅ Client-specific validation
- ✅ Circuit breakers configured

---

## PRIORITY DEFINITIONS

### 🔴 P0 (Critical - Phase 1 Foundation)
**Criteria:**
- Required for Guardian Agent Stage 1-2
- Blocks autonomous monitoring
- High ROI (used continuously)

**Tools:**
- All data access tools (get_campaigns, get_line_items, etc.)
- Core diagnostics (campaign_analysis, deal_debugging)
- Discovery (flag_deals_for_debugging)
- System (change_log)

---

### 🟠 P1 (High Value - Guardian Enhancement)
**Criteria:**
- Required for Guardian Agent Stage 3-4
- Enables pattern-specific fixes
- Proven high-value patterns from roadmap

**Tools:**
- Specialized diagnostics (detect_geo_conflicts, analyze_creative_issues)
- Pattern-specific detectors

---

### 🟡 P2 (Important - Multi-Agent Phase)
**Criteria:**
- Required for Optimization/Supply Path agents
- Enables autonomous optimization
- Phase 2 features

**Tools:**
- Optimization tools (recommend_inventory_expansion, adjust_budget)
- Supply path tools (adjust_qps_limit, enable_disable_deal)
- Action tools (create_campaign, create_line_item)

---

### 🟢 P3 (Enhancement - Future Optimization)
**Criteria:**
- Nice-to-have advanced features
- Incremental improvements
- Long-term roadmap

**Tools:**
- Advanced optimizations (update_floor_price, request_traffic_increase)
- CTV-specific tools (diagnose_ctv_issues)
- Future innovations

---

## MAINTENANCE & UPDATES

**Review Cadence:**
- Regular reviews during active development
- Periodic reviews during stable operation
- Major review at phase transitions

**When to Update:**
- New tools added: Add row with categorization, agent assignment, autonomy stages, priority
- Status changes: POC → Production progression
- Agent changes: New agents or role updates
- Priority shifts: Business requirements changes

---

## CROSS-REFERENCES

### Related Documentation

**Strategic Context:**
- `00_VISION.md` - Why these tools exist (strategic goals)
- `02_PROGRESSIVE_AUTONOMY.md` - How tools enable autonomy progression
- `04_GUARDIAN_AGENT_SPEC.md` - Guardian's tool usage patterns

**Implementation Details:**
- `plans/deal_debugging_plan.md` - Detailed specs for 7 planned tools
- `tools/README.md` - POC tool registry and documentation
- `08_PHASE_1_IMPLEMENTATION.md` - Build sequence and milestones

**Technical Specs:**
- `06_DEPLOYMENT_ARCHITECTURE.md` - Where tools run
- `07_DATA_MODELS.md` - Tool input/output schemas
- Tool-specific READMEs in `tools/*/README.md`

---

## CONCLUSION

This matrix serves as the **master reference** for tool development, providing clarity on tool categorization, agent assignments, autonomy stages, and development priorities. Use this document for agent coordination and tracking progress from POC to production deployment.

**Next Steps:**
- Update as tools progress through development stages
- Validate tool categorizations with implementation teams
