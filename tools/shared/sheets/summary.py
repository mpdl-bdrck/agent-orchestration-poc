"""
Summary dashboard orchestration for Google Sheets.

This module provides high-level orchestration for creating formula-based
summary dashboards and pacing analysis.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from .formula_extractor import FormulaExtractor
from .formula_generator import FormulaGenerator
from .formula_applicator import FormulaApplicator
from .dashboard_formatter import DashboardFormatter
from .schema import SchemaValidator

logger = logging.getLogger(__name__)


class SummaryManager:
    """
    High-level manager for creating summary dashboards.
    """

    def __init__(self, service, formula_generator: Optional[FormulaGenerator] = None):
        """
        Initialize summary manager.

        Args:
            service: Google Sheets API service instance
            formula_generator: Optional FormulaGenerator instance
        """
        self.service = service
        self.formula_generator = formula_generator or FormulaGenerator()
        self.formula_extractor = FormulaExtractor(service)
        self.formula_applicator = FormulaApplicator(service)
        self.dashboard_formatter = DashboardFormatter(service)
        self.schema_validator = SchemaValidator()

    def get_sheet_id_by_name(self, spreadsheet_id: str, sheet_name: str) -> Optional[int]:
        """
        Get the sheet ID (gid) for a sheet by name.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the worksheet

        Returns:
            Sheet ID (gid) or None if not found
        """
        return self.formula_extractor.get_sheet_id_by_name(spreadsheet_id, sheet_name)

    def create_formula_dashboard(self, spreadsheet_id: str, summary_config: Dict[str, Any],
                               rollup_sheets: List[str]) -> bool:
        """
        Create or update a formula-based summary dashboard.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            summary_config: Configuration for summary formulas
            rollup_sheets: List of available rollup sheet names

        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine sheet name for summary (default to "Summary")
            summary_sheet_name = "Summary"

            # Get or create summary sheet
            summary_sheet_id = self.get_sheet_id_by_name(spreadsheet_id, summary_sheet_name)
            if summary_sheet_id is None:
                # Create new summary sheet
                request = {
                    "addSheet": {
                        "properties": {
                            "title": summary_sheet_name
                        }
                    }
                }
                response = self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={"requests": [request]}
                ).execute()

                summary_sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]
                logger.info(f"Created new summary sheet: {summary_sheet_name}")

            # Generate formulas based on available rollup sheets
            sheet_configs = self._infer_sheet_configs(rollup_sheets)
            formulas = summary_config.get("formulas", {})

            # If no custom formulas, generate portfolio summary formulas
            if not formulas:
                formulas = self.formula_generator.generate_portfolio_total_formulas(sheet_configs)

            # Validate formulas before applying
            validation_errors = self._validate_formulas_for_sheets(formulas, sheet_configs)
            if validation_errors:
                logger.warning(f"Formula validation warnings: {'; '.join(validation_errors)}")

            # Apply formulas to the summary sheet
            success = self.formula_applicator.apply_formulas(spreadsheet_id, summary_sheet_id, formulas)
            if success:
                logger.info(f"Successfully created formula dashboard with {len(formulas)} formulas")
            return success

        except Exception as e:
            logger.error(f"Error creating formula dashboard: {e}")
            return False

    def create_pacing_dashboard(self, spreadsheet_id: str, campaign_config: Dict[str, Any],
                               rollup_sheets: List[str]) -> bool:
        """
        Create campaign pacing dashboard with timeline and budget analysis.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            campaign_config: Campaign configuration with dates and budget
            rollup_sheets: List of available rollup sheet names

        Returns:
            True if successful, False otherwise
        """
        try:
            dashboard_sheet_name = "Summary"

            # Check if Summary sheet already exists
            existing_sheet_id = self.get_sheet_id_by_name(spreadsheet_id, dashboard_sheet_name)
            if existing_sheet_id is not None:
                logger.info(f"Summary dashboard already exists at sheet ID {existing_sheet_id} - populating formulas")
                # Actually populate formulas, don't just return True
                return self._populate_pacing_formulas(spreadsheet_id, existing_sheet_id, campaign_config)

            # Create new Summary sheet
            request = {
                "addSheet": {
                    "properties": {
                        "title": dashboard_sheet_name,
                        "gridProperties": {
                            "frozenRowCount": 1,
                            "frozenColumnCount": 1
                        }
                    }
                }
            }
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": [request]}
            ).execute()

            dashboard_sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]
            logger.info(f"Created pacing dashboard sheet: {dashboard_sheet_name} (ID: {dashboard_sheet_id})")

            # Populate labels and formulas
            success = self._populate_pacing_formulas(spreadsheet_id, dashboard_sheet_id, campaign_config)

            if success:
                # Apply formatting and conditional formatting
                self.dashboard_formatter.apply_pacing_formatting(spreadsheet_id, dashboard_sheet_id, campaign_config)
                logger.info("Successfully created campaign pacing dashboard")

            return success

        except Exception as e:
            logger.error(f"Error creating pacing dashboard: {e}")
            return False

    def _populate_pacing_formulas(self, spreadsheet_id: str, sheet_id: int, campaign_config: Dict[str, Any]) -> bool:
        """Populate pacing dashboard with labels, hard values, and formulas."""
        try:
            # Generate formulas and hard values separately
            formulas, hard_values = self._generate_pacing_formulas(campaign_config)
            logger.info(f"Generated {len(formulas)} pacing formulas and {len(hard_values)} hard values")

            # Generate labels
            labels = self._generate_pacing_labels()

            # Apply labels first
            self._apply_labels(spreadsheet_id, sheet_id, labels)

            # Apply hard values (like budget) before formulas
            if hard_values:
                self._apply_hard_values(spreadsheet_id, sheet_id, hard_values)

            # Then apply formulas
            success = self.formula_applicator.apply_formulas(spreadsheet_id, sheet_id, formulas)
            logger.info(f"Applied formulas to sheet {sheet_id}: {success}")

            return success

        except Exception as e:
            logger.error(f"Error populating pacing formulas: {e}")
            return False

    def _generate_pacing_labels(self) -> Dict[str, str]:
        """Generate label text for pacing dashboard."""
        return {
            "A1": "🚀 CAMPAIGN PORTFOLIO PACING DASHBOARD",
            "A3": "📅 CAMPAIGN PORTFOLIO TIMELINE",
            "A4": "Start Date",
            "A5": "End Date",
            "A6": "Today",
            "A7": "Total Days",
            "A8": "Days Passed",
            "A9": "Days Left",
            "A11": "💰 BUDGET STATUS",
            "A12": "Portfolio Budget",
            "A13": "Spent Budget",
            "A14": "Should Have Spent",
            "A15": "Remaining Budget",
            "A17": "📊 DAILY PACING",
            "A18": "Target Daily Rate",
            "A19": "Actual Daily Rate",
            "A20": "Required Daily Rate",
            "A21": "Pacing Status",
            "A22": "Budget % Projection"
        }

    def _generate_pacing_formulas(self, campaign_config: Dict[str, Any]) -> tuple[Dict[str, str], Dict[str, Any]]:
        """Generate pacing dashboard formulas and hard values."""
        formulas = {}
        hard_values = {}

        # Extract campaign parameters
        start_date = campaign_config.get('start_date', '2025-11-01')
        end_date = campaign_config.get('end_date', '2025-12-31')
        budget = campaign_config.get('budget', 466000)

        # Convert dates to Google Sheets format
        start_parts = start_date.split('-')
        end_parts = end_date.split('-')

        # Timeline section
        formulas["B4"] = f"=DATE({start_parts[0]},{start_parts[1]},{start_parts[2]})"
        formulas["B5"] = f"=DATE({end_parts[0]},{end_parts[1]},{end_parts[2]})"
        formulas["B6"] = "=TODAY()"
        formulas["B7"] = "=DAYS(B5, B4)"
        formulas["B8"] = "=DAYS(B6, B4)"
        formulas["B9"] = "=DAYS(B5, B6)"

        # Budget section
        hard_values["B12"] = budget  # Portfolio Budget (hard value)
        formulas["B13"] = "='Portfolio TOTAL'!B2"  # Spent Budget (actual spend from Portfolio TOTAL)
        formulas["B14"] = "=(B12/B7)*B8"  # Should Have Spent (target cumulative spend to date)
        formulas["B15"] = "=B12-B13"  # Remaining Budget

        # Daily Pacing section
        formulas["B18"] = "=B12/B7"  # Target Daily Rate (budget ÷ total days)
        formulas["B19"] = "=B13/B8"  # Actual Daily Rate (spend ÷ days passed)
        formulas["B20"] = "=IF(B9>0,B15/B9,0)"  # Required Daily Rate (remaining ÷ days left)
        formulas["B21"] = '=IF(B13>=(B14-B12*0.01),IF(B13<=(B14+B12*0.01),"🟡 ON PACE","🟢 AHEAD"),"🔴 BEHIND")'  # Pacing Status
        formulas["B22"] = "=(B13 + B9 * B19) / B12"  # Budget % Projection

        return formulas, hard_values

    def _apply_labels(self, spreadsheet_id: str, sheet_id: int, labels: Dict[str, str]) -> None:
        """Apply label text to cells."""
        try:
            requests = []
            for cell_ref, label_text in labels.items():
                # Parse cell reference
                col_letter, row_str = self.formula_applicator._parse_cell_reference(cell_ref)
                col_index = self.formula_applicator._column_letter_to_index(col_letter)
                row_index = int(row_str) - 1

                requests.append({
                    "updateCells": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row_index,
                            "endRowIndex": row_index + 1,
                            "startColumnIndex": col_index,
                            "endColumnIndex": col_index + 1
                        },
                        "rows": [{
                            "values": [{
                                "userEnteredValue": {
                                    "stringValue": label_text
                                }
                            }]
                        }],
                        "fields": "userEnteredValue.stringValue"
                    }
                })

            # Execute in batches
            if requests:
                batch_size = 50
                for i in range(0, len(requests), batch_size):
                    batch = requests[i:i + batch_size]
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={"requests": batch}
                    ).execute()

        except Exception as e:
            logger.error(f"Error applying labels: {e}")

    def _apply_hard_values(self, spreadsheet_id: str, sheet_id: int, hard_values: Dict[str, Any]) -> None:
        """Apply hard values (non-formula) to cells."""
        try:
            requests = []
            for cell_ref, value in hard_values.items():
                # Parse cell reference
                col_letter, row_str = self.formula_applicator._parse_cell_reference(cell_ref)
                col_index = self.formula_applicator._column_letter_to_index(col_letter)
                row_index = int(row_str) - 1

                # Determine value type
                if isinstance(value, (int, float)):
                    value_dict = {"numberValue": value}
                else:
                    value_dict = {"stringValue": str(value)}

                requests.append({
                    "updateCells": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row_index,
                            "endRowIndex": row_index + 1,
                            "startColumnIndex": col_index,
                            "endColumnIndex": col_index + 1
                        },
                        "rows": [{
                            "values": [{
                                "userEnteredValue": value_dict
                            }]
                        }],
                        "fields": "userEnteredValue"
                    }
                })

            # Execute in batches
            if requests:
                batch_size = 50
                for i in range(0, len(requests), batch_size):
                    batch = requests[i:i + batch_size]
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={"requests": batch}
                    ).execute()

            logger.info(f"Applied {len(hard_values)} hard values to sheet")

        except Exception as e:
            logger.error(f"Error applying hard values: {e}")

    def _validate_formulas_for_sheets(self, formulas: Dict[str, str], sheet_configs: Dict[str, str]) -> List[str]:
        """
        Validate that formulas reference valid sheet names.

        Args:
            formulas: Dictionary of formulas
            sheet_configs: Dictionary of available sheet configs

        Returns:
            List of validation error messages
        """
        errors = []
        available_sheets = set(sheet_configs.values())

        for cell_ref, formula in formulas.items():
            sheet_refs = self._extract_sheet_references(formula)
            for sheet_ref in sheet_refs:
                if sheet_ref not in available_sheets:
                    errors.append(f"Formula in {cell_ref} references unknown sheet: {sheet_ref}")

        return errors

    def _extract_sheet_references(self, formula: str) -> List[str]:
        """
        Extract sheet references from a formula.

        Args:
            formula: Formula string

        Returns:
            List of sheet names referenced
        """
        import re
        # Pattern to match sheet references like 'Sheet Name'!A1 or 'Sheet Name'!A:A
        pattern = r"'([^']+)'!"
        matches = re.findall(pattern, formula)
        return matches

    def _infer_sheet_configs(self, rollup_sheets: List[str]) -> Dict[str, str]:
        """
        Infer sheet configuration from rollup sheet names.

        Args:
            rollup_sheets: List of sheet names

        Returns:
            Dictionary mapping sheet types to sheet names
        """
        configs = {}
        for sheet_name in rollup_sheets:
            sheet_lower = sheet_name.lower()
            if "portfolio" in sheet_lower and "total" in sheet_lower:
                configs["portfolio_total"] = sheet_name
            elif "portfolio" in sheet_lower and "daily" in sheet_lower:
                configs["portfolio_daily"] = sheet_name
            elif "campaigns" in sheet_lower and "total" in sheet_lower:
                configs["campaigns_total"] = sheet_name
            elif "campaigns" in sheet_lower and "daily" in sheet_lower:
                configs["campaigns_daily"] = sheet_name
            elif "line items" in sheet_lower and "total" in sheet_lower:
                configs["line_items_total"] = sheet_name
            elif "line items" in sheet_lower and "daily" in sheet_lower:
                configs["line_items_daily"] = sheet_name

        return configs

    def load_formula_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load formula configuration from JSON file.

        Args:
            config_path: Path to JSON configuration file

        Returns:
            Configuration dictionary

        Raises:
            ValueError: If configuration is invalid
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Validate configuration
            errors = self.schema_validator.validate_formula_config(config)
            if errors:
                raise ValueError(f"Invalid formula configuration: {'; '.join(errors)}")

            return config

        except FileNotFoundError:
            raise ValueError(f"Configuration file not found: {config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")

    def validate_formula_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate a formula configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        errors = self.schema_validator.validate_formula_config(config)
        return len(errors) == 0
