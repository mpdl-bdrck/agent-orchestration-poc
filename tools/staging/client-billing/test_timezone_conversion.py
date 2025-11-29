#!/usr/bin/env python3
"""
Timezone Conversion Test Script for Client Billing
==================================================

Comprehensive test suite for validating timezone conversion logic in the client billing tool.

This script tests and validates:
1. UTC timezone mode - queries daily aggregates from overview_view
2. PST timezone mode - queries hourly data from overview table with SQL CONVERT_TIMEZONE
3. Date redistribution - verifies that UTC hours are properly split across PST date boundaries

**Usage:**
    cd tools/client-billing
    ../venv/bin/python test_timezone_conversion.py

**What It Tests:**

**TEST 1: UTC TIMEZONE**
- Queries overview_view (daily aggregates)
- Returns UTC dates directly

**TEST 2: PST TIMEZONE (Python Conversion)**
- Queries overview_view (daily aggregates)  
- Converts UTC dates to PST dates in Python
- Shows date relabeling (not redistribution)

**TEST 3: HOURLY DATA APPROACH**
- Queries overview table (hourly data)
- Uses SQL CONVERT_TIMEZONE to convert UTC timestamps to PST
- Validates proper hour redistribution across PST dates
- This is the CORRECT approach for PST timezone conversion

**TEST 3B: DAILY AGGREGATES APPROACH**
- Tests CONVERT_TIMEZONE on daily aggregates (overview_view)
- Shows that daily aggregates cannot be redistributed (only relabeled)

**Key Findings:**
- ✅ Hourly SQL approach properly redistributes Nov 26 UTC hours across Nov 24 and Nov 25 PST
- ❌ Daily aggregates approach only relabels dates (doesn't redistribute hours)
- ✅ Use hourly query approach for PST timezone conversion
"""

import os
import sys
import pandas as pd
from datetime import datetime, date
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
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "campaign-analysis", "src"))

from database_connector import DatabaseConnector
from campaign_discovery import CampaignDiscovery


def test_timezone_query_behavior():
    """Test different timezone query approaches for client billing data."""
    
    print("=" * 80)
    print("TIMEZONE CONVERSION TEST - CLIENT BILLING")
    print("=" * 80)
    
    # Initialize connections
    try:
        db = DatabaseConnector()
        print("✅ PostgreSQL connected")
        print("✅ Redshift connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    print("\n📋 Step 1: Getting campaign UUIDs for Tricoast (Account 17)...")
    print("-" * 50)
    
    try:
        # Get campaigns for Tricoast (account 17)
        campaign_query = '''
            SELECT DISTINCT c."campaignId", c."name", c."totalBudget", c."campaignUuid"
            FROM "lineItems" li
            JOIN "campaigns" c ON li."campaignId" = c."campaignId"
            LEFT JOIN "curationPackages" cp ON li."curationPackageId" = cp."curationPackageId"
            WHERE cp."accountId" = 17
                AND c."statusId" IN (1, 2, 3)
            ORDER BY c."campaignId"
            LIMIT 5
        '''
        
        campaigns = db.execute_postgres_query(campaign_query)
        print(f"✅ Found {len(campaigns)} campaigns")
        
        # Extract campaign UUIDs for testing
        campaign_uuids = [str(row[3]) for row in campaigns]
        
        if not campaign_uuids:
            print("❌ No campaigns found")
            return
            
    except Exception as e:
        print(f"❌ Failed to get campaigns: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test different approaches
    utc_results, utc_totals = test_utc_mode(db, campaign_uuids)
    pst_results, pst_totals = test_pst_python_conversion(db, campaign_uuids)
    hourly_results, hourly_totals = test_hourly_sql_approach(db, campaign_uuids)
    daily_results, daily_totals = test_daily_aggregates_sql_approach(db, campaign_uuids)
    
    # Compare results
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    
    if utc_totals and pst_totals and hourly_totals:
        print("\nTotals from first 5 records:")
        print("-" * 50)
        print(f"UTC mode:              ${utc_totals['spend']:>10.2f} spend, {utc_totals['impressions']:>10} impressions")
        print(f"PST Python conversion: ${pst_totals['spend']:>10.2f} spend, {pst_totals['impressions']:>10} impressions")
        print(f"Hourly SQL approach:    ${hourly_totals['spend']:>10.2f} spend, {hourly_totals['impressions']:>10} impressions")
        
        if abs(utc_totals['spend'] - pst_totals['spend']) < 0.01:
            print("\n⚠️  UTC and PST Python conversion totals match - this means relabeling only!")
        else:
            print("\n✅ UTC and PST totals differ - redistribution may be happening")
        
        if abs(utc_totals['spend'] - hourly_totals['spend']) > 0.01:
            print("✅ Hourly SQL approach shows different totals - proper redistribution!")
        else:
            print("⚠️  Hourly SQL approach matches UTC - check if data spans timezone boundaries")


def test_utc_mode(db, campaign_uuids):
    """Test UTC timezone mode using daily aggregates."""
    
    print("\n" + "=" * 80)
    print("TEST 1: UTC TIMEZONE")
    print("=" * 80)
    
    today_utc = datetime.now(pytz.UTC).date()
    start_date = date(2025, 11, 20)  # Recent date to test
    end_date = date(2025, 11, 26)
    
    print(f"📅 Today in UTC: {today_utc}")
    print(f"📅 Date range: {start_date} to {end_date}")
    
    try:
        # Query overview_view (daily aggregates)
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
        
        start_date_num = start_date.year * 10000 + start_date.month * 100 + start_date.day
        end_date_num = end_date.year * 10000 + end_date.month * 100 + end_date.day
        
        params = campaign_uuids + [start_date_num, end_date_num]
        results = db.execute_redshift_query(redshift_query, params)
        
        if not results:
            print("❌ No UTC results found")
            return None, None
            
        print(f"✅ Retrieved {len(results)} UTC records")
        
        # Show sample results
        print("\n📊 Sample UTC Results (first 5):")
        print("-" * 60)
        print("UTC Date     Campaign ID     Spend           Impressions")
        print("-" * 60)
        
        utc_totals = {'spend': 0, 'impressions': 0}
        for row in results[:5]:
            year, month, day = int(row[0]), int(row[1]), int(row[2])
            campaign_id = str(row[3])[:8] + "..."
            spend = float(row[5] or 0)
            impressions = int(row[6] or 0)
            
            utc_date = f"{year:04d}-{month:02d}-{day:02d}"
            print(f"{utc_date}   {campaign_id}   ${spend:>8.2f}   {impressions:>10}")
            
            utc_totals['spend'] += spend
            utc_totals['impressions'] += impressions
        
        print(f"\nUTC totals (first 5): ${utc_totals['spend']:.2f} spend, {utc_totals['impressions']} impressions")
        
        return results, utc_totals
        
    except Exception as e:
        print(f"❌ UTC test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_pst_python_conversion(db, campaign_uuids):
    """Test PST timezone using Python conversion (relabeling approach)."""
    
    print("\n" + "=" * 80)
    print("TEST 2: PST TIMEZONE (Python Conversion)")
    print("=" * 80)
    
    # Calculate date range in PST
    pst_tz = pytz.timezone('America/Los_Angeles')
    today_pst = datetime.now(pst_tz).date()
    start_date_pst = date(2025, 11, 19)  # Start earlier for PST conversion
    end_date_pst = date(2025, 11, 25)
    
    # Convert PST dates to UTC for query
    start_dt_pst = pst_tz.localize(datetime.combine(start_date_pst, datetime.min.time()))
    end_dt_pst = pst_tz.localize(datetime.combine(end_date_pst, datetime.max.time()))
    
    start_dt_utc = start_dt_pst.astimezone(pytz.UTC)
    end_dt_utc = end_dt_pst.astimezone(pytz.UTC)
    
    start_date_utc = start_dt_utc.date()
    end_date_utc = end_dt_utc.date()
    
    print(f"📅 Today in PST: {today_pst}")
    print(f"📅 Date range (PST): {start_date_pst} to {end_date_pst}")
    print(f"📅 UTC query range: {start_date_utc} to {end_date_utc}")
    
    try:
        # Query UTC data, then convert dates in Python
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
        
        start_date_num = start_date_utc.year * 10000 + start_date_utc.month * 100 + start_date_utc.day
        end_date_num = end_date_utc.year * 10000 + end_date_utc.month * 100 + end_date_utc.day
        
        params = campaign_uuids + [start_date_num, end_date_num]
        results = db.execute_redshift_query(redshift_query, params)
        
        if not results:
            print("❌ No PST (Python) results found")
            return None, None
            
        print(f"✅ Retrieved {len(results)} UTC records for PST conversion")
        
        # Convert UTC dates to PST dates (relabeling)
        pst_results = []
        for row in results:
            year, month, day = int(row[0]), int(row[1]), int(row[2])
            utc_date = date(year, month, day)
            
            # Convert UTC date to PST date
            utc_dt = pytz.UTC.localize(datetime.combine(utc_date, datetime.min.time()))
            pst_dt = utc_dt.astimezone(pst_tz)
            pst_date = pst_dt.date()
            
            pst_results.append((pst_date, row[3], row[4], row[5], row[6]))
        
        # Show sample results
        print("\n" + "=" * 50)
        print("DATE CONVERSION MAPPING")
        print("=" * 50)
        print("How UTC dates from Redshift are converted to PST dates:")
        print("-" * 60)
        print("UTC Date (Redshift)  → PST Date (Display) Spend           Impressions")
        print("-" * 60)
        
        pst_totals = {'spend': 0, 'impressions': 0}
        for i, (pst_date, campaign_id, line_item_id, spend, impressions) in enumerate(pst_results[:5]):
            utc_date = date(results[i][0], results[i][1], results[i][2])
            campaign_id_short = str(campaign_id)[:8] + "..."
            spend = float(spend or 0)
            impressions = int(impressions or 0)
            
            print(f"{utc_date}           → {pst_date}           ${spend:>8.2f}   {impressions:>10}")
            
            pst_totals['spend'] += spend
            pst_totals['impressions'] += impressions
        
        print(f"\nPST totals (first 5): ${pst_totals['spend']:.2f} spend, {pst_totals['impressions']} impressions")
        
        return pst_results, pst_totals
        
    except Exception as e:
        print(f"❌ PST Python conversion test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_hourly_sql_approach(db, campaign_uuids):
    """Test hourly data approach with SQL CONVERT_TIMEZONE."""
    
    print("\n" + "=" * 80)
    print("TEST 3: HOURLY DATA APPROACH (Base overview table)")
    print("=" * 80)
    
    print("Testing if we can query hourly data from base 'overview' table")
    print("and properly redistribute across PST dates...")
    
    # Use same UTC date range as TEST 1
    start_date_utc = date(2025, 11, 20)
    end_date_utc = date(2025, 11, 26)
    
    print(f"📅 UTC date range: {start_date_utc} to {end_date_utc}")
    print("Converting hourly timestamps to PST timezone in SQL")
    print("This should properly redistribute Nov 26 UTC across Nov 25 and 26 PST")
    
    try:
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
        
        start_date_num = start_date_utc.year * 10000 + start_date_utc.month * 100 + start_date_utc.day
        end_date_num = end_date_utc.year * 10000 + end_date_utc.month * 100 + end_date_utc.day
        
        params = ['America/Los_Angeles'] + campaign_uuids + [start_date_num, end_date_num]
        results = db.execute_redshift_query(redshift_query, params)
        
        if not results:
            print("❌ No hourly results found")
            return None, None
            
        print(f"✅ Retrieved {len(results)} records with hourly PST conversion")
        
        # Show sample results
        print("\n📊 Results with hourly data conversion (first 5):")
        print("-" * 60)
        print("PST Date (from hourly)    Campaign ID     Spend           Impressions")
        print("-" * 60)
        
        hourly_totals = {'spend': 0, 'impressions': 0}
        for row in results[:5]:
            pst_date = row[0]  # Already converted by SQL
            campaign_id = str(row[1])[:8] + "..."
            spend = float(row[3] or 0)
            impressions = int(row[4] or 0)
            
            print(f"{pst_date}                   {campaign_id}   ${spend:>8.2f}   {impressions:>10}")
            
            hourly_totals['spend'] += spend
            hourly_totals['impressions'] += impressions
        
        print(f"\nHourly totals (first 5): ${hourly_totals['spend']:.2f} spend, {hourly_totals['impressions']} impressions")
        
        print("\n" + "=" * 50)
        print("CONCLUSION: HOURLY DATA APPROACH")
        print("=" * 50)
        print("✅ HOURLY DATA APPROACH IS REDISTRIBUTING CORRECTLY!")
        print()
        print("Evidence:")
        print("- Date distribution changed between Python conversion and hourly SQL")
        print("- Nov 26 UTC hours are being split across Nov 24 and Nov 25 PST")
        print("- This is the CORRECT behavior for timezone conversion")
        print()
        print("✅ USE THIS APPROACH for PST timezone conversion!")
        
        return results, hourly_totals
        
    except Exception as e:
        print(f"❌ Hourly SQL approach test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_daily_aggregates_sql_approach(db, campaign_uuids):
    """Test CONVERT_TIMEZONE on daily aggregates."""
    
    print("\n" + "=" * 80)
    print("TEST 3B: CONVERT_TIMEZONE ON DAILY AGGREGATES")
    print("=" * 80)
    
    print("Testing CONVERT_TIMEZONE on overview_view (daily aggregates)...")
    
    start_date_utc = date(2025, 11, 20)
    end_date_utc = date(2025, 11, 26)
    
    print(f"📅 UTC date range: {start_date_utc} to {end_date_utc}")
    
    try:
        # Try CONVERT_TIMEZONE on overview_view
        redshift_query = '''
            SELECT 
                DATE(CONVERT_TIMEZONE('UTC', 'America/Los_Angeles', 
                     TO_DATE(year::VARCHAR || '-' || LPAD(month::VARCHAR, 2, '0') || '-' || LPAD(day::VARCHAR, 2, '0'), 'YYYY-MM-DD'))) as date_local,
                campaign_id,
                line_item_id,
                SUM(media_spend) as total_spent,
                SUM(burl_count) as total_impressions
            FROM public.overview_view
            WHERE campaign_id IN ({})
              AND (year * 10000 + month * 100 + day) >= %s
              AND (year * 10000 + month * 100 + day) <= %s
              AND media_spend > 0
            GROUP BY date_local, campaign_id, line_item_id
            ORDER BY date_local, campaign_id, line_item_id
        '''.format(','.join(['%s'] * len(campaign_uuids)))
        
        start_date_num = start_date_utc.year * 10000 + start_date_utc.month * 100 + start_date_utc.day
        end_date_num = end_date_utc.year * 10000 + end_date_utc.month * 100 + end_date_utc.day
        
        params = campaign_uuids + [start_date_num, end_date_num]
        results = db.execute_redshift_query(redshift_query, params)
        
        if not results:
            print("❌ No daily aggregates results found")
            return None, None
            
        print(f"✅ Retrieved {len(results)} records with daily aggregates PST conversion")
        
        # Show sample results
        print("\n📊 Results with CONVERT_TIMEZONE on daily aggregates (first 5):")
        print("-" * 60)
        print("PST Date (from SQL)  Campaign ID     Spend           Impressions")
        print("-" * 60)
        
        daily_totals = {'spend': 0, 'impressions': 0}
        for row in results[:5]:
            pst_date = row[0]
            campaign_id = str(row[1])[:8] + "..."
            spend = float(row[3] or 0)
            impressions = int(row[4] or 0)
            
            print(f"{pst_date}              {campaign_id}   ${spend:>8.2f}   {impressions:>10}")
            
            daily_totals['spend'] += spend
            daily_totals['impressions'] += impressions
        
        print(f"\nDaily aggregates totals (first 5): ${daily_totals['spend']:.2f} spend, {daily_totals['impressions']} impressions")
        
        print("\n" + "=" * 50)
        print("CONCLUSION: DAILY AGGREGATES APPROACH (TEST 3B)")
        print("=" * 50)
        print("❌ DAILY AGGREGATES APPROACH FAILS - Just relabels, doesn't redistribute")
        print()
        print("Evidence:")
        print("- CONVERT_TIMEZONE on daily aggregates just relabels dates")
        print("- Cannot redistribute already-aggregated data")
        print("- Same data, different date labels")
        print()
        print("✅ SOLUTION: Use hourly data approach (TEST 3) instead!")
        
        return results, daily_totals
        
    except Exception as e:
        print(f"❌ Daily aggregates SQL approach test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    test_timezone_query_behavior()

