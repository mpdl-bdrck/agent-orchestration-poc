"""
Billing Analyzer
================

Analyzes spend and impressions for billing purposes based on account/client criteria.
Adapted from campaign_analyzer.py for billing-specific use cases.
"""

import os
import sys
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import pytz

# Add shared and campaign-analysis to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "campaign-analysis", "src"))

from database_connector import DatabaseConnector
from campaign_discovery import CampaignDiscovery
from .timezone_handler import TimezoneHandler
from .utils.config import config


class BillingAnalyzer:
    """Analyzes spend and impressions for billing purposes based on account/client criteria"""

    DEFAULT_ACCOUNT_ID = 17  # Tricoast Media LLC

    def __init__(self, account_id: str = None, client_name: str = None, client_config: Dict[str, Any] = None):
        """
        Initialize with account ID, client name, and client config

        Args:
            account_id (str): Account ID
            client_name (str): Client name (e.g., "Tricoast Media LLC")
            client_config (dict): Client configuration dictionary (includes timezone, etc.)
        """
        self.account_id = account_id or str(self.DEFAULT_ACCOUNT_ID)
        self.client_name = client_name or "Unknown"
        self.client_config = client_config or {}
        self.db = DatabaseConnector()
        self.discovery = CampaignDiscovery()

        # Initialize timezone handler from client config
        if self.client_config:
            self.timezone_handler = TimezoneHandler(self.client_config)
        else:
            self.timezone_handler = None

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

    def run_analysis(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        Run billing analysis workflow:
        1. Discover campaigns for account
        2. Collect advertiser information for campaigns
        3. Collect daily line item performance data (with timezone handling)
        
        Args:
            start_date (str): Start date (YYYY-MM-DD)
            end_date (str): End date (YYYY-MM-DD)
            
        Returns:
            dict: Analysis results with campaigns, daily line items, and advertiser info
        """
        print(f"\n💰 Billing Analysis: Account {self.account_id}")
        if self.client_name and self.client_name != "Unknown":
            print(f"   Client: {self.client_name}")
        print("=" * 70)

        try:
            # Step 1: Discover campaigns
            print("\n📊 STEP 1: Discovering campaigns...")
            print("-" * 40)
            campaigns = self._discover_campaigns()
            print(f"✅ Found {len(campaigns)} campaigns")

            if not campaigns:
                print("⚠️  No campaigns found matching criteria")
                return {"campaigns_analyzed": 0, "error": "No campaigns found"}

            # Step 2: Collect advertiser information for campaigns
            print("\n📋 STEP 2: Collecting advertiser information...")
            print("-" * 40)
            campaigns_with_advertisers = self._collect_advertiser_info(campaigns)
            print(f"✅ Collected advertiser info for {len(campaigns_with_advertisers)} campaigns")

            # Step 3: Collect daily line item data (with timezone handling)
            print("\n📅 STEP 3: Collecting daily line item data...")
            print("-" * 40)
            daily_line_items = self._collect_daily_line_items(
                campaigns_with_advertisers, 
                start_date, 
                end_date
            )

            if daily_line_items.empty:
                print("⚠️  No daily line item data found")
                return {
                    "campaigns_analyzed": len(campaigns_with_advertisers), 
                    "daily_records": 0, 
                    "error": "No data found"
                }

            unique_campaigns = daily_line_items['campaign_id'].nunique()
            unique_advertisers = daily_line_items['advertiser_name'].nunique()
            print(f"✅ Collected {len(daily_line_items)} daily records")
            print(f"   📊 Across {unique_campaigns} campaigns")
            print(f"   📊 Across {unique_advertisers} advertisers")

            # Prepare return data
            result_data = {
                'client_name': self.client_name,
                'campaigns_analyzed': len(campaigns_with_advertisers),
                'daily_records_collected': len(daily_line_items),
                'date_range': f"{start_date or '2025-11-01'} to {end_date or datetime.now().strftime('%Y-%m-%d')}",
                'daily_line_items': daily_line_items,
                'campaigns': campaigns_with_advertisers
            }

            print("\n🎉 Billing Analysis Complete!")
            print("=" * 70)
            print(f"🎯 Account: {self.account_id}")
            print(f"🎯 Client: {self.client_name}")
            print(f"🎯 Campaigns: {len(campaigns_with_advertisers)}")
            print(f"🎯 Daily Records: {len(daily_line_items)}")

            return result_data

        except Exception as e:
            print(f"\n❌ Analysis failed: {e}")
            import traceback
            print(traceback.format_exc())
            return {"error": str(e)}

    def _discover_campaigns(self) -> List[Dict[str, Any]]:
        """Discover all campaigns for the account using curation package approach"""
        campaign_query = '''
            SELECT DISTINCT c."campaignId", c."name", c."totalBudget", c."campaignUuid"
            FROM "lineItems" li
            JOIN "campaigns" c ON li."campaignId" = c."campaignId"
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
                'campaign_uuid': row[3]
            }
            campaigns.append(campaign)

        return campaigns

    def _collect_advertiser_info(self, campaigns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Collect advertiser information for each campaign
        
        Args:
            campaigns: List of campaign dictionaries
            
        Returns:
            List of campaign dictionaries with advertiser_name added
        """
        campaigns_with_advertisers = []
        
        for campaign in campaigns:
            campaign_id = campaign['campaign_id']
            
            # Query for advertiser associated with this campaign
            advertiser_query = '''
                SELECT DISTINCT a."name"
                FROM "campaigns" c
                JOIN "advertisers" a ON c."advertiserId" = a."advertiserId"
                WHERE c."campaignId" = %s
                LIMIT 1
            '''
            
            try:
                results = self.db.execute_postgres_query(advertiser_query, (campaign_id,))
                if results:
                    advertiser_name = results[0][0]
                else:
                    advertiser_name = "Unknown Advertiser"
            except Exception as e:
                print(f"   ⚠️  Could not fetch advertiser for campaign {campaign_id}: {e}")
                advertiser_name = "Unknown Advertiser"
            
            campaign['advertiser_name'] = advertiser_name
            campaigns_with_advertisers.append(campaign)
        
        return campaigns_with_advertisers

    def _collect_daily_line_items(
        self, 
        campaigns: List[Dict[str, Any]], 
        start_date: str = None, 
        end_date: str = None
    ) -> pd.DataFrame:
        """
        Collect daily line item performance data with timezone handling
        
        Args:
            campaigns: List of campaign dictionaries with advertiser_name
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            
        Returns:
            DataFrame with daily line item records including advertiser_name
        """
        # Set default date range if not provided
        if not start_date:
            start_date = '2025-11-01'
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        print(f"   📅 Collecting daily line item data from {start_date} to {end_date}...")

        # Convert dates to UTC if timezone handler is available (for query range)
        has_date_range = bool(start_date and end_date)
        if self.timezone_handler and has_date_range:
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

        try:
            # Prepare campaign UUIDs and mapping (including advertiser_name)
            campaign_uuids = [c['campaign_uuid'] for c in campaigns]
            campaign_uuid_map = {
                c['campaign_uuid']: {
                    'campaign_id': c['campaign_id'],
                    'campaign_name': c['campaign_name'],
                    'advertiser_name': c.get('advertiser_name', 'Unknown Advertiser')
                }
                for c in campaigns
            }

            if not campaign_uuids:
                print("   ⚠️  No campaign UUIDs found")
                return pd.DataFrame(columns=[
                    'date', 'campaign_id', 'campaign_name', 'advertiser_name',
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
                    'date', 'campaign_id', 'campaign_name', 'advertiser_name',
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
                advertiser_name = campaign_info.get('advertiser_name', 'Unknown Advertiser')

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
                    advertiser_name,
                    line_item_id,
                    line_item_name,
                    total_spent,
                    total_impressions
                ))

            daily_df = pd.DataFrame(
                daily_records,
                columns=[
                    'date', 'campaign_id', 'campaign_name', 'advertiser_name',
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
                'date', 'campaign_id', 'campaign_name', 'advertiser_name',
                'line_item_id', 'line_item_name', 'total_spent', 'total_impressions'
            ])

