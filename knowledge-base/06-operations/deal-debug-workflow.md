# Deal Debug Workflow

## Overview

Automated process for identifying and resolving underperforming deals. Reduces diagnosis time from 5-7 minutes to <1 minute while expanding coverage from 3 deals per session (industry standard) to continuous monitoring of all active deals.

**Efficiency Gains**: 85% time reduction, 100x scale increase, proactive detection before failure.

---

## Deal Selection Criteria

### Low Sell-Through Pattern Detection

Deals are automatically flagged when they exhibit the following pattern:

#### Primary Criteria
- **Bid Requests** ≥ 1,000/day (sufficient data volume)
- **Bid Responses** > 0 (bidder actively participating)
- **Impressions** > 0 (winning some auctions)
- **Sell-Through Rate** < 30% (underperforming threshold)

#### Secondary Filters
- **Recency**: Last 7 days of data analyzed
- **Data Maturity**: Exclude deals < 24 hours old (insufficient data)
- **Status**: Active deals only (exclude disabled/paused)

#### Priority Scoring

Deals are ranked using weighted scoring:
- **40%**: Sell-through gap (how far below 30% threshold)
- **30%**: Budget impact (spend potential at risk)
- **20%**: Recency trend (sudden drops weighted higher)
- **10%**: Account priority (client tier)

#### Actionability Assessment

Deals must have:
- Identifiable root causes (clear diagnostic patterns)
- Resolvable issues (can fix within 1 week)
- Available resources (no external dependencies blocking fix)

---

## The Five Common Culprits

### Distribution of Root Causes

Based on industry data from leading SSP operators:

| Issue Category | Frequency | Avg Resolution Time |
|----------------|-----------|---------------------|
| Creative Issues | 30% | 1-3 days |
| Double Geo-Targeting | 25% | Immediate (config change) |
| Overly Tight Allowlists | 20% | 1-2 days |
| Over-Segmentation | 15% | Strategic discussion |
| CTV Complexity | 10% | 2-5 days |

---

## Issue 1: Creative Problems (30% of cases)

### Wrong Creative Size/Format

**Symptoms**:
- Bid responses being sent successfully
- Win rate significantly below expected
- Deal requirements specify different dimensions

**Detection**:
- Compare creative dimensions vs. deal specifications
- Check creative format support by SSP
- Validate file size within limits

**Resolution**:
- Upload additional creative sizes matching deal requirements
- Adjust deal specifications if dimensions were incorrect
- Test creative rendering on target platforms

**Expected Impact**: Win rate improvement of 40-60%

---

### Creative Audit Misclassification

**Symptoms**:
- Deal suddenly stops delivering after initial success
- Significant drop in impressions (>80%) overnight
- Creative recently changed or updated

**Detection**:
- Check creative rejection reasons in BidSwitch
- Review audit status changes in timeline
- Pattern: "Approved" → "Rejected" within days

**Real-World Example**:
> "Last week, a face cream ad was flagged as a dating app (buyside DSP: The Trade Desk). Since many publishers block dating, the deal stalled. After Xandr manually reviewed 138 creatives, the deal jumped back to life."

**Resolution**:
1. Generate escalation template for DSP contact
2. Request manual creative review
3. Provide context (e.g., "Beauty/Health category, not Dating")
4. Track resolution (typically 138+ creatives reviewed)

**Timeline**: 1-3 days for manual audit review and correction

**Expected Impact**: Full delivery restoration (100% recovery)

---

### Audit Status Stuck

**Symptoms**:
- Creatives pending approval for extended periods
- No delivery despite deal being active
- Submission timestamp > 48 hours ago

**Detection**:
- Query creative approval timestamp vs. submission date
- Check for approval workflow blockages
- Identify bottlenecks in review process

**Resolution**:
- Follow up with approval team
- Escalate if > 48 hours pending
- Request priority review for high-value deals

**Expected Impact**: Approval within 24 hours of escalation

---

## Issue 2: Double Geo-Targeting (25% of cases)

**Root Cause**: Buyer and seller both apply geo-targeting using different geo-resolution libraries (BidSwitch vs. DSP), causing mismatches.

**Symptoms**: CTV deals particularly affected (50-80% delivery drop), high bid requests but low matches.

**Detection**: Check both deal settings (BidSwitch groups: 8643=EU, 9000=BR) and line item filters for geo restrictions. If BOTH present, flag as high-confidence conflict (85%+ confidence, 95% for CTV).

**Resolution**: Remove supply-side geo-targeting (open to national), let buyer handle exclusively. Document in deal terms upfront.

**Expected Impact**: 60-80% delivery restoration (immediate).

---

## Issue 3: Overly Tight Allowlists (20% of cases)

**Root Cause**: Buyer restricts inventory too narrowly (e.g., 15 sources out of 250 available = 6% restriction ratio).

**Symptoms**: Deal configured but extremely low bid request volume.

**Detection**: Calculate restriction ratio (allowlist_size / available_inventory). Flag if <10% (high restriction).

**Resolution**: Use collaborative filtering to recommend inventory expansion. Find similar buyers, identify their successful sources, rank by performance potential.

**Expected Impact**: 20-40% impression volume increase.

---

## Issue 4: Over-Segmentation (15% of cases)

**Root Cause**: Multiple audience segments + contextual + geo + device + time targeting = intersection too narrow (targeting strategy issue, not technical).

**Symptoms**: All systems working, deal active, but very low match rate despite high bid requests.

**Detection**: Count active targeting layers. 4+ layers = high risk. Flag if addressable audience <1% of available inventory.

**Resolution**: Systematic relaxation—remove one layer at a time, test impact. Recommended order: time-of-day → geo → device → contextual → audience.

**Expected Impact**: 30-60% volume increase per layer removed, minimal performance degradation (<5%).

---

## Issue 5: CTV Complexity (10% of cases)

**Common Issues**:
- **Duration mismatches**: 15s creative in 30s slot (rejected)
- **Device taxonomy**: App vs. web, living room vs. mobile confusion
- **Platform compatibility**: Roku/Samsung/Apple TV-specific requirements
- **VAST/VPAID**: Version mismatches (need 2.0, 3.0, 4.0 support)

**Resolution**: Validate creative durations, standardize CTV device categories, maintain platform-specific creative sets, test across all major platforms.

**Expected Impact**: 40-70% delivery improvement after CTV-specific fixes.

---

## 7-Day Debug Report

Generated in <1 minute with 7 sections: Deal Summary, Funnel Metrics (bid requests → responses → impressions), Red Flags, Confidence-Scored Root Causes (90-100%: clear cause, 70-89%: multiple causes, 50-69%: human review, <50%: escalate), Prioritized Actions, JIRA Ticket Draft, Escalation Template.

**Primary KPI**: Sell-Through Rate (impressions / bid_requests), target >30%.

---

## Escalation Process

### Confidence-Based Decision Tree

```
Root Cause Confidence > 80%
  └─> Implement recommended fix
      └─> Monitor for 24-48 hours
          └─> Success? Close ticket
          └─> No improvement? Escalate to Level 2

Root Cause Confidence 50-80%
  └─> Human review of recommended actions
      └─> Approved? Implement fix
      └─> Rejected? Additional analysis
      
Root Cause Confidence < 50%
  └─> Escalate to specialists
      └─> Provide all diagnostic data
      └─> Request expert analysis
```

### Escalation Levels

**Level 1: Automated Fix** (80%+ confidence)
- Configuration changes
- Targeting adjustments
- Budget/pacing modifications
- Timeline: Immediate (within hours)

**Level 2: Human Review** (50-80% confidence)
- Review recommended actions
- Approve implementation
- Monitor results
- Timeline: Same day

**Level 3: Specialist Analysis** (<50% confidence)
- Complex multi-factor issues
- Novel patterns not in playbook
- Requires expert judgment
- Timeline: 1-3 days

**Level 4: External Coordination** (Creative misclassification)
- DSP contact required
- Manual creative review requests
- Platform-level investigations
- Timeline: 3-7 days

---

## Success Metrics

### Efficiency Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Time to diagnosis** | <1 minute | Report generation timestamp |
| **Coverage** | All active deals | Continuous monitoring count |
| **Human time investment** | <0.75 hours/week | Time spent reviewing flagged deals |
| **Issue detection rate** | Proactive (before failure) | % issues caught before client escalation |

### Quality Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Flagging accuracy** | 80%+ | % flagged deals with confirmed issues |
| **Root cause confidence** | 70%+ average | Weighted average across diagnoses |
| **False positive rate** | <10% | % flags not confirmed as issues |
| **Resolution success rate** | 80%+ | % issues resolved within 1 week |

### Business Impact Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Budget recovery** | Track weekly | Spend unlocked by fixing flagged deals |
| **Scale improvement** | 20%+ | Impression volume increase post-fix |
| **Agent adoption** | 90%+ | % debugging sessions using tools |

---

## Related Documentation

- [BidSwitch Deals Management](../08-bidswitch-integration/bidswitch-deals-management.md) - Deal-specific troubleshooting patterns
- [Diagnostic Patterns](../08-bidswitch-integration/diagnostic-patterns.md) - Automated diagnostic rules
- [Campaign Troubleshooting](campaign-troubleshooting.md) - Campaign-level issues

