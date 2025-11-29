#!/usr/bin/env python3
"""
Simple standalone script to publish CSV files to Google Sheets.
Usage: python publish_csvs_to_sheets.py /path/to/rollups/directory
"""

import os
import sys
import csv

# Add the tool directory to path so we can import src modules
tool_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, tool_dir)

# Import from src package
from src.google.sheets import write_values
from src.utils.config import initialize_config, config

def read_csv_to_list(csv_path):
    """Read CSV file and return as list of lists."""
    with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        return list(reader)

def publish_csv(csv_path, worksheet_name):
    """Publish a single CSV file to Google Sheets."""
    try:
        # Read the CSV
        data = read_csv_to_list(csv_path)
        
        if not data:
            print(f"❌ CSV file {csv_path} is empty")
            return False
        
        # Get spreadsheet ID
        spreadsheet_id = config.get('google_sheets', 'default_spreadsheet_id')
        if not spreadsheet_id:
            print("❌ No spreadsheet ID configured")
            return False
        
        # Create range name for the worksheet
        range_name = f'{worksheet_name}!A1'
        
        # Write to Google Sheets
        result = write_values(spreadsheet_id, range_name, data)
        
        print(f"✅ Published {len(data)-1} rows from {csv_path} to worksheet '{worksheet_name}'")
        return True
        
    except Exception as e:
        print(f"❌ Failed to publish {csv_path} to worksheet '{worksheet_name}': {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python publish_csvs_to_sheets.py /path/to/rollups/directory")
        print("Example: python publish_csvs_to_sheets.py ../reports/rollups/17_20251118_221746")
        sys.exit(1)
    
    rollups_dir = sys.argv[1]
    
    if not os.path.exists(rollups_dir):
        print(f"❌ Directory {rollups_dir} does not exist")
        sys.exit(1)
    
    # Initialize config
    initialize_config()
    
    # Define the rollup files we expect
    rollup_files = [
        ('line_items_daily.csv', 'Line Items DAILY'),
        ('line_items_total.csv', 'Line Items TOTAL'),
        ('campaigns_daily.csv', 'Campaigns DAILY'),
        ('campaigns_total.csv', 'Campaigns TOTAL'),
        ('portfolio_daily.csv', 'Portfolio DAILY'),
        ('portfolio_total.csv', 'Portfolio TOTAL'),
    ]
    
    success_count = 0
    total_count = 0
    
    print(f"🚀 Publishing rollup CSVs from: {rollups_dir}")
    print("=" * 80)
    
    for csv_filename, worksheet_name in rollup_files:
        csv_path = os.path.join(rollups_dir, csv_filename)
        
        if not os.path.exists(csv_path):
            print(f"⚠️  Skipping {csv_filename} - file not found")
            continue
        
        total_count += 1
        print(f"\n📊 Publishing {csv_filename} to worksheet '{worksheet_name}'...")
        
        if publish_csv(csv_path, worksheet_name):
            success_count += 1
        else:
            print("   Failed - see error above")
    
    print("\n" + "=" * 80)
    print(f"📈 Published {success_count}/{total_count} rollup files successfully")
    
    if success_count > 0:
        spreadsheet_id = config.get('google_sheets', 'default_spreadsheet_id')
        print(f"🔗 View results at: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

