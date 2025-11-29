# Deal Debugging Tool

## Overview

The Deal Debugging Tool provides detailed diagnostics for individual programmatic deals, focusing on PMP Supply Deals with BidSwitch integration. It serves as the second step in the intelligent monitoring workflow, performing deep debugging on specific deals identified by the Campaign Analysis Tool.

**Key Purpose**: Individual deal diagnostics and troubleshooting - provides actionable fixes for deal-specific issues.

## Quick Start

```bash
# Debug a specific deal
./run_deal_debugging.sh <deal_id>

# Example
./run_deal_debugging.sh 724071955398
```

## Architecture

### Core Components

#### **Main Debugger**: `deal_debugger.py`
- **Purpose**: Orchestrates deal diagnostics using enhanced diagnostic engine
- **Workflow**: Data collection → Pattern debugging → Root cause identification → Recommendations
- **Output**: JSON report with diagnosis, confidence scores, and fix recommendations

#### **Diagnostic Engine**: `enhanced_diagnostics.py`
- **Purpose**: Advanced pattern matching and diagnostic logic
- **Capabilities**: 12+ diagnostic patterns, confidence scoring, root cause debugging
- **Methods**:
  - `EnhancedDealDiagnostics` class with comprehensive debugging
  - Pattern recognition for geo conflicts, performance issues, configuration problems
  - Confidence scoring and severity assessment

#### **API Integration**: `bidswitch_client.py`
- **Purpose**: BidSwitch Deals API integration for real-time deal data
- **Capabilities**: Deal status, performance metrics, geographic breakdown
- **Authentication**: OAuth2 flow with AWS SSO integration

#### **Performance Analysis**: `deal_performance.py`
- **Purpose**: Deal metrics extraction and performance debugging
- **Capabilities**: Bid request/response analysis, win rates, impression tracking

### Shared Dependencies

- **`database_connector.py`**: PostgreSQL access for deal metadata
- **`enhanced_diagnostics.py`**: Diagnostic pattern matching (shared)
- **`bidswitch_client.py`**: API integration (shared)

## Workflow

```
Deal Debugging Tool
├── Step 1: Deal Discovery
│   ├── Fetch deal metadata (PostgreSQL)
│   ├── Get real-time performance (BidSwitch API)
│   └── Validate deal configuration
│
├── Step 2: Diagnostic Analysis
│   ├── Apply 12+ diagnostic patterns
│   ├── Identify root causes with confidence scores
│   └── Assess issue severity and impact
│
├── Step 3: Report Generation
│   ├── Structured diagnosis report
│   ├── Recommended actions with priorities
│   └── Success probability estimates
│
└── Step 4: Agent Integration
    ├── JSON output for agent consumption
    ├── Actionable fix recommendations
    └── Historical pattern context
```

## Usage Examples

### Basic Deal Debugging
```bash
./run_deal_debugging.sh 724071955398
# Output: ../reports/deal_724071955398_analysis.json
```

### Active Deals Discovery
```bash
./list_active_deals.sh
# Output: ../reports/active_deals_<timestamp>.json
```

## Output Format

### Diagnostic Report Structure

```json
{
  "deal_id": "724071955398",
  "analysis_timestamp": "2025-10-25T10:30:00Z",
  "status": "SUCCESS",

  "diagnosis": {
    "primary_issue": "GEOGRAPHIC_TARGETING_MISMATCH",
    "severity": "CRITICAL",
    "confidence": 0.87,
    "description": "Deal targeting conflicts with line item geography",
    "root_cause": "BidSwitch group targets EMEA, line item targets US-only",

    "geographic_analysis": {
      "deal_geography": ["UK", "DE", "FR", "IT", "ES"],
      "line_item_geography": ["US"],
      "conflict_regions": ["UK", "DE", "FR", "IT", "ES"],
      "recommended_action": "remove_supply_side_geo"
    },

    "recommended_actions": [
      {
        "action": "remove_supply_side_geo",
        "description": "Remove geographic targeting from BidSwitch deal group",
        "expected_impact": "60-80% delivery recovery",
        "confidence": 0.85,
        "historical_success_rate": "8/8 similar fixes successful"
      }
    ]
  },

  "deal_metadata": {
    "name": "CTV Premium Inventory - EMEA",
    "ssp": "BidSwitch",
    "status": "ACTIVE",
    "floor_price": 4.50,
    "creative_type": "CTV"
  },

  "performance_metrics": {
    "bid_requests": 125000,
    "bid_responses": 89000,
    "impressions": 21000,
    "win_rate": 0.24,
    "sell_through_rate": 0.19
  }
}
```

## What It Diagnoses

### BidSwitch Integration Issues
- **Deal Status Problems**: Inactive, paused, rejected deals
- **Authentication Failures**: API credential or permission issues
- **Rate Limiting**: BidSwitch API throttling detection

### Geographic Targeting Conflicts
- **Geo Mismatches**: Deal geography vs. line item geography conflicts
- **Regional Conflicts**: EMEA vs. US targeting issues
- **Country-level Analysis**: Specific country targeting problems

### Performance Issues
- **Low Win Rates**: Below-threshold win rate detection
- **Zero Traffic**: No bid requests or responses
- **Floor Price Issues**: Bid prices below deal floor

### Configuration Problems
- **Creative Mismatches**: Deal creative type vs. line item requirements
- **Timing Issues**: Deal dates vs. campaign dates
- **Budget Conflicts**: Deal-level budget constraints

## Diagnostic Patterns

### 12+ Built-in Patterns

| Pattern | Description | Severity |
|---------|-------------|----------|
| `DEAL_INACTIVE` | Deal not found in active deals list | CRITICAL |
| `GEOGRAPHIC_TARGETING_MISMATCH` | Geo conflicts between deal and line item | CRITICAL |
| `BID_BELOW_FLOOR` | Bid prices below deal floor price | HIGH |
| `ZERO_BID_RESPONSES` | No bid responses from SSP | HIGH |
| `LOW_WIN_RATE` | Win rate below baseline | MEDIUM |
| `CREATIVE_TYPE_MISMATCH` | Creative format incompatibilities | MEDIUM |
| `DEAL_STATUS_ISSUE` | Unusual deal status conditions | LOW |

### Confidence Scoring

- **90-100%**: High confidence (clear patterns, strong evidence)
- **70-89%**: Medium confidence (multiple indicators, some ambiguity)
- **50-69%**: Low confidence (weak signals, requires human review)
- **<50%**: Insufficient data (inconclusive, needs more information)

## Integration with Campaign Analysis

### Agent Workflow
1. **Campaign Analysis Tool** identifies deals in unhealthy campaigns
2. **Agent** decides which deals need debugging based on campaign context
3. **Deal Debugging Tool** performs deep debugging on selected deals
4. **Agent** applies fixes or escalates based on diagnostic results

### Data Flow
```
Campaign Analysis → Agent → Deal Debugging → Agent → Action
     ↓              ↓           ↓            ↓       ↓
  Deal List     Decision   Diagnosis    Decision  Fix Applied
  (JSON)        Logic      Report       Logic     (BidSwitch)
                Rules      (JSON)       Rules     (PostgreSQL)
```

## Dependencies & Requirements

### System Requirements
- **Python 3.8+** with virtual environment
- **PostgreSQL access** (deal metadata, line items)
- **AWS SSO** (BidSwitch API access required)
- **BidSwitch API credentials** (client ID, OAuth2 setup)

### Package Dependencies
```
psycopg2-binary==2.9.11
boto3==1.40.52
requests==2.32.5
```

### Environment Variables
```bash
# AWS/BidSwitch Integration
AWS_PROFILE=bedrock
BIDSWITCH_CLIENT_ID=your-client-id
BIDSWITCH_CLIENT_SECRET=your-client-secret

# Database
POSTGRES_HOST=your-postgres-host
POSTGRES_DB=bedrock_db
POSTGRES_USER=your-user
```

## Troubleshooting

### Common Issues

#### "Deal not found"
- Verify deal ID exists in BidSwitch
- Check BidSwitch API credentials and permissions
- Confirm deal is active and not paused

#### "API authentication failed"
- Run AWS SSO login: `aws sso login --profile bedrock`
- Verify BidSwitch client credentials
- Check API rate limits and service status

#### "Geographic analysis incomplete"
- Deal may not have geographic targeting configured
- BidSwitch API may not return geo data for this deal
- Check deal configuration in BidSwitch UI

#### "No performance data"
- Deal may be too new (insufficient data)
- Check BidSwitch reporting delays
- Verify deal has been active and receiving traffic

### Debug Mode

Enable detailed logging:
```bash
export DEBUG_MODE=1
./run_deal_debugging.sh <deal_id>
```

### API Considerations

- **Rate Limits**: BidSwitch API has request limits
- **Authentication**: OAuth2 tokens expire, auto-refresh implemented
- **Data Latency**: Performance metrics may have 15-30 minute delays

## Scope Limitations

### PMP Supply Deals Only
- **Supported**: Deals with `sspDealId` pointing to BidSwitch
- **Not Supported**: Open Exchange deals (no external SSP deal)
- **Why**: Requires BidSwitch API for real-time diagnostics

### BidSwitch Dependency
- **Required**: BidSwitch API access for deal status and performance
- **Fallback**: Limited diagnostics using only PostgreSQL data
- **Offline Mode**: Basic validation without API calls

## Technical Details

### API Integration
- **OAuth2 Flow**: AWS SSO → BidSwitch token exchange
- **Endpoints**: Deals API, Performance API, Geographic API
- **Error Handling**: Automatic retries, graceful degradation

### Diagnostic Engine
- **Pattern Matching**: Rule-based analysis with confidence scoring
- **Root Cause Analysis**: Multi-factor issue identification
- **Historical Context**: Success rates based on similar patterns

### Data Sources
```
PostgreSQL → Deal metadata, line item relationships
BidSwitch API → Real-time performance, status, geography
Enhanced Diagnostics → Pattern matching and analysis logic
```

### Performance Optimization
- **API Batching**: Multiple deal queries in single requests
- **Caching**: Deal metadata cached to reduce database load
- **Async Processing**: Non-blocking API calls where possible

## Development & Testing

### Testing with Real Data
```bash
# Test with known active deal
./run_deal_debugging.sh 724071955398

# Test with problematic deal
./run_deal_debugging.sh 549644393850112493
```

### Adding New Diagnostic Patterns
1. Extend `enhanced_diagnostics.py` with new pattern logic
2. Add pattern to diagnostic engine
3. Test with real deal data
4. Update confidence scoring and success rates

### Performance Monitoring
- API call success rates and latency
- Diagnostic accuracy vs. human verification
- Pattern effectiveness and false positive rates

---

*This tool provides the detailed diagnostics needed to fix individual deal issues, complementing the campaign-level oversight provided by the Campaign Analysis Tool.*
