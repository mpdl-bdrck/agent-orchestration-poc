#!/usr/bin/env python3
"""
Client Billing Analysis Tool - Main Entry Point
================================================

Generates client billing reports from campaign data.
"""

import os
import sys
import argparse

# Set up paths for shared modules before importing
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..", "..")
shared_path = os.path.join(project_root, "shared")
campaign_analysis_src = os.path.join(project_root, "campaign-analysis", "src")

sys.path.insert(0, shared_path)
sys.path.insert(0, campaign_analysis_src)

# Imports after path setup
from .billing_analyzer import BillingAnalyzer  # noqa: E402
from .billing_rollup_processor import BillingRollupProcessor  # noqa: E402
from .deal_classifier import DealClassifier  # noqa: E402
from .billing_sheets_publisher import BillingSheetsPublisher  # noqa: E402
from .utils.config import initialize_config, load_client_config  # noqa: E402

initialize_config()


def resolve_client_info(account_id=None, client_name=None):
    """
    Resolve client information from either account ID or client name.

    Args:
        account_id: Account ID to look up client name for
        client_name: Client name to look up account ID for

    Returns:
        tuple: (account_id, client_name, client_config)
    """
    if account_id and client_name:
        # Both provided - validate they match
        try:
            analyzer = BillingAnalyzer(account_id=account_id)
            db_client_name = analyzer._get_client_name()
            if db_client_name.lower() != client_name.lower():
                print(f"❌ Mismatch: Account {account_id} belongs to '{db_client_name}', not '{client_name}'")
                return None, None, None
        except Exception as e:
            print(f"❌ Could not validate account/client match: {e}")
            return None, None, None
    elif account_id:
        # Only account ID provided - get client name from database
        try:
            analyzer = BillingAnalyzer(account_id=account_id)
            client_name = analyzer._get_client_name()
            print(f"✅ Account {account_id} belongs to client: '{client_name}'")
        except Exception as e:
            print(f"❌ Could not get client name for account {account_id}: {e}")
            return None, None, None
    elif client_name:
        # Only client name provided - this is not yet supported
        # Would need to query database to find account ID for client name
        print(f"❌ Specifying client name without account ID is not yet supported")
        print(f"   Please provide account ID and client name will be auto-resolved")
        return None, None, None
    else:
        print("❌ Either account-id or client-name must be provided")
        return None, None, None

    # Load client config
    try:
        client_config = load_client_config(client_name)
        print(f"✅ Loaded configuration for client: '{client_name}'")
        return account_id, client_name, client_config
    except FileNotFoundError:
        print(f"❌ Client config file not found: config/clients/{client_name.lower()}.json")
        print(f"   Please create the config file for client '{client_name}'")
        return None, None, None
    except Exception as e:
        print(f"❌ Could not load client config: {e}")
        return None, None, None


def main():
    """Main entry point for command line execution"""
    parser = argparse.ArgumentParser(description='Client Billing Analysis Tool')
    parser.add_argument('--account-id', type=str, help='Account ID to analyze (will auto-resolve client name)')
    parser.add_argument('--client-name', type=str, help='Client name (requires account-id for validation)')
    parser.add_argument('--start-date', type=str, required=True, help='Start date for analysis (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, required=True, help='End date for analysis (YYYY-MM-DD)')
    parser.add_argument('--timezone', type=str, help='Override timezone (e.g., "UTC", "PST", "America/Los_Angeles")')
    parser.add_argument('--publish-sheets', action='store_true', help='Publish billing data to Google Sheets')

    args = parser.parse_args()

    # Validate that we have the minimum required inputs
    if not args.account_id and not args.client_name:
        parser.error("Either --account-id or --client-name must be provided")

    # Resolve client information (this will populate missing values)
    account_id, client_name, client_config = resolve_client_info(
        account_id=args.account_id,
        client_name=args.client_name
    )

    if not all([account_id, client_name, client_config]):
        return 1

    # Override timezone if specified
    if args.timezone:
        # Map common timezone abbreviations to full timezone names
        tz_map = {
            'UTC': ('UTC', 'UTC'),
            'PST': ('PST', 'America/Los_Angeles'),
            'PDT': ('PDT', 'America/Los_Angeles'),
            'EST': ('EST', 'America/New_York'),
            'EDT': ('EDT', 'America/New_York'),
        }
        
        tz_override = args.timezone.upper()
        if tz_override in tz_map:
            client_config['timezone'] = tz_map[tz_override][0]
            client_config['timezone_full'] = tz_map[tz_override][1]
        else:
            # Assume it's a full timezone name (e.g., "America/Los_Angeles")
            client_config['timezone'] = args.timezone
            client_config['timezone_full'] = args.timezone
        
        print(f"   🌍 Timezone override: {client_config.get('timezone_full', client_config.get('timezone'))}")

    # Update args for consistency
    args.account_id = account_id
    args.client_name = client_name

    try:
        # Client info already resolved above
        print(f"   📊 Spreadsheet ID: {client_config.get('spreadsheet_id', 'Not set')}")
        print(f"   🌍 Timezone: {client_config.get('timezone_full', client_config.get('timezone', 'UTC'))}")
        print(f"   📅 Date Format: {client_config.get('date_format', 'DD/MM/YYYY')}")

        # Initialize analyzer
        analyzer = BillingAnalyzer(
            account_id=args.account_id,
            client_name=args.client_name,
            client_config=client_config
        )

        # Run analysis
        results = analyzer.run_analysis(args.start_date, args.end_date)
        
        # Check for errors
        if 'error' in results:
            print(f"❌ Analysis failed: {results['error']}")
            return 1
        
        daily_line_items = results.get('daily_line_items')
        if daily_line_items is None or daily_line_items.empty:
            print("⚠️  No billing data found")
            return 1
        
        # Create billing rollup
        print("\n🔄 Creating billing rollup...")
        print("-" * 40)
        
        deal_classifier = DealClassifier(client_config)
        rollup_processor = BillingRollupProcessor(deal_classifier)
        billing_rollup = rollup_processor.create_billing_rollup(
            daily_line_items, 
            split_by_inventory=True
        )
        
        if billing_rollup.empty:
            print("⚠️  Billing rollup is empty")
            return 1
        
        print(f"✅ Created billing rollup:")
        print(f"   📊 {len(billing_rollup)} rows")
        advertisers = billing_rollup['advertiser_name'].nunique()
        campaigns = billing_rollup['campaign_name'].nunique()
        print(f"   📊 {advertisers} advertisers")
        print(f"   📊 {campaigns} campaigns")
        
        if 'inventory_type' in billing_rollup.columns:
            deals_count = len(billing_rollup[billing_rollup['inventory_type'] == 'Deals'])
            marketplace_count = len(billing_rollup[billing_rollup['inventory_type'] == 'Marketplace'])
            print(f"   📊 {deals_count} Deal rows, {marketplace_count} Marketplace rows")
        
        # Publish to Google Sheets if requested
        if args.publish_sheets:
            print("\n📊 Publishing billing data to Google Sheets...")
            print("-" * 40)
            
            publisher = BillingSheetsPublisher()
            success = publisher.publish_billing_sheet(
                billing_rollup,
                client_config,
                args.start_date,
                args.end_date
            )
            
            if success:
                spreadsheet_id = client_config.get('spreadsheet_id')
                print("✅ Successfully published billing data to Google Sheets!")
                print(f"   🔗 View at: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
            else:
                print("❌ Failed to publish billing data to Google Sheets")
                return 1
        else:
            print("\n💡 Tip: Use --publish-sheets to publish data to Google Sheets")
        
            print("\n🎉 Billing Analysis Complete!")
            return 0

    except Exception as e:
        print(f"❌ Billing analysis failed: {e}")
        import traceback
        print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit(main())

