"""
Campaign Analyzer
=================

Analyzes spend and impressions for campaigns based on account/advertiser criteria.
"""

import os
import sys
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import pytz

# Add shared and campaign-analysis to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "staging", "campaign-analysis", "src"))

from database_connector import DatabaseConnector
from campaign_discovery import CampaignDiscovery
from timezone_handler import TimezoneHandler
from .data_rollup_processor import DataRollupProcessor
from .utils.config import config


class CampaignSpendAnalyzer:
    """Analyzes spend and impressions for campaigns based on account/advertiser criteria"""

    DEFAULT_ACCOUNT_ID = 17  # Tricoast Media LLC
    DEFAULT_ADVERTISER_FILTER = "Lilly"  # Eli Lilly campaigns

    def __init__(self, account_id: str = None, advertiser_filter: str = None, client_config: Dict[str, Any] = None):
        """
        Initialize with account ID, optional advertiser filter, and optional client config
        
        Args:
            account_id (str): Account ID
            advertiser_filter (str): Advertiser filter for campaign selection
            client_config (dict, optional): Client configuration dictionary (includes timezone, etc.)
        """
        self.account_id = account_id or str(self.DEFAULT_ACCOUNT_ID)
        self.advertiser_filter = advertiser_filter or self.DEFAULT_ADVERTISER_FILTER
        self.client_config = client_config or {}
        self.db = DatabaseConnector()
        self.discovery = CampaignDiscovery()
        
        # Initialize timezone handler from client config
        if self.client_config:
            self.timezone_handler = TimezoneHandler(self.client_config)
        else:
            self.timezone_handler = None

    def run_analysis(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        Run comprehensive multi-rollup campaign analysis workflow:
        1. Discover campaigns for account/advertiser
        2. Collect daily line item performance data
        3. Generate all 6 rollup views (daily/total/portfolio levels)
        """
        print(f"\n🔍 Comprehensive Campaign Analysis: Account {self.account_id}")
        if self.advertiser_filter:
            print(f"   Advertiser Filter: {self.advertiser_filter}")
        print("=" * 70)

        try:
            # Step 0: Get advertiser name
            print("\n📋 Getting advertiser information...")
            print("-" * 40)
            advertiser_name = self._get_advertiser_name()
            print(f"✅ Advertiser: {advertiser_name}")

            # Step 1: Discover campaigns
            print("\n📊 STEP 1: Discovering campaigns...")
            print("-" * 40)
            campaigns = self._discover_campaigns()
            print(f"✅ Found {len(campaigns)} campaigns")

            if not campaigns:
                print("⚠️  No campaigns found matching criteria")
                return {"campaigns_analyzed": 0, "error": "No campaigns found"}

            # Step 2: Collect daily line item data
            print("\n📅 STEP 2: Collecting daily line item data...")
            print("-" * 40)
            daily_line_items = self._collect_daily_line_items(campaigns, start_date, end_date)

            if daily_line_items.empty:
                print("⚠️  No daily line item data found")
                return {"campaigns_analyzed": len(campaigns), "daily_records": 0, "error": "No data found"}

            unique_campaigns = daily_line_items['campaign_id'].nunique()
            print(f"✅ Collected {len(daily_line_items)} daily records across {unique_campaigns} campaigns")

            # Step 3: Create campaign budgets mapping for rollup calculations
            campaign_budgets = {c['campaign_id']: c['budget'] for c in campaigns}

            # Step 4: Generate all rollup views
            print("\n🔄 STEP 3: Generating comprehensive rollup reports...")
            print("-" * 40)

            rollup_processor = DataRollupProcessor(campaign_budgets)
            all_rollups = rollup_processor.create_all_rollups(daily_line_items)

            # Log rollup sizes
            for rollup_name, data in all_rollups.items():
                worksheet_name = config.get('google_sheets', 'worksheets', {}).get(rollup_name, rollup_name)
                record_count = len(data) if isinstance(data, pd.DataFrame) else len(data) if data else 0
                print(f"   📊 {worksheet_name}: {record_count} records")

            print("✅ Generated 6 comprehensive rollup views")

            # Step 5: Export rollups to CSV
            rollup_csv_paths = self._export_rollup_csvs(all_rollups, advertiser_name)

            # Prepare return data
            # Calculate end date for display (use client timezone if available)
            if end_date:
                display_end_date = end_date
            elif self.timezone_handler:
                # Use client timezone for "today"
                client_tz_str = self.client_config.get('timezone_full') or self.client_config.get('timezone', 'UTC')
                client_tz = pytz.timezone(client_tz_str) if client_tz_str != 'UTC' else pytz.UTC
                
                # Map common abbreviations
                tz_map = {
                    'PST': 'America/Los_Angeles',
                    'PDT': 'America/Los_Angeles',
                    'EST': 'America/New_York',
                    'EDT': 'America/New_York',
                }
                if client_tz_str.upper() in tz_map:
                    client_tz = pytz.timezone(tz_map[client_tz_str.upper()])
                
                now_client = datetime.now(client_tz)
                display_end_date = now_client.date().strftime('%Y-%m-%d')
            else:
                display_end_date = datetime.now().strftime('%Y-%m-%d')
            
            result_data = {
                'advertiser_name': advertiser_name,
                'campaigns_analyzed': len(campaigns),
                'daily_records_collected': len(daily_line_items),
                'date_range': f"{start_date or '2025-11-01'} to {display_end_date}",
                'rollups': all_rollups,
                'rollup_csv_paths': rollup_csv_paths
            }

            print("\n🎉 Comprehensive Analysis Complete!")
            print("=" * 70)
            print(f"🎯 Account: {self.account_id}")
            print(f"🎯 Advertiser: {advertiser_name}")
            print(f"🎯 Campaigns: {len(campaigns)}")
            print(f"🎯 Daily Records: {len(daily_line_items)}")
            print("🎯 Rollup Views: 6 (Line Items Daily/Total, Campaigns Daily/Total, Portfolio Daily/Total)")

            return result_data

        except Exception as e:
            print(f"\n❌ Analysis failed: {e}")
            return {"error": str(e)}

    def _discover_campaigns(self) -> List[Dict[str, Any]]:
        """Discover all campaigns for the account using curation package approach"""
        campaign_query = '''
            SELECT DISTINCT c."campaignId", c."name", c."totalBudget", c."campaignUuid",
                   adv."name" as advertiser_name
            FROM "lineItems" li
            JOIN "campaigns" c ON li."campaignId" = c."campaignId"
            LEFT JOIN "advertisers" adv ON c."advertiserId" = adv."advertiserId"
            LEFT JOIN "curationPackages" cp ON li."curationPackageId" = cp."curationPackageId"
            WHERE cp."accountId" = %s
                AND c."statusId" IN (1, 2, 3)
            ORDER BY c."campaignId"
        '''

        results = self.db.execute_postgres_query(campaign_query, (int(self.account_id),))

        campaigns = []
        for row in results:
            campaign = {
                'campaign_id': row[0],
                'campaign_name': row[1],
                'budget': float(row[2]) if row[2] else 0.0,
                'campaign_uuid': row[3],
                'advertiser_name': row[4] if row[4] else None
            }
            campaigns.append(campaign)

        # Apply advertiser filter if specified
        if self.advertiser_filter:
            filtered_campaigns = []
            for campaign in campaigns:
                # Check both campaign name and advertiser name
                campaign_match = self.advertiser_filter.lower() in campaign['campaign_name'].lower()
                advertiser_match = campaign.get('advertiser_name') and \
                    self.advertiser_filter.lower() in campaign['advertiser_name'].lower()
                
                if campaign_match or advertiser_match:
                    filtered_campaigns.append(campaign)

            print(f"   Filtered to {len(filtered_campaigns)} campaigns for advertiser: {self.advertiser_filter!s}")
            return filtered_campaigns

        return campaigns

    def _collect_daily_line_items(self, campaigns: List[Dict[str, Any]], start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Collect daily line item performance data using hybrid approach:
        - Query Redshift for spend/impression data (performance metrics)
        - Query PostgreSQL for campaign/line item metadata (names, IDs)
        - Merge data in Python
        
        If no dates provided, returns all available data for the campaigns.

        Returns:
            DataFrame with daily line item records
        """
        # Determine if date filtering is needed
        has_date_range = start_date is not None and end_date is not None
        
        if has_date_range:
            print(f"   📅 Collecting daily line item data from {start_date} to {end_date}...")
            
            # Convert dates to UTC if timezone handler is available
            if self.timezone_handler:
                print(f"   🌍 Converting date range from {self.client_config.get('timezone', 'UTC')} to UTC...")
                start_date_utc, end_date_utc = self.timezone_handler.convert_date_range(
                    start_date, end_date, to_tz='UTC'
                )
                print(f"   📅 UTC date range: {start_date_utc} to {end_date_utc}")
                # Use UTC dates for query
                query_start_date = start_date_utc
                query_end_date = end_date_utc
            else:
                query_start_date = start_date
                query_end_date = end_date
        else:
            # No dates provided - default to "today" in client timezone
            if self.timezone_handler:
                # Get today's date in client timezone
                client_tz_str = self.client_config.get('timezone_full') or self.client_config.get('timezone', 'UTC')
                client_tz = pytz.timezone(client_tz_str) if client_tz_str != 'UTC' else pytz.UTC
                
                # Map common abbreviations
                tz_map = {
                    'PST': 'America/Los_Angeles',
                    'PDT': 'America/Los_Angeles',
                    'EST': 'America/New_York',
                    'EDT': 'America/New_York',
                }
                if client_tz_str.upper() in tz_map:
                    client_tz = pytz.timezone(tz_map[client_tz_str.upper()])
                
                # Get current time in client timezone
                now_client = datetime.now(client_tz)
                today_client = now_client.date()
                
                # Use a reasonable start date (e.g., 6 months ago) to today
                default_start = (today_client - timedelta(days=180)).strftime('%Y-%m-%d')
                end_date = today_client.strftime('%Y-%m-%d')
                
                print(f"   📅 No date range provided - defaulting to today in {self.client_config.get('timezone', 'UTC')}: {end_date}")
                print(f"   📅 Collecting daily line item data from {default_start} to {end_date}...")
                
                # Convert start date to UTC (beginning of day)
                start_date_utc, _ = self.timezone_handler.convert_date_range(
                    default_start, default_start, to_tz='UTC'
                )
                
                # For end date: we need to query UTC dates that contain any part of "today" PST
                # Nov 25 PST spans: Nov 25 UTC 08:00 to Nov 26 UTC 07:59
                # So we need to query up to Nov 26 UTC, but then filter out dates > today PST
                # Convert "today" PST end of day to UTC to get the maximum UTC date we might need
                today_end_pst = datetime.strptime(end_date, '%Y-%m-%d')
                today_end_pst = client_tz.localize(today_end_pst.replace(hour=23, minute=59, second=59))
                today_end_utc = today_end_pst.astimezone(pytz.UTC)
                end_date_utc = today_end_utc.date().strftime('%Y-%m-%d')
                
                print(f"   🌍 UTC date range: {start_date_utc} to {end_date_utc}")
                
                query_start_date = start_date_utc
                query_end_date = end_date_utc
                has_date_range = True  # Now we have a date range
            else:
                print(f"   📅 Collecting daily line item data (all available dates - no timezone config)...")

        try:
            # Prepare campaign UUIDs and mapping
            campaign_uuids = [c['campaign_uuid'] for c in campaigns]
            campaign_uuid_map = {
                c['campaign_uuid']: {
                    'campaign_id': c['campaign_id'],
                    'campaign_name': c['campaign_name']
                }
                for c in campaigns
            }

            if not campaign_uuids:
                print("   ⚠️  No campaign UUIDs found")
                return pd.DataFrame(columns=[
                    'date', 'campaign_id', 'campaign_name',
                    'line_item_id', 'line_item_name', 'total_spent', 'total_impressions'
                ])

            print(f"   🔍 Querying Redshift for {len(campaign_uuids)} campaigns...")

            # Determine if we need hourly query for PST timezone conversion
            use_hourly_query = False
            client_tz_str = None
            if self.timezone_handler:
                client_tz_str = self.client_config.get('timezone_full') or self.client_config.get('timezone', 'UTC')
                # Map common abbreviations
                tz_map = {
                    'PST': 'America/Los_Angeles',
                    'PDT': 'America/Los_Angeles',
                    'EST': 'America/New_York',
                    'EDT': 'America/New_York',
                }
                if client_tz_str.upper() in tz_map:
                    client_tz_str = tz_map[client_tz_str.upper()]
                
                # Use hourly query for non-UTC timezones (PST, EST, etc.)
                use_hourly_query = (client_tz_str.upper() != 'UTC')
            
            if use_hourly_query:
                # Use hourly query with SQL CONVERT_TIMEZONE for PST timezone conversion
                print(f"   🌍 Using hourly query with SQL timezone conversion to {client_tz_str}")
                
                if has_date_range:
                    # Parse date range into year/month/day components (using UTC dates for query)
                    start_dt = datetime.strptime(query_start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(query_end_date, '%Y-%m-%d')
                    
                    start_year = start_dt.year
                    start_month = start_dt.month
                    start_day = start_dt.day
                    end_year = end_dt.year
                    end_month = end_dt.month
                    end_day = end_dt.day
                    
                    start_date_num = start_year * 10000 + start_month * 100 + start_day
                    end_date_num = end_year * 10000 + end_month * 100 + end_day
                    
                    # Query overview table with hourly data and SQL timezone conversion
                    redshift_query = '''
                        SELECT 
                            DATE(CONVERT_TIMEZONE('UTC', %s, 
                                 (TO_DATE(year::VARCHAR || '-' || LPAD(month::VARCHAR, 2, '0') || '-' || LPAD(day::VARCHAR, 2, '0'), 'YYYY-MM-DD')::VARCHAR || ' ' || LPAD(hour::VARCHAR, 2, '0') || ':00:00')::TIMESTAMP)) as date_local,
                            campaign_id,
                            line_item_id,
                            SUM(media_spend) as total_spent,
                            SUM(burl_count) as total_impressions
                        FROM public.overview
                        WHERE campaign_id IN ({})
                          AND (year * 10000 + month * 100 + day) >= %s
                          AND (year * 10000 + month * 100 + day) <= %s
                          AND media_spend > 0
                        GROUP BY date_local, campaign_id, line_item_id
                        ORDER BY date_local, campaign_id, line_item_id
                    '''.format(','.join(['%s'] * len(campaign_uuids)))
                    
                    redshift_params = [client_tz_str] + campaign_uuids + [start_date_num, end_date_num]
                else:
                    # Query overview table without date filters
                    redshift_query = '''
                        SELECT 
                            DATE(CONVERT_TIMEZONE('UTC', %s, 
                                 (TO_DATE(year::VARCHAR || '-' || LPAD(month::VARCHAR, 2, '0') || '-' || LPAD(day::VARCHAR, 2, '0'), 'YYYY-MM-DD')::VARCHAR || ' ' || LPAD(hour::VARCHAR, 2, '0') || ':00:00')::TIMESTAMP)) as date_local,
                            campaign_id,
                            line_item_id,
                            SUM(media_spend) as total_spent,
                            SUM(burl_count) as total_impressions
                        FROM public.overview
                        WHERE campaign_id IN ({})
                          AND media_spend > 0
                        GROUP BY date_local, campaign_id, line_item_id
                        ORDER BY date_local, campaign_id, line_item_id
                    '''.format(','.join(['%s'] * len(campaign_uuids)))
                    
                    redshift_params = [client_tz_str] + campaign_uuids
            else:
                # Use daily aggregates (overview_view) for UTC timezone
                # Build Redshift query conditionally based on whether dates are provided
                if has_date_range:
                    # Parse date range into year/month/day components (using UTC dates for query)
                    start_dt = datetime.strptime(query_start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(query_end_date, '%Y-%m-%d')
                    
                    start_year = start_dt.year
                    start_month = start_dt.month
                    start_day = start_dt.day
                    end_year = end_dt.year
                    end_month = end_dt.month
                    end_day = end_dt.day
                    
                    start_date_num = start_year * 10000 + start_month * 100 + start_day
                    end_date_num = end_year * 10000 + end_month * 100 + end_day

                    # Query Redshift with date filters
                    redshift_query = '''
                        SELECT 
                            year,
                            month,
                            day,
                            campaign_id,
                            line_item_id,
                            SUM(media_spend) as total_spent,
                            SUM(burl_count) as total_impressions
                        FROM public.overview_view
                        WHERE campaign_id IN ({})
                          AND (year * 10000 + month * 100 + day) >= %s
                          AND (year * 10000 + month * 100 + day) <= %s
                          AND media_spend > 0
                        GROUP BY year, month, day, campaign_id, line_item_id
                        ORDER BY year, month, day, campaign_id, line_item_id
                    '''.format(','.join(['%s'] * len(campaign_uuids)))

                    redshift_params = campaign_uuids + [start_date_num, end_date_num]
                else:
                    # Query Redshift without date filters - get all available data
                    redshift_query = '''
                        SELECT 
                            year,
                            month,
                            day,
                            campaign_id,
                            line_item_id,
                            SUM(media_spend) as total_spent,
                            SUM(burl_count) as total_impressions
                        FROM public.overview_view
                        WHERE campaign_id IN ({})
                          AND media_spend > 0
                        GROUP BY year, month, day, campaign_id, line_item_id
                        ORDER BY year, month, day, campaign_id, line_item_id
                    '''.format(','.join(['%s'] * len(campaign_uuids)))

                    redshift_params = campaign_uuids

            redshift_results = self.db.execute_redshift_query(redshift_query, redshift_params)

            if not redshift_results:
                if has_date_range:
                    print("   ⚠️  No daily line item data found in Redshift for the specified date range")
                else:
                    print("   ⚠️  No daily line item data found in Redshift for these campaigns")
                return pd.DataFrame(columns=[
                    'date', 'campaign_id', 'campaign_name',
                    'line_item_id', 'line_item_name', 'total_spent', 'total_impressions'
                ])

            print(f"   ✅ Retrieved {len(redshift_results)} daily records from Redshift")

            # Collect unique line item UUIDs
            # For hourly query: row[2] is line_item_id
            # For daily aggregates: row[4] is line_item_id
            line_item_idx = 2 if use_hourly_query else 4
            line_item_uuids = list(set([
                str(row[line_item_idx]) for row in redshift_results 
                if row[line_item_idx] and str(row[line_item_idx]) != 'None' and str(row[line_item_idx]) != ''
            ]))

            # Query PostgreSQL for line item metadata
            line_item_map = {}
            if line_item_uuids:
                print(f"   🔍 Querying PostgreSQL for {len(line_item_uuids)} line item metadata...")
                try:
                    line_item_query = '''
                        SELECT "lineItemUuid", "lineItemId", "name" 
                        FROM "lineItems" 
                        WHERE "lineItemUuid" IN ({})
                    '''.format(','.join(['%s'] * len(line_item_uuids)))

                    line_item_results = self.db.execute_postgres_query(
                        line_item_query,
                        tuple(line_item_uuids)
                    )

                    line_item_map = {
                        str(row[0]): {
                            'id': int(row[1]) if row[1] else 0,
                            'name': row[2] or f"Line Item {row[1] or 'Unknown'}"
                        }
                        for row in line_item_results
                    }
                    print(f"   ✅ Retrieved metadata for {len(line_item_map)} line items")
                except Exception as e:
                    print(f"   ⚠️  Could not fetch line item metadata: {e}")

            # Merge Redshift spend data with PostgreSQL metadata
            # Also filter out dates that are "in the future" relative to client timezone
            daily_records = []
            
            # Calculate today in client timezone for filtering
            today_client = None
            if self.timezone_handler:
                client_tz_str = self.client_config.get('timezone_full') or self.client_config.get('timezone', 'UTC')
                client_tz = pytz.timezone(client_tz_str) if client_tz_str != 'UTC' else pytz.UTC
                
                # Map common abbreviations
                tz_map = {
                    'PST': 'America/Los_Angeles',
                    'PDT': 'America/Los_Angeles',
                    'EST': 'America/New_York',
                    'EDT': 'America/New_York',
                }
                if client_tz_str.upper() in tz_map:
                    client_tz = pytz.timezone(tz_map[client_tz_str.upper()])
                
                now_client = datetime.now(client_tz)
                today_client = now_client.date()
            
            for row in redshift_results:
                if use_hourly_query:
                    # Hourly query returns: date_local (already in PST), campaign_id, line_item_id, total_spent, total_impressions
                    date_local = row[0]  # Already converted to PST by SQL
                    campaign_uuid = str(row[1])
                    line_item_uuid = str(row[2]) if row[2] else None
                    total_spent = round(float(row[3]) if row[3] else 0.0, 2)
                    total_impressions = int(row[4]) if row[4] else 0
                    
                    # Convert date_local to string (it's already a date object from SQL)
                    if isinstance(date_local, date):
                        date_str = date_local.strftime('%Y-%m-%d')
                    else:
                        # Fallback: parse if it's a string
                        date_str = str(date_local)[:10] if len(str(date_local)) >= 10 else str(date_local)
                    
                    # Filter future dates (dates > today in PST)
                    if today_client is not None:
                        date_obj = date_local if isinstance(date_local, date) else datetime.strptime(date_str, '%Y-%m-%d').date()
                        if date_obj > today_client:
                            continue
                else:
                    # Daily aggregates query returns: year, month, day, campaign_id, line_item_id, total_spent, total_impressions
                    year = int(row[0]) if row[0] else 2025
                    month = int(row[1]) if row[1] else 11
                    day = int(row[2]) if row[2] else 1
                    campaign_uuid = str(row[3])
                    line_item_uuid = str(row[4]) if row[4] else None
                    total_spent = round(float(row[5]) if row[5] else 0.0, 2)
                    total_impressions = int(row[6]) if row[6] else 0
                    
                    # UTC timezone - use Redshift dates as-is (they're already UTC)
                    date_str = f"{year:04d}-{month:02d}-{day:02d}"
                    
                    # Filter by today in UTC
                    if today_client is not None:
                        date_utc = date(year, month, day)
                        if date_utc > today_client:
                            continue

                campaign_info = campaign_uuid_map.get(campaign_uuid, {})
                campaign_id = campaign_info.get('campaign_id', 0)
                campaign_name = campaign_info.get('campaign_name', f"Campaign {campaign_uuid[:8]}")

                if line_item_uuid and line_item_uuid != 'None' and line_item_uuid != '':
                    line_item_info = line_item_map.get(line_item_uuid, {})
                    line_item_id = line_item_info.get('id', 0)
                    line_item_name = line_item_info.get('name', f"Line Item {line_item_uuid[:8]}")
                else:
                    line_item_id = 0
                    line_item_name = "Unknown Line Item"

                daily_records.append((
                    date_str,
                    campaign_id,
                    campaign_name,
                    line_item_id,
                    line_item_name,
                    total_spent,
                    total_impressions
                ))

            daily_df = pd.DataFrame(
                daily_records,
                columns=[
                    'date', 'campaign_id', 'campaign_name',
                    'line_item_id', 'line_item_name', 'total_spent', 'total_impressions'
                ]
            )
            print(f"   ✅ Collected {len(daily_df)} daily line item records")
            return daily_df

        except Exception as e:
            print(f"   ❌ Error collecting daily line item data: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            return pd.DataFrame(columns=[
                'date', 'campaign_id', 'campaign_name',
                'line_item_id', 'line_item_name', 'total_spent', 'total_impressions'
            ])

    def _get_advertiser_name(self) -> str:
        """Get the actual advertiser name from the database."""
        try:
            advertiser_query = '''
                SELECT "name" FROM "advertisers"
                WHERE "accountId" = %s
                LIMIT 1
            '''
            results = self.db.execute_postgres_query(advertiser_query, (int(self.account_id),))
            if results:
                return results[0][0]
        except Exception:
            pass

        try:
            account_query = '''
                SELECT "name" FROM "accounts"
                WHERE "accountId" = %s
            '''
            results = self.db.execute_postgres_query(account_query, (int(self.account_id),))
            if results:
                account_name = results[0][0]
                if "lilly" in account_name.lower():
                    return "Eli Lilly"
                return account_name
        except Exception:
            pass

        return self.advertiser_filter or "Unknown Advertiser"

    def _get_client_name(self) -> str:
        """Get the client name from the database using account ID."""
        # Get account name (this is the client/agency name)
        try:
            account_query = '''
                SELECT "name" FROM "accounts"
                WHERE "accountId" = %s
            '''
            results = self.db.execute_postgres_query(account_query, (int(self.account_id),))
            if results:
                account_name = results[0][0]
                # Apply known transformations
                if "lilly" in account_name.lower():
                    return "Eli Lilly"
                return account_name
        except Exception as e:
            print(f"   ⚠️ Could not get account name: {e}")

        return f"Account {self.account_id}"

    def _export_rollup_csvs(self, rollups: Dict[str, pd.DataFrame], advertiser_name: str) -> Dict[str, str]:
        """Export rollups directly to reports/ directory (overwrite existing files)."""
        reports_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
        os.makedirs(reports_dir, exist_ok=True)

        csv_paths = {}
        for rollup_key, df in rollups.items():
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue

            # Round float columns to 2 decimals before exporting
            df_export = df.copy()
            float_cols = ['spend', 'total_spend', 'spend_percentage', 'prev_day_spend_ratio', 'avg_daily_spend']
            for col in float_cols:
                if col in df_export.columns:
                    # Use 4 decimal places for spend_percentage, 2 for others
                    decimal_places = 4 if col == 'spend_percentage' else 2
                    df_export[col] = df_export[col].round(decimal_places)

            file_path = os.path.join(reports_dir, f"{rollup_key}.csv")

            # Special handling for spend_percentage - convert to string with 4 decimal places
            if 'spend_percentage' in df_export.columns:
                df_export['spend_percentage'] = df_export['spend_percentage'].apply(lambda x: f"{x:.4f}" if pd.notna(x) else '')

            # Export CSV with NaN values as empty strings for better readability
            df_export.to_csv(file_path, index=False, float_format='%.2f', na_rep='')
            csv_paths[rollup_key] = file_path

        if csv_paths:
            print("📁 Rollup CSVs generated:")
            for rollup_key, path in csv_paths.items():
                print(f"   • {rollup_key}: {os.path.basename(path)}")

        return csv_paths

