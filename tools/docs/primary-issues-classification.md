# Primary Issues Classification - Deal & Campaign Analysis Tools

## 🎯 **Current Implementation Status**

### **✅ Implemented Primary Issues (Deal Analysis)**

| Primary Issue | Category | Severity | Spec Alignment | Notes |
|---------------|----------|----------|----------------|-------|
| **`DEAL_INACTIVE`** | BidSwitch Configuration | CRITICAL | ✅ Custom | Deal not found in active deals list |
| **`DEAL_PAUSED`** | BidSwitch Configuration | HIGH | ✅ Custom | Deal paused by DSP or SSP |
| **`DEAL_BROKEN`** | BidSwitch Configuration | CRITICAL | ✅ Custom | Deal marked as broken in BidSwitch |
| **`DEAL_REJECTED`** | BidSwitch Configuration | HIGH | ✅ Custom | Deal rejected by party |
| **`DEAL_STATUS_ISSUE`** | BidSwitch Configuration | MEDIUM | ✅ Custom | Unusual deal status |
| **`BID_BELOW_FLOOR`** | Auction Health | HIGH | ✅ Aligned | Bid prices below floor price threshold |
| **`GEOGRAPHIC_TARGETING_MISMATCH`** | BidSwitch Targeting | CRITICAL | ✅ **NEW ENHANCED** | Regional targeting conflicts (EMEA, APAC, etc.) |
| **`TARGETING_MISMATCH`** | BidSwitch Targeting | HIGH | ✅ Aligned | General targeting configuration issues |
| **`LOW_BID_RATE`** | Auction Health | HIGH | ✅ Aligned | Bid response rate below baseline |
| **`LOW_WIN_RATE`** | Auction Health | MEDIUM | ✅ Aligned | Win rate below expected baseline |
| **`NO_TRAFFIC`** | BidSwitch Configuration | HIGH | ✅ Aligned | Zero bid requests received |
| **`HEALTHY`** | Status | LOW | ✅ Aligned | No issues detected |

### **❌ Missing Primary Issues (From Specification)**

#### **🚨 Data Integrity Rules (CRITICAL - Not Implemented)**
| Missing Issue | Detection Logic | Severity | Priority |
|---------------|----------------|----------|----------|
| **`CONVERSIONS_EXCEED_CLICKS`** | `conversions > clicks` | CRITICAL | **HIGH** |
| **`IMPRESSIONS_EXCEED_BIDS`** | `impressions > bids` | CRITICAL | **HIGH** |
| **`BID_RATE_OVER_100_PERCENT`** | `bid_rate > 1.0` | CRITICAL | **HIGH** |

#### **📊 Auction Health Rules (Partially Implemented)**
| Missing Issue | Detection Logic | Severity | Priority |
|---------------|----------------|----------|----------|
| **`BID_RATE_BELOW_BASELINE`** | `bid_rate < 0.30` | HIGH | **MEDIUM** |
| **`BID_RATE_ABOVE_BASELINE`** | `bid_rate > 0.80` | MEDIUM | **MEDIUM** |
| **`WIN_RATE_DEVIATION`** | Significant deviation from baseline | MEDIUM | **MEDIUM** |
| **`BID_ECPM_EXCEEDS_WIN_ECPM`** | `bid_ecpm > win_ecpm` | HIGH | **MEDIUM** |
| **`WIN_ECPM_EXCEEDS_BID_ECPM`** | `win_ecpm > bid_ecpm` | MEDIUM | **LOW** |

#### **🎯 Delivery Quality Rules (Campaign-Level - Not Implemented)**
| Missing Issue | Detection Logic | Severity | Priority |
|---------------|----------------|----------|----------|
| **`CTR_BELOW_DISPLAY_BASELINE`** | `ctr < 0.001` for display | MEDIUM | **MEDIUM** |
| **`CTR_BELOW_VIDEO_BASELINE`** | `ctr < 0.005` for video | MEDIUM | **MEDIUM** |
| **`VIEWABILITY_BELOW_THRESHOLD`** | `viewability < 0.50` | HIGH | **MEDIUM** |
| **`VCR_BELOW_THRESHOLD`** | `video_completion_rate < 0.70` | MEDIUM | **LOW** |

#### **🔄 Combination Pattern Rules (Advanced - Not Implemented)**
| Missing Issue | Detection Logic | Severity | Priority |
|---------------|----------------|----------|----------|
| **`HIGH_BID_RATE_LOW_WIN_RATE`** | `bid_rate > 0.8 AND win_rate < 0.1` | HIGH | **HIGH** |
| **`HIGH_WIN_RATE_LOW_IMPRESSIONS`** | `win_rate > 0.8 AND impressions < threshold` | MEDIUM | **MEDIUM** |
| **`NORMAL_IMPRESSIONS_LOW_CTR`** | `impressions >= baseline AND ctr < baseline` | MEDIUM | **MEDIUM** |
| **`CTR_NORMAL_CONVERSION_RATE_LOW`** | `ctr >= baseline AND conversion_rate < baseline` | HIGH | **MEDIUM** |
| **`SPEND_UP_IMPRESSIONS_DOWN`** | `spend_change > 0.2 AND impression_change < -0.1` | HIGH | **MEDIUM** |
| **`LOW_CTR_HIGH_CPC`** | `ctr < baseline AND cpc > baseline * 1.3` | MEDIUM | **LOW** |

#### **🔍 BidSwitch-Specific Rules (Partially Implemented)**
| Missing Issue | Detection Logic | Severity | Priority |
|---------------|----------------|----------|----------|
| **`HIGH_SMARTSWITCH_FILTERING`** | `smartswitch_filter_rate > 0.60` | HIGH | **HIGH** |
| **`EXTREME_SMARTSWITCH_FILTERING`** | `smartswitch_filter_rate > 0.70` | CRITICAL | **HIGH** |
| **`HIGH_INVALID_REQUESTS`** | `invalid_requests / total > 0.20` | HIGH | **MEDIUM** |
| **`HIGH_GEO_TARGETING_FAILURE`** | `geo_targeting_failure_rate > 0.50` | HIGH | **MEDIUM** |
| **`HIGH_TIMEOUT_RATE`** | `timeout_rate > 0.10` | HIGH | **MEDIUM** |

---

## 🎯 **Recommended Implementation Plan**

### **Phase 1: Critical Data Integrity (Week 1)**
**Priority: CRITICAL** - Implement immediately for both deal and campaign analysis

```python
# Add to enhanced_diagnostics.py
CRITICAL_ISSUES = [
    "CONVERSIONS_EXCEED_CLICKS",    # Data integrity violation
    "IMPRESSIONS_EXCEED_BIDS",      # Impossible data combination  
    "BID_RATE_OVER_100_PERCENT",    # Rate calculation error
    "HIGH_BID_RATE_LOW_WIN_RATE"    # Bidding strategy issue
]
```

### **Phase 2: BidSwitch Enhancement (Week 2)**  
**Priority: HIGH** - Extend BidSwitch-specific diagnostics

```python
# Add SmartSwitch analysis
BIDSWITCH_ISSUES = [
    "HIGH_SMARTSWITCH_FILTERING",      # 60%+ filtering
    "EXTREME_SMARTSWITCH_FILTERING",   # 70%+ filtering (critical)
    "HIGH_INVALID_REQUESTS",           # Protocol compliance
    "HIGH_TIMEOUT_RATE"                # Performance issues
]
```

### **Phase 4: Enhanced Campaign Diagnostics (Week 3)**
**Priority: MEDIUM** - Campaign-level health and structural analysis

```python
# Campaign-level diagnostic categories
CAMPAIGN_ISSUES = [
    "CAMPAIGN_DISABLED",              # Campaign status issues
    "CAMPAIGN_DATES_INVALID",         # Date configuration problems
    "NO_CURATION_PACKAGES",           # Structural configuration issues
    "CAMPAIGN_BUDGET_EXHAUSTED"       # Budget-related problems
]
```

---

## 🔄 **Tool Extension Strategy**

### **Deal Analysis Tool** (Current)
- ✅ **Scope**: Single deal diagnostic
- ✅ **Data Sources**: BidSwitch APIs (Sync + Performance)
- ✅ **Focus**: Configuration, targeting, auction health

### **Campaign Analysis Tool** (Campaign-Level Focus)
- ✅ **Scope**: Campaign health + deal identification only
- ✅ **Data Sources**: PostgreSQL + Redshift (campaign data)
- ✅ **Focus**: Campaign status, dates, structure, configuration issues
- ✅ **Output**: Agent guidance for deal debugging decisions

### **Deal Debugging Tool** (Individual Deal Focus)
- ✅ **Scope**: Single PMP Supply Deal diagnostics
- ✅ **Data Sources**: BidSwitch APIs + PostgreSQL (deal data)
- ✅ **Focus**: Deal performance, configuration, targeting issues
- ✅ **Integration**: Called by agents for deals flagged by campaign analysis

### **Tool Architecture Overview**
```python
# Current Architecture (Post-Separation)
class CampaignAnalysisTool:
    """Campaign-level health + deal identification"""
    def run_analysis(self, campaign_id: str) -> CampaignReport:
        # Campaign diagnostics + deal discovery only

class DealDebuggingTool:
    """Individual deal diagnostics"""
    def run_debugging(self, deal_id: str) -> DealReport:
        # Individual PMP deal analysis with BidSwitch API

class GuardianAgent:
    """Orchestrates the workflow"""
    def monitor_campaigns(self):
        # Use CampaignAnalysisTool to identify issues
        # Decide which deals need debugging
        # Call DealDebuggingTool for selected deals
```

---

## 📋 **Consistency Checklist**

### **✅ Aligned with Specification**
- [x] Severity levels: CRITICAL, HIGH, MEDIUM, LOW
- [x] Category classification system
- [x] BidSwitch-specific rule integration
- [x] Industry baseline framework
- [x] Agent workflow patterns

### **🔄 Extensions Needed**  
- [ ] Data integrity validation rules
- [ ] SmartSwitch filtering analysis  
- [ ] Campaign-level delivery quality rules
- [ ] Combination pattern detection
- [ ] Cross-deal systemic analysis

### **🎯 Next Steps**
1. **Implement Phase 1 critical rules** (data integrity)
2. **Add SmartSwitch filtering analysis** (BidSwitch enhancement)
3. **Extend to campaign-level diagnostics** (multi-deal analysis)
4. **Integrate with unified reporting framework**

---

**This ensures our diagnostic engine is fully aligned with the AI Agent specification and ready for campaign analysis extension!** 🚀
