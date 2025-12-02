# Progressive Autonomy Model
## Four-Stage Evolution from Alerts to Autonomous Action

> **Key Insight**: Don't jump from "alert humans" to "act autonomously" - build trust and validation through intermediate learning stages.

---

## The Four Stages

### Overview

```
Stage 1: Diagnosis & Alert
  Guardian → Identifies issue → Human finds & executes fix
  Learning: None (human actions not captured)

Stage 2: Recommendation & Logging
  Guardian → Recommends specific fix → Human executes → System logs action
  Learning: Build validated action history (20-30 examples per pattern)

Stage 3: Approval-Based Action
  Guardian → Requests approval with context → Human approves → Agent executes
  Learning: Refine confidence thresholds based on Stage 2 success rates

Stage 4: Autonomous Action
  Guardian → Executes within policy (if success rate ≥90%) → Human oversight only
  Learning: Continuous refinement, client-specific policies
```

**Critical Point**: Stage 2 is the **trust-building bridge** that validates agent recommendations before granting autonomous authority.

---

## User Interface: The Proactive Notification Panel

The **Proactive Notification Panel** is the UI mechanism that transforms the reactive chatbot into a proactive command center, materializing each stage of progressive autonomy.

### How Stages Materialize in the Panel

**Stage 1 - Alert Display:**
- Panel shows alerts with full context (campaign ID, deal ID, issue type, details)
- User clicks alert → Context-injected message sent to Orchestrator → Agent investigates
- **Panel Behavior**: Passive notification, user initiates investigation

**Stage 2 - Recommendation Display:**
- Panel shows alerts with recommended actions and expected outcomes
- User clicks "✅ Log Fix" or "❌ False Alarm" → System logs action for learning
- **Panel Behavior**: Action logging buttons, outcome tracking begins

**Stage 3 - Approval Requests:**
- Panel shows approval requests with success rate data (e.g., "100% (8/8 successful)")
- User clicks "✅ Approve" → Agent executes action autonomously
- **Panel Behavior**: Approval workflow, success rate display

**Stage 4 - Autonomous Action Display:**
- Panel shows executed actions (FYI only) with outcomes
- User clicks → See action details and outcome verification
- **Panel Behavior**: Post-execution notifications, outcome verification display

> **See**: [`../PROACTIVE_NOTIFICATION_PANEL.md`](../PROACTIVE_NOTIFICATION_PANEL.md) for detailed implementation specifications.

---

## Stage 1: Diagnosis & Alert (Phase 1 Initial)

### Characteristics

**Agent Capability**: Hierarchical diagnostic monitoring
**Human Involvement**: 100% (finds and executes all fixes)
**Learning**: Minimal (agent learns patterns, but not from human actions)

### Specialist's Hierarchical Diagnostic Process

Specialist doesn't just diagnose deals in isolation - it understands the Bedrock Platform entity hierarchy:

**Campaign Level** (checked FIRST):
- Campaign status (enabled/disabled)
- Budget exhaustion
- Date alignment (line items within campaign flight dates)
- Line item count and health

**Line Item Level** (checked second):
- Curation package assignments (must have ONE package)
- Budget and pacing
- Targeting configuration

**Supply Deal Level** (checked last):
- **PMP Supply Deals**: Performance via BidSwitch API (geo conflicts, creative issues, QPS)
- **Open Exchange Supply Deals**: Filter list effectiveness, performance metrics

**Intelligence**: Campaign disabled? Don't analyze 50 Supply Deals - alert the campaign issue (prevents alert noise).

### Workflow

```
Every 15 minutes (or on user request):

  User Question → Orchestrator Agent
  Orchestrator → Supervisor Node (LangGraph)
  Supervisor → RouteDecision: "guardian"
  
  Guardian → Detects Campaign 89 showing delivery issues
  Guardian → Delegates to Specialist: "Investigate Campaign 89"

  Specialist → Campaign health check (campaign-analysis tool):
    Queries: Campaign status, budget, dates, line items
  
  IF campaign issues found (disabled, budget exhausted, dates invalid):
    Specialist → Slack: 
      "🚨 Campaign 89: DISABLED
       Impact: 57 Supply Deal relationships non-delivering
       Root Cause: Campaign statusId=2 (disabled)
       Fix: Enable campaign (set statusId=1)
       Affected: ALL 17 line items, 8 curation packages, 30 unique Supply Deals"
    
    Guardian → Early Exit (skip individual Supply Deal analysis)
  
  ELSE (campaign healthy):
    Guardian → Tool: flag_deals_for_debugging() # Only for healthy campaigns!
    Guardian → Tool: generate_debug_report(deal_id) # PMP Supply Deals only
    Guardian → Identifies Supply Deal-specific issue (e.g., "geo_targeting_conflict")
    
    Guardian → Response to Orchestrator
    Orchestrator → User:
      "🚨 Deal 12345: Geo conflict detected
       Confidence: 87%
       Symptoms: 68% delivery drop
       Likely cause: Double geo-targeting"
  
  Human reads alert
  Human investigates manually
  Human applies fix (maybe what Guardian suggested, maybe not)
  [System has no idea what human did or if it worked]
```

**Gap**: No feedback loop - Guardian never learns if diagnosis was correct or fix worked.

**Key Improvement**: Campaign-level check prevents alert noise when root cause is campaign-level (not deal-level).

### Notification Panel Behavior (Stage 1)

The Proactive Notification Panel displays alerts with:
- Agent emoji and alert type (e.g., 🛡️ Guardian Alert)
- Campaign/Deal ID
- Issue details and context
- Timestamp
- "Click to investigate →" prompt

When user clicks, the panel sends a context-injected message to the Orchestrator:
```
SYSTEM_TRIGGER: Focus on {entity_id}. Context: {issue_type}. {details}
```

This enables one-click investigation without manual context entry. The Orchestrator routes to the appropriate agent (Guardian, Specialist, Optimizer, or Pathfinder) with full context, eliminating the need for users to explain the issue.

---

## Stage 2: Recommendation & Automatic Detection

### Purpose

**Build validated training data** from human expertise before enabling autonomous action through **automatic change detection**.

### Characteristics

**Agent Capability**: Diagnosis + specific fix recommendation + automatic change monitoring
**Human Involvement**: 100% execution (NO logging required)
**Learning**: **Maximum** - System observes all changes automatically

### Guardian's Dual Role in Stage 2

**Role 1: Diagnostician** (Phase 1 capability)
- Detect issues via continuous monitoring
- Generate diagnosis using tools
- Recommend specific fixes with expected outcomes
- Alert humans via Slack

**Role 2: Verifier** (NEW in Stage 2)
- Store baseline state with each recommendation (from diagnosis)
- Schedule verification checks (24h after recommendation)
- Query current system state on-demand (NO snapshots)
- Detect configuration changes automatically
- Attribute changes to recommendations (timing + matching logic)
- Measure outcomes (did the fix work?)
- Update pattern success rates continuously

**Key Innovation**: Guardian observes what humans do by monitoring system state changes - **zero human logging compliance required**.

### Workflow (Automatic Detection)

```
9:00 AM - Guardian detects issue:
  Guardian → Tool: detect_geo_conflicts(deal_id="12345")
  Guardian → Generates specific recommendation
  
  Guardian → Stores to SoR:
    {
      "alert_id": "alert_abc123",
      "deal_id": "12345",
      "pattern_type": "geo_conflict",
      "recommended_action": "remove_supply_side_geo",
      "baseline_state": {  ← From diagnosis (already have!)
        "deal_geo_config": "BidSwitch Group 8643",
        "line_item_geo": ["UK", "DE", "FR"],
        "sell_through_rate": 0.12
      },
      "monitoring_fields": ["geo_targeting", "status"],
      "verify_at": "2025-10-24T09:00:00Z"
    }
  
  Guardian → Slack (simplified alert):
    "🚨 Deal 12345: Geo Conflict
     
     Diagnosis:
     • Both sides have geo-targeting
     • CTV deal with 68% delivery drop
     • Confidence: 87%
     
     Recommended Fix:
     • Remove supply-side geo-targeting (BidSwitch group 8643)
     • Expected recovery: 60-80%
     
     Historical: 8/8 similar fixes successful (avg 71% recovery)
     
     Guardian will automatically verify the outcome in 24 hours."

[Human works independently - NO logging required]

10:30 AM - Human executes fix:
  Human removes supply-side geo in BidSwitch UI
  [System automatically tracks change via database]

Next day 9:00 AM - Guardian's scheduled verification:
  Guardian → Queries current state (on-demand, NO snapshots):
    current_geo = db.query("SELECT geo_targeting FROM deals WHERE id=12345")
    current_metrics = execute_tool("generate_debug_report", deal_id="12345")
  
  Guardian → Compares to baseline:
    Before: geo_targeting = "BidSwitch Group 8643"
    After: geo_targeting = None
    Change detected: TRUE
  
  Guardian → Attribution:
    Recommended: "remove_supply_side_geo"
    Observed: geo_targeting changed to None
    Time delta: 25.5 hours
    Match: EXACT
    Confidence: 0.90 (timing + exact match)
    Inference: "Human followed recommendation"
  
  Guardian → Outcome measurement:
    Before sell-through: 0.12
    After sell-through: 0.21
    Recovery: 73% (within expected 60-80% range)
    Outcome: SUCCESS
  
  Guardian → Updates SoR:
    "detected_changes": [{"field": "geo_targeting", "before": "...", "after": null}],
    "human_action_inferred": "remove_supply_side_geo",
    "attribution_confidence": 0.90,
    "post_action_metrics": {"sell_through_rate": 0.21},
    "outcome": "SUCCESS",
    "success_metric": "Delivery recovered 73%"
  
  Guardian → Learning:
    Geo conflict pattern: 9/9 successful (100% success rate)
    Update confidence: 87% → 93% for future geo conflicts
```

**Value**: After 20-30 detected actions, Guardian has **statistically validated** success rates - all captured automatically without human logging.

---

### Critical Elements

#### **1. Structured Action Logging**

**Slack Reaction Mapping**:
```python
{
  "✅ Fixed - Removed Supply Geo": "remove_supply_side_geo",
  "✅ Fixed - Removed Buyer Geo": "remove_buyer_side_geo",
  "✅ Fixed - Paused Deal": "pause_deal",
  "✅ Fixed - Increased Budget": "increase_budget",
  "✅ Fixed - Other Solution": "custom_fix",  # Prompts for description
  "❌ False Alarm": "false_positive",
  "💬 Need Help": "escalate_to_specialist"
}
```

**When human clicks "Other Solution"**:
- Slack opens thread: "What did you do?"
- Human types: "Increased bid price by 40%"
- System logs custom action for learning

#### **2. Outcome Verification (Automated)**

```python
# Guardian's daily verification job
def verify_actions_from_24h_ago():
    pending = sor.get_actions_needing_verification(hours_ago=24)
    
    for action in pending:
        # Measure current metrics
        current = execute_tool("generate_debug_report", deal_id=action.deal_id)
        
        # Calculate success
        if action.pattern_type == "geo_conflict":
            recovery = calculate_delivery_recovery(action.pre_metrics, current)
            
            if recovery >= 0.60:  # Met 60% minimum expectation
                outcome = "SUCCESS"
            elif recovery >= 0.30:  # Partial improvement
                outcome = "PARTIAL"
            else:
                outcome = "FAILED"
            
            sor.update(action.alert_id, {
                "post_action_metrics": current,
                "outcome": outcome,
                "success_metric": f"Recovery: {recovery*100:.0f}%"
            })
```

#### **3. Pattern Success Rate Tracking**

```python
# Real-time success rates by pattern
geo_conflict_pattern:
  total_actions: 8
  successful: 8
  partial: 0
  failed: 0
  success_rate: 100%
  avg_recovery: 71%
  confidence_boost: +0.15

creative_misclassification_pattern:
  total_actions: 4
  successful: 4
  partial: 0  
  failed: 0
  success_rate: 100%
  avg_resolution_time: "2.5 days"
  confidence_boost: +0.10

allowlist_restriction_pattern:
  total_actions: 3
  successful: 2
  partial: 1
  failed: 0
  success_rate: 67%
  avg_improvement: "32% delivery increase"
  confidence_boost: +0.05  # Lower due to variability
```

---

### Stage 2 Data Collection

**Minimum requirements before advancing to Stage 3/4**:

| Pattern Type | Min Actions Needed | Target Success Rate | Current Status |
|--------------|-------------------|---------------------|----------------|
| **Geo conflicts** | 10 | ≥90% | 8/8 (100%) - Nearly ready |
| **Creative issues** | 10 | ≥80% | 4/4 (100%) - Need 6 more |
| **Allowlist restriction** | 8 | ≥70% | 3/3 (67%) - Need 5 more |
| **Over-segmentation** | 8 | ≥70% | 0/0 - Not started |
| **CTV complexity** | 5 | ≥70% | 0/0 - Not started |

**Note**: Stage 2 requires gathering sufficient training data before progressing to Stage 3.

### Notification Panel Behavior (Stage 2)

The panel enhances alerts with:
- Recommended action display (e.g., "remove_supply_side_geo")
- Expected outcome range (e.g., "60-80% recovery")
- Historical success rate (e.g., "8/8 similar fixes successful")
- Action buttons: "✅ Log Fix", "❌ False Alarm"

User actions are automatically logged for System of Record learning when users click these buttons. The system tracks which actions were taken and their outcomes, building the validated action history needed for Stage 3 progression. No manual logging required - the panel captures user intent through button clicks.

---

## Stage 3: Approval-Based Action (Phase 2 Initial)

### Characteristics

**Agent Capability**: Can execute actions (but must ask first)
**Human Involvement**: Approve/reject (but agent does the work)
**Learning**: Refine approval criteria, measure autonomous readiness

### Workflow

```
Guardian → Detects geo conflict
Guardian → Checks SoR: "Geo fixes successful 8/8 times (100%)"
Guardian → Decision: "High confidence, but need approval (policy)"

Guardian → Slack Approval Request:
  "🔔 APPROVAL REQUIRED
   
   Deal 12345: Geo Conflict
   Pattern: Double geo-targeting (CTV)
   
   Historical Performance:
   • This pattern: 8/8 successful (100%)
   • Avg recovery: 71% (range: 65-78%)
   • Similar clients: 5/5 successful
   
   Recommended Action:
   • Remove supply-side geo (BidSwitch group 8643)
   
   Expected Impact:
   • 60-80% delivery recovery
   • Budget: $45K (within $50K policy limit)
   
   ✅ Approve | ❌ Reject"

Human clicks: ✅ Approve

Agent → Tool: remove_supply_side_geo(deal_id="12345")
Agent → Executes fix autonomously
Agent → Logs to SoR (now with "approved_by" field)
Agent → Verifies outcome 24h later
```

**Difference from Stage 2**: 
- Agent **does the work** (human just approves)
- Approval informed by **validated success rates**
- Human trust built by showing historical data

---

### Approval Decision Support

**What agent provides**:
1. Historical success rate (from SoR)
2. Similar case examples
3. Expected vs. actual outcomes from past fixes
4. Client-specific patterns
5. Risk assessment based on real data

**Result**: Human approves in <2 minutes with confidence.

### Notification Panel Behavior (Stage 3)

The panel displays approval requests with:
- Recommended action with success rate data (e.g., "100% (8/8 successful)")
- Expected outcome and confidence level
- Historical performance metrics (similar cases, client-specific patterns)
- Approval buttons: "✅ Approve", "❌ Reject"

Upon approval, the agent executes the action autonomously. The panel tracks approval rates and outcomes, which are used to refine confidence thresholds for Stage 4 progression. Users maintain control through the approval workflow while agents handle execution.

---

## Stage 4: Autonomous Action (Phase 2 Goal)

### Characteristics

**Agent Capability**: Full autonomous execution within policy
**Human Involvement**: Oversight only (review logs, adjust policies)
**Learning**: Continuous refinement, expanding autonomous boundaries

### Workflow

```
Guardian → Detects geo conflict
Guardian → Checks SoR: "Geo fixes successful 12/12 (100%) at this client"
Guardian → Checks policy: "Success rate ≥90%, budget <$50K, CTV deal"
Guardian → Decision: "All criteria met - AUTONOMOUS FIX"

Guardian → Tool: remove_supply_side_geo(deal_id="12345")
Guardian → Executes fix without asking

Guardian → Slack (FYI notification):
  "✅ Auto-fixed Deal 12345: Geo conflict
   
   Action Taken: Removed supply-side geo
   Confidence: 95% (based on 12/12 successful cases)
   Expected: 60-80% recovery
   
   Monitoring: Will verify in 24 hours"

24 hours later:
  Guardian → Verifies: 76% recovery
  Guardian → SoR: Now 13/13 successful (100%)
  Guardian → Slack: "✅ Confirmed: Deal 12345 recovered 76%"
  
  Guardian → Learning: "Pattern continues to work, maintain autonomous status"
```

**Key difference**: No human involvement unless outcome is unexpected or policy threshold crossed.

---

### Autonomous Criteria (SoR-Informed)

**An action can be autonomous if ALL are true**:

1. **Pattern validated**: ≥10 historical actions logged
2. **High success rate**: ≥90% success rate from SoR
3. **Within policy**: Budget, spend, and risk thresholds met
4. **Client-appropriate**: Success rate ≥80% for this specific client
5. **Low variability**: Outcomes consistent (low standard deviation)

**Example decision tree**:
```python
if sor.success_rate("geo_conflict", client_id) >= 0.90 \
   and sor.sample_size("geo_conflict", client_id) >= 10 \
   and deal.budget < 50000 \
   and sor.outcome_variance("geo_conflict") < 0.15:
    
    return AUTONOMOUS
else:
    return REQUIRES_APPROVAL
```

### Notification Panel Behavior (Stage 4)

The panel shows executed actions (FYI notifications) with:
- Action taken and execution status
- Confidence level and historical success rate (e.g., "95% (12/12 successful)")
- Expected outcome and verification timeline (e.g., "verify in 24 hours")
- Click for detailed action log and outcome metrics

Users maintain oversight visibility without manual intervention. The panel displays autonomous actions as they occur, allowing users to review outcomes and adjust policies as needed. Post-execution notifications keep users informed while agents operate autonomously within validated policy boundaries.

---

## Agent-Specific Autonomy Paths

Different agents have different autonomy capabilities based on their roles:

### Guardian Agent: Oversight Only (Stage 1-2 Maximum)

**Autonomy Limit**: Alert and Recommend only

**Reasoning**:
- System-wide decisions require human strategic judgment
- Portfolio-level changes have high impact and need approval
- Guardian's role is coordination, not execution

**Responsibilities**:
- Detect anomalies across entire portfolio
- Delegate issues to specialized agents
- Coordinate multi-agent responses
- Generate insights for human oversight

**Does NOT progress to**: Stage 3-4 (approval or autonomous action)

---

### Specialist Agent: Full Autonomy Progression (Stage 1-4)

**Autonomy Path**: Alert → Recommend → Approve → Autonomous

**Reasoning**:
- Specific, measurable fixes with predictable outcomes
- Success rates can be validated through System of Record
- Individual campaign/deal changes have contained impact
- Pattern-based fixes proven through repeated validation

**Progressive Stages**:
- Stage 1: Diagnoses and alerts
- Stage 2: Recommends specific fixes, learns from human actions
- Stage 3: Requests approval for actions (graduated autonomy)
- Stage 4: Executes autonomously within validated policy boundaries (≥90% success)

---

### Optimizer Agent: Campaign-Level Autonomy (Stage 1-3)

**Autonomy Limit**: Approval-based action (Stage 3 maximum)

**Reasoning**:
- Budget decisions have financial impact requiring oversight
- Campaign optimizations affect multiple line items/deals
- Client KPIs and strategies vary significantly

**Responsibilities**:
- Budget allocation recommendations
- Bid adjustment proposals
- Line item pause/resume (with approval)

**Autonomy Cap**: Stage 3 (requires human approval for execution)

---

### Pathfinder Agent: Supply-Level Autonomy (Stage 1-3)

**Autonomy Limit**: Approval-based action (Stage 3 maximum)

**Reasoning**:
- SSP relationships require human strategic oversight
- Deal negotiations have contractual implications
- Supply chain changes affect multiple campaigns

**Responsibilities**:
- Deal discovery and recommendations
- QPS optimization proposals
- Traffic allocation suggestions

**Autonomy Cap**: Stage 3 (requires human approval for execution)

---

## Transition Between Stages

### Stage 1 → Stage 2

**Trigger**: Guardian Agent operational (Phase 1 complete)

**Preparation**:
- System of Record database deployed
- Human action logging interface ready
- Slack reactions configured

**Announcement**: "We're now collecting learning data - please log your actions when fixing Guardian alerts"

---

### Stage 2 → Stage 3

**Trigger**: Sufficient validated actions per pattern

**Criteria** (per pattern):
- ≥10 actions logged
- ≥70% success rate
- Outcomes measured and validated

**Decision**: Pattern-by-pattern progression
```
Geo conflicts: 12/12 successful → Enable Stage 3 for geo conflicts
Creative issues: 8/10 successful → Enable Stage 3 for creative issues
Allowlist: 5/8 successful → Keep in Stage 2 (need more data)
```

**Announcement**: "Geo conflict fixes moving to approval mode - Guardian will now request approval to execute validated fixes"

---

### Stage 3 → Stage 4

**Trigger**: High approval rate + continued success

**Criteria** (per pattern, per client):
- ≥20 total actions (Stage 2 + Stage 3 combined)
- ≥90% success rate
- ≥80% approval rate in Stage 3 (humans rarely reject)
- Low outcome variability

**Decision**: Pattern-by-pattern, client-by-client
```
Client A + Geo conflicts: 20/20 successful, 18/18 approved → Autonomous
Client B + Geo conflicts: 15/16 successful, 12/15 approved → Keep in Stage 3
```

**Announcement**: "Geo conflict fixes for Client A now autonomous - Guardian will execute without approval (within $50K budget limit)"

---

## Learning Mechanisms

### 1. Success Rate Calculation

```python
def calculate_pattern_success_rate(pattern_type, client_id=None, lookback_days=90):
    """
    Calculate success rate from SoR
    """
    actions = sor.query(
        pattern_type=pattern_type,
        client_id=client_id,
        since=days_ago(lookback_days),
        exclude_pending=True  # Only verified actions
    )
    
    total = len(actions)
    successful = len([a for a in actions if a.outcome == "SUCCESS"])
    partial = len([a for a in actions if a.outcome == "PARTIAL"])
    failed = len([a for a in actions if a.outcome == "FAILED"])
    
    # Weight partial as 0.5 success
    weighted_success = successful + (partial * 0.5)
    success_rate = weighted_success / total if total > 0 else 0.0
    
    return {
        "success_rate": success_rate,
        "sample_size": total,
        "breakdown": {
            "successful": successful,
            "partial": partial,
            "failed": failed
        }
    }
```

---

### 2. Confidence Adjustment

```python
def adjust_confidence_from_sor(base_confidence, pattern_type, client_id):
    """
    Dynamically adjust confidence based on SoR history
    """
    history = calculate_pattern_success_rate(pattern_type, client_id)
    
    if history['sample_size'] < 5:
        # Insufficient data - use base confidence
        return base_confidence, "Insufficient history"
    
    # Adjust based on success rate
    if history['success_rate'] >= 0.95:
        boost = +0.20
    elif history['success_rate'] >= 0.90:
        boost = +0.15
    elif history['success_rate'] >= 0.80:
        boost = +0.10
    elif history['success_rate'] >= 0.70:
        boost = +0.05
    else:
        boost = -0.10  # Lower confidence if pattern doesn't work well
    
    adjusted = min(0.98, max(0.50, base_confidence + boost))
    
    return adjusted, f"Adjusted from {history['sample_size']} actions ({history['success_rate']*100:.0f}% success)"
```

---

### 3. Client-Specific Learning

**Key Insight**: Same pattern might work differently for different clients

```python
# Client A (large brand advertiser)
geo_conflict_at_client_a:
  success_rate: 95% (19/20)
  avg_recovery: 73%
  → Autonomous threshold: Can auto-fix

# Client B (performance advertiser)  
geo_conflict_at_client_b:
  success_rate: 67% (4/6)
  avg_recovery: 45%
  → Approval required: Pattern less reliable here
```

**Policy implication**:
```python
if client_id == "client_a" and pattern == "geo_conflict":
    autonomous = True
elif client_id == "client_b" and pattern == "geo_conflict":
    autonomous = False  # Need approval
```

---

## Divergence Tracking

### What If Human Does Something Different?

**Scenario**: Guardian recommends one fix, human does another

```
Guardian recommends: "Remove supply-side geo"
Human actually does: "Paused deal entirely"

SoR logs:
  recommended_action: "remove_supply_side_geo"
  human_action_taken: "pause_deal"
  divergence: True
  
Outcome verification:
  If pause worked better than geo removal would have:
    → Update recommendation logic
    → Learn: "For Client B, pausing deals works better than geo fixes"
```

**Learning from divergence**:
- Humans know context agents don't have
- Track when humans override recommendations
- If override works better, update diagnostic logic

---

## Stage Progression Metrics

### Readiness Dashboard

```
Pattern: GEO_CONFLICT
├─ Stage 2 Progress: ████████░░ 8/10 actions needed
├─ Success Rate: 100% (8/8) ✅ >70% threshold met
├─ Sample Size: 8 ✅ Need 2 more for Stage 3
└─ Status: STAGE 2 (collecting data)

Pattern: CREATIVE_MISCLASSIFICATION  
├─ Stage 2 Progress: ████░░░░░░ 4/10 actions needed
├─ Success Rate: 100% (4/4) ✅ >70% threshold met
├─ Sample Size: 4 ⚠️ Need 6 more for Stage 3
└─ Status: STAGE 2 (collecting data)

Pattern: ALLOWLIST_RESTRICTION
├─ Stage 2 Progress: ███░░░░░░░ 3/8 actions needed
├─ Success Rate: 67% (2/3) ⚠️ Below 70% threshold
├─ Sample Size: 3 ⚠️ Need 5 more + better success rate
└─ Status: STAGE 2 (needs improvement)

Pattern: BID_PRICE_TOO_LOW
├─ Stage 3 Progress: ████████████████░░ 16/20 for Stage 4
├─ Success Rate: 94% (15/16) ✅ >90% for autonomous
├─ Approval Rate: 88% (14/16) ✅ Humans rarely reject
├─ Sample Size: 16 ⚠️ Need 4 more for Stage 4
└─ Status: STAGE 3 (approval mode)

Pattern: GEO_CONFLICT (Client A specific)
├─ Stage 4: AUTONOMOUS ✅
├─ Success Rate: 100% (12/12)
├─ Autonomous Since: 2025-11-15
└─ Actions This Month: 8 autonomous, 0 approvals needed
```

---

## Risk Mitigation Per Stage

### Stage 1 Risks
- **False positive alerts** → Human filters, no harm
- **Missed issues** → Human escalation path available

### Stage 2 Risks
- **Human doesn't log action** → Reminder system, gamification
- **Inaccurate logging** → Verification catches discrepancies
- **Insufficient samples** → Continue Stage 2 data collection

### Stage 3 Risks
- **Human approval fatigue** → Auto-progress high-success patterns to Stage 4
- **Agent acting poorly** → Rollback capability, approval saves from harm
- **Policy violations** → Pre-action policy check prevents execution

### Stage 4 Risks
- **Autonomous action fails** → Rollback + revert to Stage 3 for that pattern
- **Cascading failures** → Circuit breaker, emergency stop
- **Context blindness** → Human override always available

---

## Reverting to Lower Stages (Circuit Breaker)

### When to Demote Autonomy

**Automatic Stage Demotion**:
```python
# If success rate drops, automatically demote
if pattern_success_rate < 0.80:
    if current_stage == STAGE_4:
        demote_to(STAGE_3)  # Require approval again
        notify_humans("⚠️ Geo fixes demoted to approval mode - success rate dropped to 75%")

if pattern_success_rate < 0.60:
    if current_stage in [STAGE_3, STAGE_4]:
        demote_to(STAGE_2)  # Back to logging mode
        notify_humans("🚨 Geo fixes demoted to logging mode - success rate dropped to 55%")
```

**Manual Override**:
- Human can always force Stage 1 (alerts only)
- Human can pause all agent actions (emergency stop)
- Human can adjust success rate thresholds

---

## Implementation Phases

### Phase 1: Guardian Agent

**Foundation (Stages 1)**:
- Build Guardian monitoring
- Generate diagnostic alerts
- Basic pattern detection

**Learning Infrastructure (Stage 2 prep)**:
- System of Record database schema
- Human action logging interface
- Outcome verification automation
- **Deliverable**: Guardian operational + SoR ready

---

### Phase 2: Multi-Agent Ecosystem

**Stage 2: Recommendation & Logging**:
- Optimizer Agent in recommendation-only mode
- Human executes recommended actions
- System logs all actions and outcomes
- **Goal**: Build 20-30 validated actions per pattern

**Stage 3: Approval-Based**:
- Agents request approval for actions
- Approval informed by SoR success rates
- Agents execute approved actions
- Continue logging and learning
- **Goal**: Validate autonomous readiness

**Stage 4: Autonomous**:
- Patterns with ≥90% success → Autonomous
- Patterns with 70-89% → Remain in Stage 3
- Patterns with <70% → Demote to Stage 2
- **Goal**: 80%+ autonomous action rate

---

## Success Criteria by Stage

### Stage 2 Success
- ✅ 80%+ human logging compliance (humans actually mark actions)
- ✅ 20+ actions logged per major pattern
- ✅ Outcome verification working (24h automated checks)
- ✅ Initial success rates calculated

### Stage 3 Success
- ✅ Approval workflow smooth (<2 min per approval)
- ✅ 80%+ approval rate (humans trust recommendations)
- ✅ 90%+ success rate on approved actions
- ✅ Zero policy violations

### Stage 4 Success
- ✅ 80%+ actions autonomous (minimal approvals)
- ✅ Maintained 90%+ success rate
- ✅ Client-specific policies working
- ✅ Continuous learning observable

---

## The Trust-Building Strategy

### Trust Progression Example

**Phase 1**:
- Guardian sends alerts
- Humans fix issues manually
- No logging yet
- Trust building: "Guardian finds real issues"

**Stage 2 begins**:
- Guardian recommends specific fixes
- Humans execute and **log actions via Slack**
- System measures outcomes 24h later
- Trust building: "Guardian's recommendations are accurate"

**SoR shows results**:
```
Geo conflicts: 8/8 successful (100%)
"Every time Guardian recommended geo fix, it worked!"
```

**Stage 3 begins for geo conflicts**:
- Guardian requests approval for geo fixes
- Shows "8/8 successful" data
- Humans approve confidently
- Trust building: "Agent can execute validated fixes"

**Stage 3 data**:
```
Geo conflicts: 12/12 approved → 12/12 successful (100%)
"Humans always approve and fixes always work"
```

**Stage 4 for geo conflicts**:
- Guardian auto-fixes geo conflicts
- No approval needed (within policy)
- Humans just get FYI notifications
- Trust built: "Agent is reliable, handles routine fixes"

**Result**: Humans **earned trust in the agent** through data, not faith.

---

## Critical Design Principle: Learning Infrastructure

### The Trust-Building Foundation

**Progressive autonomy requires**:
- Excellent architecture ✅
- Clear agent roles ✅
- Policy boundaries ✅
- Learning capability ✅
- **Measurable learning outcomes** ← **THE KEY**

**The learning infrastructure**:
- System of Record = **The learning engine**
- Stage 2 = **The trust builder**
- Outcome verification = **The validator**
- Success rates = **The autonomous gateway**

**Without measurable outcomes**: Stakeholders trust autonomous action based on agent confidence scores (subjective)

**With System of Record**: Stakeholders see "This action has worked 20 times with 90% success" (objective, data-driven)

---

**This learning infrastructure is the bridge that makes Phase 2 trustworthy and achievable.**

---

## Related Documentation

- [System of Record](SYSTEM_OF_RECORD.md)
- [Three-Layer Architecture](THREE_LAYER_ARCHITECTURE.md)
- [Agentic Vision Overview](README.md)
- [Proactive Notification Panel](../PROACTIVE_NOTIFICATION_PANEL.md) - UI mechanism that materializes progressive autonomy stages

