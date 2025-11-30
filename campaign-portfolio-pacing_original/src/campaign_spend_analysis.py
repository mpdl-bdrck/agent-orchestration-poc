#!/usr/bin/env python3
"""
Campaign Spend Analysis Tool - Main Entry Point
=================================================

Analyzes spend and impressions for all campaigns matching account/advertiser criteria.
Defaults to Tricoast Media LLC (account ID 17) with Eli Lilly campaigns.
"""

import os
import sys
import argparse
import pandas as pd  # type: ignore

# Set up paths for shared modules before importing
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..", "..")
shared_path = os.path.join(project_root, "shared")
campaign_analysis_src = os.path.join(project_root, "campaign-analysis", "src")
sheets_path = os.path.join(shared_path, "sheets")

sys.path.insert(0, shared_path)
sys.path.insert(0, campaign_analysis_src)
sys.path.insert(0, sheets_path)

# Imports after path setup (required for dynamic module loading)
from .campaign_analyzer import CampaignSpendAnalyzer  # noqa: E402
from .sheets_publisher import publish_comprehensive_rollups  # noqa: E402
from .utils.config import initialize_config, config, load_client_config  # noqa: E402

initialize_config()


def resolve_client_from_advertiser(advertiser_filter, account_id=None):
    """
    Resolve client information from advertiser name.
    Queries campaigns to find which account/client the advertiser belongs to.
    
    Args:
        advertiser_filter: Advertiser name filter (e.g., "Lilly")
        account_id: Optional account ID to narrow search
        
    Returns:
        tuple: (account_id, client_name, client_config) or (None, None, None) on error
    """
    if not advertiser_filter:
        return None, None, None
    
    try:
        # Create temporary analyzer to query advertiser → client relationship
        analyzer = CampaignSpendAnalyzer(account_id=account_id, advertiser_filter=advertiser_filter)
        
        # Query to find account/client for this advertiser
        # Advertisers belong to one client only, so we can query campaigns to find the account
        advertiser_client_query = '''
            SELECT DISTINCT a."accountId", a."name" as account_name, adv."name" as advertiser_name
            FROM "campaigns" c
            JOIN "advertisers" adv ON c."advertiserId" = adv."advertiserId"
            JOIN "lineItems" li ON c."campaignId" = li."campaignId"
            JOIN "curationPackages" cp ON li."curationPackageId" = cp."curationPackageId"
            JOIN "accounts" a ON cp."accountId" = a."accountId"
            WHERE c."statusId" IN (1, 2, 3)
              AND adv."name" ILIKE %s
        '''
        
        # Add account filter if provided
        if account_id:
            advertiser_client_query += ' AND a."accountId" = %s'
            params = (f'%{advertiser_filter}%', int(account_id))
        else:
            params = (f'%{advertiser_filter}%',)
        
        advertiser_client_query += ' LIMIT 1'
        
        results = analyzer.db.execute_postgres_query(advertiser_client_query, params)
        
        if not results:
            print(f"⚠️  Could not find client for advertiser filter: '{advertiser_filter}'")
            return None, None, None
        
        account_id_found = results[0][0]
        client_name = results[0][1]
        advertiser_name_found = results[0][2]
        
        print(f"✅ Advertiser '{advertiser_name_found}' belongs to client: '{client_name}' (Account {account_id_found})")
        
        # Load client config
        try:
            client_config = load_client_config(client_name)
            print(f"✅ Loaded configuration for client: '{client_name}'")
            if client_config.get('timezone'):
                print(f"   🌍 Timezone: {client_config.get('timezone')} ({client_config.get('timezone_full', '')})")
            return account_id_found, client_name, client_config
        except FileNotFoundError:
            print(f"⚠️  Client config file not found: config/clients/{client_name.lower()}.json")
            print(f"   Continuing with UTC timezone (no timezone conversion)")
            return account_id_found, client_name, None
        except Exception as e:
            print(f"⚠️  Could not load client config: {e}")
            print(f"   Continuing with UTC timezone (no timezone conversion)")
            return account_id_found, client_name, None
            
    except Exception as e:
        print(f"❌ Could not resolve client from advertiser '{advertiser_filter}': {e}")
        return None, None, None


def resolve_client_info(account_id=None, advertiser_filter=None):
    """
    Resolve client information from account ID or advertiser filter.
    If advertiser_filter is provided, resolves client from advertiser (preferred).
    Otherwise, resolves from account ID.
    
    Args:
        account_id: Account ID to look up client name for
        advertiser_filter: Advertiser filter to resolve client from (takes precedence)
        
    Returns:
        tuple: (account_id, client_name, client_config) or (None, None, None) on error
    """
    # Prefer advertiser-based resolution if advertiser filter is provided
    if advertiser_filter:
        result = resolve_client_from_advertiser(advertiser_filter, account_id)
        if result[0] is not None:  # Successfully resolved
            return result
        # Fall through to account-based resolution if advertiser resolution failed
    
    # Fall back to account-based resolution
    if not account_id:
        return None, None, None
    
    try:
        # Create temporary analyzer to get client name
        analyzer = CampaignSpendAnalyzer(account_id=account_id)
        client_name = analyzer._get_client_name()
        print(f"✅ Account {account_id} belongs to client: '{client_name}'")
    except Exception as e:
        print(f"❌ Could not get client name for account {account_id}: {e}")
        return None, None, None
    
    # Load client config
    try:
        client_config = load_client_config(client_name)
        print(f"✅ Loaded configuration for client: '{client_name}'")
        if client_config.get('timezone'):
            print(f"   🌍 Timezone: {client_config.get('timezone')} ({client_config.get('timezone_full', '')})")
        return account_id, client_name, client_config
    except FileNotFoundError:
        print(f"⚠️  Client config file not found: config/clients/{client_name.lower()}.json")
        print(f"   Continuing with UTC timezone (no timezone conversion)")
        return account_id, client_name, None
    except Exception as e:
        print(f"⚠️  Could not load client config: {e}")
        print(f"   Continuing with UTC timezone (no timezone conversion)")
        return account_id, client_name, None


def main():
    """Main entry point for command line execution"""
    parser = argparse.ArgumentParser(description='Comprehensive Campaign Analysis Tool')
    parser.add_argument('--account-id', type=str, help='Account ID to analyze')
    parser.add_argument('--advertiser-filter', type=str, help='Advertiser filter for campaign selection')
    parser.add_argument('--start-date', type=str, help='Start date for analysis (YYYY-MM-DD, default: 2025-11-01)')
    parser.add_argument('--end-date', type=str, help='End date for analysis (YYYY-MM-DD, default: today)')
    parser.add_argument('--timezone', type=str, help='Override timezone (e.g., "UTC", "PST", "America/Los_Angeles")')
    parser.add_argument('--publish-sheets', action='store_true', help='Publish comprehensive rollups to Google Sheets (6 worksheets)')
    parser.add_argument('--create-summary', action='store_true', help='Create intelligent summary dashboard with formulas (requires --publish-sheets)')
    parser.add_argument('--advanced-dashboard', action='store_true', help='Create advanced dashboard with trend analysis and risk assessment (requires --create-summary)')
    parser.add_argument('--campaign-start', help='Campaign start date (YYYY-MM-DD) for pacing calculations')
    parser.add_argument('--campaign-end', help='Campaign end date (YYYY-MM-DD) for pacing calculations')
    parser.add_argument('--campaign-budget', type=float, help='Total campaign budget for pacing analysis')

    args = parser.parse_args()

    # Resolve client info and load config (prefer advertiser-based resolution)
    account_id = args.account_id or CampaignSpendAnalyzer.DEFAULT_ACCOUNT_ID
    resolved_account_id, client_name, client_config = resolve_client_info(
        account_id=account_id,
        advertiser_filter=args.advertiser_filter
    )
    
    if resolved_account_id is None:
        # Fallback: use account ID without client config
        client_config = None
        print(f"⚠️  Continuing without client config (using UTC timezone)")
    
    # Override timezone if specified
    if args.timezone:
        if client_config is None:
            # Create a minimal client config if none exists
            client_config = {}
        
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
    
    # Create analyzer with client config
    analyzer = CampaignSpendAnalyzer(
        account_id=args.account_id,
        advertiser_filter=args.advertiser_filter,
        client_config=client_config
    )
    results = analyzer.run_analysis(args.start_date, args.end_date)

    # Check for errors
    if 'error' in results:
        print(f"❌ Analysis failed: {results['error']}")
        return 1

    # Initialize worksheets config (always available)
    worksheets_config = config.get('google_sheets', 'worksheets', {})

    # Publish to Google Sheets if requested
    rollups = results.get('rollups', {})
    if args.publish_sheets and rollups:
        print("\n📊 Publishing comprehensive rollups to Google Sheets...")
        success = publish_comprehensive_rollups(
            rollups,
            results.get('advertiser_name', 'Unknown'),
            analyzer.account_id,
            results.get('rollup_csv_paths')
        )
        if success:
            print("✅ Successfully published all rollup views to Google Sheets!")

            # Get spreadsheet ID for pacing dashboard creation
            spreadsheet_id = config.get('google_sheets', 'default_spreadsheet_id')

            # Prepare rollup sheets list for both pacing and summary dashboards
            rollup_sheets = []
            for rollup_key in ['line_items_daily', 'line_items_total', 'campaigns_daily', 'campaigns_total', 'portfolio_daily', 'portfolio_total']:
                worksheet_name = worksheets_config.get(rollup_key, rollup_key)
                rollup_sheets.append(worksheet_name)

            # Create campaign pacing dashboard if campaign parameters provided
            pacing_config = {}
            if args.campaign_start or args.campaign_end or args.campaign_budget:
                print("\n📊 Creating campaign pacing dashboard...")
                print(f"   📅 Start: {args.campaign_start or '2025-11-01'}")
                print(f"   📅 End: {args.campaign_end or '2025-12-31'}")
                print(f"   💰 Budget: {args.campaign_budget or 466000}")
                try:
                    from sheets import get_summary_manager, get_sheets_service  # type: ignore

                    sheets_service = get_sheets_service()
                    summary_mgr = get_summary_manager(sheets_service)

                    pacing_config = {
                        'start_date': args.campaign_start or '2025-11-01',
                        'end_date': args.campaign_end or '2025-12-31',
                        'budget': args.campaign_budget or 466000
                    }

                    print("DEBUG: About to call create_pacing_dashboard")
                    pacing_success = summary_mgr.create_pacing_dashboard(
                        spreadsheet_id=spreadsheet_id,
                        campaign_config=pacing_config,
                        rollup_sheets=rollup_sheets
                    )
                    print(f"DEBUG: create_pacing_dashboard returned: {pacing_success}")

                    if pacing_success:
                        print("✅ Campaign pacing dashboard created!")
                        print("   📅 Timeline calculations and budget pacing analysis")
                        print(f"   🔗 Summary dashboard: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid=6")

                    else:
                        print("⚠️  Pacing dashboard creation had some issues")
                        # Check if Summary sheet was actually created
                        try:
                            from sheets import get_sheets_service  # type: ignore
                            service = get_sheets_service()
                            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                            sheet_names = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
                            if "Summary" in sheet_names:
                                print("   ✅ Summary sheet exists in spreadsheet")
                            else:
                                print("   ❌ Summary sheet NOT found in spreadsheet")
                                print(f"   📋 Available sheets: {sheet_names}")
                        except Exception as check_error:
                            print(f"   ❌ Could not verify sheet creation: {check_error}")

                except Exception as e:
                    print(f"⚠️  Failed to create pacing dashboard: {e}")
                    print("   Data export was successful, continuing...")

            # Always create Daily Rates Trend sheet when publishing to sheets
            # It will read campaign parameters from Summary tab if not provided
            print("\n📈 Creating daily rates trend sheet...")
            try:
                from .sheets_publisher import publish_daily_rates_trend  # noqa: E402

                # Use provided config or empty dict (will read from Summary tab)
                trend_config = pacing_config if pacing_config else {}

                trend_success = publish_daily_rates_trend(
                    spreadsheet_id=spreadsheet_id,
                    campaign_config=trend_config
                )

                if trend_success:
                    print("✅ Daily rates trend sheet created!")
                    print("   📊 4-column format: Date | Target Daily Rate | Actual Daily Rate | Required Daily Rate")
                    if trend_config:
                        print("   📈 Using provided campaign parameters")
                    else:
                        print("   📈 Reading campaign parameters from Summary tab")
                    print(f"   🔗 Trend data: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid=7")
                else:
                    print("⚠️  Daily rates trend sheet creation had some issues")

            except Exception as trend_error:
                print(f"⚠️  Failed to create daily rates trend sheet: {trend_error}")
                import traceback
                print(traceback.format_exc())
                print("   Continuing with other operations...")

            # Apply professional formatting to all worksheets
            try:
                from sheets import get_sheets_service  # type: ignore
                from sheets.formatting import FormattingManager  # type: ignore

                sheets_service = get_sheets_service()
                formatting_mgr = FormattingManager(sheets_service)

                # Load campaign report formatting preset
                campaign_preset = formatting_mgr.applicator.load_preset(
                    config.get('google_sheets', 'formatting_preset', 'presets/formatting/campaign_report.json')
                )

                print("🎨 Applying professional formatting to worksheets...")

                # Apply formatting to each worksheet
                worksheets_config = config.get('google_sheets', 'worksheets', {})

                formatted_count = 0
                for rollup_key in ['line_items_daily', 'line_items_total', 'campaigns_daily', 'campaigns_total', 'portfolio_daily', 'portfolio_total']:
                    worksheet_name = worksheets_config.get(rollup_key, rollup_key)

                    # Get sheet ID for the worksheet
                    sheet_id = formatting_mgr.extractor.get_sheet_id_by_name(spreadsheet_id, worksheet_name)
                    if sheet_id is not None:
                        # Apply formatting preset
                        format_success = formatting_mgr.apply_preset(spreadsheet_id, sheet_id, campaign_preset)
                        if format_success:
                            formatted_count += 1
                            print(f"      ✓ {worksheet_name}: formatted")
                        else:
                            print(f"      ⚠️ {worksheet_name}: formatting failed")
                    else:
                        print(f"      ⚠️ {worksheet_name}: sheet not found for formatting")

                if formatted_count > 0:
                    print(f"✅ Applied professional formatting to {formatted_count} worksheets")

            except Exception as e:
                print(f"⚠️ Formatting application failed: {e}")
                print("   Data export was successful, continuing...")

            print(f"🔗 View at: https://docs.google.com/spreadsheets/d/{config.get('google_sheets', 'default_spreadsheet_id')}")
            print("   📋 Worksheets created:")
            for rollup_key in ['line_items_daily', 'line_items_total', 'campaigns_daily', 'campaigns_total', 'portfolio_daily', 'portfolio_total']:
                worksheet_name = worksheets_config.get(rollup_key, rollup_key)
                rollup_data = rollups.get(rollup_key)
                record_count = len(rollup_data) if isinstance(rollup_data, pd.DataFrame) else len(rollup_data) if rollup_data else 0
                print(f"      • {worksheet_name}: {record_count} records")
            # Add Daily Rates Trend sheet only if campaign parameters were provided
            if args.campaign_start or args.campaign_end or args.campaign_budget:
                from datetime import datetime
                start_dt = datetime.strptime(args.campaign_start or '2025-11-01', '%Y-%m-%d')
                end_dt = datetime.strptime(args.campaign_end or '2025-12-31', '%Y-%m-%d')
                total_dates = (end_dt - start_dt).days + 2  # +1 for inclusive, +1 for header
                trend_sheet_name = worksheets_config.get('daily_rates_trend', 'Daily Rates Trend')
                print(f"      • {trend_sheet_name}: {total_dates} rows (header + all campaign dates with Summary!B12 formulas)")

    rollup_csv_paths = results.get('rollup_csv_paths') or {}
    if rollup_csv_paths:
        print("   📂 Source CSV snapshots:")
        for rollup_key, path in rollup_csv_paths.items():
            worksheet_name = worksheets_config.get(rollup_key, rollup_key)
            print(f"      • {worksheet_name}: {path}")

            # Create intelligent summary dashboard if requested
            if args.create_summary:
                print("\n📊 Creating intelligent summary dashboard...")
                try:
                    from sheets import get_summary_manager, get_sheets_service  # type: ignore

                    # Get service and summary manager
                    service = get_sheets_service()
                    summary_mgr = get_summary_manager(service)

                    # Load dashboard preset
                    summary_config_path = config.get('google_sheets', 'summary_config', 'presets/summaries/campaign_dashboard.json')
                    # Resolve path relative to tools directory
                    if not summary_config_path.startswith('/'):
                        summary_config_path = os.path.join(project_root, summary_config_path)
                    summary_config = summary_mgr.load_formula_config(summary_config_path)

                    # Rollup sheets already prepared above

                    # Create the summary dashboard
                    spreadsheet_id = config.get('google_sheets', 'default_spreadsheet_id')
                    summary_success = summary_mgr.create_formula_dashboard(
                        spreadsheet_id=spreadsheet_id,
                        summary_config=summary_config,
                        rollup_sheets=rollup_sheets
                    )

                    if summary_success:
                        print("✅ Intelligent summary dashboard created!")
                        print(f"   📈 {len(summary_config.get('formulas', {}))} live formulas added")
                        print(f"   🔗 Summary sheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid=6")


                        # Advanced dashboard feature not yet implemented
                        if args.advanced_dashboard:
                            print("\n⚠️  Advanced dashboard feature is not yet implemented")
                            print("   Use --create-summary for basic summary dashboard")
                    else:
                        print("⚠️  Summary dashboard creation had some issues (check logs)")

                except Exception as e:
                    print(f"⚠️  Failed to create dashboard: {e}")
                    print("   Continuing with successful data export...")

    else:
        print("❌ Failed to publish comprehensive rollups to Google Sheets")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
