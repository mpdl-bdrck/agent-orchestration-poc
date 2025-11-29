#!/usr/bin/env python3
"""
Lightweight script to update only the Summary dashboard worksheet.

Usage:
    python update_summary_dashboard.py --spreadsheet-id <ID> --campaign-start 2025-11-01 --campaign-end 2025-12-31 --campaign-budget 466000
"""

import os
import sys
import argparse

# Set up paths for shared modules
script_dir = os.path.dirname(os.path.abspath(__file__))
# Script is in tools/campaign-spend-analysis/, so go up one level to tools/, then to shared
tools_dir = os.path.join(script_dir, "..")
shared_path = os.path.join(tools_dir, "shared")
src_path = os.path.join(script_dir, "src")
sys.path.insert(0, shared_path)
sys.path.insert(0, src_path)

from sheets import get_summary_manager, get_sheets_service  # type: ignore
from utils.config import initialize_config, config  # type: ignore


def main():
    # Initialize config to get default spreadsheet ID
    initialize_config()
    
    default_spreadsheet_id = config.get('google_sheets', 'default_spreadsheet_id', '1syJFthysZXZKAyDiv-O-dDGawE7ZZqXyI08WmY4Pcoc')
    
    parser = argparse.ArgumentParser(description='Update Summary dashboard worksheet only')
    parser.add_argument('--spreadsheet-id', default=default_spreadsheet_id, help=f'Google Sheets spreadsheet ID (default: {default_spreadsheet_id})')
    parser.add_argument('--campaign-start', required=True, help='Campaign start date (YYYY-MM-DD)')
    parser.add_argument('--campaign-end', required=True, help='Campaign end date (YYYY-MM-DD)')
    parser.add_argument('--campaign-budget', type=float, required=True, help='Total campaign budget')

    args = parser.parse_args()

    print("🔄 Updating Summary dashboard...")
    print(f"   📅 Start: {args.campaign_start}")
    print(f"   📅 End: {args.campaign_end}")
    print(f"   💰 Budget: {args.campaign_budget}")

    try:
        # Get services
        sheets_service = get_sheets_service()
        summary_mgr = get_summary_manager(sheets_service)

        # Prepare campaign config
        campaign_config = {
            'start_date': args.campaign_start,
            'end_date': args.campaign_end,
            'budget': args.campaign_budget
        }

        # Get rollup sheet names (hardcoded for now, could be made configurable)
        rollup_sheets = [
            'Line Items DAILY',
            'Line Items TOTAL',
            'Campaigns DAILY',
            'Campaigns TOTAL',
            'Portfolio DAILY',
            'Portfolio TOTAL'
        ]

        # Update the dashboard
        success = summary_mgr.create_pacing_dashboard(
            spreadsheet_id=args.spreadsheet_id,
            campaign_config=campaign_config,
            rollup_sheets=rollup_sheets
        )

        if success:
            print("✅ Summary dashboard updated successfully!")
            print(f"   🔗 View: https://docs.google.com/spreadsheets/d/{args.spreadsheet_id}/edit#gid=6")
            return 0
        else:
            print("⚠️  Dashboard update had some issues (check logs)")
            return 1

    except Exception as e:
        print(f"❌ Error updating dashboard: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

