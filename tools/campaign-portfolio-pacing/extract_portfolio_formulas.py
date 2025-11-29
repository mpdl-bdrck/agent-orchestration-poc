#!/usr/bin/env python3
"""
Extract formulas from Portfolio DAILY worksheet to understand user requirements.
"""

import os
import sys

# Add shared modules to path
script_dir = os.path.dirname(os.path.abspath(__file__))
shared_path = os.path.join(script_dir, "..", "shared")
sys.path.insert(0, shared_path)

# Also add the local src directory for other imports
src_path = os.path.join(script_dir, "src")
sys.path.insert(0, src_path)

from sheets.credentials import get_sheets_service
from sheets.formula_extractor import FormulaExtractor
from utils.config import initialize_config, config

def main():
    """Extract formulas from specified worksheet."""

    if len(sys.argv) != 2:
        print("Usage: python extract_portfolio_formulas.py <worksheet_name>")
        sys.exit(1)

    sheet_name = sys.argv[1]

    # Initialize configuration (loads config.json)
    initialize_config()

    spreadsheet_id = config.get('google_sheets', 'default_spreadsheet_id')

    print(f"🔍 Extracting formulas from {sheet_name} worksheet...")
    print(f"📊 Spreadsheet ID: {spreadsheet_id}")
    print()

    try:
        # Get authenticated service
        service = get_sheets_service()

        # Create formula extractor
        extractor = FormulaExtractor(service)

        # Extract formulas
        print("📝 Extracting formulas...")
        print(f"🔍 Checking if sheet '{sheet_name}' exists...")
        try:
            sheet_id = extractor.get_sheet_id_by_name(spreadsheet_id, sheet_name)
            print(f"✅ Sheet ID: {sheet_id}")
        except Exception as e:
            print(f"❌ Error getting sheet ID: {e}")
            return

        formulas = extractor.extract_formulas(spreadsheet_id, sheet_name, "A:ZZ")  # Expanded range

        print(f"✅ Found {len(formulas)} formulas in {sheet_name}:")
        print("=" * 60)

        # Analyze formulas by column
        tool_formulas = {}
        user_formulas = {}

        for cell_ref, formula in formulas.items():
            col_letter = cell_ref.rstrip('0123456789')
            col_idx = ord(col_letter.upper()) - ord('A')

            if col_idx < 5:  # A-E: tool columns
                if col_letter not in tool_formulas:
                    tool_formulas[col_letter] = []
                tool_formulas[col_letter].append(f"{cell_ref}: {formula}")
            else:  # F+: user columns
                if col_letter not in user_formulas:
                    user_formulas[col_letter] = []
                user_formulas[col_letter].append(f"{cell_ref}: {formula}")

        if not formulas:
            print("⚠️  No formulas found in the worksheet")
            print("💡 This might mean the user is using hardcoded values or manual calculations")
        else:
            print(f"✅ Found {len(formulas)} total formulas:")
            if tool_formulas:
                print(f"   🤖 Tool column formulas (A-E): {len([f for formulas_list in tool_formulas.values() for f in formulas_list])}")
                for col, formulas_list in tool_formulas.items():
                    print(f"      {col}: {len(formulas_list)} formulas")
            if user_formulas:
                print(f"   👤 User column formulas (F+): {len([f for formulas_list in user_formulas.values() for f in formulas_list])}")
                for col, formulas_list in user_formulas.items():
                    print(f"      {col}: {len(formulas_list)} formulas")
                    # Show first formula as example
                    if formulas_list:
                        print(f"         Example: {formulas_list[0]}")

        print("=" * 60)

        print()
        print("🔍 Now let's also extract some data to understand the structure...")

        # Get all worksheets in the spreadsheet
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        all_sheets = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]

        print("📋 Available Worksheets:")
        print("-" * 30)
        for sheet_title in all_sheets:
            marker = " ← CURRENT" if sheet_title == sheet_name else ""
            print(f"  • {sheet_title}{marker}")
        print()

        # Get sheet data to understand structure - EXPANDED RANGE
        sheet_data = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            ranges=[f"{sheet_name}!A:ZZ"],  # Much broader range to catch user-added columns
            includeGridData=True
        ).execute()

        # Extract header row and some sample data
        sheets = sheet_data.get('sheets', [])
        if sheets:
            grid_data = sheets[0].get('data', [])
            if grid_data:
                row_data = grid_data[0].get('rowData', [])

                print("📋 Portfolio DAILY Structure Analysis:")
                print("-" * 45)

                if row_data:
                    # Get headers - FOCUS ON USER-ADDED COLUMNS
                    if row_data[0].get('values'):
                        headers = []
                        tool_columns = []  # A-E: tool-managed
                        user_columns = []  # F+: user-added

                        for i, cell in enumerate(row_data[0]['values']):
                            col_letter = chr(65 + i)  # A, B, C, etc.
                            value = cell.get('formattedValue', '').strip()

                            if i < 5:  # A-E: tool columns
                                tool_columns.append(f"{col_letter}: '{value}'")
                            else:  # F+: user columns
                                user_columns.append(f"{col_letter}: '{value}'")  # Show all, even empty

                        print(f"🤖 TOOL COLUMNS (A-E): {', '.join(tool_columns)}")
                        user_non_empty = [col for col in user_columns if not col.endswith(": ''")]
                        if user_non_empty:
                            print(f"👤 USER COLUMNS (F+): {', '.join(user_non_empty[:10])}")
                        else:
                            print("👤 USER COLUMNS (F+): None found (but checking data rows...)")

                    # Get data row count
                    data_rows = len(row_data) - 1 if len(row_data) > 0 else 0
                    print(f"📈 Data rows: {data_rows}")

                    # Show sample data if available - FOCUS ON USER CONTENT
                    if len(row_data) > 1:
                        print("💡 Sample data rows (showing user-added columns F+):")
                        for sample_idx in [1]:  # Just show first data row
                            if sample_idx < len(row_data):
                                sample_row = row_data[sample_idx].get('values', [])
                                tool_values = []
                                user_values = []

                                for i, cell in enumerate(sample_row):
                                    value = cell.get('formattedValue', '').strip()
                                    col_letter = chr(65 + i)

                                    if i < 5:  # A-E: tool columns
                                        if value:  # Only show non-empty
                                            tool_values.append(f"{col_letter}: '{value}'")
                                    else:  # F+: user columns
                                        if value:  # Only show non-empty user content
                                            user_values.append(f"{col_letter}: '{value}'")

                                if tool_values:
                                    print(f"   🤖 TOOL DATA: {', '.join(tool_values)}")
                                if user_values:
                                    print(f"   👤 USER DATA: {', '.join(user_values[:8])}")  # Show first 8 user columns
                                    if len(user_values) > 8:
                                        print(f"   ... and {len(user_values) - 8} more user columns")
                                else:
                                    print("   👤 USER DATA: No user-added data found")

                # Check for any user content across ALL rows in columns F+
                print("🔍 Scanning ALL rows for user content in columns F+...")
                user_content_found = False
                max_col_idx = 0

                for row_idx, row in enumerate(row_data[:10]):  # Check first 10 rows
                    if 'values' in row:
                        for col_idx, cell in enumerate(row['values']):
                            if col_idx >= 5:  # F+ columns
                                value = cell.get('formattedValue', '').strip()
                                if value:  # Any non-empty content
                                    if not user_content_found:
                                        print("📝 USER CONTENT FOUND in columns F+:")
                                        user_content_found = True
                                    col_letter = chr(65 + col_idx)
                                    row_num = row_idx + 1
                                    print(f"   {col_letter}{row_num}: '{value}'")
                                    max_col_idx = max(max_col_idx, col_idx)

                if user_content_found:
                    print(f"   📊 User content extends to column {chr(65 + max_col_idx)}")
                else:
                    print("   ❌ No user content found in columns F+ across first 10 rows")

                print()
                print("🔍 ANALYSIS:")
                print("=" * 50)
                print("📊 This worksheet contains DAILY portfolio-level aggregations")
                print("📅 Data spans from recent past to future projections")
                print("💰 Shows spend, impressions, campaign counts, and day-over-day ratios")
                print("📈 Perfect for trend analysis and performance monitoring")
                print()
                print("🎯 USER INTENT ANALYSIS:")
                print("=" * 50)
                print("The user appears to want:")
                print("• Daily portfolio performance visibility")
                print("• Trend monitoring across campaigns")
                print("• Spend pacing and budget utilization tracking")
                print("• Historical performance analysis for forecasting")
                print()
                print("📋 IMPLICATIONS FOR TOOL DESIGN:")
                print("=" * 50)
                print("• Tool should generate these daily aggregations automatically")
                print("• Summary dashboard should show portfolio trends and KPIs")
                print("• Advanced analytics should include forecasting and pacing alerts")
                print("• Tool name should reflect 'portfolio' scope, not just 'campaign spend'")

    except Exception as e:
        print(f"❌ Error extracting formulas: {e}")
        print("💡 Make sure you're in the correct virtual environment with Google API access")

if __name__ == '__main__':
    main()
