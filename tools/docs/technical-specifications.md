# Technical Specifications - Analysis Tools
*Consolidated technical documentation for campaign and deal analysis tools*

## 🎯 **Overview**

This document provides the complete technical specification for diagnostic rules, issue classifications, and AI agent workflows used by the Bedrock Platform Intelligence analysis tools.

**Scope**: All diagnostic rules, baselines, and decision trees for tool implementation  
**Audience**: Developers, AI agents, technical implementers  
**Related**: Knowledge base remains separate and RAG-optimized for agent consumption

---

## 📋 **Document Structure**

### **Primary Categories**
1. **[Scope and Object Model](#scope-and-object-model)** - Supply Deal vs. External Deal distinction and entity hierarchy
2. **[Primary Issue Classifications](#primary-issue-classifications)** - Current implementation status and mappings
3. **[Diagnostic Rules Engine](#diagnostic-rules-engine)** - Structured rules for automated diagnosis
4. **[BidSwitch Integration Specifications](#bidswitch-integration-specifications)** - API integration and diagnostic patterns
5. **[Implementation Guidelines](#implementation-guidelines)** - Code integration and testing procedures

---

## 🏗️ **Scope and Object Model**

### **Bedrock Platform Entity Hierarchy**

Understanding the relationships is critical for effective troubleshooting:

**Supply Deals** (Bedrock Platform entities):
- Created in Bedrock UI
- Configure EITHER Private Deals (PMP) OR Open Exchange traffic
- Have: name, dates, creative type, floor CPM, filter lists
- Bundle into curation packages

**External Deals** (SSP marketplace deals):
- Created in BidSwitch, Index Exchange, Google Authorized Buyers, etc.
- Have: deal IDs, performance metrics, bid requests, impressions
- Associated with PMP-configured Supply Deals via sspDealId

**Relationship** (Correct Entity Hierarchy):
```
Campaign (Bedrock)
└─→ Line Items
    └─→ Curation Package
        └─→ Supply Deal (Bedrock)
            └─→ External Deal (SSP via sspDealId)
```

**Tools Query BOTH**:
- Supply Deal configuration (Bedrock database)
- External Deal performance (BidSwitch API) - when PMP type

### **Diagnostic Scope**

**Campaign Analysis Tools**:
- Work with ALL Supply Deals (Bedrock entities)
- Provide hierarchical context (campaign → line items → deals)
- Early exit intelligence (campaign disabled = skip deal analysis)

**Deal Debugging Tools**:
- Require BidSwitch integration (PMP Supply Deals only)
- Analyze external Deal performance via BidSwitch API
- Focus on deal-specific issues (geo conflicts, creative problems, etc.)

**Open Exchange Supply Deals**:
- No BidSwitch API integration
- Analyzed via filter list effectiveness and internal metrics
- Different diagnostic approach than PMP deals

### **Hierarchical Monitoring Architecture**

**Three-Level Analysis Framework**:
1. **Campaign Level**: Health status, configuration, structural issues
2. **Line Item Level**: Targeting, budget, delivery metrics
3. **Supply Deal Level**: Individual deal performance and diagnostics

**Agent Orchestration Workflow**:
```
Guardian Agent
├── Campaign Analysis Tool → Campaign health + deal identification
├── Agent Decision Logic → Which deals need debugging?
└── Deal Debugging Tool → Individual deal diagnostics
```

**Separation of Concerns**:
- **Campaign Analysis Tool**: Campaign-level issues, provides deal list for agent
- **Deal Debugging Tool**: Individual PMP deal diagnostics, called by agent for selected deals
- **Agent**: Orchestrates workflow, makes decisions about which deals to debug

---

## 🏷️ **Primary Issue Classifications**

### **✅ Currently Implemented Issues (Deal Analysis)**

| Primary Issue | Category | Severity | Implementation | Notes |
|---------------|----------|----------|----------------|-------|
| **`DEAL_INACTIVE`** | BidSwitch Configuration | CRITICAL | ✅ Custom | Deal not found in active deals list |
| **`DEAL_PAUSED`** | BidSwitch Configuration | HIGH | ✅ Custom | Deal paused by DSP or SSP |
| **`DEAL_BROKEN`** | BidSwitch Configuration | CRITICAL | ✅ Custom | Deal marked as broken in BidSwitch |
| **`DEAL_REJECTED`** | BidSwitch Configuration | HIGH | ✅ Custom | Deal rejected by party |
| **`DEAL_STATUS_ISSUE`** | BidSwitch Configuration | MEDIUM | ✅ Custom | Unusual deal status |
| **`BID_BELOW_FLOOR`** | Auction Health | HIGH | ✅ Aligned | Bid prices below floor price threshold |
| **`GEOGRAPHIC_TARGETING_MISMATCH`** | BidSwitch Targeting | CRITICAL | ✅ **Enhanced** | Regional targeting conflicts (EMEA, APAC, etc.) |
| **`TARGETING_MISMATCH`** | BidSwitch Targeting | HIGH | ✅ Aligned | General targeting configuration issues |
| **`LOW_BID_RATE`** | Auction Health | HIGH | ✅ Aligned | Bid response rate below baseline |
| **`LOW_WIN_RATE`** | Auction Health | MEDIUM | ✅ Aligned | Win rate below expected baseline |
| **`NO_TRAFFIC`** | BidSwitch Configuration | HIGH | ✅ Aligned | Zero bid requests received |
| **`HEALTHY`** | Status | LOW | ✅ Aligned | No issues detected |

### **❌ Missing Primary Issues (Roadmap)**

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

#### **🔍 BidSwitch-Specific Rules (Partially Implemented)**
| Missing Issue | Detection Logic | Severity | Priority |
|---------------|----------------|----------|----------|
| **`HIGH_SMARTSWITCH_FILTERING`** | `smartswitch_filter_rate > 0.60` | HIGH | **HIGH** |
| **`EXTREME_SMARTSWITCH_FILTERING`** | `smartswitch_filter_rate > 0.70` | CRITICAL | **HIGH** |
| **`HIGH_INVALID_REQUESTS`** | `invalid_requests / total > 0.20` | HIGH | **MEDIUM** |
| **`HIGH_GEO_TARGETING_FAILURE`** | `geo_targeting_failure_rate > 0.50` | HIGH | **MEDIUM** |
| **`HIGH_TIMEOUT_RATE`** | `timeout_rate > 0.10` | HIGH | **MEDIUM** |

---

## 📊 **Campaign-Level Diagnostic Patterns** ⭐ **HIERARCHICAL CONTEXT**

### **CAMPAIGN_DISABLED** ⭐ **CRITICAL**
**Symptoms**: Campaign statusId != 1 (disabled/paused)
**Detection**: Query campaign status from PostgreSQL
**Resolution**: Enable campaign (set statusId=1)
**Impact**: Affects ALL line items and Supply Deals in campaign
**Early Exit**: Skip individual deal analysis (root cause found)
**Example**: Campaign 89 disabled → 57 deal relationships affected (ONE fix vs. 57 fixes)

### **CAMPAIGN_BUDGET_EXHAUSTED** ⭐ **HIGH**
**Symptoms**: Campaign budget fully spent (spend >= budget)
**Detection**: Compare campaign spend vs. budget
**Resolution**: Increase budget or adjust pacing
**Impact**: Prevents all line item spending
**Early Exit**: Skip deal analysis (budget constraint)
**Validation**: Compare Looker vs. BidSwitch spend (within 10-20% variance)

### **CAMPAIGN_DATES_INVALID** ⭐ **MEDIUM**
**Symptoms**: Campaign dates misaligned with line items
**Detection**: Compare campaign vs. line item date ranges
**Resolution**: Adjust campaign dates or line item assignments
**Impact**: Line items outside campaign flight
**Early Exit**: Skip deal analysis (date constraint)
**Validation**: Alert if line items end after campaign (data alignment issue)

---

## 🤖 **Diagnostic Rules Engine**

### **Rule Categories** (Based on Operational Framework)
1. **Campaign-Level Rules** - Monitor campaign health and configuration (early exit)
2. **Data Integrity Rules** - Detect impossible data combinations
3. **Auction Health Rules** - Monitor bidding and auction performance
4. **Delivery Quality Rules** - Assess creative and viewability metrics
5. **Performance Deviation Rules** - Identify metric trends and anomalies
6. **Combination Pattern Rules** - Multi-metric issue detection
7. **Flow Issues Rules** - Configuration and setup problems

### **🚨 Data Integrity Rules**

#### **Rule: CONVERSIONS_EXCEED_CLICKS**
- **Detection Logic**: `conversions > clicks` 
- **Severity**: CRITICAL
- **Category**: Data Error
- **Agent Response**: "Data integrity violation detected: Conversions cannot exceed clicks"
- **Root Causes**: 
  - Attribution window misconfiguration
  - Pixel tracking errors
  - Data processing pipeline issues
- **Recommended Actions**:
  1. Verify conversion pixel implementation
  2. Check attribution window settings
  3. Review data processing logs
- **Implementation**: `enhanced_diagnostics.py::check_data_integrity()`
- **Agent Workflow**:
  ```python
  if conversions > clicks:
      return DiagnosticResult(
          issue="CONVERSIONS_EXCEED_CLICKS",
          severity="CRITICAL", 
          confidence=1.0,
          actions=["verify_pixel", "check_attribution", "review_logs"]
      )
  ```

#### **Rule: IMPRESSIONS_EXCEED_BIDS**
- **Detection Logic**: `impressions > bids`
- **Severity**: CRITICAL  
- **Category**: Data Error
- **Agent Response**: "Impossible data detected: Impressions cannot exceed total bids"
- **Root Causes**:
  - Data synchronization issues
  - Reporting pipeline errors
  - Database integrity problems
- **Recommended Actions**:
  1. Check data pipeline synchronization
  2. Verify database integrity constraints
  3. Review bid request/response logs

#### **Rule: BID_RATE_OVER_100_PERCENT**
- **Detection Logic**: `bid_rate > 1.0` OR `win_rate > 1.0`
- **Severity**: CRITICAL
- **Category**: Data Error  
- **Agent Response**: "Rate calculation error: Rates cannot exceed 100%"
- **Root Causes**:
  - Division by zero errors
  - Incorrect metric calculations
  - Data type overflow issues
- **Recommended Actions**:
  1. Review rate calculation formulas
  2. Check for division by zero conditions
  3. Validate input data ranges

### **📊 Auction Health Rules**

#### **Rule: BID_RATE_BELOW_BASELINE**
- **Detection Logic**: `bid_rate < 0.30` (30%)
- **Severity**: HIGH
- **Category**: Auction Health
- **Baseline**: Industry standard 30-80%
- **Agent Response**: "Bid rate below healthy baseline - potential targeting or inventory issues"
- **Root Causes**:
  - Targeting too narrow
  - Inventory shortage
  - Budget constraints
  - Technical bidding issues
- **Recommended Actions**:
  1. Review targeting parameters
  2. Check inventory availability
  3. Verify budget allocation
  4. Examine technical bid logs

#### **Rule: WIN_RATE_BELOW_BASELINE**
- **Detection Logic**: `win_rate < 0.10` (10%) for display OR `win_rate < 0.05` (5%) for video
- **Severity**: MEDIUM
- **Category**: Auction Health
- **Baseline**: Display: 10-30%, Video: 5-15%
- **Agent Response**: "Win rate below expected baseline for media type"
- **Root Causes**:
  - Bid price too low
  - Auction competition high
  - Creative quality issues
  - Targeting misalignment
- **Recommended Actions**:
  1. Increase bid prices
  2. Analyze competitor activity
  3. Review creative performance
  4. Optimize targeting strategy

#### **Rule: HIGH_BID_RATE_LOW_WIN_RATE**
- **Detection Logic**: `bid_rate > 0.80 AND win_rate < 0.10`
- **Severity**: HIGH
- **Category**: Combination Pattern
- **Agent Response**: "High bid participation but low wins - likely bid price issue"
- **Root Causes**:
  - Bid prices consistently below market
  - Poor creative quality
  - Brand safety filtering
  - Technical bid issues
- **Recommended Actions**:
  1. Increase bid prices significantly
  2. A/B test creative variations
  3. Review brand safety settings
  4. Audit bid request processing

### **🎯 Delivery Quality Rules**

#### **Rule: CTR_BELOW_BASELINE**
- **Detection Logic**: 
  - Display: `ctr < 0.001` (0.1%)
  - Video: `ctr < 0.005` (0.5%)
- **Severity**: MEDIUM
- **Category**: Delivery Quality
- **Baseline**: Display: 0.1-0.3%, Video: 0.5-2.0%
- **Agent Response**: "Click-through rate below industry baseline for media type"
- **Root Causes**:
  - Poor creative design
  - Audience misalignment
  - Ad placement issues
  - Creative fatigue
- **Recommended Actions**:
  1. Test new creative variations
  2. Refine audience targeting
  3. Review placement quality
  4. Implement creative rotation

#### **Rule: VIEWABILITY_BELOW_THRESHOLD**
- **Detection Logic**: `viewability_rate < 0.50` (50%)
- **Severity**: HIGH
- **Category**: Delivery Quality
- **Baseline**: Industry standard >70%
- **Agent Response**: "Viewability rate below acceptable threshold"
- **Root Causes**:
  - Poor inventory quality
  - Below-the-fold placements
  - Fast-loading pages
  - Mobile viewport issues
- **Recommended Actions**:
  1. Audit inventory sources
  2. Implement viewability optimization
  3. Review placement strategies
  4. Optimize for mobile viewability

---

## 🔌 **BidSwitch Integration Specifications**

### **API Integration Requirements**
- **Authentication**: OAuth2 with refresh token handling
- **Rate Limiting**: Respect BidSwitch API limits (100 requests/minute)
- **Error Handling**: Exponential backoff for 429/503 responses
- **Data Freshness**: Cache responses for 5 minutes maximum

### **Diagnostic Pattern Matching Structure**

```python
class DiagnosticPattern:
    def __init__(self, name, condition, severity, message, actions):
        self.name = name
        self.condition = condition  # Function that returns True if pattern matches
        self.severity = severity    # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
        self.message = message      # Human-readable description
        self.actions = actions      # List of recommended actions
```

### **Traffic Volume Patterns**

#### **Pattern: No Traffic**
```python
{
    "name": "no_traffic",
    "condition": lambda metrics: metrics.get('bid_requests', 0) == 0,
    "severity": "HIGH",
    "message": "No bid requests received for deal",
    "symptoms": ["bid_requests = 0"],
    "root_causes": [
        "Deal not properly configured",
        "Targeting restrictions too narrow", 
        "Deal paused or inactive",
        "SSP integration issues"
    ],
    "recommended_actions": [
        "Verify deal status in BidSwitch",
        "Check targeting configuration",
        "Review SSP integration logs",
        "Validate deal ID mapping"
    ]
}
```

#### **Pattern: Low Traffic Volume**
```python
{
    "name": "low_traffic_volume",
    "condition": lambda metrics: 0 < metrics.get('bid_requests', 0) < 1000,
    "severity": "MEDIUM",
    "message": "Deal receiving low traffic volume",
    "baseline": "Expected: >1000 bid requests/day",
    "recommended_actions": [
        "Expand targeting parameters",
        "Check inventory availability",
        "Review deal floor prices",
        "Verify geographic targeting"
    ]
}
```

### **Geographic Analysis Patterns**

#### **Pattern: Geographic Targeting Mismatch**
```python
{
    "name": "geographic_targeting_mismatch",
    "condition": lambda geo_data: check_regional_mismatch(geo_data),
    "severity": "CRITICAL",
    "message": "Geographic targeting mismatch detected",
    "detection_logic": {
        "emea_targeting_us_traffic": "EMEA deal receiving >50% US traffic",
        "apac_targeting_eu_traffic": "APAC deal receiving >50% EU traffic",
        "us_targeting_international": "US deal receiving >70% international traffic"
    },
    "recommended_actions": [
        "Review geographic targeting settings",
        "Verify deal geographic restrictions",
        "Check SSP geographic filtering",
        "Validate audience geographic distribution"
    ]
}
```

### **SmartSwitch Analysis**

#### **Pattern: High SmartSwitch Filtering**
```python
{
    "name": "high_smartswitch_filtering",
    "condition": lambda metrics: metrics.get('smartswitch_filter_rate', 0) > 0.60,
    "severity": "HIGH",
    "message": "SmartSwitch filtering >60% of requests",
    "baseline": "Expected: <30% filtering rate",
    "root_causes": [
        "Aggressive fraud detection settings",
        "Poor inventory quality",
        "Bot traffic in supply",
        "Geographic misalignment"
    ],
    "recommended_actions": [
        "Review SmartSwitch filter settings",
        "Audit inventory quality metrics",
        "Implement additional fraud detection",
        "Optimize geographic targeting"
    ]
}
```

---

## 🛠️ **Implementation Guidelines**

### **Code Integration Requirements**

#### **File Structure**
```
tools/
├── campaign-analysis/
│   ├── src/
│   │   ├── utils/
│   │   │   ├── enhanced_diagnostics.py    # Core diagnostic engine
│   │   │   ├── deal_analyzer.py           # Deal-specific analysis
│   │   │   └── bidswitch_client.py        # BidSwitch API integration
│   │   ├── campaign_diagnostics.py        # Campaign-level diagnostics
│   │   └── campaign_analyzer.py           # Main orchestrator
└── deal-analysis/
    ├── src/
    │   ├── enhanced_diagnostics.py         # Shared diagnostic engine
    │   ├── deal_analyzer.py                # Core deal analysis
    │   └── bidswitch_client.py             # BidSwitch API client
```

#### **Diagnostic Engine Integration**
```python
# enhanced_diagnostics.py
class DiagnosticEngine:
    def __init__(self):
        self.rules = self._load_diagnostic_rules()
        
    def analyze_deal(self, deal_data, performance_metrics):
        """
        Run all diagnostic rules against deal data
        Returns: DiagnosticResult with primary issue, severity, confidence
        """
        results = []
        
        # Data integrity checks (CRITICAL)
        results.extend(self._check_data_integrity(performance_metrics))
        
        # Auction health analysis
        results.extend(self._analyze_auction_health(performance_metrics))
        
        # BidSwitch-specific diagnostics
        results.extend(self._analyze_bidswitch_metrics(deal_data))
        
        # Geographic analysis
        if 'geographic_data' in deal_data:
            results.extend(self._analyze_geographic_patterns(deal_data['geographic_data']))
            
        return self._prioritize_issues(results)
        
    def _check_data_integrity(self, metrics):
        """Critical data integrity validation"""
        issues = []
        
        # Conversions cannot exceed clicks
        if metrics.get('conversions', 0) > metrics.get('clicks', 0):
            issues.append(DiagnosticResult(
                issue="CONVERSIONS_EXCEED_CLICKS",
                severity="CRITICAL",
                confidence=1.0,
                message="Data integrity violation: Conversions exceed clicks"
            ))
            
        # Impressions cannot exceed bids
        if metrics.get('impressions', 0) > metrics.get('bids', 0):
            issues.append(DiagnosticResult(
                issue="IMPRESSIONS_EXCEED_BIDS", 
                severity="CRITICAL",
                confidence=1.0,
                message="Impossible data: Impressions exceed total bids"
            ))
            
        return issues
```

#### **AI Agent Integration**
```python
# campaign_analyzer.py
class CampaignAnalyzer:
    def __init__(self):
        self.diagnostic_engine = DiagnosticEngine()
        self.deal_analyzer = DealAnalyzer()
        
    def run_analysis(self, campaign_id):
        """
        Main analysis workflow optimized for AI agent consumption
        Returns: Structured JSON with diagnostic results
        """
        # 1. Discover campaign data
        campaign_data = self.discovery.get_campaign_data(campaign_id)
        
        # 2. Analyze each unique deal (with deduplication)
        deal_results = self.diagnostics.analyze_campaign_deals(campaign_data['deals'])
        
        # 3. Detect campaign-level patterns
        patterns = self.diagnostics.detect_campaign_patterns(deal_results)
        
        # 4. Generate AI-optimized output
        return {
            "campaign_id": campaign_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "diagnostic_summary": {
                "primary_issues": [r['primary_issue'] for r in deal_results],
                "severity_distribution": self._calculate_severity_distribution(deal_results),
                "confidence_scores": [r['confidence'] for r in deal_results]
            },
            "deal_analysis": deal_results,
            "campaign_patterns": patterns,
            "recommended_actions": self._generate_recommendations(patterns)
        }
```

### **Testing Requirements**

#### **Unit Tests**
```python
# test_diagnostic_engine.py
class TestDiagnosticEngine:
    def test_data_integrity_conversions_exceed_clicks(self):
        """Test critical data integrity rule"""
        metrics = {'conversions': 100, 'clicks': 50}
        engine = DiagnosticEngine()
        results = engine._check_data_integrity(metrics)
        
        assert len(results) == 1
        assert results[0].issue == "CONVERSIONS_EXCEED_CLICKS"
        assert results[0].severity == "CRITICAL"
        assert results[0].confidence == 1.0
        
    def test_geographic_targeting_mismatch(self):
        """Test geographic analysis patterns"""
        geo_data = {
            'deal_targeting': ['US'],
            'traffic_distribution': {'EU': 0.8, 'US': 0.2}
        }
        engine = DiagnosticEngine()
        results = engine._analyze_geographic_patterns(geo_data)
        
        assert any(r.issue == "GEOGRAPHIC_TARGETING_MISMATCH" for r in results)
```

#### **Integration Tests**
```python
# test_campaign_analysis_integration.py
class TestCampaignAnalysisIntegration:
    def test_end_to_end_analysis(self):
        """Test complete campaign analysis workflow"""
        analyzer = CampaignAnalyzer()
        results = analyzer.run_analysis(campaign_id=89)
        
        # Validate output structure
        assert 'diagnostic_summary' in results
        assert 'deal_analysis' in results
        assert 'campaign_patterns' in results
        
        # Validate diagnostic results
        assert all('primary_issue' in deal for deal in results['deal_analysis'])
        assert all('confidence' in deal for deal in results['deal_analysis'])
```

---

## 📈 **Implementation Roadmap**

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

### **Phase 3: Campaign-Level Analysis (Week 3)**
**Priority: MEDIUM** - Extend for campaign analysis tool

```python
# Campaign-specific diagnostics
CAMPAIGN_ISSUES = [
    "CTR_BELOW_DISPLAY_BASELINE",      # Creative performance
    "CTR_BELOW_VIDEO_BASELINE",        # Video creative performance  
    "VIEWABILITY_BELOW_THRESHOLD",     # Inventory quality
    "SPEND_UP_IMPRESSIONS_DOWN"        # Pacing issues
]
```

### **Phase 4: Advanced Pattern Detection (Week 4)**
**Priority: LOW** - Implement combination pattern rules

```python
# Multi-metric pattern analysis
COMBINATION_PATTERNS = [
    "HIGH_WIN_RATE_LOW_IMPRESSIONS",   # Inventory shortage
    "NORMAL_IMPRESSIONS_LOW_CTR",      # Creative issues
    "CTR_NORMAL_CONVERSION_RATE_LOW"   # Landing page issues
]
```

---

## 🎯 **Success Metrics**

### **Diagnostic Accuracy**
- **Coverage**: >95% of known issues detected
- **False Positives**: <5% incorrect diagnoses  
- **Confidence Scores**: Average >0.8 for implemented rules

### **Performance Requirements**
- **Analysis Speed**: <30 seconds for 50-deal campaign
- **API Response**: <5 seconds for individual deal analysis
- **Memory Usage**: <500MB for largest campaign analysis

### **Agent Integration**
- **JSON Validation**: 100% valid structured output
- **Rule Consistency**: Identical results across tools
- **Documentation Coverage**: All rules documented with examples

---

*This specification serves as the single source of truth for all diagnostic rules and implementation guidelines across the Bedrock Platform Intelligence analysis tools.*
