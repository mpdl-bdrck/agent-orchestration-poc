"""
Data Rollup Processor
=====================

Processes raw daily line item data into multiple rollup views for comprehensive reporting.
Uses pandas DataFrames for efficient tabular operations.
"""

import pandas as pd
from .utils.logging import setup_logger


class DataRollupProcessor:
    """
    Processes raw daily line item data into multiple rollup views for comprehensive reporting.
    Uses pandas DataFrames for efficient tabular operations.
    """

    def __init__(self, campaign_budgets=None):
        """
        Initialize the rollup processor.

        Args:
            campaign_budgets: Dict mapping campaign_id to budget amount
        """
        self.campaign_budgets = campaign_budgets or {}
        self.logger = setup_logger('data.rollup.processor')

    def _find_common_prefix(self, names):
        """Find the longest common prefix among a list of strings."""
        if not names:
            return ""

        # Sort names to make prefix comparison easier
        sorted_names = sorted(names)

        # Compare first and last (they will have the least in common)
        first, last = sorted_names[0], sorted_names[-1]

        # Find common prefix
        prefix = ""
        for i, char in enumerate(first):
            if i < len(last) and char == last[i]:
                prefix += char
            else:
                break

        # Only keep prefix if it's meaningful (at least 3 chars and ends with separator)
        if len(prefix) >= 3 and (prefix.endswith(' - ') or prefix.endswith(' ')):
            # Find the last complete word/phrase separator
            separators = [' - ', ' ', '-']
            for sep in separators:
                if sep in prefix:
                    last_sep_idx = prefix.rfind(sep)
                    if last_sep_idx > 0:
                        return prefix[:last_sep_idx + len(sep)]

        return ""

    def _clean_names(self, df, name_columns):
        """Remove common prefixes from campaign and line item names."""
        for col in name_columns:
            if col in df.columns and not df[col].empty:
                names = df[col].dropna().unique().tolist()
                common_prefix = self._find_common_prefix(names)
                if common_prefix:
                    # Debug: show before/after
                    print(f"DEBUG: Cleaning {col} - found prefix '{common_prefix}' in {len(names)} names")
                    sample_before = names[:3] if names else []
                    df[col] = df[col].str.replace(f"^{common_prefix}", "", regex=True)
                    sample_after = df[col].dropna().unique().tolist()[:3] if not df[col].empty else []
                    print(f"DEBUG: Sample before: {sample_before}")
                    print(f"DEBUG: Sample after: {sample_after}")
                    self.logger.info(f"Removed common prefix '{common_prefix[:-1]}' from {len(names)} {col} names")

    def create_all_rollups(self, daily_line_items_data):
        """
        Create all 6 rollup views from the raw daily line item data.

        Args:
            daily_line_items_data: List of daily line item records or DataFrame

        Returns:
            dict: Dictionary with all 6 rollup datasets (as pandas DataFrames)
        """
        # Convert to DataFrame for efficient operations
        if isinstance(daily_line_items_data, pd.DataFrame):
            df = daily_line_items_data.copy()
        else:
            df = pd.DataFrame(daily_line_items_data)
        
        # Ensure numeric columns are properly typed and round floats to 2 decimals
        numeric_cols = ['campaign_id', 'line_item_id', 'total_spent', 'total_impressions']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                if col == 'total_spent':
                    df[col] = df[col].round(2)
        
        # Add prev_day_spend_ratio to line_items_daily
        df_with_delta = df.copy()
        if 'line_item_id' in df_with_delta.columns and 'date' in df_with_delta.columns and 'total_spent' in df_with_delta.columns:
            # Sort by line_item_id and date
            df_with_delta = df_with_delta.sort_values(['line_item_id', 'date']).copy()

            # Rename total_spent to spend first (before calculations)
            df_with_delta = df_with_delta.rename(columns={'total_spent': 'spend'})

            # Group by line_item_id and calculate day-over-day delta
            df_with_delta['prev_day_spend'] = df_with_delta.groupby('line_item_id')['spend'].shift(1)

            # Calculate spend multiplier: current / previous
            # Example: 50 -> 100 = 2.00x (2 times previous day), 100 -> 75 = 0.75x (75% of previous day)
            df_with_delta['prev_day_spend_ratio'] = (
                df_with_delta['spend'] / df_with_delta['prev_day_spend']
            )

            # Handle edge cases:
            # - First day (prev_day_spend is NaN) -> prev_day_spend_ratio should be None
            # - Previous day was 0 -> prev_day_spend_ratio should be None (avoid division by zero)
            df_with_delta.loc[df_with_delta['prev_day_spend'].isna(), 'prev_day_spend_ratio'] = None
            df_with_delta.loc[df_with_delta['prev_day_spend'] == 0, 'prev_day_spend_ratio'] = None

            # Round to 2 decimal places (only for non-null values)
            df_with_delta['prev_day_spend_ratio'] = df_with_delta['prev_day_spend_ratio'].round(2)
            
            # Remove temporary column
            df_with_delta = df_with_delta.drop(columns=['prev_day_spend'])
            
            # Rename total_impressions to impressions
            df_with_delta = df_with_delta.rename(columns={'total_impressions': 'impressions'})

            # Reorder columns: date, campaign_id, campaign_name, line_item_id, line_item_name, impressions, spend, prev_day_spend_ratio
            desired_order = ['date', 'campaign_id', 'campaign_name', 'line_item_id', 'line_item_name', 'impressions', 'spend', 'prev_day_spend_ratio']
            available_cols = [col for col in desired_order if col in df_with_delta.columns]
            df_with_delta = df_with_delta[available_cols]
            
            # Sort: line_item_id DESC, date DESC (group line items together chronologically)
            sort_cols = []
            if 'line_item_id' in df_with_delta.columns:
                sort_cols.append('line_item_id')
            if 'date' in df_with_delta.columns:
                sort_cols.append('date')

            if sort_cols:
                df_with_delta = df_with_delta.sort_values(sort_cols, ascending=False).reset_index(drop=True)

        rollups = {
            'line_items_daily': df_with_delta,
            'line_items_total': self._create_line_items_total(df),
            'campaigns_daily': self._create_campaigns_daily(df),
            'campaigns_total': self._create_campaigns_total(df),
            'portfolio_daily': self._create_portfolio_daily(df),
            'portfolio_total': self._create_portfolio_total(df)
        }

        # Apply name cleanup to remove common prefixes
        name_cleanup_rollups = ['line_items_daily', 'line_items_total', 'campaigns_daily', 'campaigns_total']
        for rollup_key in name_cleanup_rollups:
            if rollup_key in rollups and not rollups[rollup_key].empty:
                name_columns = []
                if 'campaign_name' in rollups[rollup_key].columns:
                    name_columns.append('campaign_name')
                if 'line_item_name' in rollups[rollup_key].columns:
                    name_columns.append('line_item_name')
                if name_columns:
                    self._clean_names(rollups[rollup_key], name_columns)

        return rollups

    def _create_line_items_total(self, df):
        """Rollup: Line Items TOTAL - Aggregate by line item across all dates."""
        grouped = df.groupby(['campaign_id', 'line_item_id', 'campaign_name', 'line_item_name'], as_index=False).agg({
            'total_spent': 'sum',
            'total_impressions': 'sum'
        })

        # Rename total_spent to total_spend
        grouped = grouped.rename(columns={'total_spent': 'total_spend'})

        # Round to 2 decimals
        grouped['total_spend'] = grouped['total_spend'].round(2)

        # Calculate spend percentages in decimal format (0.xx)
        grouped['spend_percentage'] = grouped.apply(
            lambda row: round((row['total_spend'] / self.campaign_budgets.get(int(row['campaign_id']), 1)), 4)
            if self.campaign_budgets.get(int(row['campaign_id']), 0) > 0 else 0.0,
            axis=1
        )

        return grouped.sort_values('spend_percentage', ascending=False)

    def _create_campaigns_daily(self, df):
        """Rollup: Campaigns DAILY - Aggregate by campaign and date across line items."""
        grouped = df.groupby(['date', 'campaign_id', 'campaign_name'], as_index=False).agg({
            'total_spent': 'sum',
            'total_impressions': 'sum'
        })

        # Rename total_spent to spend and total_impressions to impressions
        grouped = grouped.rename(columns={
            'total_spent': 'spend',
            'total_impressions': 'impressions'
        })

        # Round to 2 decimals
        grouped['spend'] = grouped['spend'].round(2)

        # Sort by campaign_id and date for prev_day_spend_ratio calculation
        grouped = grouped.sort_values(['campaign_id', 'date'])

        # Calculate prev_day_spend_ratio by campaign_id
        grouped['prev_day_spend'] = grouped.groupby('campaign_id')['spend'].shift(1)
        grouped['prev_day_spend_ratio'] = (
            grouped['spend'] / grouped['prev_day_spend']
        )

        # Handle edge cases: First day or previous day was 0
        grouped.loc[grouped['prev_day_spend'].isna(), 'prev_day_spend_ratio'] = None
        grouped.loc[grouped['prev_day_spend'] == 0, 'prev_day_spend_ratio'] = None

        # Round to 2 decimal places
        grouped['prev_day_spend_ratio'] = grouped['prev_day_spend_ratio'].round(2)

        # Remove temporary column and sort: campaign_id DESC, date DESC
        grouped = grouped.drop(columns=['prev_day_spend'])

        return grouped.sort_values(['campaign_id', 'date'], ascending=[False, False])

    def _create_campaigns_total(self, df):
        """Rollup: Campaigns TOTAL - Aggregate by campaign across dates and line items."""
        grouped = df.groupby(['campaign_id', 'campaign_name'], as_index=False).agg({
            'total_spent': 'sum',
            'total_impressions': 'sum'
        })

        # Rename total_spent to total_spend
        grouped = grouped.rename(columns={'total_spent': 'total_spend'})

        # Round to 2 decimals
        grouped['total_spend'] = grouped['total_spend'].round(2)

        # Add campaign budget
        grouped['campaign_budget'] = grouped['campaign_id'].apply(
            lambda x: float(self.campaign_budgets.get(int(x), 0))
        )

        # Calculate spend percentages in decimal format (0.xx)
        grouped['spend_percentage'] = grouped.apply(
            lambda row: round((row['total_spend'] / row['campaign_budget']), 4)
            if row['campaign_budget'] > 0 else 0.0,
            axis=1
        )

        return grouped.sort_values('spend_percentage', ascending=False)

    def _create_portfolio_daily(self, df):
        """Rollup: Portfolio DAILY - Aggregate all campaigns by date (portfolio-level daily totals)."""
        grouped = df.groupby('date', as_index=False).agg({
            'total_spent': 'sum',
            'total_impressions': 'sum',
            'campaign_id': 'nunique'
        })

        grouped.rename(columns={'campaign_id': 'total_campaigns'}, inplace=True)

        # Rename total_spent to spend and total_impressions to impressions
        grouped = grouped.rename(columns={
            'total_spent': 'spend',
            'total_impressions': 'impressions'
        })

        # Round to 2 decimals
        grouped['spend'] = grouped['spend'].round(2)

        # Sort by date for prev_day_spend_ratio calculation (portfolio level)
        grouped = grouped.sort_values('date')

        # Calculate prev_day_spend_ratio at portfolio level (by date)
        grouped['prev_day_spend'] = grouped['spend'].shift(1)
        grouped['prev_day_spend_ratio'] = (
            grouped['spend'] / grouped['prev_day_spend']
        )

        # Handle edge cases: First day or previous day was 0
        grouped.loc[grouped['prev_day_spend'].isna(), 'prev_day_spend_ratio'] = None
        grouped.loc[grouped['prev_day_spend'] == 0, 'prev_day_spend_ratio'] = None

        # Round to 2 decimal places
        grouped['prev_day_spend_ratio'] = grouped['prev_day_spend_ratio'].round(2)

        # Remove temporary column
        grouped = grouped.drop(columns=['prev_day_spend'])

        # Reorder columns: date, total_campaigns, impressions, spend, prev_day_spend_ratio
        desired_order = ['date', 'total_campaigns', 'impressions', 'spend', 'prev_day_spend_ratio']
        available_cols = [col for col in desired_order if col in grouped.columns]
        grouped = grouped[available_cols]

        return grouped.sort_values('date', ascending=False)

    def _create_portfolio_total(self, df):
        """Rollup: Portfolio TOTAL - Single row with totals across entire portfolio."""
        if df.empty:
            return pd.DataFrame()

        total_spent = round(df['total_spent'].sum(), 2)
        total_impressions = df['total_impressions'].sum()
        total_budget = sum(self.campaign_budgets.values()) if self.campaign_budgets else 0

        # Calculate date range for averaging calculations
        min_date = df['date'].min()
        max_date = df['date'].max()
        days_diff = (pd.to_datetime(max_date) - pd.to_datetime(min_date)).days + 1
        avg_daily_spend = round(total_spent / days_diff, 2) if days_diff > 0 else 0.0
        avg_daily_impressions = int(total_impressions / days_diff) if days_diff > 0 else 0

        # Calculate spend percentage in decimal format (0.xx)
        spend_percentage = round((total_spent / total_budget), 4) if total_budget > 0 else 0.0

        # Create date range string from actual data
        date_range = f"{min_date} to {max_date}"

        return pd.DataFrame([{
            'total_budget': float(total_budget),
            'total_spend': float(total_spent),
            'spend_percentage': float(spend_percentage),
            'avg_daily_spend': float(avg_daily_spend),
            'total_impressions': int(total_impressions),
            'avg_daily_impressions': int(avg_daily_impressions),
            'date_range': date_range
        }])

