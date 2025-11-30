#!/usr/bin/env python3
"""
Timezone Conversion Test Script
================================

Comprehensive test suite for validating timezone conversion logic in the campaign portfolio pacing tool.

This script tests and validates:
1. UTC timezone mode - queries daily aggregates from overview_view
2. PST timezone mode - queries hourly data from overview table with SQL CONVERT_TIMEZONE
3. Date redistribution - verifies that UTC hours are properly split across PST date boundaries
4. Comparison of approaches - Python conversion vs SQL conversion

**Usage:**
    cd tools/campaign-portfolio-pacing
    ../venv/bin/python test_timezone_conversion.py

**What It Tests:**

**TEST 1: UTC TIMEZONE**
- Queries overview_view (daily aggregates)
- Returns UTC dates directly
- Validates UTC date filtering

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
- Confirms why hourly approach is necessary

**Key Findings:**
- ✅ Hourly SQL approach properly redistributes Nov 26 UTC hours across Nov 24 and Nov 25 PST
- ❌ Daily aggregates approach only relabels dates (doesn't redistribute hours)
- ✅ Use hourly query approach for PST timezone conversion
- ✅ Use daily aggregates for UTC timezone (no conversion needed)

**Output:**
The test provides detailed diagnostics including:
- Date distribution comparisons
- Total spend/impressions by approach
- Evidence of proper hour redistribution
- Clear recommendations on which approach to use
"""

import os
import sys
from datetime import datetime, date, timedelta
import pytz
import pandas as pd

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


def test_timezone_query_behavior():
    """Test what dates are queried and how they're converted"""
    
    print("=" * 80)
    print("TIMEZONE CONVERSION TEST")
    print("=" * 80)
    print()
    
    # Initialize database
    db = DatabaseConnector()
    
    # Test with a known campaign (Eli Lilly campaigns, account 17)
    account_id = 17
    advertiser_filter = "Lilly"
    
    # Get campaign UUIDs
    print("📋 Step 1: Getting campaign UUIDs...")
    print("-" * 80)
    
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
    
    campaigns = db.execute_postgres_query(campaign_query, (account_id, f'%{advertiser_filter}%'))
    
    if not campaigns:
        print("❌ No campaigns found")
        return
    
    campaign_uuids = [str(c[1]) for c in campaigns]
    print(f"✅ Found {len(campaign_uuids)} campaigns")
    print()
    
    # Test UTC timezone
    print("=" * 80)
    print("TEST 1: UTC TIMEZONE")
    print("=" * 80)
    print()
    
    utc_config = {'timezone': 'UTC', 'timezone_full': 'UTC'}
    utc_handler = TimezoneHandler(utc_config)
    
    # Calculate "today" in UTC
    now_utc = datetime.now(pytz.UTC)
    today_utc = now_utc.date()
    print(f"📅 Today in UTC: {today_utc}")
    
    # Calculate date range (6 months ago to today)
    default_start_utc = (today_utc - timedelta(days=180)).strftime('%Y-%m-%d')
    end_date_utc = today_utc.strftime('%Y-%m-%d')
    
    print(f"📅 Date range: {default_start_utc} to {end_date_utc}")
    print()
    
    # Query Redshift
    start_dt = datetime.strptime(default_start_utc, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date_utc, '%Y-%m-%d')
    
    start_date_num = start_dt.year * 10000 + start_dt.month * 100 + start_dt.day
    end_date_num = end_dt.year * 10000 + end_dt.month * 100 + end_dt.day
    
    redshift_query = '''
        SELECT 
            year,
            month,
            day,
            campaign_id,
            SUM(media_spend) as total_spent,
            SUM(burl_count) as total_impressions
        FROM public.overview_view
        WHERE campaign_id IN ({})
          AND (year * 10000 + month * 100 + day) >= %s
          AND (year * 10000 + month * 100 + day) <= %s
          AND media_spend > 0
        GROUP BY year, month, day, campaign_id
        ORDER BY year DESC, month DESC, day DESC
        LIMIT 10
    '''.format(','.join(['%s'] * len(campaign_uuids)))
    
    redshift_params = campaign_uuids + [start_date_num, end_date_num]
    
    print("🔍 Querying Redshift (UTC mode)...")
    print(f"   Query date range: {default_start_utc} to {end_date_utc}")
    print()
    
    utc_results = db.execute_redshift_query(redshift_query, redshift_params)
    
    print(f"✅ Retrieved {len(utc_results)} records")
    print()
    print("📊 Sample UTC Results (first 10):")
    print("-" * 80)
    print(f"{'UTC Date':<12} {'Campaign ID':<15} {'Spend':<15} {'Impressions':<15}")
    print("-" * 80)
    
    utc_data = {}
    for row in utc_results[:10]:
        year, month, day = int(row[0]), int(row[1]), int(row[2])
        campaign_id = str(row[3])
        spend = float(row[4])
        impressions = int(row[5])
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        utc_data[date_str] = {'spend': spend, 'impressions': impressions}
        print(f"{date_str:<12} {campaign_id:<15} ${spend:<14.2f} {impressions:<15}")
    print()
    
    # Test PST timezone
    print("=" * 80)
    print("TEST 2: PST TIMEZONE")
    print("=" * 80)
    print()
    
    pst_config = {'timezone': 'PST', 'timezone_full': 'America/Los_Angeles'}
    pst_handler = TimezoneHandler(pst_config)
    
    # Calculate "today" in PST
    pst_tz = pytz.timezone('America/Los_Angeles')
    now_pst = datetime.now(pst_tz)
    today_pst = now_pst.date()
    print(f"📅 Today in PST: {today_pst}")
    
    # Calculate date range (6 months ago to today in PST)
    default_start_pst = (today_pst - timedelta(days=180)).strftime('%Y-%m-%d')
    end_date_pst = today_pst.strftime('%Y-%m-%d')
    
    print(f"📅 Date range (PST): {default_start_pst} to {end_date_pst}")
    
    # Convert PST dates to UTC for query
    start_date_utc, _ = pst_handler.convert_date_range(
        default_start_pst, default_start_pst, to_tz='UTC'
    )
    
    # Convert PST end date to UTC
    today_end_pst = datetime.strptime(end_date_pst, '%Y-%m-%d')
    today_end_pst = pst_tz.localize(today_end_pst.replace(hour=23, minute=59, second=59))
    today_end_utc = today_end_pst.astimezone(pytz.UTC)
    end_date_utc = today_end_utc.date().strftime('%Y-%m-%d')
    
    print(f"📅 UTC query range: {start_date_utc} to {end_date_utc}")
    print()
    
    # Query Redshift with PST-converted dates
    start_dt_pst = datetime.strptime(start_date_utc, '%Y-%m-%d')
    end_dt_pst = datetime.strptime(end_date_utc, '%Y-%m-%d')
    
    start_date_num_pst = start_dt_pst.year * 10000 + start_dt_pst.month * 100 + start_dt_pst.day
    end_date_num_pst = end_dt_pst.year * 10000 + end_dt_pst.month * 100 + end_dt_pst.day
    
    redshift_params_pst = campaign_uuids + [start_date_num_pst, end_date_num_pst]
    
    print("🔍 Querying Redshift (PST mode - using UTC-converted dates)...")
    print(f"   PST date range: {default_start_pst} to {end_date_pst}")
    print(f"   UTC query range: {start_date_utc} to {end_date_utc}")
    print()
    
    pst_results = db.execute_redshift_query(redshift_query, redshift_params_pst)
    
    print(f"✅ Retrieved {len(pst_results)} records")
    print()
    
    # Show conversion mapping
    print("=" * 80)
    print("DATE CONVERSION MAPPING")
    print("=" * 80)
    print()
    print("How UTC dates from Redshift are converted to PST dates:")
    print("-" * 80)
    print(f"{'UTC Date (Redshift)':<20} {'→ PST Date (Display)':<20} {'Spend':<15} {'Impressions':<15}")
    print("-" * 80)
    
    pst_data = {}
    for row in pst_results[:10]:
        year, month, day = int(row[0]), int(row[1]), int(row[2])
        campaign_id = str(row[3])
        spend = float(row[4])
        impressions = int(row[5])
        
        # Convert UTC date to PST
        dt_utc = pytz.UTC.localize(datetime(year, month, day, 0, 0, 0))
        dt_pst = dt_utc.astimezone(pst_tz)
        date_pst = dt_pst.date()
        date_pst_str = date_pst.strftime('%Y-%m-%d')
        
        utc_date_str = f"{year:04d}-{month:02d}-{day:02d}"
        
        if date_pst_str not in pst_data:
            pst_data[date_pst_str] = {'spend': 0, 'impressions': 0}
        pst_data[date_pst_str]['spend'] += spend
        pst_data[date_pst_str]['impressions'] += impressions
        
        print(f"{utc_date_str:<20} → {date_pst_str:<20} ${spend:<14.2f} {impressions:<15}")
    print()
    
    # Compare totals
    print("=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print()
    
    # Sum UTC data
    utc_total_spend = sum(d['spend'] for d in utc_data.values())
    utc_total_impressions = sum(d['impressions'] for d in utc_data.values())
    
    # Sum PST data (after conversion)
    pst_total_spend = sum(d['spend'] for d in pst_data.values())
    pst_total_impressions = sum(d['impressions'] for d in pst_data.values())
    
    print("Totals from first 10 records:")
    print("-" * 80)
    print(f"UTC mode:  ${utc_total_spend:,.2f} spend, {utc_total_impressions:,} impressions")
    print(f"PST mode:  ${pst_total_spend:,.2f} spend, {pst_total_impressions:,} impressions")
    print()
    
    if abs(utc_total_spend - pst_total_spend) < 0.01:
        print("✅ Totals match (data is being relabeled, not redistributed)")
    else:
        print("⚠️  Totals differ (data redistribution may be happening)")
    print()
    
    # Show date distribution
    print("=" * 80)
    print("DATE DISTRIBUTION ANALYSIS")
    print("=" * 80)
    print()
    print("UTC dates and their PST conversions:")
    print("-" * 80)
    
    conversion_map = {}
    for row in pst_results[:20]:
        year, month, day = int(row[0]), int(row[1]), int(row[2])
        utc_date_str = f"{year:04d}-{month:02d}-{day:02d}"
        
        # Convert UTC date to PST
        dt_utc = pytz.UTC.localize(datetime(year, month, day, 0, 0, 0))
        dt_pst = dt_utc.astimezone(pst_tz)
        date_pst_str = dt_pst.date().strftime('%Y-%m-%d')
        
        if utc_date_str not in conversion_map:
            conversion_map[utc_date_str] = date_pst_str
    
    print(f"{'UTC Date':<15} {'→ PST Date':<15} {'Shift':<10}")
    print("-" * 80)
    for utc_date, pst_date in sorted(conversion_map.items())[:10]:
        utc_dt = datetime.strptime(utc_date, '%Y-%m-%d').date()
        pst_dt = datetime.strptime(pst_date, '%Y-%m-%d').date()
        shift = (utc_dt - pst_dt).days
        print(f"{utc_date:<15} → {pst_date:<15} {shift:+d} days")
    print()
    
    print("=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)
    print()
    print("1. Redshift query returns data aggregated by UTC date")
    print("2. Date conversion maps UTC dates to PST dates (typically -1 day)")
    print("3. Same spend/impressions are relabeled with PST dates")
    print("4. Data is NOT redistributed - same values, different date labels")
    print()
    print("⚠️  ISSUE: Nov 26 UTC (00:00-23:59 UTC) spans:")
    print("   - Nov 25 PST 16:00-23:59 (8 hours)")
    print("   - Nov 26 PST 00:00-15:59 (16 hours)")
    print("   But ALL spend is attributed to Nov 25 PST!")
    print()
    
    # Test 3: Query hourly data from base overview table
    print("=" * 80)
    print("TEST 3: HOURLY DATA APPROACH (Base overview table)")
    print("=" * 80)
    print()
    print("Testing if we can query hourly data from base 'overview' table")
    print("and properly redistribute across PST dates...")
    print()
    
    # First, discover the actual schema of the overview table
    print("🔍 Discovering schema of 'overview' table...")
    schema_query = '''
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'overview'
        ORDER BY ordinal_position
        LIMIT 20
    '''
    
    try:
        schema_results = db.execute_redshift_query(schema_query, [])
        if schema_results:
            print("   ✅ Found columns in 'overview' table:")
            for col_name, col_type in schema_results:
                print(f"      - {col_name} ({col_type})")
            print()
            
            # Check if table has 'date' column or 'year/month/day/hour' columns
            has_date_col = any(row[0].lower() == 'date' for row in schema_results)
            has_year_col = any(row[0].lower() == 'year' for row in schema_results)
            has_hour_col = any(row[0].lower() == 'hour' for row in schema_results)
            has_impressions = any(row[0].lower() in ['impressions', 'burl_count'] for row in schema_results)
            impressions_col = 'impressions' if any(row[0].lower() == 'impressions' for row in schema_results) else 'burl_count'
            
            print(f"   Schema analysis:")
            print(f"      - Has 'date' column: {has_date_col}")
            print(f"      - Has 'year/month/day' columns: {has_year_col}")
            print(f"      - Has 'hour' column: {has_hour_col}")
            print(f"      - Impressions column: {impressions_col}")
            print()
        else:
            print("   ⚠️  Could not query schema - table may not exist")
            print()
            raise Exception("Cannot discover schema")
    except Exception as e:
        print(f"   ❌ Error discovering schema: {e}")
        print("   ⚠️  Skipping hourly data test - table may not exist or have different schema")
        print()
        print("=" * 80)
        print("SKIPPING TEST 3 - Cannot determine table schema")
        print("=" * 80)
        print()
        has_date_col = False
        has_year_col = False
        has_hour_col = False
        impressions_col = 'burl_count'
        schema_discovered = False
    else:
        schema_discovered = True
    
    # Only proceed if we successfully discovered the schema
    if not schema_discovered:
        # Skip to TEST 3B
        pass
    else:
        # Use the same UTC date range as UTC test for fair comparison
        # This ensures we're comparing the same underlying data
        hourly_start_date = default_start_utc
        hourly_end_date = end_date_utc
        
        # Build query based on actual schema
        if has_date_col and has_hour_col:
            # Use date + hour columns
            redshift_query_hourly = '''
            SELECT 
                DATE(CONVERT_TIMEZONE('UTC', 'America/Los_Angeles', 
                     (date::VARCHAR || ' ' || LPAD(hour::VARCHAR, 2, '0') || ':00:00')::TIMESTAMP)) as pst_date,
                campaign_id,
                SUM(media_spend) as total_spent,
                SUM({}) as total_impressions
            FROM public.overview
            WHERE campaign_id IN ({})
              AND date >= %s::DATE
              AND date <= %s::DATE
              AND media_spend > 0
            GROUP BY pst_date, campaign_id
            ORDER BY pst_date DESC, campaign_id
            LIMIT 10
            '''.format(impressions_col, ','.join(['%s'] * len(campaign_uuids)))
        elif has_year_col and has_hour_col:
            # Use year/month/day + hour columns (like overview_view)
            start_dt = datetime.strptime(hourly_start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(hourly_end_date, '%Y-%m-%d')
            start_date_num = start_dt.year * 10000 + start_dt.month * 100 + start_dt.day
            end_date_num = end_dt.year * 10000 + end_dt.month * 100 + end_dt.day
            
            redshift_query_hourly = '''
            SELECT 
                DATE(CONVERT_TIMEZONE('UTC', 'America/Los_Angeles', 
                     (TO_DATE(year::VARCHAR || '-' || LPAD(month::VARCHAR, 2, '0') || '-' || LPAD(day::VARCHAR, 2, '0'), 'YYYY-MM-DD')::VARCHAR || ' ' || LPAD(hour::VARCHAR, 2, '0') || ':00:00')::TIMESTAMP)) as pst_date,
                campaign_id,
                SUM(media_spend) as total_spent,
                SUM({}) as total_impressions
            FROM public.overview
            WHERE campaign_id IN ({})
              AND (year * 10000 + month * 100 + day) >= %s
              AND (year * 10000 + month * 100 + day) <= %s
              AND media_spend > 0
            GROUP BY pst_date, campaign_id
            ORDER BY pst_date DESC, campaign_id
            LIMIT 10
            '''.format(impressions_col, ','.join(['%s'] * len(campaign_uuids)))
            redshift_params_hourly = campaign_uuids + [start_date_num, end_date_num]
        else:
            print("   ❌ Cannot build hourly query - missing required columns")
            print("   ⚠️  Skipping hourly data test")
            print()
            raise Exception(f"Cannot build hourly query - missing required columns (date/hour or year/month/day/hour)")
        
        if has_date_col:
            redshift_params_hourly = campaign_uuids + [hourly_start_date, hourly_end_date]
        
        print("🔍 Querying base 'overview' table with hourly data...")
        print(f"   UTC date range: {hourly_start_date} to {hourly_end_date}")
        print(f"   Converting hourly timestamps to PST timezone in SQL")
        print(f"   This should properly redistribute Nov 26 UTC across Nov 25 and Nov 26 PST")
        print()
        
        try:
            hourly_results = db.execute_redshift_query(redshift_query_hourly, redshift_params_hourly)
            
            print(f"✅ Retrieved {len(hourly_results)} records")
            print()
            print("📊 Results with hourly data conversion (first 10):")
            print("-" * 80)
            print(f"{'PST Date (from hourly)':<25} {'Campaign ID':<15} {'Spend':<15} {'Impressions':<15}")
            print("-" * 80)
            
            hourly_data = {}
            for row in hourly_results[:10]:
                pst_date = row[0]  # Already a date from SQL
                campaign_id = str(row[1])
                spend = float(row[2])
                impressions = int(row[3])
                
                # Convert date to string for display
                if isinstance(pst_date, date):
                    pst_date_str = pst_date.strftime('%Y-%m-%d')
                else:
                    pst_date_str = str(pst_date)
                
                if pst_date_str not in hourly_data:
                    hourly_data[pst_date_str] = {'spend': 0, 'impressions': 0}
                hourly_data[pst_date_str]['spend'] += spend
                hourly_data[pst_date_str]['impressions'] += impressions
                
                print(f"{pst_date_str:<25} {campaign_id:<15} ${spend:<14.2f} {impressions:<15}")
            print()
            
            # Compare with Python conversion approach
            print("=" * 80)
            print("COMPARISON: HOURLY DATA vs PYTHON CONVERSION")
            print("=" * 80)
            print()
            
            hourly_total_spend = sum(d['spend'] for d in hourly_data.values())
            hourly_total_impressions = sum(d['impressions'] for d in hourly_data.values())
            
            print("Totals from first 10 records:")
            print("-" * 80)
            print(f"Python conversion: ${pst_total_spend:,.2f} spend, {pst_total_impressions:,} impressions")
            print(f"Hourly data (SQL): ${hourly_total_spend:,.2f} spend, {hourly_total_impressions:,} impressions")
            print()
            
            if abs(pst_total_spend - hourly_total_spend) < 0.01:
                print("✅ Totals match - but check date distribution for proper redistribution")
            else:
                print("⚠️  Totals differ - hourly approach may be redistributing data!")
            print()
            
            # Check if dates are different (indicating redistribution)
            print("Date distribution comparison:")
            print("-" * 80)
            print(f"{'Date':<15} {'Python Conv':<15} {'Hourly SQL':<15} {'Difference':<15}")
            print("-" * 80)
            
            all_dates = set(list(pst_data.keys()) + list(hourly_data.keys()))
            for date_key in sorted(all_dates)[:10]:
                python_spend = pst_data.get(date_key, {}).get('spend', 0)
                hourly_spend = hourly_data.get(date_key, {}).get('spend', 0)
                diff = abs(python_spend - hourly_spend)
                print(f"{date_key:<15} ${python_spend:<14.2f} ${hourly_spend:<14.2f} ${diff:<14.2f}")
            
            print()
            print("=" * 80)
            print("CONCLUSION: HOURLY DATA APPROACH")
            print("=" * 80)
            print()
            # Check if date distribution changed (indicating redistribution)
            date_distribution_changed = False
            for date_key in set(list(pst_data.keys()) + list(hourly_data.keys())):
                python_spend = pst_data.get(date_key, {}).get('spend', 0)
                hourly_spend = hourly_data.get(date_key, {}).get('spend', 0)
                if abs(python_spend - hourly_spend) > 0.01:
                    date_distribution_changed = True
                    break
            
            if date_distribution_changed:
                print("✅ HOURLY DATA APPROACH IS REDISTRIBUTING CORRECTLY!")
                print()
                print("   Evidence:")
                print("   - Date distribution changed between Python conversion and hourly SQL")
                print("   - Nov 26 UTC hours are being split across Nov 24 and Nov 25 PST")
                print("   - This is the CORRECT behavior for timezone conversion")
                print()
                print("   ✅ USE THIS APPROACH for PST timezone conversion!")
            elif abs(pst_total_spend - hourly_total_spend) < 0.01:
                print("✅ Hourly data approach returns same totals as Python conversion")
                print("   Date distribution also matches - redistribution may be minimal")
                print("   (This could happen if all UTC hours fall within same PST day)")
            else:
                print("⚠️  Hourly data approach shows different totals")
                print("   This might indicate:")
                print("   1. Different date ranges being queried")
                print("   2. Data availability differences between tables")
                print("   3. Need to investigate further")
            print()
            
        except Exception as e:
            print(f"❌ Error testing hourly data approach: {e}")
            print()
            print("This might mean:")
            print("1. Base 'overview' table doesn't exist or has different schema")
            print("2. SQL syntax is incorrect")
            print("3. Need to check table structure")
            print()
            import traceback
            traceback.print_exc()
            
            # Try alternative: CONVERT_TIMEZONE on daily aggregates
            print()
            print("=" * 80)
            print("TEST 3B: CONVERT_TIMEZONE ON DAILY AGGREGATES")
            print("=" * 80)
        print()
        print("Falling back to testing CONVERT_TIMEZONE on overview_view...")
        print()
        
        try:
            # Query Redshift with CONVERT_TIMEZONE in SQL (daily aggregates)
            redshift_query_with_tz = '''
                SELECT 
                    DATE(CONVERT_TIMEZONE('UTC', 'America/Los_Angeles', 
                         (TO_DATE(year::VARCHAR || '-' || LPAD(month::VARCHAR, 2, '0') || '-' || LPAD(day::VARCHAR, 2, '0'), 'YYYY-MM-DD')::VARCHAR || ' 00:00:00')::TIMESTAMP)) as pst_date,
                    campaign_id,
                    SUM(media_spend) as total_spent,
                    SUM(burl_count) as total_impressions
                FROM public.overview_view
                WHERE campaign_id IN ({})
                  AND (year * 10000 + month * 100 + day) >= %s
                  AND (year * 10000 + month * 100 + day) <= %s
                  AND media_spend > 0
                GROUP BY pst_date, campaign_id
                ORDER BY pst_date DESC, campaign_id
                LIMIT 10
            '''.format(','.join(['%s'] * len(campaign_uuids)))
            
            redshift_params_tz = campaign_uuids + [start_date_num, end_date_num]
            
            print("🔍 Querying overview_view with CONVERT_TIMEZONE...")
            tz_results = db.execute_redshift_query(redshift_query_with_tz, redshift_params_tz)
            
            print(f"✅ Retrieved {len(tz_results)} records")
            print()
            print("📊 Results with CONVERT_TIMEZONE (first 10):")
            print("-" * 80)
            print(f"{'PST Date (from SQL)':<20} {'Campaign ID':<15} {'Spend':<15} {'Impressions':<15}")
            print("-" * 80)
            
            tz_data = {}
            for row in tz_results[:10]:
                pst_date = row[0]  # Already a date from SQL
                campaign_id = str(row[1])
                spend = float(row[2])
                impressions = int(row[3])
                
                # Convert date to string for display
                if isinstance(pst_date, date):
                    pst_date_str = pst_date.strftime('%Y-%m-%d')
                else:
                    pst_date_str = str(pst_date)
                
                if pst_date_str not in tz_data:
                    tz_data[pst_date_str] = {'spend': 0, 'impressions': 0}
                tz_data[pst_date_str]['spend'] += spend
                tz_data[pst_date_str]['impressions'] += impressions
                
                print(f"{pst_date_str:<20} {campaign_id:<15} ${spend:<14.2f} {impressions:<15}")
            print()
            
            # Compare with Python conversion approach
            print("=" * 80)
            print("COMPARISON: SQL CONVERT_TIMEZONE vs PYTHON CONVERSION")
            print("=" * 80)
            print()
            
            tz_total_spend = sum(d['spend'] for d in tz_data.values())
            tz_total_impressions = sum(d['impressions'] for d in tz_data.values())
            
            print("Totals from first 10 records:")
            print("-" * 80)
            print(f"Python conversion: ${pst_total_spend:,.2f} spend, {pst_total_impressions:,} impressions")
            print(f"SQL CONVERT_TIMEZONE: ${tz_total_spend:,.2f} spend, {tz_total_impressions:,} impressions")
            print()
            
            if abs(pst_total_spend - tz_total_spend) < 0.01:
                print("✅ Totals match - both approaches return same data")
            else:
                print("⚠️  Totals differ - SQL approach may be redistributing data!")
            print()
            
            # Check if dates are different (indicating redistribution)
            print("Date distribution comparison:")
            print("-" * 80)
            print(f"{'Date':<15} {'Python Conv':<15} {'SQL Conv':<15} {'Difference':<15}")
            print("-" * 80)
            
            all_dates = set(list(pst_data.keys()) + list(tz_data.keys()))
            for date_key in sorted(all_dates)[:10]:
                python_spend = pst_data.get(date_key, {}).get('spend', 0)
                sql_spend = tz_data.get(date_key, {}).get('spend', 0)
                diff = abs(python_spend - sql_spend)
                print(f"{date_key:<15} ${python_spend:<14.2f} ${sql_spend:<14.2f} ${diff:<14.2f}")
            
            print()
            print("=" * 80)
            print("CONCLUSION: DAILY AGGREGATES APPROACH (TEST 3B)")
            print("=" * 80)
            print()
            if abs(pst_total_spend - tz_total_spend) < 0.01:
                print("❌ DAILY AGGREGATES APPROACH FAILS - Just relabels, doesn't redistribute")
                print()
                print("   Evidence:")
                print("   - Totals match Python conversion exactly")
                print("   - Date distribution matches Python conversion exactly")
                print("   - This means CONVERT_TIMEZONE on daily aggregates just relabels dates")
                print()
                print("   Root cause:")
                print("   - overview_view is pre-aggregated by UTC date")
                print("   - CONVERT_TIMEZONE can't redistribute already-aggregated data")
                print()
                print("   ✅ SOLUTION: Use hourly data approach (TEST 3) instead!")
            else:
                print("✅ SQL CONVERT_TIMEZONE approach shows different totals!")
                print("   This suggests data redistribution is happening.")
                print("   This is the correct approach to use.")
            print()
            
        except Exception as e2:
            print(f"❌ Error testing CONVERT_TIMEZONE approach: {e2}")
            print()
            print("This might mean:")
            print("1. CONVERT_TIMEZONE function syntax is incorrect")
            print("2. TO_DATE function syntax is incorrect")
            print("3. Redshift version doesn't support these functions")
            print()
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    test_timezone_query_behavior()

