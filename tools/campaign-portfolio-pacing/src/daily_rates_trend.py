"""
Daily Rates Trend Calculator
============================

Calculates Target, Actual, and Required Daily Rates for each day of the campaign.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DailyRatesTrendCalculator:
    """Calculates daily rates trend data for campaign pacing analysis."""

    def __init__(self, sheets_service):
        """
        Initialize calculator with Google Sheets service.

        Args:
            sheets_service: Google Sheets API service instance
        """
        self.service = sheets_service

    def read_campaign_config_from_summary(self, spreadsheet_id: str) -> Dict[str, Any]:
        """
        Read campaign configuration from Summary tab.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID

        Returns:
            Dict with start_date, end_date, budget
        """
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range="'Summary'!B4:B12",
                valueRenderOption='FORMATTED_VALUE'
            ).execute()

            values = result.get('values', [])
            if len(values) >= 9:
                start_val = values[0][0] if len(values[0]) > 0 else None
                end_val = values[1][0] if len(values) > 1 and len(values[1]) > 0 else None
                budget_val = values[8][0] if len(values) > 8 and len(values[8]) > 0 else None

                # Parse dates (DD/MM/YYYY format from Google Sheets)
                start_date = None
                end_date = None
                budget = None

                if start_val:
                    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y']:
                        try:
                            parsed = datetime.strptime(str(start_val), fmt)
                            start_date = parsed.strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            continue

                if end_val:
                    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y']:
                        try:
                            parsed = datetime.strptime(str(end_val), fmt)
                            end_date = parsed.strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            continue

                if budget_val:
                    budget_str = str(budget_val).replace('$', '').replace(',', '').strip()
                    try:
                        budget = float(budget_str)
                    except ValueError:
                        pass

                if start_date and end_date and budget:
                    return {
                        'start_date': start_date,
                        'end_date': end_date,
                        'budget': budget
                    }

        except Exception as e:
            logger.warning(f"Could not read campaign config from Summary tab: {e}")

        return {}

    def read_portfolio_daily_spend(self, spreadsheet_id: str) -> Dict[str, float]:
        """
        Read historical daily spend from Portfolio DAILY sheet.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID

        Returns:
            Dict mapping date strings (YYYY-MM-DD) to spend amounts
        """
        portfolio_daily_spend = {}
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range="'Portfolio DAILY'!A:D"
            ).execute()

            values = result.get('values', [])
            if values and len(values) > 1:
                # Skip header row, get date (col A) and spend (col D)
                for row in values[1:]:
                    if len(row) >= 4:
                        try:
                            date_val = row[0]
                            spend_val = row[3] if len(row) > 3 else "0"

                            # Parse date
                            parsed_date = None
                            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                                try:
                                    parsed_date = datetime.strptime(str(date_val), fmt)
                                    break
                                except ValueError:
                                    continue

                            if parsed_date is None:
                                continue

                            date_str = parsed_date.strftime('%Y-%m-%d')

                            # Parse spend (remove $ and commas)
                            spend_clean = str(spend_val).replace('$', '').replace(',', '').strip()
                            spend = float(spend_clean) if spend_clean else 0

                            portfolio_daily_spend[date_str] = spend

                        except (ValueError, IndexError, TypeError):
                            continue

            logger.info(f"Loaded {len(portfolio_daily_spend)} days of historical spend data")

        except Exception as e:
            logger.warning(f"Could not read Portfolio DAILY data: {e}")

        return portfolio_daily_spend

    def calculate_daily_rates(
        self,
        start_date: str,
        end_date: str,
        budget: float,
        portfolio_daily_spend: Dict[str, float]
    ) -> List[List[Any]]:
        """
        Calculate daily rates for each day of the campaign.

        Args:
            start_date: Campaign start date (YYYY-MM-DD)
            end_date: Campaign end date (YYYY-MM-DD)
            budget: Total campaign budget
            portfolio_daily_spend: Dict mapping dates to daily spend amounts

        Returns:
            List of rows, each row is [date, target_rate, actual_rate, required_rate]
        """
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        total_days = (end_dt - start_dt).days + 1
        today = datetime.now().date()

        # Build data array
        data = []
        data.append([
            "Date",
            "Target Daily Rate",
            "Actual Daily Rate",
            "Required Daily Rate"
        ])

        # Generate one row per date
        current_date = start_dt

        for i in range(total_days):
            date_str = current_date.strftime('%Y-%m-%d')
            date_obj = current_date.date()

            # Target Daily Rate: Same for all dates (budget ÷ total days)
            target_rate = budget / total_days

            # Actual Daily Rate: Use actual spend from Portfolio DAILY for this date
            actual_spend = portfolio_daily_spend.get(date_str, 0)
            actual_rate = actual_spend if actual_spend > 0 else ""

            # Required Daily Rate: Calculate for each date based on that date's perspective
            # Formula: (budget - cumulative_spend_up_to_this_date) / days_remaining_from_this_date
            days_remaining = (end_dt.date() - date_obj).days + 1  # +1 to include the end date

            if days_remaining > 0:
                # Calculate cumulative spend up to this date (including this date)
                spend_up_to_date = 0
                check_date = start_dt
                while check_date.date() <= date_obj:
                    check_str = check_date.strftime('%Y-%m-%d')
                    spend_up_to_date += portfolio_daily_spend.get(check_str, 0)
                    check_date += timedelta(days=1)

                budget_remaining = budget - spend_up_to_date
                required_rate = budget_remaining / days_remaining if days_remaining > 0 and budget_remaining > 0 else 0
            else:
                required_rate = ""

            data.append([
                date_str,
                target_rate,
                actual_rate,
                required_rate if required_rate != "" else ""
            ])

            current_date += timedelta(days=1)

        return data

    def generate_trend_data(
        self,
        spreadsheet_id: str,
        campaign_config: Optional[Dict[str, Any]] = None
    ) -> List[List[Any]]:
        """
        Generate complete daily rates trend data.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            campaign_config: Optional campaign config dict (reads from Summary if not provided)

        Returns:
            List of rows for the trend sheet
        """
        # Read campaign config from Summary tab if not provided
        if not campaign_config:
            campaign_config = self.read_campaign_config_from_summary(spreadsheet_id)

        if not campaign_config:
            logger.error("Could not determine campaign configuration")
            return []

        start_date = campaign_config.get('start_date')
        end_date = campaign_config.get('end_date')
        budget = campaign_config.get('budget')

        if not start_date or not end_date or not budget:
            logger.error("Missing required campaign parameters")
            return []

        # Read historical spend data
        portfolio_daily_spend = self.read_portfolio_daily_spend(spreadsheet_id)

        # Calculate daily rates
        return self.calculate_daily_rates(
            start_date=start_date,
            end_date=end_date,
            budget=float(budget),
            portfolio_daily_spend=portfolio_daily_spend
        )

