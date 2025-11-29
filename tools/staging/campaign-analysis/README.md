# Campaign Analysis Tool

## Overview

The Campaign Analysis Tool provides comprehensive campaign health assessment and deal identification for programmatic advertising campaigns. It serves as the first step in the intelligent monitoring workflow, identifying which deals an agent should debug individually.

**Key Purpose**: Campaign-level diagnostics without individual deal analysis - provides context for downstream deal debugging.

## Quick Start

```bash
# Basic campaign analysis
./run_campaign_analysis.sh <campaign_id>

# Example
./run_campaign_analysis.sh 89
```

## Architecture

### Core Components

#### **Main Orchestrator**: `campaign_analyzer.py`
- **4-step workflow**: Discovery → Structure Analysis → Diagnostics → Agent Report
- **Purpose**: Coordinates all analysis components
- **Output**: Agent-ready JSON report with deal identification

#### **Data Collector**: `campaign_discovery.py`
- **Purpose**: Fetches campaign data from databases
- **Sources**: PostgreSQL (campaign metadata), Redshift (spend data)
- **Methods**:
  - `get_campaign_info()` → Campaign status, budget, dates
  - `discover_deals()` → Deal relationships for the campaign
  - `get_spend_data()` → Budget vs. spend analysis

#### **Health Checker**: `campaign_diagnostics.py`
- **Purpose**: Campaign-level diagnostic checks (no individual deal analysis)
- **Focus**: Campaign status, dates, structure, configuration issues
- **Methods**:
  - `check_campaign_level_issues()` → Campaign-specific problems
  - `calculate_campaign_health()` → CRITICAL/WARNING/HEALTHY scoring
  - `generate_recommendations()` → Actionable fixes

#### **Structure Analyzer**: `campaign_deal_breakdown.py`
- **Purpose**: Maps relationships between campaigns, line items, packages, and deals
- **Focus**: Explains deal duplication and many-to-many relationships
- **Methods**:
  - `analyze_campaign_structure()` → Complete relationship mapping

### Shared Dependencies

- **`database_connector.py`**: PostgreSQL/Redshift database access
- **`bidswitch_client.py`**: SSP API integration for deal status checks
- **`deal_performance.py`**: Deal metrics extraction utilities
- **`enhanced_diagnostics.py`**: Diagnostic pattern matching logic

## Workflow

```
Campaign Analysis Tool
├── Step 1: Discovery
│   ├── Get campaign metadata (PostgreSQL)
│   ├── Discover deal relationships (PostgreSQL)
│   └── Fetch spend data (Redshift)
│
├── Step 2: Structure Analysis
│   ├── Map line items → curation packages → deals
│   ├── Calculate duplication factors
│   └── Identify unique deals vs. relationships
│
├── Step 3: Health Diagnostics
│   ├── Check campaign status/issues
│   ├── Validate dates and configuration
│   └── Assess overall campaign health
│
└── Step 4: Agent Report Generation
    ├── List unique deals for debugging
    ├── Provide campaign health assessment
    └── Generate actionable recommendations
```

## Usage Examples

### Basic Campaign Analysis
```bash
./run_campaign_analysis.sh 89
# Output: ../reports/campaign_89_analysis.json
```

### Understanding Campaign Structure
```bash
./campaign_deal_breakdown.sh 89
# Output: ../reports/campaign_89_deal_breakdown.json
# Focus: Relationship mapping and duplication analysis
```

## Output Format

### Agent-Ready Report Structure

```json
{
  "campaign_id": 89,
  "campaign_name": "GBS - July - Aug - Sept 25 - Display",
  "campaign_health": "HEALTHY",
  "analysis_timestamp": "2025-10-25T10:30:00Z",

  "unique_deals": ["deal_123", "deal_456", "deal_789"],
  "deal_relationships": [
    {
      "deal_id": "deal_123",
      "package_name": "CTV Premium",
      "line_item_count": 3,
      "ssp": "BidSwitch"
    }
  ],
  "total_relationships": 57,
  "duplication_factor": 1.9,

  "campaign_structure": {
    "total_line_items": 17,
    "total_packages": 8,
    "ssp_breakdown": {
      "Pubmatic": 26,
      "Google AdX": 1,
      "Criteo": 2
    }
  },

  "campaign_issues": [
    {
      "pattern": "CAMPAIGN_DATES_INVALID",
      "severity": "MEDIUM",
      "description": "Campaign dates misaligned with line items"
    }
  ],

  "agent_guidance": {
    "campaign_ready_for_deal_debugging": true,
    "deals_needing_attention": ["deal_123"],
    "recommended_next_steps": ["Campaign healthy - proceed with targeted deal debugging"]
  },

  "campaign_data": {
    "budget": 50000.00,
    "start_date": "2025-07-01",
    "end_date": "2025-09-30",
    "status_name": "Active"
  },

  "spend_analysis": {
    "total_spent": 12500.00,
    "budget_utilization": 0.25
  },

  "recommended_actions": [
    "Campaign healthy - proceed with targeted deal debugging"
  ]
}
```

## What It Analyzes

### Campaign Structure Analysis
- **Basic campaign information**: Budget, dates, status, configuration
- **Line item mapping**: All line items within the campaign
- **Curation package relationships**: Which packages each line item uses
- **Deal relationship mapping**: How deals connect to packages and line items

### Relationship Mapping
- **Line Items → Curation Packages**: Package assignments per line item
- **Curation Packages → Deals**: Deal composition of each package
- **Deals → SSPs**: Supply-side platform identification
- **Cross-references**: How deals appear across multiple line items/packages

### Duplication Analysis
- **Frequency tracking**: How often each deal appears
- **Duplication ratios**: Total relationships vs. unique deals
- **Impact assessment**: Which deals affect most line items

### Campaign Health Diagnostics
- **Status validation**: Active/inactive/paused campaign states
- **Date verification**: Campaign vs. line item date alignment
- **Configuration checks**: Package and deal setup validation
- **Budget monitoring**: Spend vs. budget analysis

## Why This Matters

### Understanding Programmatic Complexity

In programmatic advertising, the same deal often appears multiple times:

**Example Campaign 89**:
- **30 unique deals** across the campaign
- **57 total relationships** (line item + package combinations)
- **1.9x duplication factor** (57 ÷ 30)

**Why this happens**:
- Multiple line items targeting the same audience segments
- Same inventory used for different campaign objectives
- Curation packages bundling deals across line items

### Agent Workflow Integration

**Campaign Analysis Tool** = **Context Provider**
- Identifies campaign health status
- Lists which deals exist in the campaign
- Provides structural understanding

**Deal Debugging Tool** = **Detail Specialist**
- Takes individual deal IDs from campaign analysis
- Performs deep diagnostics on specific deals
- Provides fix recommendations

**Combined Workflow**:
1. Campaign Analysis: "This campaign has 30 deals, health is GOOD"
2. Agent Decision: "Debug these 5 deals that might have issues"
3. Deal Debugging: "Deal 123 has geographic mismatch - fix targeting"

## Dependencies & Requirements

### System Requirements
- **Python 3.8+** with virtual environment
- **PostgreSQL access** (campaign metadata, line items, packages)
- **Redshift access** (spend data, optional)
- **AWS SSO** (BidSwitch API integration)

### Package Dependencies
```
psycopg2-binary==2.9.11
boto3==1.40.52
requests==2.32.5
```

### Environment Variables
```bash
# Database connections
POSTGRES_HOST=your-postgres-host
POSTGRES_DB=bedrock_db
POSTGRES_USER=your-user

# AWS/BidSwitch
AWS_PROFILE=bedrock
BIDSWITCH_CLIENT_ID=your-client-id
```

## Troubleshooting

### Common Issues

#### "Campaign not found"
- Verify campaign ID exists in PostgreSQL
- Check database connection and permissions
- Confirm campaign is not archived

#### "No deal relationships"
- Campaign may have no active line items
- Check curation package assignments
- Verify deal configurations

#### "AWS SSO authentication failed"
- Run `aws sso login --profile bedrock`
- Verify AWS profile configuration
- Check BidSwitch API credentials

#### "Database connection timeout"
- Verify network connectivity
- Check database server status
- Confirm connection pool limits

### Debug Mode

Enable verbose logging:
```bash
export DEBUG_MODE=1
./run_campaign_analysis.sh <campaign_id>
```

### Performance Considerations

- **Large campaigns**: Analysis time scales with deal count
- **Database load**: Uses read-only queries, minimal impact
- **API calls**: BidSwitch requests limited to avoid rate limits

## Integration with Other Tools

### Deal Debugging Tool
```python
# Campaign analysis provides deal list for debugging
campaign_report = campaign_analysis(campaign_id)
deal_ids_to_debug = campaign_report['agent_guidance']['deals_needing_attention']

for deal_id in deal_ids_to_debug:
    debug_result = deal_debugging(deal_id)
    # Apply fixes based on debug results
```

### Agent Workflow
1. **Campaign Analysis**: Get campaign context and deal list
2. **Agent Decision**: Determine which deals need attention
3. **Deal Debugging**: Perform detailed analysis on selected deals
4. **Action Execution**: Apply fixes based on combined insights

## Technical Details

### Database Queries
- **Campaign metadata**: Single query with JOINs
- **Deal relationships**: Complex multi-table JOINs
- **Spend analysis**: Redshift aggregation queries
- **Performance**: Optimized with proper indexing

### Data Flow
```
PostgreSQL → Campaign Discovery → campaign_analyzer.py
Redshift   → Spend Analysis    → campaign_analyzer.py
BidSwitch → Deal Status       → campaign_analyzer.py (via discovery)
```

### Error Handling
- **Database failures**: Graceful degradation, partial results
- **API timeouts**: Continues with available data
- **Invalid campaigns**: Clear error messages with suggestions

### Output Validation
- **JSON schema validation**: Ensures agent-ready format
- **Data consistency checks**: Validates relationships
- **Completeness verification**: Confirms all expected data present

## Development & Testing

### Running Tests
```bash
cd src/
python -m pytest test_*.py -v
```

### Adding New Diagnostics
1. Extend `campaign_diagnostics.py` with new check methods
2. Update `check_campaign_level_issues()` to include new checks
3. Test with real campaign data
4. Update this documentation

### Performance Monitoring
- Campaign analysis time tracking
- Database query performance metrics
- API call success rates
- Memory usage monitoring

---

*This tool provides the foundation for intelligent campaign monitoring, enabling agents to make informed decisions about which deals require individual attention.*
