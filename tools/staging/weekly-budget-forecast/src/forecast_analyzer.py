"""
Forecast Analyzer
=================

Analyzes spend and impressions for campaigns for weekly budget forecasting.
Supports ALL campaigns across ALL accounts by default, with optional filtering.
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Add shared and campaign-analysis to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "campaign-analysis", "src"))

from database_connector import DatabaseConnector
from campaign_discovery import CampaignDiscovery


class ForecastAnalyzer:
    """Analyzes spend and impressions for campaigns for weekly budget forecasting"""

    def __init__(self, account_id: str = None, advertiser_filter: str = None):
        """
        Initialize with optional account ID and advertiser filter.
        If not provided, analyzes ALL campaigns across ALL accounts.
        
        Args:
            account_id (str, optional): Account ID filter
            advertiser_filter (str, optional): Advertiser filter for campaign selection
        """
        self.account_id = account_id
        self.advertiser_filter = advertiser_filter
        self.db = DatabaseConnector()
        self.discovery = CampaignDiscovery()

    def _discover_campaigns(self) -> List[Dict[str, Any]]:
        """
        Discover campaigns with budget, start_date, and end_date.
        If account_id is provided, filters by account. Otherwise returns ALL campaigns.
        """
        if self.account_id:
            # Filter by account ID
            # Campaigns belong to one advertiser (via c."advertiserId") and one account (via lineItems -> curationPackages)
            campaign_query = '''
                SELECT DISTINCT ON (c."campaignId")
                    c."campaignId", 
                    c."name", 
                    c."totalBudget", 
                    c."campaignUuid",
                    c."startDate", 
                    c."endDate",
                    COALESCE(a."name", 'Unknown') as account_name,
                    COALESCE(adv."name", 'Unknown') as advertiser_name
                FROM "lineItems" li
                JOIN "campaigns" c ON li."campaignId" = c."campaignId"
                LEFT JOIN "advertisers" adv ON c."advertiserId" = adv."advertiserId"
                LEFT JOIN "curationPackages" cp ON li."curationPackageId" = cp."curationPackageId"
                LEFT JOIN "accounts" a ON cp."accountId" = a."accountId"
                WHERE cp."accountId" = %s
                    AND c."statusId" IN (1, 2, 3)
                ORDER BY c."campaignId", a."name" NULLS LAST
            '''
            results = self.db.execute_postgres_query(campaign_query, (int(self.account_id),))
        else:
            # Get ALL campaigns across ALL accounts with account and advertiser info
            # Campaigns belong to one advertiser (via c."advertiserId") and one account (via lineItems -> curationPackages)
            campaign_query = '''
                SELECT DISTINCT ON (c."campaignId")
                    c."campaignId", 
                    c."name", 
                    c."totalBudget", 
                    c."campaignUuid",
                    c."startDate", 
                    c."endDate",
                    COALESCE(a."name", 'Unknown') as account_name,
                    COALESCE(adv."name", 'Unknown') as advertiser_name
                FROM "campaigns" c
                LEFT JOIN "advertisers" adv ON c."advertiserId" = adv."advertiserId"
                LEFT JOIN "lineItems" li ON c."campaignId" = li."campaignId"
                LEFT JOIN "curationPackages" cp ON li."curationPackageId" = cp."curationPackageId"
                LEFT JOIN "accounts" a ON cp."accountId" = a."accountId"
                WHERE c."statusId" IN (1, 2, 3)
                ORDER BY c."campaignId", a."name" NULLS LAST
            '''
            results = self.db.execute_postgres_query(campaign_query)

        campaigns = []
        for row in results:
            # Parse dates - handle both date and datetime objects
            start_date_obj = row[4]
            end_date_obj = row[5]
            
            if start_date_obj:
                if isinstance(start_date_obj, datetime):
                    start_date_str = start_date_obj.date().isoformat()
                else:
                    start_date_str = start_date_obj.isoformat() if hasattr(start_date_obj, 'isoformat') else str(start_date_obj)
                    # Remove timestamp if present (e.g., "2024-12-16T00:00:00" -> "2024-12-16")
                    if 'T' in start_date_str:
                        start_date_str = start_date_str.split('T')[0]
            else:
                start_date_str = None
            
            if end_date_obj:
                if isinstance(end_date_obj, datetime):
                    end_date_str = end_date_obj.date().isoformat()
                else:
                    end_date_str = end_date_obj.isoformat() if hasattr(end_date_obj, 'isoformat') else str(end_date_obj)
                    # Remove timestamp if present
                    if 'T' in end_date_str:
                        end_date_str = end_date_str.split('T')[0]
            else:
                end_date_str = None
            
            campaign = {
                'campaign_id': row[0],
                'campaign_name': row[1],
                'budget': float(row[2]) if row[2] else 0.0,
                'campaign_uuid': row[3],
                'start_date': start_date_str,
                'end_date': end_date_str,
                'account_name': row[6] if len(row) > 6 else None,
                'advertiser_name': row[7] if len(row) > 7 else None
            }
            campaigns.append(campaign)

        # Apply advertiser filter if specified
        if self.advertiser_filter:
            filtered_campaigns = []
            for campaign in campaigns:
                if self.advertiser_filter.lower() in campaign['campaign_name'].lower():
                    filtered_campaigns.append(campaign)
            print(f"   Filtered to {len(filtered_campaigns)} campaigns for advertiser: {self.advertiser_filter!s}")
            return filtered_campaigns

        return campaigns

    def _collect_daily_line_items(
        self, 
        campaigns: List[Dict[str, Any]], 
        start_date: str = None, 
        end_date: str = None
    ) -> pd.DataFrame:
        """
        Collect daily line item performance data for 6 weeks past + 6 weeks future.
        If dates not provided, calculates automatically: today - 42 days to today + 42 days.
        
        Uses UTC for all date calculations.
        
        Returns:
            DataFrame with daily line item records
        """
        # Calculate date range if not provided
        if not start_date or not end_date:
            today = datetime.now().date()
            start_date = (today - timedelta(days=42)).strftime('%Y-%m-%d')  # 6 weeks past
            end_date = (today + timedelta(days=42)).strftime('%Y-%m-%d')    # 6 weeks future
            print(f"   📅 Auto-calculated date range: {start_date} to {end_date} (6 weeks past + 6 weeks future)")
        else:
            print(f"   📅 Collecting daily line item data from {start_date} to {end_date}...")

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

            # Parse date range into year/month/day components (UTC)
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
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

            redshift_results = self.db.execute_redshift_query(redshift_query, redshift_params)

            if not redshift_results:
                print("   ⚠️  No daily line item data found in Redshift for the specified date range")
                return pd.DataFrame(columns=[
                    'date', 'campaign_id', 'campaign_name',
                    'line_item_id', 'line_item_name', 'total_spent', 'total_impressions'
                ])

            print(f"   ✅ Retrieved {len(redshift_results)} daily records from Redshift")

            # Collect unique line item UUIDs
            line_item_uuids = list(set([
                row[4] for row in redshift_results 
                if row[4] and row[4] != 'None' and row[4] != ''
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
            daily_records = []
            for row in redshift_results:
                year = int(row[0]) if row[0] else 2025
                month = int(row[1]) if row[1] else 11
                day = int(row[2]) if row[2] else 1
                campaign_uuid = str(row[3])
                line_item_uuid = str(row[4]) if row[4] else None
                total_spent = round(float(row[5]) if row[5] else 0.0, 2)  # Round to 2 decimals
                total_impressions = int(row[6]) if row[6] else 0
                
                date_str = f"{year:04d}-{month:02d}-{day:02d}"

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

