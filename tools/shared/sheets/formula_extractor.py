"""
Formula extraction from Google Sheets worksheets.

This module provides functionality to extract formulas from existing worksheets
for analysis and productization.
"""

import json
import logging
from typing import Dict, Optional
from pathlib import Path

from .schema import SchemaValidator

logger = logging.getLogger(__name__)


class FormulaExtractor:
    """
    Extract formulas from existing Google Sheets worksheets.
    """

    def __init__(self, service):
        """
        Initialize formula extractor.

        Args:
            service: Google Sheets API service instance
        """
        self.service = service
        self.schema_validator = SchemaValidator()

    def extract_formulas(self, spreadsheet_id: str, sheet_name: str, range_notation: str = "A:Z") -> Dict[str, str]:
        """
        Extract all formulas from a worksheet range.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the worksheet
            range_notation: Range to extract from (default: A:Z)

        Returns:
            Dictionary mapping cell references to formulas (e.g., {"A1": "=SUM(B:B)", "B2": "=AVERAGE(C:C)"})
        """
        try:
            # Get sheet ID
            sheet_id = self.get_sheet_id_by_name(spreadsheet_id, sheet_name)
            if sheet_id is None:
                raise ValueError(f"Sheet '{sheet_name}' not found in spreadsheet")

            # Get the data with formulas
            result = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                ranges=[f"{sheet_name}!{range_notation}"],
                includeGridData=True
            ).execute()

            formulas = {}

            if 'sheets' in result and len(result['sheets']) > 0:
                sheet_data = result['sheets'][0]

                if 'data' in sheet_data and len(sheet_data['data']) > 0:
                    grid_data = sheet_data['data'][0]

                    if 'rowData' in grid_data:
                        for row_idx, row in enumerate(grid_data['rowData']):
                            if 'values' in row:
                                for col_idx, cell in enumerate(row['values']):
                                    # Check if cell contains a formula
                                    if 'formulaValue' in cell:
                                        # Convert column index to letter (A, B, C, etc.)
                                        col_letter = self._column_index_to_letter(col_idx)
                                        cell_ref = f"{col_letter}{row_idx + 1}"
                                        formulas[cell_ref] = cell['formulaValue']

            logger.info(f"Extracted {len(formulas)} formulas from {sheet_name}")
            return formulas

        except Exception as e:
            logger.error(f"Error extracting formulas from {sheet_name}: {e}")
            raise

    def _column_index_to_letter(self, index: int) -> str:
        """
        Convert column index to Excel-style letter (0 = A, 1 = B, etc.)

        Args:
            index: Zero-based column index

        Returns:
            Column letter (A, B, C, ..., Z, AA, AB, etc.)
        """
        result = ""
        while index >= 0:
            result = chr(65 + (index % 26)) + result
            index = index // 26 - 1
        return result

    def extract_and_save_formulas(self, spreadsheet_id: str, sheet_name: str,
                                output_path: str, range_notation: str = "A:Z") -> bool:
        """
        Extract formulas from a sheet and save them in the JSON schema format.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the worksheet
            output_path: Path to save the JSON file
            range_notation: Range to extract from

        Returns:
            True if successful, False otherwise
        """
        try:
            formulas = self.extract_formulas(spreadsheet_id, sheet_name, range_notation)

            # Convert to schema format
            schema_formulas = {}
            for cell_ref, formula in formulas.items():
                schema_formulas[cell_ref] = {
                    "formula": formula,
                    "description": f"Extracted formula from {cell_ref}",
                    "fallback_value": ""
                }

            config_data = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "metadata": {
                    "name": f"Extracted Formulas from {sheet_name}",
                    "description": f"Formulas extracted from {sheet_name} in spreadsheet {spreadsheet_id}",
                    "version": "1.0",
                    "extracted_from": {
                        "spreadsheet_id": spreadsheet_id,
                        "sheet_name": sheet_name,
                        "range": range_notation
                    },
                    "extraction_date": "2025-11-21"
                },
                "formulas": schema_formulas
            }

            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Validate the generated configuration
            validation_errors = self.schema_validator.validate_formula_config(config_data)
            if validation_errors:
                logger.warning(f"Generated config has validation issues: {'; '.join(validation_errors)}")

            with open(output_path, 'w') as f:
                json.dump(config_data, f, indent=2)

            logger.info(f"Saved {len(formulas)} extracted formulas to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error extracting and saving formulas: {e}")
            return False

    def get_sheet_id_by_name(self, spreadsheet_id: str, sheet_name: str) -> Optional[int]:
        """
        Get the sheet ID (gid) for a sheet by name.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the worksheet

        Returns:
            Sheet ID (gid) or None if not found
        """
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            return None
        except Exception as e:
            logger.error(f"Error getting sheet ID for {sheet_name}: {e}")
            return None

