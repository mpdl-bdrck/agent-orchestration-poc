"""
Formula generation for Google Sheets dashboards.

This module provides functionality to generate formulas for summary dashboards
and pacing analysis.
"""

import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class FormulaGenerator:
    """
    Generate formulas for summary dashboards.
    """

    def __init__(self):
        """Initialize formula generator."""
        pass

    def generate_sum_formula(self, range_ref: str, sheet_name: Optional[str] = None) -> str:
        """
        Generate a SUM formula.

        Args:
            range_ref: Range reference (e.g., "B:B", "B2:B10")
            sheet_name: Optional sheet name for cross-sheet reference

        Returns:
            Google Sheets SUM formula
        """
        full_range = self._format_range_reference(range_ref, sheet_name)
        return f"=SUM({full_range})"

    def generate_average_formula(self, range_ref: str, sheet_name: Optional[str] = None) -> str:
        """
        Generate an AVERAGE formula.

        Args:
            range_ref: Range reference
            sheet_name: Optional sheet name for cross-sheet reference

        Returns:
            Google Sheets AVERAGE formula
        """
        full_range = self._format_range_reference(range_ref, sheet_name)
        return f"=AVERAGE({full_range})"

    def generate_max_formula(self, range_ref: str, sheet_name: Optional[str] = None) -> str:
        """
        Generate a MAX formula.

        Args:
            range_ref: Range reference
            sheet_name: Optional sheet name for cross-sheet reference

        Returns:
            Google Sheets MAX formula
        """
        full_range = self._format_range_reference(range_ref, sheet_name)
        return f"=MAX({full_range})"

    def generate_iferror_formula(self, formula: str, fallback_value: Any = 0) -> str:
        """
        Generate an IFERROR formula.

        Args:
            formula: The formula to wrap with error handling
            fallback_value: Value to return if formula errors

        Returns:
            Google Sheets IFERROR formula
        """
        return f"=IFERROR({formula}, {fallback_value})"

    def generate_portfolio_total_formulas(self, sheet_configs: Dict[str, str]) -> Dict[str, str]:
        """
        Generate a complete set of summary formulas for portfolio analysis.

        Args:
            sheet_configs: Dictionary mapping sheet types to sheet names
                          e.g., {"portfolio_total": "Portfolio TOTAL"}

        Returns:
            Dictionary of cell references to formulas
        """
        formulas = {}

        # Total Budget
        portfolio_sheet = sheet_configs.get("portfolio_total", "Portfolio TOTAL")
        formulas["B2"] = self.generate_sum_formula("B2", portfolio_sheet)

        # Total Spend
        formulas["C2"] = self.generate_sum_formula("C2", portfolio_sheet)

        # Spend Percentage (with error handling)
        spend_pct_formula = f"{formulas['C2']}/{formulas['B2']}"
        formulas["D2"] = self.generate_iferror_formula(spend_pct_formula, 0)

        # Average Campaign Spend %
        campaigns_sheet = sheet_configs.get("campaigns_total", "Campaigns TOTAL")
        formulas["E2"] = self.generate_average_formula("E:E", campaigns_sheet)

        # Best Daily Spend Ratio
        daily_sheet = sheet_configs.get("portfolio_daily", "Portfolio DAILY")
        formulas["F2"] = self.generate_max_formula("F:F", daily_sheet)

        return formulas

    def _format_range_reference(self, range_ref: str, sheet_name: Optional[str] = None) -> str:
        """
        Format a range reference with optional sheet name.

        Args:
            range_ref: Range reference (e.g., "B:B", "B2:B10")
            sheet_name: Optional sheet name

        Returns:
            Formatted range reference
        """
        if sheet_name:
            return f"'{sheet_name}'!{range_ref}"
        return range_ref

    def generate_daily_rates_trend_formulas(self, campaign_config: Dict[str, Any]) -> tuple[Dict[str, str], Dict[str, Any], Dict[str, str]]:
        """
        Generate simple 4-column trend sheet: Date, Target, Actual, Required Daily Rates.

        Returns just the data needed for charting, no extra labels or complexity.

        Args:
            campaign_config: Campaign configuration with dates and budget

        Returns:
            Tuple of (formulas dict, hard_values dict, labels dict)
        """
        # Extract campaign parameters
        start_date = campaign_config.get('start_date', '2025-11-01')
        end_date = campaign_config.get('end_date', '2025-12-31')
        budget = campaign_config.get('budget', 466000)

        # Convert dates to Google Sheets format
        start_parts = start_date.split('-')
        end_parts = end_date.split('-')

        formulas = {}
        hard_values = {}

        # Headers as labels
        labels = {
            "A1": "Date",
            "B1": "Target Daily Rate",
            "C1": "Actual Daily Rate",
            "D1": "Required Daily Rate"
        }

        # Campaign parameters stored in hidden columns for calculations
        hard_values["F2"] = budget  # Campaign Budget as hard value
        formulas["G2"] = f"=DATE({start_parts[0]},{start_parts[1]},{start_parts[2]})"  # Start Date
        formulas["H2"] = f"=DATE({end_parts[0]},{end_parts[1]},{end_parts[2]})"  # End Date

        # Today's data row - the main data for charting
        formulas["A2"] = "=TODAY()"  # Date
        formulas["B2"] = "=F2/DAYS(H2,G2)"  # Target: budget ÷ total_days
        formulas["C2"] = "='Portfolio TOTAL'!B2/DAYS(TODAY(),G2)"  # Actual: spent ÷ days_passed
        formulas["D2"] = "=IF(DAYS(H2,TODAY())>0,(F2-'Portfolio TOTAL'!B2)/DAYS(H2,TODAY()),0)"  # Required: remaining ÷ days_left

        return formulas, hard_values, labels

