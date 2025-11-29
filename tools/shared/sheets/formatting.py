"""
Automated formatting extraction and application for Google Sheets.

This module provides functionality to:
- Extract formatting presets from professionally designed sheets
- Apply consistent formatting to new worksheets
- Manage formatting configurations as version-controlled JSON
- Handle number formats, conditional formatting, and layout properties
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class FormattingExtractor:
    """
    Extract formatting configurations from Google Sheets.
    """

    def __init__(self, service):
        """
        Initialize formatting extractor.

        Args:
            service: Google Sheets API service instance
        """
        self.service = service

    def extract_formatting_preset(self, spreadsheet_id: str, sheet_name: str) -> Dict[str, Any]:
        """
        Extract complete formatting preset from a worksheet.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the worksheet to extract from

        Returns:
            Formatting preset dictionary
        """
        try:
            # Get spreadsheet metadata
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

            # Find the target sheet
            target_sheet = None
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    target_sheet = sheet
                    break

            if not target_sheet:
                raise ValueError(f"Sheet '{sheet_name}' not found in spreadsheet")

            # Get detailed sheet data with formatting
            sheet_data = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                ranges=[f"{sheet_name}!A:Z"],
                includeGridData=True
            ).execute()

            # Extract formatting from the sheet data
            preset = {
                "metadata": {
                    "extracted_from": spreadsheet_id,
                    "sheet_name": sheet_name,
                    "extracted_at": "2025-11-21T00:00:00Z",
                    "description": f"Auto-extracted formatting preset from {sheet_name}"
                },
                "columns": self._extract_column_formatting(target_sheet),
                "header_row": self._extract_header_formatting(sheet_data, sheet_name),
                "conditional_formatting_rules": target_sheet.get('conditionalFormats', []),
                "filters": self._extract_filter_settings(target_sheet),
                "frozen_rows": target_sheet['properties'].get('gridProperties', {}).get('frozenRowCount', 0),
                "frozen_columns": target_sheet['properties'].get('gridProperties', {}).get('frozenColumnCount', 0),
                "sheet_properties": self._extract_sheet_properties(target_sheet)
            }

            logger.info(f"Successfully extracted formatting preset from {sheet_name}")
            return preset

        except Exception as e:
            logger.error(f"Error extracting formatting from {sheet_name}: {e}")
            raise

    def _extract_column_formatting(self, sheet: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract column formatting from sheet properties.

        Args:
            sheet: Sheet object from Google Sheets API

        Returns:
            List of column formatting configurations
        """
        columns = []

        # Extract column metadata
        column_metadata = sheet.get('columnMetadata', [])
        for col_idx, col_meta in enumerate(column_metadata):
            col_config = {
                "index": col_meta.get('columnIndex', col_idx),
                "width": col_meta.get('pixelSize', 100),
                "hidden": col_meta.get('hiddenByUser', False)
            }
            columns.append(col_config)

        # If no column metadata, create default columns
        if not columns:
            # Assume at least 10 columns with default formatting
            for i in range(10):
                columns.append({
                    "index": i,
                    "width": 100,
                    "hidden": False
                })

        return columns

    def _extract_header_formatting(self, sheet_data: Dict[str, Any], sheet_name: str) -> Dict[str, Any]:
        """
        Extract header row formatting.

        Args:
            sheet_data: Sheet data from Google Sheets API
            sheet_name: Name of the sheet

        Returns:
            Header row formatting configuration
        """
        header_format = {}

        # Get the first sheet's data
        sheets = sheet_data.get('sheets', [])
        if not sheets:
            return header_format

        sheet = sheets[0]
        grid_data = sheet.get('data', [])
        if not grid_data:
            return header_format

        row_data = grid_data[0].get('rowData', [])
        if not row_data:
            return header_format

        # Get first row (header row)
        header_row = row_data[0]
        values = header_row.get('values', [])

        if values:
            first_cell = values[0]
            effective_format = first_cell.get('effectiveFormat', {})

            # Extract key formatting properties
            if 'backgroundColor' in effective_format:
                header_format['backgroundColor'] = effective_format['backgroundColor']
            if 'textFormat' in effective_format:
                header_format['textFormat'] = effective_format['textFormat']
            if 'horizontalAlignment' in effective_format:
                header_format['horizontalAlignment'] = effective_format['horizontalAlignment']
            if 'verticalAlignment' in effective_format:
                header_format['verticalAlignment'] = effective_format['verticalAlignment']

        return header_format

    def _extract_filter_settings(self, sheet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract filter settings from sheet.

        Args:
            sheet: Sheet object from Google Sheets API

        Returns:
            Filter configuration
        """
        filters = {"enabled": False}

        if 'basicFilter' in sheet:
            filters = {
                "enabled": True,
                "range": sheet['basicFilter'].get('range', {}),
                "sortSpecs": sheet['basicFilter'].get('sortSpecs', []),
                "criteria": sheet['basicFilter'].get('criteria', {})
            }

        return filters

    def _extract_sheet_properties(self, sheet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract general sheet properties.

        Args:
            sheet: Sheet object from Google Sheets API

        Returns:
            Sheet properties configuration
        """
        properties = sheet.get('properties', {})

        return {
            "title": properties.get('title', ''),
            "sheetType": properties.get('sheetType', 'GRID'),
            "gridProperties": properties.get('gridProperties', {}),
            "tabColor": properties.get('tabColor', {}),
            "hidden": properties.get('hidden', False)
        }

    def extract_data_formatting(self, spreadsheet_id: str, sheet_name: str,
                              range_notation: str = "A:Z") -> Dict[str, Dict[str, Any]]:
        """
        Extract data formatting from cell ranges (number formats, etc.).

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the worksheet
            range_notation: Range to extract from

        Returns:
            Dictionary mapping cell references to formatting
        """
        try:
            # Get sheet data with formatting
            sheet_data = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                ranges=[f"{sheet_name}!{range_notation}"],
                includeGridData=True
            ).execute()

            formatting = {}

            sheets = sheet_data.get('sheets', [])
            if sheets:
                grid_data = sheets[0].get('data', [])
                if grid_data:
                    row_data = grid_data[0].get('rowData', [])

                    for row_idx, row in enumerate(row_data):
                        values = row.get('values', [])
                        for col_idx, cell in enumerate(values):
                            if 'effectiveFormat' in cell:
                                col_letter = chr(65 + col_idx)  # A, B, C, etc.
                                cell_ref = f"{col_letter}{row_idx + 1}"

                                format_info = {}

                                # Extract number format
                                if 'numberFormat' in cell['effectiveFormat']:
                                    format_info['numberFormat'] = cell['effectiveFormat']['numberFormat']

                                # Extract text format
                                if 'textFormat' in cell['effectiveFormat']:
                                    format_info['textFormat'] = cell['effectiveFormat']['textFormat']

                                # Extract background color
                                if 'backgroundColor' in cell['effectiveFormat']:
                                    format_info['backgroundColor'] = cell['effectiveFormat']['backgroundColor']

                                # Extract borders
                                if 'borders' in cell['effectiveFormat']:
                                    format_info['borders'] = cell['effectiveFormat']['borders']

                                if format_info:
                                    formatting[cell_ref] = format_info

            return formatting

        except Exception as e:
            logger.error(f"Error extracting data formatting: {e}")
            return {}

    def create_comprehensive_preset(self, spreadsheet_id: str, sheet_name: str,
                                  include_data_formatting: bool = True) -> Dict[str, Any]:
        """
        Create a comprehensive formatting preset including all formatting aspects.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the worksheet
            include_data_formatting: Whether to include detailed cell formatting

        Returns:
            Comprehensive formatting preset
        """
        try:
            # Get basic formatting preset
            preset = self.extract_formatting_preset(spreadsheet_id, sheet_name)

            # Add detailed data formatting if requested
            if include_data_formatting:
                data_formatting = self.extract_data_formatting(spreadsheet_id, sheet_name)
                preset['data_formatting'] = data_formatting

                # Update metadata
                preset['metadata']['data_formatting_included'] = True
                preset['metadata']['data_cells_formatted'] = len(data_formatting)

            logger.info(f"Created comprehensive formatting preset for {sheet_name}")
            return preset

        except Exception as e:
            logger.error(f"Error creating comprehensive preset: {e}")
            raise

    def save_preset(self, preset: Dict[str, Any], filepath: str) -> None:
        """
        Save formatting preset to JSON file.

        Args:
            preset: Formatting preset dictionary
            filepath: Path to save the preset
        """
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'w') as f:
                json.dump(preset, f, indent=2)

            logger.info(f"Formatting preset saved to {filepath}")

        except Exception as e:
            logger.error(f"Error saving formatting preset: {e}")
            raise


class FormattingApplicator:
    """
    Apply formatting presets to Google Sheets.
    """

    def __init__(self, service):
        """
        Initialize formatting applicator.

        Args:
            service: Google Sheets API service instance
        """
        self.service = service

    def apply_preset(self, spreadsheet_id: str, sheet_id: int, preset: Dict[str, Any]) -> bool:
        """
        Apply a formatting preset to a worksheet.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_id: Google Sheets sheet ID (gid)
            preset: Formatting preset dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            requests = []

            # Apply column formatting
            if 'columns' in preset:
                requests.extend(self._create_column_requests(sheet_id, preset['columns']))

            # Apply header row formatting
            if 'header_row' in preset:
                requests.extend(self._create_header_requests(sheet_id, preset['header_row']))

            # Apply data cell formatting
            if 'data_formatting' in preset:
                requests.extend(self._create_data_formatting_requests(sheet_id, preset['data_formatting']))

            # Apply conditional formatting
            if 'conditional_formatting_rules' in preset:
                requests.extend(self._create_conditional_formatting_requests(sheet_id, preset['conditional_formatting_rules']))

            # Apply filters
            if preset.get('filters', {}).get('enabled'):
                requests.extend(self._create_filter_requests(sheet_id, preset['filters']))

            # Apply frozen rows/columns
            frozen_requests = self._create_frozen_requests(sheet_id, preset)
            if frozen_requests:
                requests.extend(frozen_requests)

            # Execute all requests
            if requests:
                batch_size = 50  # Google Sheets API limit
                for i in range(0, len(requests), batch_size):
                    batch = requests[i:i + batch_size]
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={"requests": batch}
                    ).execute()

                logger.info(f"Successfully applied {len(requests)} formatting operations to sheet {sheet_id}")
            else:
                logger.info("No formatting operations to apply")

            return True

        except Exception as e:
            logger.error(f"Error applying formatting preset: {e}")
            return False

    def _create_column_requests(self, sheet_id: int, columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create requests for column formatting."""
        requests = []

        for col in columns:
            col_index = col['index']

            # Column width and visibility
            if 'width' in col or 'hidden' in col:
                request = {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": col_index,
                            "endIndex": col_index + 1
                        },
                        "properties": {},
                        "fields": ""
                    }
                }

                if 'width' in col:
                    request["properties"]["pixelSize"] = col["width"]
                    request["fields"] += "pixelSize,"

                if 'hidden' in col:
                    request["properties"]["hiddenByUser"] = col["hidden"]
                    request["fields"] += "hiddenByUser,"

                if request["fields"]:
                    request["fields"] = request["fields"].rstrip(",")
                    requests.append(request)

        return requests

    def _create_header_requests(self, sheet_id: int, header_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create requests for header row formatting."""
        if not header_config:
            return []

        # Apply to first row (header row)
        range_spec = {
            "sheetId": sheet_id,
            "startRowIndex": 0,
            "endRowIndex": 1
        }

        cell_format = {}

        if 'backgroundColor' in header_config:
            cell_format['backgroundColor'] = header_config['backgroundColor']
        if 'textFormat' in header_config:
            cell_format['textFormat'] = header_config['textFormat']
        if 'horizontalAlignment' in header_config:
            cell_format['horizontalAlignment'] = header_config['horizontalAlignment']
        if 'verticalAlignment' in header_config:
            cell_format['verticalAlignment'] = header_config['verticalAlignment']

        if cell_format:
            return [{
                "repeatCell": {
                    "range": range_spec,
                    "cell": {
                        "userEnteredFormat": cell_format
                    },
                    "fields": f"userEnteredFormat({','.join(cell_format.keys())})"
                }
            }]

        return []

    def _create_data_formatting_requests(self, sheet_id: int, data_formatting: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create requests for data cell formatting."""
        requests = []

        for cell_range, formatting in data_formatting.items():
            # Parse cell range (e.g., "A2:A1000" or "D2:E1000")
            range_spec = self._parse_cell_range(sheet_id, cell_range)

            if range_spec and formatting:
                request = {
                    "repeatCell": {
                        "range": range_spec,
                        "cell": {
                            "userEnteredFormat": formatting
                        },
                        "fields": f"userEnteredFormat({','.join(formatting.keys())})"
                    }
                }
                requests.append(request)

        return requests

    def _create_conditional_formatting_requests(self, sheet_id: int, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create requests for conditional formatting."""
        requests = []

        for rule in rules:
            # Update sheet ID in rule ranges
            if 'ranges' in rule:
                for range_obj in rule['ranges']:
                    range_obj['sheetId'] = sheet_id

            requests.append({
                "addConditionalFormatRule": {
                    "rule": rule,
                    "index": len(requests)
                }
            })

        return requests

    def _create_filter_requests(self, sheet_id: int, filter_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create requests for filter application."""
        if not filter_config.get('enabled'):
            return []

        filter_range = filter_config.get('range', {})
        if filter_range:
            filter_range['sheetId'] = sheet_id

            return [{
                "setBasicFilter": {
                    "filter": {
                        "range": filter_range
                    }
                }
            }]

        return []

    def _create_frozen_requests(self, sheet_id: int, preset: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create requests for frozen rows/columns."""
        frozen_row_count = preset.get('frozen_rows', 0)
        frozen_col_count = preset.get('frozen_columns', 0)

        if frozen_row_count > 0 or frozen_col_count > 0:
            return [{
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {
                            "frozenRowCount": frozen_row_count,
                            "frozenColumnCount": frozen_col_count
                        }
                    },
                    "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount"
                }
            }]

        return []

    def _parse_cell_range(self, sheet_id: int, cell_range: str) -> Optional[Dict[str, Any]]:
        """
        Parse a cell range string into Google Sheets API format.

        Args:
            sheet_id: Sheet ID
            cell_range: Range string like "A2:A1000" or "D2:E1000"

        Returns:
            Range specification for Google Sheets API
        """
        try:
            if ':' in cell_range:
                start_cell, end_cell = cell_range.split(':')

                start_col, start_row = self._parse_cell_reference(start_cell)
                end_col, end_row = self._parse_cell_reference(end_cell)

                start_col_idx = self._column_letter_to_index(start_col)
                end_col_idx = self._column_letter_to_index(end_col)

                return {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row - 1,  # 0-based
                    "endRowIndex": end_row,  # Exclusive
                    "startColumnIndex": start_col_idx,
                    "endColumnIndex": end_col_idx + 1  # Exclusive
                }
            else:
                # Single cell
                col_letter, row_num = self._parse_cell_reference(cell_range)
                col_idx = self._column_letter_to_index(col_letter)

                return {
                    "sheetId": sheet_id,
                    "startRowIndex": row_num - 1,
                    "endRowIndex": row_num,
                    "startColumnIndex": col_idx,
                    "endColumnIndex": col_idx + 1
                }

        except Exception as e:
            logger.warning(f"Could not parse cell range '{cell_range}': {e}")
            return None

    def _parse_cell_reference(self, cell_ref: str) -> tuple[str, int]:
        """
        Parse a cell reference like 'A1' into column letter and row number.

        Args:
            cell_ref: Cell reference

        Returns:
            Tuple of (column_letter, row_number)
        """
        import re
        match = re.match(r'^([A-Z]+)([0-9]+)$', cell_ref)
        if match:
            return match.group(1), int(match.group(2))
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

    def load_preset(self, filepath: str) -> Dict[str, Any]:
        """
        Load formatting preset from JSON file.

        Args:
            filepath: Path to preset file

        Returns:
            Formatting preset dictionary
        """
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading formatting preset: {e}")
            raise

    def apply_preset_from_file(self, spreadsheet_id: str, sheet_id: int, preset_filepath: str) -> bool:
        """
        Load and apply preset from file.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_id: Google Sheets sheet ID (gid)
            preset_filepath: Path to preset file

        Returns:
            True if successful, False otherwise
        """
        try:
            preset = self.load_preset(preset_filepath)
            return self.apply_preset(spreadsheet_id, sheet_id, preset)
        except Exception as e:
            logger.error(f"Error applying preset from file: {e}")
            return False


class FormattingManager:
    """
    High-level manager for formatting operations.
    """

    def __init__(self, service):
        """
        Initialize formatting manager.

        Args:
            service: Google Sheets API service instance
        """
        self.service = service
        self.extractor = FormattingExtractor(service)
        self.applicator = FormattingApplicator(service)

    def extract_and_save_preset(self, spreadsheet_id: str, sheet_name: str,
                              preset_filepath: str) -> bool:
        """
        Extract formatting from a sheet and save as preset.

        Args:
            spreadsheet_id: Source spreadsheet ID
            sheet_name: Source sheet name
            preset_filepath: Where to save the preset

        Returns:
            True if successful, False otherwise
        """
        try:
            preset = self.extractor.extract_formatting_preset(spreadsheet_id, sheet_name)
            self.extractor.save_preset(preset, preset_filepath)
            return True
        except Exception as e:
            logger.error(f"Error extracting and saving preset: {e}")
            return False
