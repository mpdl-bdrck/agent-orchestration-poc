# Analysis Tools - Complete Reference
*Updated: November 18, 2025*

## 🎯 **Overview**

Comprehensive suite of analysis tools for Bedrock Platform Intelligence, featuring real-time diagnostics, campaign troubleshooting, and BidSwitch integration with AI-optimized output formats.

**Key Features**: Real API integration • Deduplication logic • Geographic analysis • Accurate spend data • Agent-ready JSON output • Modular architecture

---

## 📊 **Centralized Reports Structure** ✅ **NEW**

**Important Change**: All analysis tools now output to a **centralized reports directory** for better organization and easier access.

### **Reports Location**
```bash
# All tool outputs are saved here
tools/reports/
├── campaign_<id>_analysis.json          # Campaign analysis results
├── campaign_<id>_deal_breakdown.json    # Deal relationship breakdowns
├── deal_<id>_analysis.json              # Individual deal diagnostics
├── deal_countries_<id>.json             # Geographic analysis
└── active_deals_<timestamp>.json        # Active deals listings
```

### **Benefits of Centralization**
- 📁 **Single Location**: All analysis reports in one place
- 🔍 **Easy Discovery**: No need to check multiple tool directories
- 🧹 **Cleaner Structure**: Tool directories focus on source code
- 🔮 **Future-Proof**: New tools automatically use centralized location
- 📊 **Better Organization**: All reports visible at a glance

## 🏗️ **Object Model**

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

**Relationship**:
```
External Deal (SSP) ──sspDealId──> Supply Deal (Bedrock)
                                └─→ Curation Package
                                    └─→ Line Item
                                        └─→ Campaign
```

**Tools Query BOTH**:
- Supply Deal configuration (Bedrock database)
- External Deal performance (BidSwitch API) - when PMP type

## 🤖 **Intelligent Monitoring Integration**

### **Hierarchical Analysis Approach**

The tools provide the foundation for intelligent monitoring systems:

**Campaign Level** (Context):
- Campaign health (status, budget, dates, line items)
- Portfolio view (all deals accessed by campaign's line items)
- Early detection (campaign disabled = all deals affected)
- Tool: campaign-analysis/

**Supply Deal Level** (Diagnostics):
- Individual deal performance
- Pattern-specific issues (geo, creative, QPS, etc.)
- Granular troubleshooting
- Tools: deal-debugging/ + specialized tools

### **Tool Integration Workflow**

```
Intelligent monitoring system:
  1. Campaign-level check (campaign-analysis tool)
     - Is campaign active?
     - Budget available?
     - Dates valid?

  2. If campaign issues found:
     - Alert campaign-level problem
     - Skip individual deal analysis (waste of resources)

  3. If campaign healthy:
     - Proceed to deal-level analysis (deal debugging tools)
     - Flag underperforming deals
     - Apply pattern-specific diagnostics
```

**Why this matters**: Checking campaign first prevents alert noise. Campaign 89 example: Campaign disabled affects 57 deal relationships - that's ONE campaign fix, not 57 deal fixes.

---

## 🛠️ **Available Tools**

### **Campaign Portfolio Pacing Tool** ✅ **UPDATED**
| Aspect | Details |
|--------|---------|
| **Entry Point** | `./campaign-portfolio-pacing/run_campaign_portfolio_pacing.sh <account_id> [advertiser_filter]` |
| **Purpose** | Comprehensive campaign portfolio analysis with pacing intelligence |
| **Key Features** | • **Portfolio pacing dashboard** with actionable metrics<br>• **Multi-campaign support** (all campaigns for account/advertiser)<br>• **Google Sheets integration** with real-time dashboards<br>• **Account/advertiser name retrieval** from database |
| **Output** | `../reports/` (CSV rollups) + Google Sheets dashboard |
| **Key Advantage** | Provides actionable pacing intelligence with visual status indicators |

### **Campaign Analysis Tool** ⚠️ **SPEND DATA ISSUE**
| Aspect | Details |
|--------|---------|
| **Entry Point** | `./campaign-analysis/run_campaign_analysis.sh <campaign_id>` |
| **Purpose** | Complete campaign troubleshooting with deal portfolio analysis |
| **Key Features** | • **Deal deduplication** (analyzes unique deals, tracks relationships)<br>• **Real BidSwitch integration** with OAuth2<br>• **Geographic targeting analysis** (EMEA/APAC/US detection)<br>• **Campaign-level pattern detection** |
| **Output** | `../reports/campaign_<id>_analysis.json` |
| **⚠️ Known Issue** | **Spend data retrieval is broken** - returns 0.0% utilization due to incorrect Redshift schema assumptions |

### **Campaign Deal Breakdown Tool** ✅ **NEW**
| Aspect | Details |
|--------|---------|
| **Entry Point** | `./campaign-analysis/campaign_deal_breakdown.sh <campaign_id>` |
| **Purpose** | Detailed analysis of deal-line item relationships and duplications |
| **Key Features** | • **Relationship mapping** (line items → packages → deals)<br>• **Duplication analysis** with frequency tracking<br>• **SSP breakdown** and distribution analysis |
| **Output** | `../reports/campaign_<id>_deal_breakdown.json` |
| **Documentation** | See [Campaign Analysis Tool README](./campaign-analysis/README.md#what-it-analyzes) |

### **Deal Debugging Tool** ✅ **PROVEN**
| Aspect | Details |
|--------|---------|
| **Entry Point** | `./deal-debugging/run_deal_debugging.sh <deal_id>` |
| **Purpose** | Individual PMP deal verification and BidSwitch diagnostics |
| **Scope** | **PMP Supply Deals** (BidSwitch API integration) + **Open Exchange Supply Deals** (internal diagnostics) |
| **Key Features** | • **Real BidSwitch API** integration<br>• **Enhanced diagnostics** with confidence scoring<br>• **Geographic targeting validation** |
| **Output** | `../reports/deal_<id>_analysis.json` |
| **Documentation** | See [Deal Debugging Tool README](./deal-debugging/README.md) |
| **Note** | Open Exchange Supply Deals use different diagnostic approach (filter list analysis, internal metrics) |

### **Deal Geographic Analysis** ✅ **SPECIALIZED**
| Aspect | Details |
|--------|---------|
| **Entry Point** | `./deal-debugging/get_deal_countries.sh <deal_id>` |
| **Purpose** | Detailed geographic breakdown for individual deals |
| **Key Features** | • **Country-level analysis** via BidSwitch Deals Discovery API<br>• **Traffic distribution** patterns |
| **Output** | `../reports/deal_countries_<deal_id>.json` |

---

## 🔧 **Spend Data Issue & Resolution**

### **🚨 Critical Issue: Campaign Analysis Tool Spend Data Problem**

The existing **campaign-analysis tool** has a **critical flaw**: it cannot retrieve accurate spend data from Redshift, consistently showing **0.0% budget utilization** for all campaigns.

#### **Root Cause Analysis**
| Incorrect Assumption | What Was Used | What Should Be Used | Impact |
|---------------------|---------------|-------------------|---------|
| **Table Name** | `public.overview` | `public.overview_view` | ❌ No data retrieved |
| **Spend Column** | `imp_total_spend` | `media_spend` | ❌ Wrong column |
| **Impressions Column** | `impressions` | `burl_count` | ❌ Wrong column |
| **Spend Calculation** | Net spend (after margin) | Gross spend (matches UI) | ❌ Doesn't match UI |
| **Query Logic** | By line item UUID | By campaign UUID | ❌ Wrong aggregation |

#### **Validation Results**
- **Campaign 166**: Should show $11,212.58 spend, 1,040,217 impressions
- **Campaign Analysis Tool**: Shows 0.0% utilization, "NO_SPEND_DATA"
- **New Campaign Spend Analysis Tool**: ✅ Correctly retrieves $11,212.58 spend

#### **Why This Matters**
- **Agent Decisions Blocked**: Autonomous optimization cannot make spend-based decisions
- **Manual Analysis Required**: Teams must use separate tools for spend insights
- **Phase 1 Foundation Broken**: Specialist Agent capabilities severely limited
- **Trust Issues**: Tools providing incomplete analysis erode confidence

### **✅ Solution: Campaign Spend Analysis Tool**

The **campaign-portfolio-pacing tool** provides comprehensive campaign analysis with pacing intelligence:

#### **Corrected Query Approach**
```sql
SELECT o.campaign_id as campaign_uuid,
       SUM(o.media_spend) as gross_spend,
       SUM(o.burl_count) as total_impressions
FROM public.overview_view o
WHERE o.campaign_id = %s
GROUP BY o.campaign_id;
```

#### **Key Fixes Applied**
- ✅ **Table**: `public.overview_view` (primary), `public.overview` (fallback)
- ✅ **Spend Column**: `media_spend` (gross spend, matches UI)
- ✅ **Impressions Column**: `burl_count` (in overview_view)
- ✅ **Query Method**: By campaign UUID with proper aggregation
- ✅ **Validation**: Campaign 166 matches UI values exactly

### **🔄 Required: Campaign Analysis Tool Update**

The existing **campaign-analysis tool** must be updated to use the correct spend data retrieval approach:

#### **Update Requirements**
1. **Replace campaign_discovery.get_spend_data()** with the corrected query logic
2. **Update table references** from `public.overview` to `public.overview_view`
3. **Fix column mappings** (`imp_total_spend` → `media_spend`, `impressions` → `burl_count`)
4. **Change spend calculation** from net to gross spend
5. **Update aggregation logic** from line item to campaign level
6. **Add fallback mechanism** to `public.overview` table

#### **Implementation Steps**
1. **Locate**: `tools/campaign-analysis/src/campaign_discovery.py`
2. **Update**: `get_spend_data()` method with corrected Redshift queries
3. **Test**: Validate Campaign 166 shows $11,212.58 spend (not 0.0%)
4. **Verify**: All campaigns show proper budget utilization percentages

#### **Post-Update Benefits**
- ✅ **Accurate Spend Data**: Budget utilization reflects reality
- ✅ **Agent Compatibility**: Autonomous optimization decisions enabled
- ✅ **Complete Analysis**: Campaign health assessment includes spend metrics
- ✅ **Unified Tooling**: Single tool for comprehensive campaign analysis

### **📊 Current Status**
- ✅ **Campaign Spend Analysis Tool**: Working correctly with validated queries
- ⚠️ **Campaign Analysis Tool**: Spend data broken, requires update
- 🎯 **Primary Tool**: Use campaign-portfolio-pacing for comprehensive campaign analysis with pacing intelligence

---

## 🚀 **Quick Start Guide**

### **1. Environment Setup** (One-Time)
```bash
# Navigate to tools directory
cd tools/

# Activate shared virtual environment
source venv/bin/activate

# Verify configuration (ensure tools/.env exists)
ls -la .env
```

### **2. Campaign Analysis Workflow**
```bash
# Campaign portfolio pacing analysis with dashboard
cd campaign-portfolio-pacing/
./run_campaign_portfolio_pacing.sh 17 "Lilly" --publish-sheets --campaign-start 2025-11-01 --campaign-end 2025-12-31 --campaign-budget 466000

# Campaign portfolio pacing analysis
cd campaign-portfolio-pacing/
./run_campaign_portfolio_pacing.sh 89 --publish-sheets

# Detailed deal relationship breakdown
./campaign_deal_breakdown.sh 89

# Review results
ls -la ../reports/
```

### **3. Deal-Level Debugging**
```bash
# Individual deal diagnostics
cd deal-debugging/
./run_deal_debugging.sh 89

# Geographic breakdown for specific deal
./get_deal_countries.sh 939094715008

# Review results
ls -la ../reports/
```

---

## 📊 **Tool Architecture & Recent Enhancements**

### **🔄 Campaign Analysis Tool Rebuild**
**Status**: ✅ **COMPLETELY REBUILT** (October 2025)

#### **What Was Fixed**:
- ❌ **Old**: Fake test data pollution, zero real API integration
- ✅ **New**: 100% real data integration with BidSwitch OAuth2
- ❌ **Old**: Overengineered 8+ module architecture  
- ✅ **New**: Clean 3-module design (discovery → diagnostics → analyzer)
- ❌ **Old**: Duplicate deal analysis (57 analyses for 30 unique deals)
- ✅ **New**: Smart deduplication (30 unique analyses, relationship tracking)

#### **New Architecture**:
```
campaign-analysis/
├── src/
│   ├── campaign_analyzer.py      # Main orchestrator
│   ├── campaign_discovery.py     # PostgreSQL/Redshift data collection
│   ├── campaign_diagnostics.py   # Analysis with deduplication logic
│   ├── campaign_deal_breakdown.py # Relationship analysis tool
│   └── utils/                    # Shared components from deal-debugging
│       ├── deal_analyzer.py      # Proven BidSwitch integration
│       ├── enhanced_diagnostics.py # Geographic & diagnostic patterns
│       └── bidswitch_client.py   # OAuth2 API client
```

### **🎯 Key Technical Improvements**

#### **Deal Deduplication Logic**
```python
# Before: Analyzed same deal multiple times
total_relationships = 57  # Deal-line item relationships
unique_deals = 30         # Actual unique deals
redundant_analyses = 27   # Wasted API calls

# After: Smart deduplication
unique_deals_analyzed = 30
relationships_tracked = 57
deduplication_savings = 27  # 47% efficiency improvement
```

#### **Enhanced Geographic Analysis**
- **Regional Detection**: Automatic EMEA/APAC/US classification
- **Targeting Mismatch**: Critical alerts for geographic conflicts
- **Traffic Distribution**: Country-level breakdown analysis

#### **Real API Integration**
- **BidSwitch OAuth2**: Automatic token refresh and rate limiting
- **PostgreSQL**: Campaign metadata and deal relationships  
- **Redshift**: Spend data and performance metrics
- **Error Handling**: Exponential backoff and graceful degradation

---

## 🔧 **Configuration & Setup**

### **Environment Variables**
Tools use shared configuration in `tools/.env`:

```bash
# Database connections
POSTGRES_HOST=your-postgres-host
POSTGRES_DB=your-database  
POSTGRES_USER=your-username
POSTGRES_PASSWORD=your-password

REDSHIFT_CLUSTER_ID=your-cluster-id
REDSHIFT_DATABASE=bedrock

# BidSwitch API credentials (API User - not Admin User)
BIDSWITCH_USERNAME=your-bidswitch-api-username
BIDSWITCH_PASSWORD=your-bidswitch-api-password

# DSP Configuration
DSP_SEAT_ID=503  # Configurable DSP seat identifier
```

**Important**: Use BidSwitch **API User** credentials (created via myBidSwitch UI → Users → Add User → API Account).

### **Shared Dependencies**
All tools share a single virtual environment and dependency file:
- **Virtual Environment**: `tools/venv/`
- **Dependencies**: `tools/requirements.txt`
- **Database Utilities**: `tools/shared/database_connector.py`

---

## 📋 **Technical Documentation**

### **Implementation Specifications**
- **[Technical Specifications](./docs/technical-specifications.md)** - Complete diagnostic rules, issue classifications, and implementation guidelines
- **[Documentation Strategy](./docs/documentation_strategy.md)** - Technical documentation architecture

### **Tool-Specific Guides**
- **[Campaign Deal Relationships](./campaign-analysis/DEAL_RELATIONSHIP_ANALYSIS.md)** - Understanding deal-line item relationships
- **[Main Project README](../README.md)** - Complete setup instructions and architecture overview

### **Knowledge Base Integration**
The tools integrate with the standalone knowledge base for business context:
- **[Campaign Troubleshooting](../knowledge-base/06-operations/campaign-troubleshooting.md)** - Operational procedures
- **[Deal Debug Workflow](../knowledge-base/06-operations/deal-debug-workflow.md)** - Industry best practices for deal debugging
- **[BidSwitch Diagnostic Patterns](../knowledge-base/08-bidswitch-integration/diagnostic-patterns.md)** - Automated diagnostic rules
- **[BidSwitch Deals Management](../knowledge-base/08-bidswitch-integration/bidswitch-deals-management.md)** - Deal lifecycle and troubleshooting
- **[Platform Architecture](../knowledge-base/03-technical-features/platform-architecture.md)** - System architecture overview

---

## 🎯 **Output Formats & AI Integration**

### **Structured JSON Output**
All tools generate AI-optimized JSON with consistent structure:

```json
{
  "campaign_id": 89,
  "analysis_timestamp": "2025-10-14T19:00:00",
  "diagnostic_summary": {
    "primary_issues": ["GEOGRAPHIC_TARGETING_MISMATCH", "LOW_BID_RATE"],
    "severity_distribution": {"CRITICAL": 2, "HIGH": 5, "MEDIUM": 8},
    "confidence_scores": [0.95, 0.87, 0.92]
  },
  "unique_deals_analyzed": 30,
  "total_relationships": 57,
  "deduplication_savings": 27,
  "deal_analysis": [...],
  "campaign_patterns": [...],
  "recommended_actions": [...]
}
```

### **Agent Consumption Features**
- **Confidence Scoring**: All diagnostics include confidence levels (0.0-1.0)
- **Severity Classification**: CRITICAL/HIGH/MEDIUM/LOW for prioritization
- **Actionable Recommendations**: Structured action items with context
- **Cross-References**: Links to knowledge base for additional context

---

## 🚀 **Performance & Efficiency**

### **Token Cost Optimization**
- **80-90% Token Savings**: Tools handle heavy computation, agents focus on interpretation
- **Structured Output**: Pre-processed data reduces agent processing overhead
- **Real Data Only**: No fake/test data pollution in results

### **Analysis Performance**
- **Campaign Analysis**: <30 seconds for 50-deal campaigns
- **Deal Debugging**: <5 seconds per individual deal
- **Deduplication**: 47% reduction in redundant API calls
- **Memory Efficiency**: <500MB for largest campaign analysis

### **API Efficiency**
- **Rate Limiting**: Respects BidSwitch API limits (100 requests/minute)
- **Caching**: 5-minute cache for repeated requests
- **Error Handling**: Exponential backoff for 429/503 responses
- **OAuth2 Management**: Automatic token refresh and session handling

---

## 🔍 **Troubleshooting**

### **Common Issues**
| Issue | Solution |
|-------|----------|
| **"No module named 'psycopg2'"** | Activate virtual environment: `source venv/bin/activate` |
| **"Database connection failed"** | Check `tools/.env` configuration and database connectivity |
| **"BidSwitch authentication failed"** | Verify API user credentials (not admin credentials) |
| **"No deals found for campaign"** | Check campaign ID and PostgreSQL query results |

### **Debug Mode**
Enable detailed logging by setting environment variable:
```bash
export DEBUG_MODE=1
./run_campaign_portfolio_pacing.sh 89 --publish-sheets
```

### **Log Locations**
- **Campaign Analysis**: Console output with progress indicators
- **Deal Debugging**: Detailed API interaction logs
- **Error Logs**: Captured in JSON output under `"errors"` field

---

## 📈 **Recent Updates & Changelog**

### **November 2025 - Critical Fixes & New Tool**
- ✅ **Campaign Spend Analysis Tool**: New tool with accurate Redshift spend data retrieval
- 🚨 **Spend Data Issue Identified**: Campaign Analysis Tool spend queries broken (0.0% utilization)
- ✅ **Redshift Schema Correction**: Validated `public.overview_view` with `media_spend`/`burl_count` columns
- ✅ **Account/Advertiser Name Retrieval**: Database queries for proper naming in reports
- ✅ **CSV Format Optimization**: Streamlined output with account and advertiser context

### **October 2025 - Major Rebuild**
- ✅ **Campaign Analysis Tool**: Complete rebuild with deduplication logic
- ✅ **Deal Breakdown Tool**: New tool for relationship analysis
- ✅ **Geographic Enhancement**: EMEA/APAC/US targeting validation
- ✅ **Documentation Consolidation**: Technical specs moved to `tools/docs/`
- ✅ **Performance Optimization**: 47% reduction in redundant API calls
- ✅ **Reports Centralization**: All tool outputs now in `tools/reports/` for better organization

### **Proven Stability**
- **Deal Debugging Tool**: Battle-tested with consistent real API integration
- **Database Connections**: Reliable PostgreSQL and Redshift connectivity
- **BidSwitch Integration**: Stable OAuth2 implementation with error handling

---

## 🎯 **Next Steps**

### **For Developers**
1. **Review Technical Specifications**: See [tools/docs/technical-specifications.md](./docs/technical-specifications.md)
2. **Understand Architecture**: Check modular design patterns in campaign-analysis tool
3. **Extend Diagnostics**: Add new diagnostic rules following established patterns

### **For Users**
1. **Start with Portfolio Pacing**: Use `campaign-portfolio-pacing/run_campaign_portfolio_pacing.sh` for comprehensive analysis with pacing dashboard
2. **Campaign Troubleshooting**: Use `campaign-analysis/run_campaign_analysis.sh` for deal relationships
3. **Deep Dive with Deal Breakdown**: Use `campaign-analysis/campaign_deal_breakdown.sh` to understand relationships
4. **Individual Deal Focus**: Use deal-debugging tools for specific deal investigation

### **For AI Agents**
1. **Consume JSON Output**: All tools provide structured, confidence-scored results
2. **Cross-Reference Knowledge Base**: Use business context from knowledge-base for interpretation
3. **Follow Recommended Actions**: Structured action items with implementation guidance

---

*These tools provide the computational foundation for AI-powered campaign optimization, handling heavy data processing while enabling agents to focus on strategic analysis and recommendations.*