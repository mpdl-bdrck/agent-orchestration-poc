# Weekly Budget Forecast Tool

Generates 12-week budget forecast reports (6 weeks past + 6 weeks future) showing weekly spend, budget allocation, and forecasted spend.

## Overview

This tool analyzes **ALL campaigns across ALL accounts** by default and generates a comprehensive weekly budget forecast report. The report includes:

- **Past 6 weeks**: Actual spend and budget allocated
- **Future 6 weeks**: Budget allocated (prorated) and forecast spend (based on historical pacing)

## Features

- **Budget Allocation (Option B: Prorated)**: Distributes remaining campaign budgets across future weeks based on campaign duration, respecting end dates
- **Spend Forecasting (Option C: Historical Pacing)**: Projects future spend based on actual spend rates from the past 6 weeks
- **Weekly Aggregation**: Aggregates daily spend data into weekly totals (Monday-Sunday, ISO week)
- **Company-Wide Analysis**: Analyzes all campaigns by default, with optional filtering

## Usage

### Basic Usage (All Campaigns)

```bash
./run_weekly_budget_forecast.sh
```

### With Account Filter

```bash
./run_weekly_budget_forecast.sh 17
```

### With Account and Advertiser Filter

```bash
./run_weekly_budget_forecast.sh 17 "Lilly"
```

### Using Python Directly

```bash
python3 src/weekly_budget_forecast_analysis.py
python3 src/weekly_budget_forecast_analysis.py --account-id 17
python3 src/weekly_budget_forecast_analysis.py --account-id 17 --advertiser-filter "Lilly"
```

## Configuration

The tool uses `config.json` for configuration:

```json
{
  "default_timezone": "UTC",
  "default_date_format": "YYYY-MM-DD",
  "spreadsheet_id": "1psKu2Qfo4t0n2OJg8bd_S5RVwJmg49tRUfiuMoLks38"
}
```

## Output

The tool publishes a report to Google Sheets with the following structure:

| Week Start Date | Week End Date | Past Spend | Budget Allocated | Forecast Spend |
|----------------|---------------|------------|------------------|----------------|
| 2024-12-02     | 2024-12-08    | $45,230    | $50,000         | -              |
| 2024-12-09     | 2024-12-15    | $48,500    | $50,000         | -              |
| ...            | ...           | ...        | ...              | ...            |
| 2025-01-13     | 2025-01-19    | -          | $48,500         | $47,500        |
| 2025-01-20     | 2025-01-26    | -          | $48,500         | $47,500        |

- **Past weeks**: Show actual spend and budget allocated
- **Future weeks**: Show budget allocated (prorated) and forecast spend (historical pacing)

## Architecture

### Components

1. **ForecastAnalyzer**: Discovers campaigns and collects daily line item data
2. **WeeklyBudgetProcessor**: Orchestrates weekly aggregation and forecasting
3. **BudgetAllocator**: Allocates remaining budgets using Option B (Prorated)
4. **SpendForecaster**: Forecasts future spend using Option C (Historical Pacing)
5. **WeeklyForecastSheetsPublisher**: Publishes results to Google Sheets

### Data Flow

1. Discover campaigns (with optional account/advertiser filtering)
2. Collect daily line item data for 6 weeks past + 6 weeks future
3. Aggregate past weeks: daily spend → weekly totals
4. Calculate past weeks budget: sum campaign budgets active each week
5. Allocate future weeks budget: prorated by campaign duration
6. Forecast future weeks spend: based on historical pacing
7. Publish to Google Sheets

## Requirements

- Python 3.8+
- Google Sheets API credentials (`credentials/bdrck-gsheets-key.json`)
- Database access (PostgreSQL for metadata, Redshift for performance data)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure credentials are in place
# credentials/bdrck-gsheets-key.json
```

## Notes

- All date calculations use UTC
- Week boundaries are Monday-Sunday (ISO week)
- Campaign end dates are respected (no allocation after end)
- Forecasts are capped at remaining budget allocation

