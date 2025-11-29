"""
Spend Forecaster
================

Forecasts future spend based on historical pacing patterns (Option C: Historical Pacing).
Uses actual spend rate from past 6 weeks to project future 6 weeks, capped at remaining budget.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

from utils.date_parser import parse_date


class SpendForecaster:
    """
    Forecasts future spend based on historical pacing patterns
    """

    def forecast_future_spend(
        self,
        daily_line_items: pd.DataFrame,
        campaigns: List[Dict],
        budget_allocations: pd.DataFrame,
        weeks_past: int = 6,
        weeks_future: int = 6,
        today: datetime = None
    ) -> pd.DataFrame:
        """
        Forecast future weekly spend based on Option C (Historical Pacing).
        
        For each campaign:
        - Calculate past daily spend rate = total_spent / days_elapsed
        - Project weekly spend = daily_rate × 7
        - Cap at remaining budget allocation
        
        For each future week:
        - Sum forecast spend from all campaigns active in that week
        - Respect campaign end dates
        
        Args:
            daily_line_items: DataFrame with daily spend data
            campaigns: List of campaign dicts with campaign_id, campaign_name, budget, start_date, end_date
            budget_allocations: DataFrame from BudgetAllocator with weekly budget allocations
            weeks_past: Number of past weeks to use for historical pacing (default: 6)
            weeks_future: Number of future weeks to forecast (default: 6)
            today: Reference date (defaults to today)
            
        Returns:
            DataFrame with columns: week_start_date, week_end_date, campaign_id, campaign_name, forecast_spend
        """
        if today is None:
            today = datetime.now().date()
        else:
            today = today.date() if isinstance(today, datetime) else today
        
        if not campaigns or daily_line_items.empty:
            return pd.DataFrame(columns=['week_start_date', 'week_end_date', 'campaign_id', 'campaign_name', 'forecast_spend'])
        
        # Filter to past weeks only
        past_cutoff = today - timedelta(days=weeks_past * 7)
        past_spend = daily_line_items[
            pd.to_datetime(daily_line_items['date']).dt.date >= past_cutoff
        ].copy()
        
        # Get unique future weeks from budget_allocations
        if budget_allocations.empty:
            return pd.DataFrame(columns=['week_start_date', 'week_end_date', 'campaign_id', 'campaign_name', 'forecast_spend'])
        
        future_weeks = budget_allocations[['week_start_date', 'week_end_date']].drop_duplicates().values
        
        forecasts = []
        
        for campaign in campaigns:
            campaign_id = campaign['campaign_id']
            campaign_name = campaign['campaign_name']
            start_date_str = campaign.get('start_date')
            end_date_str = campaign.get('end_date')
            
            if not start_date_str or not end_date_str:
                continue
            
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            if not start_date or not end_date:
                continue
            
            # Calculate past daily spend rate
            campaign_past_spend = past_spend[past_spend['campaign_id'] == campaign_id]
            
            if not campaign_past_spend.empty:
                total_spent = campaign_past_spend['total_spent'].sum()
                # Calculate days elapsed (from campaign start or past_cutoff, whichever is later)
                effective_start = max(start_date, past_cutoff)
                days_elapsed = (today - effective_start).days
                
                if days_elapsed > 0:
                    daily_rate = total_spent / days_elapsed
                    projected_weekly = daily_rate * 7
                else:
                    # No historical data, use budget allocation as baseline
                    projected_weekly = None
            else:
                # No historical spend, use budget allocation as baseline
                projected_weekly = None
            
            # Get budget allocations for this campaign
            campaign_budget = budget_allocations[
                budget_allocations['campaign_id'] == campaign_id
            ]
            
            # Forecast for each future week
            for week_start, week_end in future_weeks:
                # Check if campaign is active during this week
                if end_date < week_start or start_date > week_end:
                    continue
                
                # Get budget allocation for this week
                week_budget = campaign_budget[
                    (campaign_budget['week_start_date'] == week_start) &
                    (campaign_budget['week_end_date'] == week_end)
                ]
                
                if week_budget.empty:
                    continue
                
                allocated_budget = week_budget['weekly_budget'].iloc[0]
                
                # Calculate forecast: use projected weekly if available, otherwise use allocated budget
                if projected_weekly is not None:
                    # Cap forecast at allocated budget
                    forecast_spend = min(projected_weekly, allocated_budget)
                else:
                    # No historical data, use allocated budget as forecast
                    forecast_spend = allocated_budget
                
                forecasts.append({
                    'week_start_date': week_start,
                    'week_end_date': week_end,
                    'campaign_id': campaign_id,
                    'campaign_name': campaign_name,
                    'forecast_spend': round(forecast_spend, 2)
                })
        
        if not forecasts:
            return pd.DataFrame(columns=['week_start_date', 'week_end_date', 'campaign_id', 'campaign_name', 'forecast_spend'])
        
        return pd.DataFrame(forecasts)

