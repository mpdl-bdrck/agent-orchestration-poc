"""
Weekly Budget Forecast Analysis
================================

Main entry point for generating 12-week budget forecast reports.
Analyzes ALL campaigns across ALL accounts by default, with optional filtering.
"""

import argparse
import sys
import os
from datetime import datetime

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "campaign-analysis", "src"))

# Add src directory to path for absolute imports
src_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, src_dir)

from forecast_analyzer import ForecastAnalyzer
from weekly_budget_processor import WeeklyBudgetProcessor
from weekly_forecast_sheets_publisher import WeeklyForecastSheetsPublisher
from utils.config import get_spreadsheet_id
from utils.logging import setup_logger


def main():
    """
    Main entry point for weekly budget forecast tool.
    """
    parser = argparse.ArgumentParser(
        description='Generate 12-week budget forecast (6 weeks past + 6 weeks future)'
    )
    parser.add_argument(
        '--account-id',
        help='Optional account ID filter (defaults to ALL accounts)'
    )
    parser.add_argument(
        '--advertiser-filter',
        help='Optional advertiser filter (e.g., "Lilly")'
    )
    
    args = parser.parse_args()
    
    logger = setup_logger('weekly.budget.forecast')
    
    try:
        print("\n" + "=" * 70)
        print("📊 Weekly Budget Forecast Tool")
        print("=" * 70)
        
        if args.account_id:
            print(f"   Account ID Filter: {args.account_id}")
        else:
            print(f"   Scope: ALL campaigns across ALL accounts")
        
        if args.advertiser_filter:
            print(f"   Advertiser Filter: {args.advertiser_filter}")
        
        # Load spreadsheet ID from config
        print("\n📋 Loading configuration...")
        try:
            spreadsheet_id = get_spreadsheet_id()
            print(f"✅ Spreadsheet ID loaded: {spreadsheet_id[:20]}...")
        except Exception as e:
            print(f"❌ Failed to load spreadsheet ID: {e}")
            return 1
        
        # Initialize components
        print("\n🔧 Initializing components...")
        analyzer = ForecastAnalyzer(args.account_id, args.advertiser_filter)
        processor = WeeklyBudgetProcessor([], args.account_id, args.advertiser_filter)
        publisher = WeeklyForecastSheetsPublisher(spreadsheet_id)
        print("✅ Components initialized")
        
        # Step 1: Discover campaigns
        print("\n📊 STEP 1: Discovering campaigns...")
        print("-" * 70)
        campaigns = analyzer._discover_campaigns()
        print(f"✅ Found {len(campaigns)} campaigns")
        
        if not campaigns:
            print("⚠️  No campaigns found matching criteria")
            return 1
        
        # Update processor with campaigns
        processor.campaigns = campaigns
        
        # Step 2: Collect daily line items
        print("\n📅 STEP 2: Collecting daily line item data...")
        print("-" * 70)
        daily_line_items = analyzer._collect_daily_line_items(campaigns)
        
        if daily_line_items.empty:
            print("⚠️  No daily line item data found")
            return 1
        
        unique_campaigns = daily_line_items['campaign_id'].nunique()
        print(f"✅ Collected {len(daily_line_items)} daily records across {unique_campaigns} campaigns")
        
        # Step 3: Process weekly forecast
        print("\n🔄 STEP 3: Processing weekly budget forecast...")
        print("-" * 70)
        forecast_data = processor.create_weekly_forecast(daily_line_items)
        print(f"✅ Generated forecast for {len(forecast_data)} weeks")
        
        # Step 4: Publish to Google Sheets
        print("\n📤 STEP 4: Publishing to Google Sheets...")
        print("-" * 70)
        success = publisher.publish_weekly_forecast(forecast_data)
        
        if success:
            print("\n" + "=" * 70)
            print("✅ Weekly budget forecast published successfully!")
            print("=" * 70)
            print(f"📊 Campaigns analyzed: {len(campaigns)}")
            print(f"📅 Date range: 6 weeks past + 6 weeks future")
            print(f"📈 Weeks in forecast: {len(forecast_data)}")
            print(f"📋 Spreadsheet: {spreadsheet_id}")
            return 0
        else:
            print("\n❌ Failed to publish weekly budget forecast")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

