"""
Weekly Budget Processor
=======================

Processes daily spend data into weekly aggregates and future projections.
Orchestrates budget allocation and spend forecasting.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

from budget_allocator import BudgetAllocator
from spend_forecaster import SpendForecaster
from utils.date_parser import parse_date


class WeeklyBudgetProcessor:
    """
    Processes daily spend data into weekly aggregates and future projections
    """

    def __init__(self, campaigns: List[Dict], account_id: str = None, advertiser_filter: str = None):
        """
        Initialize the processor.
        
        Args:
            campaigns: List with campaign_id, campaign_name, budget, start_date, end_date
            account_id: Optional account ID for database queries
            advertiser_filter: Optional advertiser filter for database queries
        """
        self.campaigns = campaigns
        self.account_id = account_id
        self.advertiser_filter = advertiser_filter
        self.budget_allocator = BudgetAllocator()
        self.spend_forecaster = SpendForecaster()

    def create_weekly_forecast(
        self, 
        daily_line_items: pd.DataFrame, 
        weeks_past: int = 6, 
        weeks_future: int = 6
    ) -> pd.DataFrame:
        """
        Creates 12-week forecast report (6 weeks past + 6 weeks future).
        
        1. Calculate week boundaries (Monday-Sunday) in UTC
        2. Aggregate past weeks: daily spend → weekly totals
        3. Calculate past weeks budget: sum campaign budgets active each week
        4. Call BudgetAllocator for future weeks budget
        5. Call SpendForecaster for future weeks forecast
        6. Combine into single DataFrame
        
        Args:
            daily_line_items: DataFrame with daily spend data
            weeks_past: Number of past weeks to include (default: 6)
            weeks_future: Number of future weeks to forecast (default: 6)
            
        Returns:
            DataFrame with columns:
            - week_start_date (date)
            - week_end_date (date)
            - past_spend (float, null for future weeks)
            - budget_allocated (float)
            - forecast_spend (float, null for past weeks)
        """
        today = datetime.now().date()
        
        # Generate week boundaries for past and future weeks
        past_weeks = self._generate_past_week_boundaries(today, weeks_past)
        future_weeks = self._generate_future_week_boundaries(today, weeks_future)
        
        # Process past weeks: aggregate spend and calculate budget allocated
        past_data = self._process_past_weeks(daily_line_items, past_weeks)
        
        # Debug: Check campaigns
        campaigns_with_dates = [c for c in self.campaigns if c.get('start_date') and c.get('end_date')]
        print(f"   📊 Campaigns with dates: {len(campaigns_with_dates)}/{len(self.campaigns)}")
        if campaigns_with_dates:
            sample = campaigns_with_dates[0]
            print(f"   📅 Sample campaign: {sample.get('campaign_name', 'Unknown')[:50]}")
            print(f"      Budget: ${sample.get('budget', 0):,.2f}")
            print(f"      Dates: {sample.get('start_date')} to {sample.get('end_date')}")
        
        # Process future weeks: allocate budget and forecast spend
        # Pass db_connector to budget_allocator so it can query total historical spend
        db_connector = None
        if self.account_id or True:  # Always try to get db connector
            try:
                from forecast_analyzer import ForecastAnalyzer
                analyzer = ForecastAnalyzer(self.account_id, self.advertiser_filter)
                db_connector = analyzer.db
            except Exception as e:
                print(f"   ⚠️  Could not initialize database connector: {e}")
        
        future_budget = self.budget_allocator.allocate_future_budget(
            self.campaigns, daily_line_items, weeks_future, today, db_connector
        )
        print(f"   💰 Future budget allocations: {len(future_budget)} rows")
        if not future_budget.empty:
            print(f"      Total budget allocated: ${future_budget['weekly_budget'].sum():,.2f}")
        
        future_forecast = self.spend_forecaster.forecast_future_spend(
            daily_line_items, self.campaigns, future_budget, weeks_past, weeks_future, today
        )
        print(f"   📈 Future forecasts: {len(future_forecast)} rows")
        
        # Aggregate future budget and forecast by week
        future_data = self._process_future_weeks(future_budget, future_forecast, future_weeks)
        
        # Combine past and future data
        all_weeks = past_weeks + future_weeks
        forecast_df = pd.DataFrame({
            'week_start_date': [w[0] for w in all_weeks],
            'week_end_date': [w[1] for w in all_weeks]
        })
        
        # Merge past spend
        forecast_df = forecast_df.merge(
            past_data[['week_start_date', 'past_spend']],
            on='week_start_date',
            how='left'
        )
        
        # Merge budget allocated (from past and future)
        past_budget = past_data[['week_start_date', 'budget_allocated']].rename(
            columns={'budget_allocated': 'budget_allocated_past'}
        )
        future_budget_agg = future_data[['week_start_date', 'budget_allocated']].rename(
            columns={'budget_allocated': 'budget_allocated_future'}
        )
        
        forecast_df = forecast_df.merge(past_budget, on='week_start_date', how='left')
        forecast_df = forecast_df.merge(future_budget_agg, on='week_start_date', how='left')
        
        # Combine budget_allocated columns
        forecast_df['budget_allocated'] = forecast_df['budget_allocated_past'].fillna(0) + \
                                         forecast_df['budget_allocated_future'].fillna(0)
        forecast_df = forecast_df.drop(columns=['budget_allocated_past', 'budget_allocated_future'])
        
        # Merge forecast spend
        forecast_df = forecast_df.merge(
            future_data[['week_start_date', 'forecast_spend']],
            on='week_start_date',
            how='left'
        )
        
        # Sort by week_start_date
        forecast_df = forecast_df.sort_values('week_start_date').reset_index(drop=True)
        
        return forecast_df

    def _generate_past_week_boundaries(self, today: datetime.date, num_weeks: int) -> List[tuple]:
        """Generate week boundaries for past weeks (Monday-Sunday, ISO week)."""
        # Find the Monday of the current week
        days_since_monday = (today.weekday()) % 7
        if days_since_monday == 0:
            current_monday = today
        else:
            current_monday = today - timedelta(days=days_since_monday)
        
        weeks = []
        # Generate past weeks: go back num_weeks weeks from current week
        for i in range(num_weeks, 0, -1):  # Go backwards: num_weeks, num_weeks-1, ..., 1
            week_start = current_monday - timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)
            weeks.append((week_start, week_end))
        
        return weeks

    def _generate_future_week_boundaries(self, today: datetime.date, num_weeks: int) -> List[tuple]:
        """Generate week boundaries for future weeks (Monday-Sunday, ISO week)."""
        # Find the Monday of the current week
        days_since_monday = (today.weekday()) % 7
        if days_since_monday == 0:
            current_monday = today
        else:
            current_monday = today - timedelta(days=days_since_monday)
        
        # Start from next week
        next_monday = current_monday + timedelta(weeks=1)
        
        weeks = []
        for i in range(num_weeks):
            week_start = next_monday + timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)
            weeks.append((week_start, week_end))
        
        return weeks

    def _process_past_weeks(self, daily_line_items: pd.DataFrame, past_weeks: List[tuple]) -> pd.DataFrame:
        """Process past weeks: aggregate spend and calculate budget allocated."""
        if daily_line_items.empty:
            return pd.DataFrame({
                'week_start_date': [w[0] for w in past_weeks],
                'week_end_date': [w[1] for w in past_weeks],
                'past_spend': [0.0] * len(past_weeks),
                'budget_allocated': [0.0] * len(past_weeks)
            })
        
        # Convert date column to date type
        daily_line_items = daily_line_items.copy()
        daily_line_items['date'] = pd.to_datetime(daily_line_items['date']).dt.date
        
        results = []
        
        for week_start, week_end in past_weeks:
            # Aggregate spend for this week
            week_spend = daily_line_items[
                (daily_line_items['date'] >= week_start) &
                (daily_line_items['date'] <= week_end)
            ]
            past_spend = week_spend['total_spent'].sum() if not week_spend.empty else 0.0
            
            # Calculate budget allocated: prorated weekly allocation (consistent with future weeks)
            budget_allocated = 0.0
            for campaign in self.campaigns:
                start_date_str = campaign.get('start_date')
                end_date_str = campaign.get('end_date')
                
                if not start_date_str or not end_date_str:
                    continue
                
                start_date = parse_date(start_date_str)
                end_date = parse_date(end_date_str)
                if not start_date or not end_date:
                    continue
                
                # Check if campaign is active during this week
                if start_date <= week_end and end_date >= week_start:
                    budget = float(campaign.get('budget', 0))
                    if budget <= 0:
                        continue
                    
                    # Calculate prorated weekly budget allocation (same logic as future weeks)
                    total_campaign_days = (end_date - start_date).days + 1
                    if total_campaign_days <= 0:
                        continue
                    
                    daily_budget_rate = budget / total_campaign_days
                    
                    # Calculate days active in this specific week
                    week_start_effective = max(start_date, week_start)
                    week_end_effective = min(end_date, week_end)
                    days_in_week = (week_end_effective - week_start_effective).days + 1
                    
                    if days_in_week > 0:
                        weekly_allocation = daily_budget_rate * days_in_week
                        budget_allocated += weekly_allocation
            
            results.append({
                'week_start_date': week_start,
                'week_end_date': week_end,
                'past_spend': round(past_spend, 2),
                'budget_allocated': round(budget_allocated, 2)
            })
        
        return pd.DataFrame(results)

    def _process_future_weeks(
        self, 
        future_budget: pd.DataFrame, 
        future_forecast: pd.DataFrame,
        future_weeks: List[tuple]
    ) -> pd.DataFrame:
        """Process future weeks: aggregate budget and forecast by week."""
        results = []
        
        for week_start, week_end in future_weeks:
            # Aggregate budget allocated for this week
            week_budget = future_budget[
                (future_budget['week_start_date'] == week_start) &
                (future_budget['week_end_date'] == week_end)
            ]
            budget_allocated = week_budget['weekly_budget'].sum() if not week_budget.empty else 0.0
            
            # Debug: Show which campaigns contribute to December weeks
            if week_start.year == 2025 and week_start.month == 12 and not week_budget.empty:
                print(f"   📊 Dec week {week_start}: {len(week_budget)} campaigns contributing ${budget_allocated:.2f}")
                # Get account and advertiser names from campaigns
                campaign_map = {c['campaign_id']: c for c in self.campaigns}
                for _, row in week_budget.iterrows():
                    campaign_id = row.get('campaign_id')
                    campaign_info = campaign_map.get(campaign_id, {})
                    account_name = campaign_info.get('account_name', 'Unknown')
                    advertiser_name = campaign_info.get('advertiser_name', 'Unknown')
                    print(f"      - {row['campaign_name'][:40]} | Account: {account_name[:25]} | Advertiser: {advertiser_name[:25]} | ${row['weekly_budget']:.2f}")
            
            # Aggregate forecast spend for this week
            week_forecast = future_forecast[
                (future_forecast['week_start_date'] == week_start) &
                (future_forecast['week_end_date'] == week_end)
            ]
            forecast_spend = week_forecast['forecast_spend'].sum() if not week_forecast.empty else None
            
            results.append({
                'week_start_date': week_start,
                'week_end_date': week_end,
                'budget_allocated': round(budget_allocated, 2),
                'forecast_spend': round(forecast_spend, 2) if forecast_spend is not None else None
            })
        
        return pd.DataFrame(results)

