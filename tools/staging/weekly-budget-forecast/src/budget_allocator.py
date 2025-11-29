"""
Budget Allocator
================

Allocates remaining campaign budgets across future weeks using Option B (Prorated by Campaign Duration).
Respects campaign end dates and maintains original pacing intent.
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from utils.date_parser import parse_date


class BudgetAllocator:
    """
    Allocates remaining campaign budgets across future weeks using prorated method
    """

    def allocate_future_budget(
        self, 
        campaigns: List[Dict], 
        daily_line_items: pd.DataFrame,
        weeks_future: int = 6,
        today: datetime = None,
        db_connector = None
    ) -> pd.DataFrame:
        """
        Allocate remaining campaign budgets across future weeks using Option B (Prorated).
        
        For each campaign:
        - Calculate remaining budget = total_budget - spent_to_date
        - Calculate remaining days = min(campaign_end_date - today, weeks_future * 7)
        - Calculate daily rate = remaining_budget / remaining_days
        - Calculate weekly budget = daily_rate × 7
        
        For each week:
        - Sum weekly budgets from all campaigns active in that week
        - If campaign ends mid-week, prorate for partial week
        - If campaign ends before week starts, allocate $0
        
        Args:
            campaigns: List of campaign dicts with campaign_id, campaign_name, budget, start_date, end_date
            daily_line_items: DataFrame with daily spend data (to calculate spent_to_date)
            weeks_future: Number of future weeks to allocate (default: 6)
            today: Reference date (defaults to today)
            
        Returns:
            DataFrame with columns: week_start_date, week_end_date, campaign_id, campaign_name, weekly_budget
        """
        if today is None:
            today = datetime.now().date()
        else:
            today = today.date() if isinstance(today, datetime) else today
        
        if not campaigns:
            return pd.DataFrame(columns=['week_start_date', 'week_end_date', 'campaign_id', 'campaign_name', 'weekly_budget'])
        
        # Calculate spent_to_date for each campaign
        # IMPORTANT: We need ALL historical spend, not just from the 6-week window
        campaign_spent = {}
        if db_connector and campaigns:
            try:
                # Get campaign UUIDs
                campaign_uuids = [c['campaign_uuid'] for c in campaigns if c.get('campaign_uuid')]
                
                if campaign_uuids:
                    # Query ALL historical spend up to today (no date filter for start, only end)
                    redshift_query = '''
                        SELECT 
                            campaign_id,
                            SUM(media_spend) as total_spent
                        FROM public.overview_view
                        WHERE campaign_id IN ({})
                          AND (year * 10000 + month * 100 + day) < %s
                          AND media_spend > 0
                        GROUP BY campaign_id
                    '''.format(','.join(['%s'] * len(campaign_uuids)))
                    
                    # Calculate today as YYYYMMDD number
                    today_num = today.year * 10000 + today.month * 100 + today.day
                    redshift_params = campaign_uuids + [today_num]
                    
                    results = db_connector.execute_redshift_query(redshift_query, redshift_params)
                    
                    # Map UUIDs to campaign_ids
                    uuid_to_id = {c['campaign_uuid']: c['campaign_id'] for c in campaigns}
                    
                    for row in results:
                        campaign_uuid = str(row[0])
                        total_spent = float(row[1]) if row[1] else 0.0
                        campaign_id = uuid_to_id.get(campaign_uuid)
                        if campaign_id:
                            campaign_spent[campaign_id] = total_spent
                    
                    print(f"      💰 Queried total historical spend for {len(campaign_spent)} campaigns")
            except Exception as e:
                print(f"      ⚠️  Could not query total spend from Redshift: {e}")
                import traceback
                print(f"      Traceback: {traceback.format_exc()[:200]}")
        
        # Fallback to daily_line_items (limited to 6-week window) if Redshift query failed
        if not campaign_spent and not daily_line_items.empty and 'campaign_id' in daily_line_items.columns:
            past_spend = daily_line_items[
                pd.to_datetime(daily_line_items['date']).dt.date < today
            ]
            if not past_spend.empty:
                campaign_spent = past_spend.groupby('campaign_id')['total_spent'].sum().to_dict()
                print(f"      ⚠️  Using fallback: spend from 6-week window only ({len(campaign_spent)} campaigns)")
        
        # Generate future week boundaries (Monday-Sunday, ISO week)
        # Start from next week (not current week)
        days_since_monday = (today.weekday()) % 7
        if days_since_monday == 0:
            current_monday = today
        else:
            current_monday = today - timedelta(days=days_since_monday)
        next_monday = current_monday + timedelta(weeks=1)
        
        # Generate weeks starting from next Monday
        future_weeks = []
        for i in range(weeks_future):
            week_start = next_monday + timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)
            future_weeks.append((week_start, week_end))
        
        # Debug
        campaigns_with_dates = [c for c in campaigns if c.get('start_date') and c.get('end_date')]
        print(f"      📊 Budget allocator: {len(campaigns_with_dates)} campaigns with dates")
        
        # Calculate weekly budget allocation for each campaign
        allocations = []
        
        for campaign in campaigns:
            campaign_id = campaign['campaign_id']
            campaign_name = campaign['campaign_name']
            budget = float(campaign.get('budget', 0))
            start_date_str = campaign.get('start_date')
            end_date_str = campaign.get('end_date')
            
            if not start_date_str or not end_date_str:
                continue
            
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            if not start_date or not end_date:
                continue
            
            # Calculate spent_to_date
            spent_to_date = campaign_spent.get(campaign_id, 0.0)
            remaining_budget = budget - spent_to_date
            
            if remaining_budget <= 0:
                # Campaign already spent all budget
                continue
            
            # Calculate remaining days (capped at weeks_future * 7)
            days_until_end = (end_date - today).days
            if days_until_end <= 0:
                # Campaign already ended
                continue
            
            remaining_days = min(days_until_end, weeks_future * 7)
            if remaining_days <= 0:
                continue
            
            # Calculate daily rate and weekly budget
            # IMPORTANT: Use remaining_days (not total campaign days) for allocation
            daily_rate = remaining_budget / remaining_days
            weekly_budget = daily_rate * 7
            
            # Debug: Show allocation for first few campaigns
            if len(allocations) < 3:
                print(f"      💰 Campaign '{campaign_name[:40]}': Budget ${budget:,.2f}, Spent ${spent_to_date:,.2f}, Remaining ${remaining_budget:,.2f}, Days: {remaining_days}, Weekly: ${weekly_budget:,.2f}")
            
            # Allocate budget to each future week
            for week_start, week_end in future_weeks:
                # Check if campaign is active during this week
                if end_date < week_start:
                    # Campaign ended before this week
                    continue
                
                if start_date > week_end:
                    # Campaign hasn't started yet
                    continue
                
                # Calculate days in this week for this campaign
                week_start_effective = max(week_start, start_date)
                week_end_effective = min(week_end, end_date)
                
                days_in_week = (week_end_effective - week_start_effective).days + 1
                
                if days_in_week <= 0:
                    continue
                
                # Prorate weekly budget if partial week
                if days_in_week < 7:
                    week_budget = daily_rate * days_in_week
                else:
                    week_budget = weekly_budget
                
                allocations.append({
                    'week_start_date': week_start,
                    'week_end_date': week_end,
                    'campaign_id': campaign_id,
                    'campaign_name': campaign_name,
                    'weekly_budget': round(week_budget, 2)
                })
                
                # Debug: Show which campaigns contribute to December weeks
                if week_start.year == 2025 and week_start.month == 12:
                    account_name = campaign.get('account_name', 'Unknown')
                    advertiser_name = campaign.get('advertiser_name', 'Unknown')
                    print(f"      📅 Dec week {week_start}: Campaign '{campaign_name[:40]}' (ID: {campaign_id}) | Account: {account_name[:30]} | Advertiser: {advertiser_name[:30]} | Contributes ${week_budget:.2f} (Ends: {end_date}, Remaining: ${remaining_budget:.2f})")
        
        if not allocations:
            print(f"      ⚠️  No budget allocations generated")
            if campaigns_with_dates:
                sample = campaigns_with_dates[0]
                print(f"      Sample campaign dates: {sample.get('start_date')} to {sample.get('end_date')}")
                print(f"      Today: {today}, Future weeks start: {future_weeks[0][0] if future_weeks else 'N/A'}")
            return pd.DataFrame(columns=['week_start_date', 'week_end_date', 'campaign_id', 'campaign_name', 'weekly_budget'])
        
        print(f"      ✅ Generated {len(allocations)} budget allocation rows")
        return pd.DataFrame(allocations)
    
    def _generate_week_boundaries(self, start_date: datetime.date, num_weeks: int) -> List[tuple]:
        """
        Generate week boundaries (Monday-Sunday, ISO week) starting from start_date.
        
        Args:
            start_date: Starting date
            num_weeks: Number of weeks to generate
            
        Returns:
            List of (week_start, week_end) tuples
        """
        # Find the Monday of the week containing start_date
        days_since_monday = (start_date.weekday()) % 7
        if days_since_monday == 0:
            # Already Monday
            current_monday = start_date
        else:
            # Go back to Monday
            current_monday = start_date - timedelta(days=days_since_monday)
        
        weeks = []
        for i in range(num_weeks):
            week_start = current_monday + timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)
            weeks.append((week_start, week_end))
        
        return weeks

