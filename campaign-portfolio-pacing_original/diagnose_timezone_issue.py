#!/usr/bin/env python3
"""
Timezone Issue Diagnostic
==========================

Diagnoses the exact issue with timezone conversion by:
1. Showing what dates SHOULD be queried
2. Showing what dates ARE being queried
3. Showing how dates are being converted
4. Identifying the root cause
"""

import os
import sys
from datetime import datetime, date, timedelta
import pytz

def diagnose():
    """Diagnose the timezone conversion issue"""
    
    print("=" * 80)
    print("TIMEZONE CONVERSION DIAGNOSTIC")
    print("=" * 80)
    print()
    
    # Simulate the logic from campaign_analyzer.py
    
    # Test 1: UTC mode
    print("TEST 1: UTC MODE")
    print("-" * 80)
    
    utc_config = {'timezone': 'UTC', 'timezone_full': 'UTC'}
    
    # Calculate "today" in UTC
    now_utc = datetime.now(pytz.UTC)
    today_utc = now_utc.date()
    print(f"Current UTC time: {now_utc}")
    print(f"Today in UTC: {today_utc}")
    
    # Calculate date range
    default_start_utc = (today_utc - timedelta(days=180)).strftime('%Y-%m-%d')
    end_date_utc = today_utc.strftime('%Y-%m-%d')
    
    print(f"Query date range: {default_start_utc} to {end_date_utc}")
    print()
    
    # Simulate what happens when processing Redshift results
    print("Processing Redshift results (UTC mode):")
    print("-" * 80)
    
    # Simulate Nov 25 and Nov 26 UTC dates from Redshift
    test_dates_utc = [
        (2025, 11, 25),
        (2025, 11, 26),
    ]
    
    for year, month, day in test_dates_utc:
        date_utc = date(year, month, day)
        
        # UTC mode logic (from my fix)
        is_utc = True  # UTC mode
        if is_utc:
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
            if date_utc > today_utc:
                print(f"  {date_str} UTC: FILTERED OUT (future date)")
            else:
                print(f"  {date_str} UTC: INCLUDED → {date_str}")
    
    print()
    
    # Test 2: PST mode
    print("TEST 2: PST MODE")
    print("-" * 80)
    
    pst_config = {'timezone': 'PST', 'timezone_full': 'America/Los_Angeles'}
    pst_tz = pytz.timezone('America/Los_Angeles')
    
    # Calculate "today" in PST
    now_pst = datetime.now(pst_tz)
    today_pst = now_pst.date()
    print(f"Current PST time: {now_pst}")
    print(f"Today in PST: {today_pst}")
    
    # Calculate date range in PST
    default_start_pst = (today_pst - timedelta(days=180)).strftime('%Y-%m-%d')
    end_date_pst = today_pst.strftime('%Y-%m-%d')
    
    print(f"PST date range: {default_start_pst} to {end_date_pst}")
    
    # Convert PST dates to UTC for query
    # PST Nov 25 00:00 = UTC Nov 25 08:00
    # PST Nov 25 23:59 = UTC Nov 26 07:59
    today_start_pst = pst_tz.localize(datetime.strptime(end_date_pst, '%Y-%m-%d').replace(hour=0, minute=0, second=0))
    today_start_utc = today_start_pst.astimezone(pytz.UTC)
    
    today_end_pst = pst_tz.localize(datetime.strptime(end_date_pst, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
    today_end_utc = today_end_pst.astimezone(pytz.UTC)
    
    print(f"PST Nov 25 spans: {today_start_utc.date()} {today_start_utc.time()} UTC to {today_end_utc.date()} {today_end_utc.time()} UTC")
    print(f"So we query UTC dates: up to {today_end_utc.date()}")
    print()
    
    # Simulate what happens when processing Redshift results
    print("Processing Redshift results (PST mode):")
    print("-" * 80)
    
    for year, month, day in test_dates_utc:
        date_utc = date(year, month, day)
        
        # PST mode logic
        is_utc = False  # PST mode
        if is_utc:
            # Shouldn't happen in PST mode
            pass
        else:
            # Convert UTC date to PST
            dt_utc = pytz.UTC.localize(datetime(year, month, day, 0, 0, 0))
            dt_pst = dt_utc.astimezone(pst_tz)
            date_pst = dt_pst.date()
            date_pst_str = date_pst.strftime('%Y-%m-%d')
            
            if date_pst > today_pst:
                print(f"  {date_utc} UTC → {date_pst_str} PST: FILTERED OUT (future date)")
            else:
                print(f"  {date_utc} UTC → {date_pst_str} PST: INCLUDED → {date_pst_str}")
    
    print()
    
    # Test 3: The actual bug
    print("=" * 80)
    print("THE ACTUAL BUG")
    print("=" * 80)
    print()
    
    print("When Redshift returns Nov 26 UTC data:")
    print("-" * 80)
    print("Nov 26 UTC 00:00-23:59 contains:")
    print("  - Nov 25 PST 16:00-23:59 (8 hours)")
    print("  - Nov 26 PST 00:00-15:59 (16 hours)")
    print()
    print("Current behavior:")
    print("  - ALL Nov 26 UTC spend is labeled as Nov 25 PST")
    print("  - This is WRONG - 16 hours belong to Nov 26 PST!")
    print()
    print("Root cause:")
    print("  - Redshift aggregates by UTC date (daily aggregates)")
    print("  - We convert UTC date → PST date label")
    print("  - But we DON'T redistribute the spend/impressions")
    print("  - We just relabel the entire UTC day's data")
    print()
    print("Why totals match:")
    print("  - Same underlying data from Redshift")
    print("  - Just different date labels")
    print("  - No data is lost, but attribution is wrong")
    print()
    
    # Test 4: What SHOULD happen
    print("=" * 80)
    print("WHAT SHOULD HAPPEN")
    print("=" * 80)
    print()
    print("Option 1: Query hourly data from Redshift (if available)")
    print("  - Redistribute spend/impressions by hour")
    print("  - Attribute to correct PST dates")
    print()
    print("Option 2: Accept daily aggregates limitation")
    print("  - Document that dates are approximate")
    print("  - Use UTC dates for accurate attribution")
    print()
    print("Option 3: Proportional redistribution")
    print("  - Split UTC day's data proportionally")
    print("  - Based on time overlap (8h vs 16h)")
    print("  - But this is still approximate")
    print()


if __name__ == "__main__":
    diagnose()

