"""
Formula application to Google Sheets.

This module handles applying formulas to worksheets with error handling
and fallback values.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class FormulaApplicator:
    """
    Apply formulas to Google Sheets with error handling.
    """

    def __init__(self, service):
        """
        Initialize formula applicator.

        Args:
            service: Google Sheets API service instance
        """
        self.service = service

    def apply_formulas_with_fallbacks(self, spreadsheet_id: str, sheet_id: int,
                                    formula_configs: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        """
        Apply formulas with individual error handling and fallbacks.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_id: Sheet ID (gid)
            formula_configs: Dictionary mapping cell refs to formula configs with fallbacks

        Returns:
            Dictionary mapping cell refs to success status
        """
        results = {}

        for cell_ref, config in formula_configs.items():
            try:
                formula = config["formula"]
                fallback = config.get("fallback_value", "")

                # Try to apply the formula
                success = self._apply_single_formula(spreadsheet_id, sheet_id, cell_ref, formula)
                results[cell_ref] = success

                if not success:
                    logger.warning(f"Failed to apply formula to {cell_ref}, using fallback")
                    # Apply fallback value
                    self._apply_fallback_value(spreadsheet_id, sheet_id, cell_ref, fallback)

            except Exception as e:
                logger.error(f"Error applying formula to {cell_ref}: {e}")
                results[cell_ref] = False
                try:
                    fallback = config.get("fallback_value", "")
                    self._apply_fallback_value(spreadsheet_id, sheet_id, cell_ref, fallback)
                except Exception as fallback_error:
                    logger.error(f"Error applying fallback to {cell_ref}: {fallback_error}")

        return results

    def apply_formulas(self, spreadsheet_id: str, sheet_id: int,
                      formulas: Dict[str, str]) -> bool:
        """
        Apply formulas to a specific sheet with error handling.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_id: Sheet ID (gid)
            formulas: Dictionary of cell references to formulas

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert simple formula dict to config format with fallbacks
            formula_configs = {}
            for cell_ref, formula in formulas.items():
                formula_configs[cell_ref] = {
                    "formula": formula,
                    "fallback_value": "#ERROR!"
                }

            # Apply with error handling
            results = self.apply_formulas_with_fallbacks(spreadsheet_id, sheet_id, formula_configs)

            # Check overall success
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)

            logger.info(f"Applied {success_count}/{total_count} formulas successfully")

            # Consider it successful if at least 80% of formulas worked
            return success_count / total_count >= 0.8 if total_count > 0 else True

        except Exception as e:
            logger.error(f"Error applying formulas to sheet: {e}")
            return False

    def _apply_single_formula(self, spreadsheet_id: str, sheet_id: int,
                            cell_ref: str, formula: str) -> bool:
        """
        Apply a single formula to a cell.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_id: Sheet ID (gid)
            cell_ref: Cell reference (e.g., 'A1')
            formula: Formula to apply

        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse cell reference
            col_letter, row_str = self._parse_cell_reference(cell_ref)
            col_index = self._column_letter_to_index(col_letter)
            row_index = int(row_str) - 1  # Convert to 0-based

            request = {
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
                                "formulaValue": formula
                            }
                        }]
                    }],
                    "fields": "userEnteredValue.formulaValue"
                }
            }

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": [request]}
            ).execute()

            return True

        except Exception as e:
            logger.error(f"Error applying formula {formula} to {cell_ref}: {e}")
            return False

    def _apply_fallback_value(self, spreadsheet_id: str, sheet_id: int,
                            cell_ref: str, fallback_value: Any) -> None:
        """
        Apply a fallback value to a cell when formula fails.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_id: Sheet ID (gid)
            cell_ref: Cell reference
            fallback_value: Value to apply as fallback
        """
        try:
            # Parse cell reference
            col_letter, row_str = self._parse_cell_reference(cell_ref)
            col_index = self._column_letter_to_index(col_letter)
            row_index = int(row_str) - 1  # Convert to 0-based

            # Determine value type
            if isinstance(fallback_value, str):
                value_type = "stringValue"
            elif isinstance(fallback_value, (int, float)):
                value_type = "numberValue"
            else:
                value_type = "stringValue"
                fallback_value = str(fallback_value)

            request = {
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
                                value_type: fallback_value
                            }
                        }]
                    }],
                    "fields": f"userEnteredValue.{value_type}"
                }
            }

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": [request]}
            ).execute()

        except Exception as e:
            logger.error(f"Error applying fallback value to {cell_ref}: {e}")

    def _parse_cell_reference(self, cell_ref: str) -> tuple[str, str]:
        """
        Parse a cell reference like 'A1' into column letter and row number.

        Args:
            cell_ref: Cell reference (e.g., 'A1', 'B2')

        Returns:
            Tuple of (column_letter, row_number)
        """
        import re
        match = re.match(r'^([A-Z]+)([0-9]+)$', cell_ref.upper())
        if match:
            return match.group(1), match.group(2)
        raise ValueError(f"Invalid cell reference: {cell_ref}")

    def _column_letter_to_index(self, col_letter: str) -> int:
        """
        Convert column letter to zero-based column index.

        Args:
            col_letter: Column letter (A, B, C, ..., AA, AB, etc.)

        Returns:
            Zero-based column index
        """
        index = 0
        for i, char in enumerate(reversed(col_letter)):
            index += (ord(char) - ord('A') + 1) * (26 ** i)
        return index - 1

