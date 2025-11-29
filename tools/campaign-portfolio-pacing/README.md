# Campaign Portfolio Pacing Tool

A comprehensive tool for analyzing campaign performance and providing actionable portfolio-level pacing intelligence. Generates detailed rollup reports and creates intuitive pacing dashboards that help campaign managers understand their spend velocity and adjust strategies in real-time.

## Overview

The Campaign Portfolio Pacing Tool analyzes advertising campaign data to provide actionable insights about spend performance, pacing status, and required adjustments. It transforms raw campaign data into clear, actionable metrics that answer the key question: **"Are we on track to hit our budget goals, and if not, what do we need to do?"**

## Features

### 📊 Data Analysis & Rollups
- **Multi-level Aggregation**: Processes line item data into comprehensive rollups
  - Line Items DAILY/TOTAL: Individual creative performance
  - Campaigns DAILY/TOTAL: Campaign-level aggregation
  - Portfolio DAILY/TOTAL: Account-wide portfolio view
- **Automated Data Cleaning**: Removes common prefixes and standardizes naming
- **Date Range Analysis**: Configurable analysis periods with flexible date handling

### 📈 Google Sheets Integration
- **Automated Publishing**: Publishes 6 comprehensive worksheets to Google Sheets
- **Real-time Updates**: Data refreshes automatically as campaigns run
- **Collaborative Access**: Team members can view and analyze data simultaneously

### 🎯 Portfolio Pacing Dashboard
- **Timeline Tracking**: Clear view of campaign duration and progress
- **Budget Monitoring**: Side-by-side comparison of actual vs. target spend
- **Daily Rate Analysis**: Target, actual, and required daily spending rates
- **Visual Status Indicators**: Color-coded pacing status (🟢 AHEAD / 🟡 ON PACE / 🔴 BEHIND)

## Dashboard Structure

### 📅 CAMPAIGN PORTFOLIO TIMELINE
```
Start Date          01/11/2025
End Date           31/12/2025
Today              21/11/2025
Total Days         60
Days Passed        20
Days Left          40
```

### 💰 BUDGET STATUS
```
Campaign Budget     $466,000
Budget Used         $107,174    ← Actual spend to date
Should Have Spent   $155,333    ← Target cumulative spend
Budget Remaining    $358,826
```

### 📊 DAILY PACING
```
Target Daily Rate   $7,767      ← Budget ÷ Total Days
Actual Daily Rate   $5,359      ← Spend ÷ Days Passed
Required Daily Rate $8,971      ← Remaining ÷ Days Left
Pacing Status       🔴 BEHIND
```

## Usage

### **📊 Data Refresh** - Update all sheets except Summary
```bash
# Refresh all data rollups (Line Items, Campaigns, Portfolio sheets)
# Summary sheet stays unchanged (formulas pull from these sheets)
./run_campaign_portfolio_pacing.sh 17 "Lilly" --publish-sheets

# With custom date range
./run_campaign_portfolio_pacing.sh 17 "Lilly" --publish-sheets \
  --start-date 2025-11-01 --end-date 2025-11-15

# With timezone override (PST)
./run_campaign_portfolio_pacing.sh 17 "Lilly" --publish-sheets \
  --timezone PST

# With timezone override (UTC)
./run_campaign_portfolio_pacing.sh 17 "Lilly" --publish-sheets \
  --timezone UTC
```

### **🎯 Summary Dashboard Update** - Update Summary design/formulas only
```bash
# Update pacing dashboard layout/formulas (no data reprocessing)
./update_summary.sh --campaign-start 2025-11-01 --campaign-end 2025-12-31 --campaign-budget 466000

# Or update existing dashboard with new budget
./update_summary.sh --campaign-budget 500000
```

### **🚀 Full Workflow** - Initial setup with data + dashboard
```bash
# First time: Create data rollups AND pacing dashboard
./run_campaign_portfolio_pacing.sh 17 "Lilly" --publish-sheets \
  --campaign-start 2025-11-01 --campaign-end 2025-12-31 --campaign-budget 466000

# Ongoing: Refresh data only (Summary updates automatically)
./run_campaign_portfolio_pacing.sh 17 "Lilly" --publish-sheets

# When needed: Update Summary design/formulas
./update_summary.sh --campaign-budget [new_budget]
```

### **Workflow Summary**
- **Daily/Weekly**: Use `./run_campaign_portfolio_pacing.sh --publish-sheets` to refresh data
- **After Dashboard Changes**: Use `./update_summary.sh` to update Summary worksheet
- **Initial Setup**: Use full command with campaign parameters

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--start-date YYYY-MM-DD` | Analysis start date | 2025-11-01 |
| `--end-date YYYY-MM-DD` | Analysis end date | Today |
| `--timezone TZ` | Override timezone (UTC, PST, PDT, EST, EDT, or full timezone name) | Client config default (usually PST) |
| `--publish-sheets` | Publish rollups to Google Sheets | Disabled |
| `--campaign-start DATE` | Campaign start date for pacing | 2025-11-01 |
| `--campaign-end DATE` | Campaign end date for pacing | 2025-12-31 |
| `--campaign-budget AMOUNT` | Total campaign budget | 466000 |
| `--extract-formulas SHEET` | Extract formulas from worksheet | N/A |

### Timezone Handling

The tool automatically detects the client's timezone from the client configuration file. You can override this using the `--timezone` parameter.

**Supported Timezone Formats:**
- **Abbreviations**: `UTC`, `PST`, `PDT`, `EST`, `EDT`
- **Full timezone names**: `America/Los_Angeles`, `America/New_York`, etc.

**How Timezone Conversion Works:**

1. **PST/PDT Timezone (Default for Tricoast Media LLC)**:
   - Uses hourly data from `overview` table
   - SQL `CONVERT_TIMEZONE` function converts UTC timestamps to PST timestamps
   - Properly redistributes hours across PST date boundaries
   - Example: Nov 26 UTC hours (00:00-23:59 UTC) are split between Nov 25 PST (16:00-23:59) and Nov 26 PST (00:00-15:59)
   - Python only filters future dates (dates > today in PST)

2. **UTC Timezone**:
   - Uses daily aggregates from `overview_view` table
   - No timezone conversion needed (data is already in UTC)
   - Python filters future dates (dates > today in UTC)

**Examples:**
```bash
# Use PST timezone (default for Tricoast)
./run_campaign_portfolio_pacing.sh 17 "Lilly" --timezone PST

# Use UTC timezone
./run_campaign_portfolio_pacing.sh 17 "Lilly" --timezone UTC

# Use full timezone name
./run_campaign_portfolio_pacing.sh 17 "Lilly" --timezone "America/Los_Angeles"
```

**Important Notes:**
- When using PST timezone, the tool queries hourly data to properly redistribute spend/impressions across timezone boundaries
- UTC timezone uses daily aggregates (faster, but no hour-level redistribution)
- The tool automatically filters out future dates based on the selected timezone's "today"

## Key Metrics Explained

### Timeline Metrics
- **Total Days**: Campaign duration
- **Days Passed**: Elapsed campaign time
- **Days Left**: Remaining campaign time

### Budget Metrics
- **Campaign Budget**: Total allocated budget
- **Budget Used**: Actual spend to date
- **Should Have Spent**: Target cumulative spend (Budget × Progress %)
- **Budget Remaining**: Unspent budget

### Pacing Metrics
- **Target Daily Rate**: Budget ÷ Total Days (ideal daily spend)
- **Actual Daily Rate**: Budget Used ÷ Days Passed (current daily average)
- **Required Daily Rate**: Budget Remaining ÷ Days Left (needed to hit target)
- **Pacing Status**: Visual indicator based on actual vs target rates

## Data Sources

### Input Data
- **PostgreSQL**: Campaign metadata, advertiser information
- **Redshift**: Daily line item performance data (spend, impressions)
- **Configuration**: Budget amounts, date ranges

### Output Formats
- **CSV Files**: Detailed rollup reports in `/reports` directory
- **Google Sheets**: Interactive dashboard with real-time formulas
- **Console Output**: Progress indicators and summary statistics

## Architecture

### Core Components
- `campaign_analyzer.py`: Main analysis orchestration
- `data_rollup_processor.py`: Data aggregation and rollup generation
- `sheets_publisher.py`: Google Sheets integration
- `summary.py`: Pacing dashboard generation

### Shared Modules
- `formula_extractor.py`: Extract existing formulas from sheets
- `formula_generator.py`: Generate dashboard formulas
- `formula_applicator.py`: Apply formulas to worksheets
- `dashboard_formatter.py`: Format and style dashboards

## Requirements

### System Dependencies
- Python 3.8+
- AWS CLI configured with SSO
- Google Cloud Service Account with Sheets API access

### Python Packages
- pandas: Data processing and analysis
- google-api-python-client: Google Sheets integration
- psycopg2: PostgreSQL connectivity
- sqlalchemy: Database ORM
- boto3: AWS integration

## Configuration

### Environment Variables
```bash
# Database connections
DB_HOST=your-postgres-host
DB_NAME=your-database
REDSHIFT_HOST=your-redshift-host

# Google Sheets
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
DEFAULT_SPREADSHEET_ID=your-google-sheet-id
```

### Budget Configuration
Campaign budgets are configured per account in the application logic. Contact the development team to add new campaign budgets.

## Troubleshooting

### Common Issues

**"Module not found" errors**
- Ensure virtual environment is activated: `source ../venv/bin/activate`
- Check Python path setup in scripts

**Google Sheets authentication failures**
- Verify service account credentials are properly configured
- Check Google Sheets API is enabled in Google Cloud Console
- Ensure spreadsheet sharing permissions allow service account access

**Database connection issues**
- Verify AWS SSO login: `aws sso login`
- Check database credentials and network connectivity
- Confirm Redshift cluster is available

**Empty or incorrect data**
- Verify date ranges cover actual campaign data
- Check advertiser filter matches campaign naming conventions
- Review data cleaning logic for campaign name prefixes

**Timezone conversion issues**
- Run the timezone test script: `python test_timezone_conversion.py`
- Verify client config has correct timezone settings
- Check that hourly data is available in `overview` table (for PST timezone)
- Ensure dates are not showing future dates (should filter by timezone's "today")

### Debug Mode
Enable verbose logging by modifying the script's logging configuration.

### Timezone Diagnostics
If you encounter timezone-related issues, use the timezone conversion test script:

```bash
cd tools/campaign-portfolio-pacing
../venv/bin/python test_timezone_conversion.py
```

This will:
- Show what dates are queried from Redshift
- Show how dates are converted
- Validate proper hour redistribution for PST timezone
- Provide recommendations on which approach to use

## Development

### Code Structure
```
campaign-portfolio-pacing/
├── src/                    # Main application code
│   ├── campaign_analyzer.py    # Main analysis logic
│   ├── data_rollup_processor.py # Data aggregation
│   ├── sheets_publisher.py     # Google Sheets integration
│   └── utils/                 # Utility functions
├── run_campaign_portfolio_pacing.sh  # Main execution script
├── update_summary.sh         # Dashboard update script
├── extract_portfolio_formulas.py  # Formula extraction tool
└── test_timezone_conversion.py  # Timezone conversion test suite
```

### Testing

**Unit Tests:**
```bash
python -m pytest tests/
```

**Timezone Conversion Testing:**
The tool includes a comprehensive timezone conversion test script that validates the timezone handling logic:

```bash
# Run timezone conversion tests
cd tools/campaign-portfolio-pacing
../venv/bin/python test_timezone_conversion.py
```

This test script:
- Tests UTC timezone mode (daily aggregates)
- Tests PST timezone mode (hourly data with SQL conversion)
- Validates that hourly data properly redistributes across PST date boundaries
- Compares Python conversion vs SQL conversion approaches
- Provides detailed diagnostics and recommendations

**What the Test Validates:**
1. ✅ UTC mode returns correct UTC dates
2. ✅ PST mode properly redistributes UTC hours across PST dates
3. ✅ Hourly SQL approach correctly splits Nov 26 UTC across Nov 24 and Nov 25 PST
4. ✅ Daily aggregates approach only relabels dates (doesn't redistribute)
5. ✅ Future dates are correctly filtered based on timezone's "today"

**Test Output:**
The test provides detailed output showing:
- Date distribution comparisons
- Total spend/impressions by approach
- Evidence of proper hour redistribution
- Clear recommendations on which approach to use

### Contributing
1. Follow the existing code style and patterns
2. Add comprehensive docstrings
3. Include unit tests for new functionality
4. Update this README for any new features

## Support

For issues, questions, or feature requests:
1. Check this README for common solutions
2. Review recent changes in commit history
3. Create an issue with detailed reproduction steps
4. Include relevant log output and error messages

## License

Internal tool - All rights reserved.