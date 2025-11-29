#!/usr/bin/env python3
"""
Command-line tool for extracting formatting presets from Google Sheets.

Usage:
    python extract_formatting.py SPREADSHEET_ID SHEET_NAME [OUTPUT_FILE]

This tool extracts professional formatting from an existing Google Sheet
and saves it as a reusable JSON preset for automated formatting.
"""

import sys
import os
import json
from pathlib import Path

# Add shared modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sheets.credentials import get_sheets_service
from sheets.formatting import FormattingManager


def main():
    """Main entry point for formatting extraction tool."""
    if len(sys.argv) < 3:
        print("Usage: python extract_formatting.py SPREADSHEET_ID SHEET_NAME [OUTPUT_FILE]")
        print("")
        print("Arguments:")
        print("  SPREADSHEET_ID: Google Sheets spreadsheet ID")
        print("  SHEET_NAME:     Name of the worksheet to extract from")
        print("  OUTPUT_FILE:    Optional output file path (default: extracted_preset.json)")
        print("")
        print("Example:")
        print("  python extract_formatting.py 1abc123def456 MySheet presets/my_preset.json")
        sys.exit(1)

    spreadsheet_id = sys.argv[1]
    sheet_name = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else "extracted_preset.json"

    try:
        print(f"🔍 Extracting formatting from '{sheet_name}' in spreadsheet {spreadsheet_id}...")

        # Get authenticated service
        service = get_sheets_service()

        # Initialize formatting manager
        formatting_mgr = FormattingManager(service)

        # Extract comprehensive formatting preset
        print("📊 Analyzing sheet structure and formatting...")
        preset = formatting_mgr.extractor.create_comprehensive_preset(
            spreadsheet_id, sheet_name, include_data_formatting=True
        )

        # Save the preset
        print(f"💾 Saving preset to {output_file}...")
        formatting_mgr.extractor.save_preset(preset, output_file)

        # Print summary
        metadata = preset.get('metadata', {})
        print("✅ Formatting extraction complete!")
        print(f"   📋 Sheet: {metadata.get('sheet_name', 'Unknown')}")
        print(f"   📊 Columns formatted: {metadata.get('data_cells_formatted', 0)}")
        print(f"   🎨 Conditional rules: {len(preset.get('conditional_formatting_rules', []))}")
        print(f"   📁 Filters: {'Enabled' if preset.get('filters', {}).get('enabled') else 'Disabled'}")
        print(f"   📄 Preset saved to: {output_file}")

        # Validate the preset
        from sheets.schema import SchemaValidator
        validator = SchemaValidator()
        errors = validator.validate_formatting_preset(preset)
        if errors:
            print("⚠️  Preset validation warnings:")
            for error in errors:
                print(f"     • {error}")
        else:
            print("✅ Preset validation passed!")

    except Exception as e:
        print(f"❌ Error extracting formatting: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
