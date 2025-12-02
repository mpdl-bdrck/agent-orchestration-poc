# System of Record & Learning Engine
## The Foundation for Autonomous Action

> **Purpose**: Document how agents learn from human expertise to earn autonomous authority through validated success rates.

> **Key Insight**: Before agents can act autonomously, they must prove their recommendations work by learning from human actions and measuring outcomes.

---

## Overview

The **System of Record (SoR)** is the learning engine that bridges human expertise and agent autonomy through **automatic change detection**. It captures:
1. What the agent recommended (baseline state at recommendation time)
2. What actually changed in the system (detected automatically 24-48h later)
3. Whether it worked (outcome validation via metrics comparison)
4. Pattern-specific success rates (validated through real outcomes)
5. Client-specific learnings (different patterns work differently per client)

**Key Innovation**: No manual human logging required - Specialist observes system state changes to infer actions taken.

**Without SoR**: Agents have confidence scores but no validation
**With SoR**: Agents have **statistically proven** success rates from observed outcomes

---

## Database Schema

### Core Table: agent_action_log

```sql
CREATE TABLE agent_action_log (
    -- Identifiers
    alert_id VARCHAR(255) PRIMARY KEY,
    deal_id VARCHAR(255),
    line_item_id VARCHAR(255),
    campaign_id VARCHAR(255),
    client_id VARCHAR(255),
    
    -- Specialist Recommendation
    action_level VARCHAR(50),               -- CAMPAIGN, LINE_ITEM, SUPPLY_DEAL
    pattern_type VARCHAR(255),              -- campaign_disabled, geo_conflict, creative_issue, etc.
    recommended_action VARCHAR(255),        -- enable_campaign, remove_supply_side_geo, pause_creative, etc.
    recommended_tool VARCHAR(255),          -- Which tool to call
    supply_deal_type VARCHAR(50),           -- PMP, OPEN_EXCHANGE, or NULL (for campaign/line item actions)
    agent_confidence DECIMAL(3,2),          -- Original confidence (0.00-1.00)
    recommendation_timestamp TIMESTAMP,
    recommendation_rationale TEXT,          -- Why agent recommended this
    
    -- Baseline State (captured from diagnosis)
    baseline_state JSONB,                   -- System state when recommendation made
    monitoring_fields JSONB,                -- Which fields to check during verification
    
    -- Detected Changes (automatic, 24h later)
    detected_changes JSONB,                 -- Actual configuration changes observed
    human_action_inferred VARCHAR(255),     -- What system deduced human did
    attribution_confidence DECIMAL(3,2),    -- Confidence in attribution (0.50-0.95)
    change_detected_at TIMESTAMP,           -- When change was observed
    time_to_action_hours INT,               -- Hours between recommendation and change
    divergence BOOLEAN,                     -- Did change differ from recommendation?
    
    -- Pre-Action State
    pre_action_metrics JSONB,               -- Baseline metrics before fix
    /* Example:
    {
      "sell_through_rate": 0.12,
      "bid_requests_per_day": 5000,
      "impressions_per_day": 600,
      "delivery_drop_percent": 68,
      "cpa": 45.00
    }
    */
    
    -- Post-Action Validation (24-48h later)
    post_action_metrics JSONB,              -- Metrics after fix
    verification_timestamp TIMESTAMP,       -- When outcome measured
    success_metric VARCHAR(255),            -- Human-readable outcome
    outcome VARCHAR(50),                    -- SUCCESS, PARTIAL, FAILED, FALSE_POSITIVE
    outcome_score DECIMAL(3,2),             -- Quantified success (0.00-1.00)
    
    -- Learning Metadata
    stage VARCHAR(50),                      -- STAGE_1, STAGE_2, STAGE_3, STAGE_4
    execution_mode VARCHAR(50),             -- human_only, human_approved, autonomous
    client_tier VARCHAR(50),                -- For client-specific learning
    deal_type VARCHAR(50),                  -- CTV, Display, Video, etc.
    budget_affected DECIMAL(12,2),          -- For risk assessment
    
    -- Contribution to Learning
    contributed_to_pattern_success BOOLEAN, -- Used in success rate calc
    confidence_adjustment DECIMAL(3,2),     -- How much this action adjusted confidence
    
    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX idx_pattern_client ON agent_action_log(pattern_type, client_id);
CREATE INDEX idx_outcome ON agent_action_log(outcome);
CREATE INDEX idx_verification_pending ON agent_action_log(verification_timestamp) 
    WHERE verification_timestamp IS NULL;
```

---

## Automatic Change Detection System

### Overview

**Core Principle**: Don't ask humans what they did - **observe what changed** in the system.

**Why**: 
- ✅ 100% capture rate (vs. ~80% manual logging compliance)
- ✅ Zero human friction (no extra work required)
- ✅ Perfectly accurate (source of truth: database state)
- ✅ Captures proactive fixes (changes before alerts)
- ✅ Detects divergences (when humans choose alternative fixes)

**How**: 
1. Store baseline state with each recommendation (from diagnostic report)
2. Query current state during verification (on-demand, no snapshots)
3. Compare to detect changes
4. Attribute changes to recommendations using timing + matching logic
5. Measure outcomes

---

### Baseline Capture (At Recommendation Time)

```python
class RecommendationLogger:
    """
    Stores baseline state when Guardian makes recommendation
    """
    
    def store_recommendation(self, diagnosis, recommendation):
        """
        Baseline already exists in diagnosis - just save it
        """
        sor.create({
            "alert_id": generate_id(),
            "deal_id": diagnosis.deal_id,
            "pattern_type": diagnosis.pattern,
            "recommended_action": recommendation.action,
            
            # Baseline from diagnosis (already have this!)
            "baseline_state": {
                "deal_geo_config": diagnosis.deal_geo_targeting,
                "line_item_geo": diagnosis.line_item_geo_filters,
                "deal_status": diagnosis.deal_status,
                "sell_through_rate": diagnosis.metrics.sell_through_rate,
                "bid_requests_per_day": diagnosis.metrics.bid_requests_per_day
            },
            
            # What to monitor during verification
            "monitoring_fields": {
                "deal": ["geo_targeting", "status"],
                "line_item": ["geo_filters"],
                "metrics": ["sell_through_rate", "delivery"]
            },
            
            # When to verify
            "verify_at": now() + hours(24)
        })
```

---

### On-Demand Verification (24h Later)

```python
class VerificationMonitor:
    """
    Verifies outcomes by querying current state (NO SNAPSHOTS)
    """
    
    def run_daily_verification(self):
        """
        Check all recommendations from 24-48h ago
        """
        due_for_verification = sor.get_pending_verifications(
            hours_ago_min=24,
            hours_ago_max=48
        )
        
        for rec in due_for_verification:
            self.verify_single_recommendation(rec)
    
    def verify_single_recommendation(self, rec):
        """
        Query current state and compare to baseline
        """
        # Query ONLY the fields we care about (efficient!)
        current_state = {
            "deal_geo": db.query(
                "SELECT geo_targeting FROM deals WHERE deal_id = ?",
                rec.deal_id
            ),
            "line_item_geo": db.query(
                "SELECT geo_filters FROM lineItems WHERE line_item_id = ?",
                rec.line_item_id
            ),
            "deal_status": db.query(
                "SELECT status FROM deals WHERE deal_id = ?",
                rec.deal_id
            ),
            "metrics": execute_tool("generate_debug_report", {
                "deal_id": rec.deal_id,
                "days": 2
            })
        }
        
        # Detect changes
        changes = self.detect_changes(rec.baseline_state, current_state)
        
        # Attribute changes to recommendation
        attribution = self.attribute_changes(changes, rec)
        
        # Measure outcome
        outcome = self.measure_outcome(rec, current_state['metrics'])
        
        # Update SoR
        sor.update(rec.alert_id, {
            "detected_changes": changes,
            "human_action_inferred": attribution.action,
            "attribution_confidence": attribution.confidence,
            "change_detected_at": now(),
            "time_to_action_hours": attribution.time_delta_hours,
            "divergence": attribution.divergence,
            "post_action_metrics": current_state['metrics'],
            "outcome": outcome.classification,
            "success_metric": outcome.description,
            "verification_timestamp": now()
        })
```

---

### Change Detection Logic

```python
def detect_changes(baseline, current):
    """
    Find what changed between baseline and current state
    """
    changes = []
    
    # Check deal geo-targeting
    if baseline['deal_geo_config'] != current['deal_geo']:
        changes.append({
            "field": "deal_geo_targeting",
            "before": baseline['deal_geo_config'],
            "after": current['deal_geo'],
            "change_type": classify_change(
                field="deal_geo_targeting",
                before=baseline['deal_geo_config'],
                after=current['deal_geo']
            )
        })
    
    # Check line item geo
    if baseline.get('line_item_geo') != current['line_item_geo']:
        changes.append({
            "field": "line_item_geo_filters",
            "before": baseline['line_item_geo'],
            "after": current['line_item_geo'],
            "change_type": "geo_filters_modified"
        })
    
    # Check status
    if baseline.get('deal_status') != current['deal_status']:
        changes.append({
            "field": "deal_status",
            "before": baseline['deal_status'],
            "after": current['deal_status'],
            "change_type": "status_changed"
        })
    
    return changes
```

---

###Attribution Logic

```python
class ChangeAttributor:
    """
    Infers human action from observed changes
    """
    
    def attribute_changes(self, changes, recommendation):
        """
        Match changes to recommendation
        """
        if not changes:
            return {
                "action": "no_action_taken",
                "confidence": 0.95,
                "attribution": "FALSE_POSITIVE or IGNORED",
                "divergence": False
            }
        
        # Find best matching change
        for change in changes:
            match = self.matches_recommendation(change, recommendation)
            
            if match.exact:
                # Change exactly matches recommendation
                return {
                    "action": recommendation.recommended_action,
                    "confidence": self.calculate_timing_confidence(change, recommendation),
                    "attribution": "FOLLOWED_RECOMMENDATION",
                    "divergence": False,
                    "time_delta_hours": (change.timestamp - recommendation.timestamp).hours
                }
            
            elif match.directional:
                # Change in right direction but different magnitude
                return {
                    "action": f"{recommendation.recommended_action}_variant",
                    "confidence": 0.80,
                    "attribution": "FOLLOWED_DIRECTION",
                    "divergence": False
                }
        
        # Changes don't match recommendation
        return {
            "action": self.infer_from_changes(changes),
            "confidence": 0.70,
            "attribution": "DIVERGENCE or ALTERNATIVE_FIX",
            "divergence": True
        }
    
    def calculate_timing_confidence(self, change, recommendation):
        """
        How confident based on timing?
        """
        hours = (change.timestamp - recommendation.timestamp).hours
        
        if hours <= 6:
            return 0.95  # Very likely related
        elif hours <= 24:
            return 0.85  # Probably related
        elif hours <= 48:
            return 0.70  # Possibly related
        else:
            return 0.50  # Could be coincidence
    
    def matches_recommendation(self, change, recommendation):
        """
        Does change match what was recommended?
        """
        # Geo-targeting example
        if recommendation.recommended_action == "remove_supply_side_geo":
            if change.field == "deal_geo_targeting" and change.after in [None, [], "national"]:
                return Match(exact=True, directional=True)
        
        # Pause example
        elif recommendation.recommended_action == "pause_deal":
            if change.field == "deal_status" and change.after == "paused":
                return Match(exact=True, directional=True)
        
        # Bid increase example
        elif recommendation.recommended_action == "increase_bid_price":
            if change.field == "bid_price" and change.after > change.before:
                return Match(exact=False, directional=True)
        
        return Match(exact=False, directional=False)
```

---

### Handling Edge Cases

#### **Case 1: Proactive Fixes** (Human fixes before alert)

```python
# Guardian (9:00 AM): Runs morning scan
diagnosis = diagnose_deal("12345")
# Issue: Geo conflict detected

# Check: Did someone already fix this?
current_geo = query_current_geo("12345")

if current_geo != diagnosis.expected_geo_if_broken:
    # Already fixed!
    sor.record_proactive_fix({
        "deal_id": "12345",
        "pattern_detected": "geo_conflict",
        "already_resolved": True,
        "resolution_time": "before_alert",
        "learning": "Issue was real (validated), but human beat us to it"
    })
    
    # Don't send alert (already fixed)
    # But count as validation of diagnostic accuracy
```

#### **Case 2: Multiple Recommendations** (Ambiguity)

```python
# Deal 12345 has 2 active recommendations:
#   Rec 1 (6h ago): "Remove supply geo"
#   Rec 2 (2h ago): "Increase budget"

# Change detected: geo_targeting removed

# Attribution logic:
# - Matches Rec 1 (exact match)
# - Doesn't match Rec 2
# - Rec 1 is older but more relevant
# → Attribute to Rec 1 with 0.95 confidence
```

#### **Case 3: Divergent Fix**

```python
# Recommended: "Remove supply-side geo"
# Detected: deal_status changed to "paused"

# Attribution:
attribution = {
    "action": "pause_deal",
    "confidence": 0.85,  # Timing suggests related
    "attribution": "DIVERGENCE",
    "divergence": True,
    "note": "Human chose to pause deal instead of fix geo"
}

# Outcome measurement still happens:
if outcome == "SUCCESS":
    # Learn: "For this pattern, pausing works too"
    sor.record_alternative_solution(
        pattern="geo_conflict",
        alternative="pause_deal",
        success_rate="Track separately"
    )
```

---

## Outcome Verification Automation

### Daily Verification Job

```python
class OutcomeValidator:
    """
    Automatically measures if actions worked
    """
    
    def run_daily_verification(self):
        """
        Called every day - verifies actions from 24-48h ago
        """
        # Get actions needing verification (24h old, not yet verified)
        pending = self.sor.get_pending_verifications(
            hours_ago_min=24,
            hours_ago_max=48
        )
        
        print(f"🔍 Verifying {len(pending)} actions from 24-48h ago...")
        
        for action in pending:
            outcome = self.verify_single_action(action)
            self.sor.update_outcome(action.alert_id, outcome)
            self.update_pattern_statistics(action.pattern_type, outcome)
    
    def verify_single_action(self, action):
        """
        Measure outcome for specific action
        """
        # Get current metrics
        current_report = self.execute_tool(
            "generate_debug_report",
            {"deal_id": action.deal_id, "days": 2}
        )
        
        # Pattern-specific outcome calculation
        if action.pattern_type == "geo_conflict":
            return self._verify_geo_conflict_outcome(action, current_report)
        
        elif action.pattern_type == "creative_misclassification":
            return self._verify_creative_outcome(action, current_report)
        
        elif action.pattern_type == "allowlist_restriction":
            return self._verify_allowlist_outcome(action, current_report)
    
    def _verify_geo_conflict_outcome(self, action, current_report):
        """
        Verify geo conflict fix worked
        """
        pre = action.pre_action_metrics
        post = current_report['funnel_metrics']
        
        # Calculate recovery
        baseline = 0.30  # Target sell-through rate
        pre_gap = baseline - pre['sell_through_rate']
        post_gap = baseline - post['sell_through_rate']
        
        recovery_rate = (pre_gap - post_gap) / pre_gap if pre_gap > 0 else 0
        
        # Classify outcome
        if recovery_rate >= 0.60:  # Met minimum expectation
            if recovery_rate >= 0.80:  # Exceeded expectations
                outcome = "SUCCESS"
                outcome_score = 1.0
            else:
                outcome = "SUCCESS"
                outcome_score = recovery_rate / 0.80  # Normalize to 0.75-1.0
        elif recovery_rate >= 0.30:  # Partial improvement
            outcome = "PARTIAL"
            outcome_score = 0.5
        else:  # Didn't work
            outcome = "FAILED"
            outcome_score = 0.0
        
        return {
            "post_action_metrics": post,
            "success_metric": f"Delivery recovered {recovery_rate*100:.0f}% (expected 60-80%)",
            "outcome": outcome,
            "outcome_score": outcome_score,
            "verification_timestamp": datetime.now(),
            "notes": self._generate_outcome_notes(recovery_rate, action)
        }
```

---

## Confidence Refinement Engine

### Dynamic Confidence Calculation

```python
class ConfidenceEngine:
    """
    Adjusts agent confidence based on SoR historical data
    """
    
    def calculate_dynamic_confidence(self, pattern_type, context):
        """
        Confidence informed by actual outcomes, not just rules
        """
        # Start with base diagnostic confidence
        base_confidence = self.diagnostic_rules[pattern_type]['base_confidence']
        
        # Get historical performance from SoR
        history = self.sor.get_pattern_history(
            pattern_type=pattern_type,
            client_id=context.client_id,
            deal_type=context.deal_type,
            min_age_hours=24,  # Only use verified actions
            lookback_days=90
        )
        
        if history.sample_size < 5:
            # Insufficient data - use base confidence
            return {
                "confidence": base_confidence,
                "rationale": "Base confidence (insufficient history)",
                "sample_size": history.sample_size
            }
        
        # Calculate success-based adjustment
        success_rate = history.successful / history.total
        
        if success_rate >= 0.95:
            adjustment = +0.20
        elif success_rate >= 0.90:
            adjustment = +0.15
        elif success_rate >= 0.80:
            adjustment = +0.10
        elif success_rate >= 0.70:
            adjustment = +0.05
        elif success_rate >= 0.60:
            adjustment = 0.00
        else:
            adjustment = -0.10  # Pattern not working well
        
        # Apply bounds
        adjusted_confidence = min(0.98, max(0.50, base_confidence + adjustment))
        
        return {
            "confidence": adjusted_confidence,
            "rationale": f"Based on {history.sample_size} actions ({success_rate*100:.0f}% success)",
            "sample_size": history.sample_size,
            "success_rate": success_rate,
            "adjustment": adjustment
        }
```

---

### Client-Specific Learning

```python
def get_client_specific_success_rate(pattern_type, client_id):
    """
    Some patterns work better for certain clients
    """
    # Global success rate
    global_history = sor.get_pattern_history(pattern_type)
    global_rate = global_history.success_rate
    
    # Client-specific success rate
    client_history = sor.get_pattern_history(pattern_type, client_id=client_id)
    
    if client_history.sample_size >= 5:
        client_rate = client_history.success_rate
        
        if client_rate >= global_rate + 0.10:
            # This pattern works especially well for this client
            return client_rate, "ABOVE_AVERAGE", "Lower thresholds appropriate"
        
        elif client_rate <= global_rate - 0.10:
            # This pattern struggles with this client
            return client_rate, "BELOW_AVERAGE", "Higher scrutiny needed"
        
        else:
            return client_rate, "AVERAGE", "Use standard thresholds"
    
    else:
        # Insufficient client-specific data, use global
        return global_rate, "INSUFFICIENT_DATA", "Using global success rate"
```

**Example policy adjustment**:
```python
# Client A: Geo fixes work great (19/20 successful = 95%)
if client_id == "client_a" and pattern == "geo_conflict":
    autonomous_threshold = 0.80  # Lower bar (pattern proven for this client)

# Client B: Geo fixes unreliable (4/6 successful = 67%)
if client_id == "client_b" and pattern == "geo_conflict":
    autonomous_threshold = 0.95  # Higher bar (need more confidence)
```

---

## Divergence Tracking

### Learning from Alternative Actions

**Scenario**: Guardian recommends one thing, human does another

```python
# SoR captures divergence
{
  "alert_id": "alert_xyz789",
  "recommended_action": "remove_supply_side_geo",
  "human_action_taken": "pause_deal",
  "divergence": True,
  "divergence_type": "ALTERNATIVE_ACTION",
  
  # Measure outcome of alternative
  "outcome": "SUCCESS",
  "success_metric": "Deal paused, budget reallocated, campaign CPA improved 35%",
  
  # Learning opportunity
  "learning_note": "Human chose pause over geo fix - verify if better approach"
}
```

**Divergence analysis**:
```python
def analyze_divergence_patterns():
    """
    Learn from cases where humans override recommendations
    """
    divergent_actions = sor.query(divergence=True, lookback_days=90)
    
    for action in divergent_actions:
        if action.outcome == "SUCCESS":
            # Human's alternative worked - learn from it
            pattern = f"{action.pattern_type}_alternative"
            
            # Track: "For pattern X, humans often choose Y instead of Z"
            sor.record_pattern(
                pattern=pattern,
                trigger=action.pattern_type,
                alternative_action=action.human_action_taken,
                success_rate="Calculate from similar divergences"
            )
    
    # Update recommendations
    if divergence_success_rate > primary_recommendation_success_rate:
        update_diagnostic_rule(
            pattern=action.pattern_type,
            new_primary_recommendation=alternative_action
        )
```

---

## Outcome Classification

### Success Criteria by Pattern

#### **Geo Targeting Conflicts**

```python
def classify_geo_conflict_outcome(pre_metrics, post_metrics):
    """
    Success = 60-80% delivery recovery
    """
    recovery = calculate_delivery_recovery(pre_metrics, post_metrics)
    
    if recovery >= 0.80:
        return "SUCCESS", 1.0, "Exceeded expectations"
    elif recovery >= 0.60:
        return "SUCCESS", 0.85, "Met expectations"
    elif recovery >= 0.40:
        return "PARTIAL", 0.50, "Some improvement"
    elif recovery >= 0.20:
        return "PARTIAL", 0.25, "Minimal improvement"
    else:
        return "FAILED", 0.0, "No significant improvement"
```

#### **Creative Issues**

```python
def classify_creative_outcome(pre_metrics, post_metrics, days_elapsed):
    """
    Success = Issue resolved + delivery restored
    """
    if post_metrics['creative_rejection_rate'] == 0:
        # Creative no longer being rejected
        if post_metrics['impressions'] >= pre_metrics['impressions'] * 0.80:
            return "SUCCESS", 1.0, "Creative approved, delivery restored"
        else:
            return "PARTIAL", 0.60, "Creative approved, delivery recovering"
    
    elif days_elapsed >= 3:
        # Still not resolved after expected resolution period
        return "FAILED", 0.0, "Creative still blocked after 3 days"
    
    else:
        # Still pending (within expected 1-3 day resolution)
        return "PENDING", None, "Awaiting creative review completion"
```

#### **Budget Optimization**

```python
def classify_budget_optimization_outcome(pre_metrics, post_metrics):
    """
    Success = CPA improved toward target
    """
    pre_cpa = pre_metrics['cpa']
    post_cpa = post_metrics['cpa']
    target_cpa = pre_metrics['target_cpa']
    
    cpa_improvement = (pre_cpa - post_cpa) / pre_cpa
    gap_closed = (pre_cpa - post_cpa) / (pre_cpa - target_cpa)
    
    if post_cpa <= target_cpa:
        return "SUCCESS", 1.0, f"Reached target CPA (${post_cpa:.2f})"
    elif gap_closed >= 0.60:
        return "SUCCESS", 0.90, f"CPA improved {cpa_improvement*100:.0f}% toward target"
    elif gap_closed >= 0.30:
        return "PARTIAL", 0.60, f"Partial CPA improvement ({cpa_improvement*100:.0f}%)"
    else:
        return "FAILED", 0.0, "No significant CPA improvement"
```

---

## Action Categories by Level

### Campaign-Level Actions
```python
{
  "action_level": "CAMPAIGN",
  "patterns": [
    "campaign_disabled",      # Campaign statusId != 1
    "campaign_budget_exhausted",
    "campaign_dates_invalid",
    "line_items_misconfigured"
  ],
  "actions": [
    "enable_campaign",
    "disable_campaign",
    "extend_campaign_dates",
    "increase_campaign_budget",
    "pause_all_line_items"
  ]
}
```

### Line Item-Level Actions
```python
{
  "action_level": "LINE_ITEM",
  "patterns": [
    "line_item_budget_exhausted",
    "curation_package_missing",
    "targeting_too_restrictive"
  ],
  "actions": [
    "adjust_line_item_budget",
    "change_curation_package_assignment",
    "modify_targeting_filters",
    "adjust_bid_multipliers"
  ]
}
```

### Supply Deal-Level Actions
```python
{
  "action_level": "SUPPLY_DEAL",
  "supply_deal_type": "PMP",  # PMP or OPEN_EXCHANGE
  "patterns": [
    "geo_conflict",              # PMP only
    "creative_misclassification", # PMP only
    "allowlist_restriction",      # PMP only
    "filter_list_misconfigured"   # Open Exchange only
  ],
  "actions": [
    "remove_supply_side_geo",     # PMP
    "fix_creative_audit_issue",   # PMP
    "adjust_qps_limits",          # PMP
    "update_filter_lists"         # Open Exchange
  ]
}
```

---

## Pattern Success Rate Dashboard

### Real-Time Learning Status

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PATTERN LEARNING STATUS (Last 90 Days)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CAMPAIGN_DISABLED (Campaign-level):
  Total Actions: 5 ✅
  Success Rate: 100% (5/5) ✅
  Avg Time to Fix: 2 hours
  Confidence Adjustment: +0.25 (high leverage fix)
  Stage Readiness: READY FOR STAGE 4
  
  Impact: Avg 45 Supply Deal relationships restored per campaign fix

GEO_CONFLICT (Supply Deal-level, PMP only):
  Total Actions: 12 ✅ (min 10 for autonomous)
  Success Rate: 100% (12/12) ✅ (target: ≥90%)
  Avg Recovery: 71% (range: 65-78%)
  Avg Time to Fix: Immediate
  Confidence Adjustment: +0.20
  Stage Readiness: READY FOR STAGE 4 (Autonomous)
  
  Client Breakdown:
  • Client A: 8/8 (100%) → Autonomous enabled
  • Client B: 4/4 (100%) → Autonomous enabled

CREATIVE_MISCLASSIFICATION:
  Total Actions: 6 ⚠️ (min 10 for autonomous)
  Success Rate: 100% (6/6) ✅
  Avg Resolution: 2.3 days
  Confidence Adjustment: +0.15
  Stage Readiness: STAGE 2 (need 4 more actions)

ALLOWLIST_RESTRICTION:
  Total Actions: 5 ⚠️ (min 8 for approval)
  Success Rate: 80% (4/5) ✅
  Avg Improvement: +32% delivery
  Confidence Adjustment: +0.10
  Stage Readiness: STAGE 2 (need 3 more actions)
  
  Note: 1 failed action (Client C - need investigation)

BID_PRICE_TOO_LOW:
  Total Actions: 18 ✅
  Success Rate: 89% (16/18) ⚠️ (target: ≥90%)
  Avg CPA Improvement: 28%
  Confidence Adjustment: +0.12
  Stage Readiness: STAGE 3 (approval mode)
  
  Recent Trend: Last 5 actions all successful → Consider Stage 4

OVER_SEGMENTATION:
  Total Actions: 2 ❌ (min 8 for approval)
  Success Rate: 100% (2/2)
  Confidence Adjustment: +0.05 (low sample)
  Stage Readiness: STAGE 2 (need 6 more actions)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OVERALL LEARNING PROGRESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Actions Logged: 43
Verified Outcomes: 43 (100%)
Overall Success Rate: 91% (39/43)
Patterns Ready for Autonomous: 1 (Geo Conflicts)
Patterns in Approval Mode: 1 (Bid Price Adjustments)
Patterns Building Data: 3
```

---

## Integration with Policy Engine

### SoR-Informed Policy Boundaries

```python
class PolicyEngine:
    """
    Policies informed by actual success rates from SoR
    """
    
    def check_autonomous_eligibility(self, pattern_type, context):
        """
        Can this action be autonomous?
        """
        # Get pattern success rate
        success_data = self.sor.get_success_rate(
            pattern_type=pattern_type,
            client_id=context.client_id
        )
        
        # Autonomous criteria (ALL must be true)
        criteria = {
            "sample_size": success_data.total_actions >= 10,
            "success_rate": success_data.success_rate >= 0.90,
            "budget_limit": context.budget < 50000,
            "client_validated": success_data.client_actions >= 5,
            "low_variance": success_data.std_deviation < 0.15
        }
        
        if all(criteria.values()):
            return {
                "autonomous": True,
                "rationale": f"{success_data.success_rate*100:.0f}% success over {success_data.total_actions} actions",
                "stage": "STAGE_4"
            }
        
        elif success_data.total_actions >= 5 and success_data.success_rate >= 0.70:
            return {
                "autonomous": False,
                "requires_approval": True,
                "rationale": f"Proven pattern ({success_data.success_rate*100:.0f}% success) but needs approval",
                "stage": "STAGE_3"
            }
        
        else:
            return {
                "autonomous": False,
                "requires_approval": False,
                "recommendation_only": True,
                "rationale": "Insufficient validation - recommendation mode only",
                "stage": "STAGE_2"
            }
```

---

## Failure Analysis & Adaptation

### When Actions Fail

```python
def analyze_failed_actions():
    """
    Learn from failures to improve diagnostic rules
    """
    failed = sor.query(outcome="FAILED", lookback_days=90)
    
    for failure in failed:
        # Investigate why it failed
        failure_analysis = {
            "alert_id": failure.alert_id,
            "pattern": failure.pattern_type,
            "recommended_action": failure.recommended_action,
            "why_failed": analyze_failure_root_cause(failure)
        }
        
        # Common failure patterns
        if failure.pattern == "geo_conflict":
            # Check if maybe it wasn't actually a geo issue
            actual_issue = re_diagnose_with_post_data(failure)
            
            if actual_issue != "geo_conflict":
                # Misdiagnosis - update diagnostic rules
                update_diagnostic_rule(
                    pattern="geo_conflict",
                    add_exclusion_criteria=actual_issue.symptoms
                )
        
        # Update confidence negatively
        adjust_confidence(failure.pattern_type, -0.05)
```

---

## Stage Progression Framework

### Automatic Stage Advancement

```python
class StageProgressionEngine:
    """
    Automatically advances patterns through stages based on validated performance
    """
    
    def evaluate_stage_progression(self):
        """
        Daily check - can any patterns advance to next stage?
        """
        for pattern in self.patterns:
            current_stage = self.get_current_stage(pattern)
            history = self.sor.get_pattern_history(pattern)
            
            if current_stage == "STAGE_2":
                if self.ready_for_stage_3(history):
                    self.advance_to_stage_3(pattern, history)
            
            elif current_stage == "STAGE_3":
                if self.ready_for_stage_4(history):
                    self.advance_to_stage_4(pattern, history)
    
    def ready_for_stage_3(self, history):
        """Can pattern move to approval mode?"""
        return (
            history.sample_size >= 10 and
            history.success_rate >= 0.70 and
            history.outcome_variance < 0.20
        )
    
    def ready_for_stage_4(self, history):
        """Can pattern move to autonomous mode?"""
        total_actions = history.stage_2_actions + history.stage_3_actions
        
        return (
            total_actions >= 20 and
            history.success_rate >= 0.90 and
            history.stage_3_approval_rate >= 0.80 and
            history.outcome_variance < 0.15
        )
    
    def advance_to_stage_3(self, pattern, history):
        """Enable approval-based mode"""
        self.config.set_stage(pattern, "STAGE_3")
        
        self.slack.notify(
            f"📈 Pattern Advancement: {pattern}\n"
            f"Stage 2 → Stage 3 (Approval Mode)\n\n"
            f"Validation: {history.sample_size} actions, {history.success_rate*100:.0f}% success\n"
            f"Guardian will now request approval to execute {pattern} fixes."
        )
    
    def advance_to_stage_4(self, pattern, history):
        """Enable autonomous mode"""
        self.config.set_stage(pattern, "STAGE_4")
        
        self.slack.notify(
            f"🚀 Pattern Advancement: {pattern}\n"
            f"Stage 3 → Stage 4 (Autonomous Mode)\n\n"
            f"Validation: {total_actions} actions, {history.success_rate*100:.0f}% success\n"
            f"Approval rate: {history.stage_3_approval_rate*100:.0f}%\n"
            f"Guardian will now execute {pattern} fixes autonomously (within policy limits)."
        )
```

---

### Automatic Stage Demotion (Circuit Breaker)

```python
def evaluate_stage_demotion(self):
    """
    Safety mechanism - demote if performance degrades
    """
    for pattern in self.patterns:
        current_stage = self.get_current_stage(pattern)
        recent_history = self.sor.get_pattern_history(pattern, lookback_days=30)
        
        if current_stage == "STAGE_4":
            # Autonomous mode - strict monitoring
            if recent_history.success_rate < 0.80:
                # Performance degraded - demote to approval
                self.demote_to_stage_3(pattern, recent_history)
                
                self.slack.alert(
                    f"⚠️ Pattern Demotion: {pattern}\n"
                    f"Stage 4 → Stage 3 (Approval Required)\n\n"
                    f"Reason: Success rate dropped to {recent_history.success_rate*100:.0f}%\n"
                    f"Recent actions: {recent_history.recent_actions}\n"
                    f"Guardian will now request approval for {pattern} fixes."
                )
        
        elif current_stage == "STAGE_3":
            # Approval mode - moderate monitoring
            if recent_history.success_rate < 0.60:
                # Pattern not working - back to logging
                self.demote_to_stage_2(pattern, recent_history)
                
                self.slack.alert(
                    f"🚨 Pattern Demotion: {pattern}\n"
                    f"Stage 3 → Stage 2 (Logging Mode)\n\n"
                    f"Reason: Success rate dropped to {recent_history.success_rate*100:.0f}%\n"
                    f"Guardian will recommend fixes but humans must execute and log."
                )
```

---

## Phase Integration

### Phase 1: Build SoR Infrastructure

**Foundation**:
- Create SoR database schema
- Implement action logging interface
- Build outcome verification automation
- **Deliverable**: SoR operational, ready for Stage 2

**All Phase 1 in Stage 1**:
- Guardian alerts only
- Humans fix manually
- No logging yet (gathering requirements)
- Focus: Prove Guardian finds real issues

---

### Phase 2: Progressive Autonomy

**Stage 2: Recommendation & Logging**
- Guardian recommends specific fixes with "after you fix, click here" buttons
- Humans execute and log via Slack reactions
- Guardian verifies outcomes 24h later
- **Goal**: 20-30 validated actions per major pattern

**Stage 3: Approval-Based**
- Patterns with ≥10 actions + ≥70% success move here
- Guardian requests approval showing historical data
- Agents execute approved actions
- **Goal**: Build trust, validate autonomous readiness

**Stage 4: Autonomous**
- Patterns with ≥20 actions + ≥90% success move here
- Guardian executes autonomously within policy
- Humans receive FYI notifications only
- **Goal**: 80%+ autonomous action rate

---

## Success Metrics by Stage

| Metric | Stage 1 | Stage 2 | Stage 3 | Stage 4 |
|--------|---------|---------|---------|---------|
| **Human involvement** | 100% fix execution | 100% execution + logging | Approval only | Oversight only |
| **Action logging rate** | N/A | 80%+ | 100% | 100% |
| **Outcome verification** | Manual | Automated (24h) | Automated (24h) | Automated (24h) |
| **Agent learning** | Pattern detection | Maximum learning | Confidence refinement | Continuous improvement |
| **Time to action** | Hours/days | Hours/days | Minutes | Seconds |

---

## The Trust Progression

### How Trust is Built

**Stage 1**:
- "Guardian finds real issues" (diagnostic accuracy proven)

**Stage 2**:
- "Guardian's recommendations work" (8/8 geo fixes successful)

**Stage 3**:
- "I always approve Guardian's requests" (18/18 approvals granted)

**Stage 4**:
- "Guardian handles routine fixes autonomously" (trust earned through data)

**Result**: Autonomous action **earned** through validated performance, not granted on faith.

---

## Related Documentation

- [Progressive Autonomy](PROGRESSIVE_AUTONOMY.md)
- [Four-Layer Architecture](FOUR_LAYER_ARCHITECTURE.md)
- [Agentic Vision Overview](README.md)

