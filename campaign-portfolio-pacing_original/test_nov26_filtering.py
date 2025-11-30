#!/usr/bin/env python3
"""
Diagnostic Test for Nov 26 PST Filtering Issue
==============================================

Tests why Nov 26 PST data is not showing up when it's Nov 26 1:53 AM PST.

This script:
1. Checks what "today" is calculated as in PST
2. Queries for Nov 26 PST data specifically
3. Checks if Nov 26 PST data exists but is being filtered out
4. Verifies the filtering logic
"""

import os
import sys
from datetime import datetime, date, timedelta
import pytz

# Load environment variables manually
env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from database_connector import DatabaseConnector
from timezone_handler import TimezoneHandler


def test_nov26_filtering():
    """Test why Nov 26 PST data is not showing up."""
    
    print("=" * 80)
    print("NOV 26 PST FILTERING DIAGNOSTIC")
    print("=" * 80)
    
    # Initialize database
    db = DatabaseConnector()
    print("✅ PostgreSQL connected")
    print("✅ Redshift connected")
    
    # Get campaign UUIDs for Eli Lilly
    print("\n📋 Getting campaign UUIDs for Eli Lilly...")
    campaign_query = '''
        SELECT DISTINCT c."campaignId", c."campaignUuid", c."name"
        FROM "lineItems" li
        JOIN "campaigns" c ON li."campaignId" = c."campaignId"
        LEFT JOIN "advertisers" adv ON c."advertiserId" = adv."advertiserId"
        LEFT JOIN "curationPackages" cp ON li."curationPackageId" = cp."curationPackageId"
        WHERE cp."accountId" = %s
            AND c."statusId" IN (1, 2, 3)
            AND adv."name" ILIKE %s
        ORDER BY c."campaignId"
        LIMIT 5
    '''
    
    campaigns = db.execute_postgres_query(campaign_query, (17, '%Lilly%'))
    campaign_uuids = [str(c[1]) for c in campaigns]
    print(f"✅ Found {len(campaign_uuids)} campaigns")
    
    # Test PST timezone
    pst_tz = pytz.timezone('America/Los_Angeles')
    now_pst = datetime.now(pst_tz)
    today_pst = now_pst.date()
    
    print("\n" + "=" * 80)
    print("CURRENT TIME CHECK")
    print("=" * 80)
    print(f"📅 Current time PST: {now_pst}")
    print(f"📅 Today in PST: {today_pst}")
    print(f"📅 Current time UTC: {now_pst.astimezone(pytz.UTC)}")
    print(f"📅 Today in UTC: {now_pst.astimezone(pytz.UTC).date()}")
    
    # Test 1: Query for Nov 26 PST data specifically
    print("\n" + "=" * 80)
    print("TEST 1: Query Nov 26 PST Data (Hourly Query)")
    print("=" * 80)
    
    # Simulate what the tool does: convert "today" PST end of day to UTC
    pst_tz = pytz.timezone('America/Los_Angeles')
    today_pst_end = datetime(2025, 11, 26, 23, 59, 59)
    today_pst_end = pst_tz.localize(today_pst_end)
    today_pst_end_utc = today_pst_end.astimezone(pytz.UTC)
    end_date_utc = today_pst_end_utc.date()
    
    # Start date: 6 months ago
    start_date_utc = date(2025, 5, 30)
    
    print(f"📅 Today PST end: {today_pst_end}")
    print(f"📅 Today PST end UTC: {today_pst_end_utc}")
    print(f"📅 End date UTC: {end_date_utc}")
    
    print(f"📅 Querying UTC dates: {start_date_utc} to {end_date_utc}")
    print("   (This should capture all Nov 26 PST data)")
    
    try:
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
        
        start_date_num = start_date_utc.year * 10000 + start_date_utc.month * 100 + start_date_utc.day
        end_date_num = end_date_utc.year * 10000 + end_date_utc.month * 100 + end_date_utc.day
        
        params = ['America/Los_Angeles'] + campaign_uuids + [start_date_num, end_date_num]
        results = db.execute_redshift_query(redshift_query, params)
        
        if not results:
            print("❌ No results found for Nov 25-27 UTC range")
            return
        
        print(f"✅ Retrieved {len(results)} records")
        
        # Group by PST date
        by_date = {}
        for row in results:
            pst_date = row[0]  # Already converted to PST by SQL
            if isinstance(pst_date, date):
                date_str = pst_date.strftime('%Y-%m-%d')
            else:
                date_str = str(pst_date)[:10]
            
            if date_str not in by_date:
                by_date[date_str] = {'spend': 0, 'impressions': 0, 'count': 0}
            
            by_date[date_str]['spend'] += float(row[3] or 0)
            by_date[date_str]['impressions'] += int(row[4] or 0)
            by_date[date_str]['count'] += 1
        
        print("\n📊 Data by PST Date:")
        print("-" * 60)
        print("PST Date     Records    Spend           Impressions")
        print("-" * 60)
        for date_str in sorted(by_date.keys()):
            data = by_date[date_str]
            print(f"{date_str}   {data['count']:>5}   ${data['spend']:>10.2f}   {data['impressions']:>10}")
        
        # Check if Nov 26 PST data exists
        nov26_str = "2025-11-26"
        if nov26_str in by_date:
            print(f"\n✅ Nov 26 PST data EXISTS: {by_date[nov26_str]['count']} records, ${by_date[nov26_str]['spend']:.2f} spend")
        else:
            print(f"\n❌ Nov 26 PST data DOES NOT EXIST in query results")
        
        # Test 2: Check filtering logic
        print("\n" + "=" * 80)
        print("TEST 2: Filtering Logic Check")
        print("=" * 80)
        
        print(f"📅 Today in PST: {today_pst}")
        print(f"📅 Filter condition: date_obj > today_client")
        print(f"📅 Filter condition: date_obj > {today_pst}")
        
        nov26_date = date(2025, 11, 26)
        print(f"\n📅 Nov 26 PST date object: {nov26_date}")
        print(f"📅 Comparison: {nov26_date} > {today_pst} = {nov26_date > today_pst}")
        print(f"📅 Comparison: {nov26_date} == {today_pst} = {nov26_date == today_pst}")
        print(f"📅 Comparison: {nov26_date} <= {today_pst} = {nov26_date <= today_pst}")
        
        if nov26_date > today_pst:
            print("\n❌ PROBLEM: Nov 26 PST is being filtered out because it's > today!")
            print("   This means today_client is being calculated as Nov 25 or earlier")
        elif nov26_date == today_pst:
            print("\n✅ Nov 26 PST should NOT be filtered (date_obj == today_client)")
        else:
            print("\n✅ Nov 26 PST should NOT be filtered (date_obj < today_client)")
        
        # Test 3: Check what the actual tool would calculate
        print("\n" + "=" * 80)
        print("TEST 3: Simulate Tool's today_client Calculation")
        print("=" * 80)
        
        client_config = {'timezone': 'PST', 'timezone_full': 'America/Los_Angeles'}
        tz_handler = TimezoneHandler(client_config)
        
        # Simulate what the tool does
        client_tz_str = client_config.get('timezone_full') or client_config.get('timezone', 'UTC')
        tz_map = {
            'PST': 'America/Los_Angeles',
            'PDT': 'America/Los_Angeles',
            'EST': 'America/New_York',
            'EDT': 'America/New_York',
        }
        if client_tz_str.upper() in tz_map:
            client_tz_str = tz_map[client_tz_str.upper()]
        
        client_tz = pytz.timezone(client_tz_str)
        now_client = datetime.now(client_tz)
        today_client = now_client.date()
        
        print(f"📅 Client timezone: {client_tz_str}")
        print(f"📅 Now in client TZ: {now_client}")
        print(f"📅 Today in client TZ: {today_client}")
        print(f"📅 Comparison with Nov 26: {date(2025, 11, 26)} > {today_client} = {date(2025, 11, 26) > today_client}")
        
        # Test 4: Check if Nov 26 data exists but is filtered
        print("\n" + "=" * 80)
        print("TEST 4: Check Filtering Impact")
        print("=" * 80)
        
        if nov26_str in by_date:
            print(f"✅ Nov 26 PST data exists in query results")
            print(f"   Records: {by_date[nov26_str]['count']}")
            print(f"   Spend: ${by_date[nov26_str]['spend']:.2f}")
            print(f"   Impressions: {by_date[nov26_str]['impressions']}")
            
            # Simulate filtering
            nov26_date_obj = date(2025, 11, 26)
            if nov26_date_obj > today_client:
                print(f"\n❌ FILTERING ISSUE: Nov 26 PST ({nov26_date_obj}) > today_client ({today_client})")
                print("   Nov 26 data would be FILTERED OUT incorrectly!")
            else:
                print(f"\n✅ FILTERING OK: Nov 26 PST ({nov26_date_obj}) <= today_client ({today_client})")
                print("   Nov 26 data would be INCLUDED")
        else:
            print(f"❌ Nov 26 PST data does NOT exist in query results")
            print("   This means either:")
            print("   1. There's no data for Nov 26 PST yet (too early in the day)")
            print("   2. The query isn't capturing Nov 26 PST data correctly")
        
        # Test 5: Check what UTC dates map to Nov 26 PST
        print("\n" + "=" * 80)
        print("TEST 5: UTC to PST Date Mapping for Nov 26")
        print("=" * 80)
        
        print("Nov 26 PST spans:")
        print("  - Nov 25 UTC 16:00-23:59 → Nov 25 PST 08:00-15:59")
        print("  - Nov 26 UTC 00:00-15:59 → Nov 25 PST 16:00-23:59")
        print("  - Nov 26 UTC 16:00-23:59 → Nov 26 PST 00:00-07:59")
        print("  - Nov 27 UTC 00:00-07:59 → Nov 26 PST 16:00-23:59")
        print("  - Nov 27 UTC 08:00-23:59 → Nov 27 PST 00:00-15:59")
        
        print(f"\nCurrent time: {now_pst.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Current UTC: {now_pst.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        if now_pst.hour < 16:
            print("\n⚠️  It's early morning PST (< 4 PM PST)")
            print("   Most of Nov 26 UTC hasn't happened yet")
            print("   Nov 26 PST data might be sparse or non-existent")
        else:
            print("\n✅ It's afternoon/evening PST (>= 4 PM PST)")
            print("   Nov 26 UTC has started, so Nov 26 PST data should exist")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_nov26_filtering()

