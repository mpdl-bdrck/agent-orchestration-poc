#!/usr/bin/env python3
"""
Analyze Timezone Difference
===========================

Analyzes the PST and UTC CSV files to identify the exact difference
in how dates are being handled.
"""

import os
import sys
import pandas as pd
from datetime import datetime

def analyze_csvs():
    """Analyze PST and UTC CSV files"""
    
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    pst_file = os.path.join(reports_dir, "portfolio_daily_PST.csv")
    utc_file = os.path.join(reports_dir, "portfolio_daily.csv")
    
    print("=" * 80)
    print("TIMEZONE DIFFERENCE ANALYSIS")
    print("=" * 80)
    print()
    
    # Check if files exist
    if not os.path.exists(pst_file):
        print(f"❌ PST file not found: {pst_file}")
        return
    
    if not os.path.exists(utc_file):
        print(f"❌ UTC file not found: {utc_file}")
        return
    
    # Load CSVs
    print("📂 Loading CSV files...")
    pst_df = pd.read_csv(pst_file)
    utc_df = pd.read_csv(utc_file)
    
    print(f"✅ PST file: {len(pst_df)} rows")
    print(f"✅ UTC file: {len(utc_df)} rows")
    print()
    
    # Convert date strings to dates for comparison
    pst_df['date'] = pd.to_datetime(pst_df['date'])
    utc_df['date'] = pd.to_datetime(utc_df['date'])
    
    # Sort by date
    pst_df = pst_df.sort_values('date')
    utc_df = utc_df.sort_values('date')
    
    print("=" * 80)
    print("DATE COMPARISON")
    print("=" * 80)
    print()
    print(f"{'PST Date':<15} {'UTC Date':<15} {'Date Shift':<15}")
    print("-" * 80)
    
    # Compare dates
    min_len = min(len(pst_df), len(utc_df))
    date_shifts = []
    
    for i in range(min_len):
        pst_date = pst_df.iloc[i]['date']
        utc_date = utc_df.iloc[i]['date']
        shift = (utc_date - pst_date).days
        date_shifts.append(shift)
        print(f"{pst_date.strftime('%Y-%m-%d'):<15} {utc_date.strftime('%Y-%m-%d'):<15} {shift:+d} days")
    
    print()
    print(f"Average date shift: {sum(date_shifts) / len(date_shifts):.1f} days")
    print()
    
    # Compare values
    print("=" * 80)
    print("VALUE COMPARISON")
    print("=" * 80)
    print()
    
    # Create a mapping: PST date -> UTC date
    date_mapping = {}
    for i in range(min_len):
        pst_date_str = pst_df.iloc[i]['date'].strftime('%Y-%m-%d')
        utc_date_str = utc_df.iloc[i]['date'].strftime('%Y-%m-%d')
        date_mapping[pst_date_str] = utc_date_str
    
    print("Comparing spend and impressions for corresponding dates:")
    print("-" * 80)
    print(f"{'PST Date':<15} {'PST Spend':<15} {'UTC Date':<15} {'UTC Spend':<15} {'Match':<10}")
    print("-" * 80)
    
    matches = 0
    mismatches = 0
    
    for i in range(min_len):
        pst_row = pst_df.iloc[i]
        pst_date_str = pst_row['date'].strftime('%Y-%m-%d')
        pst_spend = pst_row['spend']
        pst_impressions = pst_row['impressions']
        
        # Find corresponding UTC row
        utc_date_str = date_mapping.get(pst_date_str)
        if utc_date_str:
            utc_row = utc_df[utc_df['date'].dt.strftime('%Y-%m-%d') == utc_date_str]
            if not utc_row.empty:
                utc_row = utc_row.iloc[0]
                utc_spend = utc_row['spend']
                utc_impressions = utc_row['impressions']
                
                spend_match = abs(pst_spend - utc_spend) < 0.01
                imp_match = pst_impressions == utc_impressions
                
                if spend_match and imp_match:
                    matches += 1
                    match_str = "✅ MATCH"
                else:
                    mismatches += 1
                    match_str = "❌ DIFF"
                
                print(f"{pst_date_str:<15} ${pst_spend:<14.2f} {utc_date_str:<15} ${utc_spend:<14.2f} {match_str:<10}")
    
    print()
    print(f"Matches: {matches}")
    print(f"Mismatches: {mismatches}")
    print()
    
    # Total comparison
    print("=" * 80)
    print("TOTAL COMPARISON")
    print("=" * 80)
    print()
    
    pst_total_spend = pst_df['spend'].sum()
    pst_total_impressions = pst_df['impressions'].sum()
    
    utc_total_spend = utc_df['spend'].sum()
    utc_total_impressions = utc_df['impressions'].sum()
    
    print(f"PST Totals:  ${pst_total_spend:,.2f} spend, {pst_total_impressions:,} impressions")
    print(f"UTC Totals:  ${utc_total_spend:,.2f} spend, {utc_total_impressions:,} impressions")
    print()
    
    spend_diff = abs(pst_total_spend - utc_total_spend)
    imp_diff = abs(pst_total_impressions - utc_total_impressions)
    
    if spend_diff < 0.01 and imp_diff == 0:
        print("✅ Totals match exactly - data is being RELABELED, not redistributed")
        print()
        print("🔍 DIAGNOSIS:")
        print("   The same spend/impressions are being attributed to different dates.")
        print("   This is because:")
        print("   1. Redshift aggregates by UTC date")
        print("   2. We convert UTC date labels to PST date labels")
        print("   3. But the underlying data is NOT redistributed")
        print()
        print("   Example:")
        print("   - Nov 26 UTC (00:00-23:59 UTC) contains:")
        print("     * Nov 25 PST 16:00-23:59 (8 hours)")
        print("     * Nov 26 PST 00:00-15:59 (16 hours)")
        print("   - But ALL spend is labeled as Nov 25 PST")
    else:
        print(f"⚠️  Totals differ: ${spend_diff:.2f} spend, {imp_diff:,} impressions")
    
    print()
    
    # Show date ranges
    print("=" * 80)
    print("DATE RANGES")
    print("=" * 80)
    print()
    print(f"PST file: {pst_df['date'].min().strftime('%Y-%m-%d')} to {pst_df['date'].max().strftime('%Y-%m-%d')}")
    print(f"UTC file: {utc_df['date'].min().strftime('%Y-%m-%d')} to {utc_df['date'].max().strftime('%Y-%m-%d')}")
    print()


if __name__ == "__main__":
    analyze_csvs()

