"""
AI-powered intelligence layer for Google Sheets automation.

This module provides advanced features like:
- Intelligent formula suggestions based on data analysis
- Dynamic formatting that adapts to data patterns
- Automated chart generation
- Performance optimization and error recovery
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class IntelligenceEngine:
    """
    AI-powered intelligence engine for Google Sheets automation.
    """

    def __init__(self, service):
        """
        Initialize intelligence engine.

        Args:
            service: Google Sheets API service instance
        """
        self.service = service

    def analyze_data_patterns(self, spreadsheet_id: str, sheet_name: str,
                            range_notation: str = "A:Z") -> Dict[str, Any]:
        """
        Analyze data patterns in a worksheet to understand content structure.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the worksheet
            range_notation: Range to analyze

        Returns:
            Analysis results with data patterns and insights
        """
        try:
            # Get sheet data
            sheet_data = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                ranges=[f"{sheet_name}!{range_notation}"],
                includeGridData=True
            ).execute()

            analysis = {
                "row_count": 0,
                "column_count": 0,
                "data_types": {},
                "patterns": {},
                "insights": []
            }

            sheets = sheet_data.get('sheets', [])
            if sheets:
                grid_data = sheets[0].get('data', [])
                if grid_data:
                    row_data = grid_data[0].get('rowData', [])
                    analysis["row_count"] = len(row_data)

                    if row_data:
                        # Analyze first row for column count and headers
                        first_row = row_data[0]
                        values = first_row.get('values', [])
                        analysis["column_count"] = len(values)

                        # Analyze data types and patterns
                        analysis["data_types"] = self._analyze_data_types(row_data)
                        analysis["patterns"] = self._detect_data_patterns(row_data)
                        analysis["insights"] = self._generate_insights(analysis)

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing data patterns: {e}")
            return {}

    def _analyze_data_types(self, row_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Analyze data types in each column."""
        data_types = {}

        if not row_data:
            return data_types

        # Sample first 10 rows (skip header)
        sample_rows = row_data[1:11] if len(row_data) > 1 else []

        for col_idx in range(len(row_data[0].get('values', []))):
            col_type = self._infer_column_type(sample_rows, col_idx)
            col_letter = chr(65 + col_idx)  # A, B, C, etc.
            data_types[col_letter] = col_type

        return data_types

    def _infer_column_type(self, rows: List[Dict[str, Any]], col_idx: int) -> str:
        """Infer the data type of a column."""
        type_counts = {"text": 0, "number": 0, "date": 0, "currency": 0, "percentage": 0}

        for row in rows:
            values = row.get('values', [])
            if col_idx < len(values):
                cell = values[col_idx]
                cell_type = self._classify_cell_type(cell)
                type_counts[cell_type] += 1

        # Return the most common type
        return max(type_counts, key=type_counts.get)

    def _classify_cell_type(self, cell: Dict[str, Any]) -> str:
        """Classify the type of a cell."""
        if 'formattedValue' in cell:
            value = cell['formattedValue']

            # Check for currency symbols
            if any(symbol in value for symbol in ['$', '€', '£', '¥']):
                return "currency"

            # Check for percentage
            if '%' in value:
                return "percentage"

            # Check for numbers
            try:
                float(value.replace(',', '').replace('%', ''))
                return "number"
            except ValueError:
                pass

        # Check effective format
        if 'effectiveFormat' in cell:
            format_info = cell['effectiveFormat']

            if 'numberFormat' in format_info:
                format_type = format_info['numberFormat'].get('type', '')
                if format_type == 'CURRENCY':
                    return "currency"
                elif format_type == 'PERCENT':
                    return "percentage"
                elif format_type in ['NUMBER', 'DATE', 'TIME']:
                    return format_type.lower()

        return "text"

    def _detect_data_patterns(self, row_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect patterns in the data."""
        patterns = {
            "has_headers": False,
            "has_numeric_data": False,
            "has_dates": False,
            "estimated_data_rows": 0,
            "sparsity": 0.0
        }

        if not row_data:
            return patterns

        total_cells = 0
        filled_cells = 0

        # Analyze first row (potential headers)
        first_row = row_data[0]
        first_row_values = first_row.get('values', [])
        if first_row_values:
            # Simple heuristic: headers are often text and don't look like numbers
            header_like = 0
            for cell in first_row_values:
                if 'formattedValue' in cell:
                    value = cell['formattedValue']
                    # Headers are typically not just numbers
                    try:
                        float(value)
                        header_like -= 1
                    except ValueError:
                        header_like += 1
                else:
                    header_like += 1

            patterns["has_headers"] = header_like > len(first_row_values) * 0.5

        # Analyze data density and types
        for row in row_data[1:]:  # Skip header row
            values = row.get('values', [])
            total_cells += len(first_row_values)  # Use first row as reference

            for cell in values:
                if 'formattedValue' in cell and cell['formattedValue'].strip():
                    filled_cells += 1

                    # Check for dates and numbers
                    if self._classify_cell_type(cell) == "date":
                        patterns["has_dates"] = True
                    elif self._classify_cell_type(cell) in ["number", "currency", "percentage"]:
                        patterns["has_numeric_data"] = True

        if total_cells > 0:
            patterns["sparsity"] = 1.0 - (filled_cells / total_cells)
            patterns["estimated_data_rows"] = len(row_data) - (1 if patterns["has_headers"] else 0)

        return patterns

    def _generate_insights(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate insights based on analysis."""
        insights = []

        patterns = analysis.get("patterns", {})

        if patterns.get("has_headers"):
            insights.append("Dataset appears to have headers in the first row")

        if patterns.get("has_numeric_data"):
            insights.append("Contains numeric data - good candidates for SUM, AVERAGE formulas")

        if patterns.get("has_dates"):
            insights.append("Contains date columns - consider trend analysis and date-based filtering")

        sparsity = patterns.get("sparsity", 0)
        if sparsity > 0.5:
            insights.append(".1f")
        elif sparsity > 0.2:
            insights.append("Moderate data density - some columns may be sparsely populated")

        data_rows = patterns.get("estimated_data_rows", 0)
        if data_rows > 1000:
            insights.append("Large dataset - consider performance optimizations")
        elif data_rows < 10:
            insights.append("Small dataset - may benefit from detailed formatting")

        return insights

    def suggest_formulas(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Suggest formulas based on data analysis.

        Args:
            analysis: Data analysis results

        Returns:
            List of formula suggestions with confidence scores
        """
        suggestions = []

        data_types = analysis.get("data_types", {})
        patterns = analysis.get("patterns", {})

        # Suggest SUM formulas for numeric columns
        numeric_cols = [col for col, type_ in data_types.items()
                       if type_ in ["number", "currency"]]

        for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
            suggestions.append({
                "formula": f"=SUM({col}:{col})",
                "description": f"Sum all values in column {col}",
                "confidence": 0.9,
                "category": "aggregation",
                "target_cell": f"{col}{analysis.get('row_count', 0) + 1}"
            })

        # Suggest AVERAGE for numeric data
        if patterns.get("has_numeric_data"):
            suggestions.append({
                "formula": "=AVERAGE(A2:A100)",
                "description": "Calculate average of numeric data range",
                "confidence": 0.8,
                "category": "statistics",
                "target_cell": "B1"
            })

        # Suggest COUNTIF for text columns
        text_cols = [col for col, type_ in data_types.items() if type_ == "text"]
        if text_cols:
            first_text_col = text_cols[0]
            suggestions.append({
                "formula": f"=COUNTIF({first_text_col}:{first_text_col}, \"*<value>*\")",
                "description": f"Count occurrences in {first_text_col} column",
                "confidence": 0.7,
                "category": "counting",
                "target_cell": f"{first_text_col}1"
            })

        # Suggest trend analysis if dates are present
        if patterns.get("has_dates"):
            suggestions.append({
                "formula": "=SLOPE(B2:B100)",
                "description": "Analyze trend slope for time series data",
                "confidence": 0.6,
                "category": "analytics",
                "target_cell": "C1"
            })

        return suggestions

    def suggest_formatting(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest formatting based on data analysis.

        Args:
            analysis: Data analysis results

        Returns:
            Formatting suggestions
        """
        formatting = {
            "column_formats": {},
            "conditional_rules": [],
            "filters": False,
            "frozen_rows": 0
        }

        data_types = analysis.get("data_types", {})
        patterns = analysis.get("patterns", {})

        # Suggest column formats based on data types
        for col, type_ in data_types.items():
            if type_ == "currency":
                formatting["column_formats"][col] = {"type": "CURRENCY", "pattern": "$#,##0.00"}
            elif type_ == "percentage":
                formatting["column_formats"][col] = {"type": "PERCENT", "pattern": "0.00%"}
            elif type_ == "number":
                formatting["column_formats"][col] = {"type": "NUMBER", "pattern": "#,##0.00"}
            elif type_ == "date":
                formatting["column_formats"][col] = {"type": "DATE", "pattern": "yyyy-mm-dd"}

        # Suggest header formatting
        if patterns.get("has_headers"):
            formatting["header_format"] = {
                "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.6},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            }
            formatting["frozen_rows"] = 1

        # Suggest conditional formatting for numeric data
        if patterns.get("has_numeric_data"):
            numeric_cols = [col for col, type_ in data_types.items()
                           if type_ in ["number", "currency", "percentage"]]

            for col in numeric_cols[:2]:  # Limit to first 2 numeric columns
                formatting["conditional_rules"].append({
                    "range": f"{col}2:{col}1000",
                    "condition": "greater_than",
                    "value": "1000",
                    "format": {"backgroundColor": {"red": 0.9, "green": 0.95, "blue": 0.9}}
                })

        # Suggest filters for datasets with headers
        if patterns.get("has_headers") and analysis.get("row_count", 0) > 10:
            formatting["filters"] = True

        return formatting

    def optimize_performance(self, spreadsheet_id: str, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize a list of operations for better performance.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            operations: List of operations to optimize

        Returns:
            Optimized list of operations
        """
        # Group operations by type
        grouped_ops = {
            "formatting": [],
            "data_updates": [],
            "sheet_operations": []
        }

        for op in operations:
            if any(key in op for key in ["repeatCell", "updateCells", "addConditionalFormatRule"]):
                grouped_ops["formatting"].append(op)
            elif "updateCells" in op and "userEnteredValue" in str(op):
                grouped_ops["data_updates"].append(op)
            else:
                grouped_ops["sheet_operations"].append(op)

        # Optimize formatting operations (batch similar operations)
        optimized_formatting = self._optimize_formatting_operations(grouped_ops["formatting"])

        # Return operations in optimal order: sheet ops first, then data, then formatting
        return grouped_ops["sheet_operations"] + grouped_ops["data_updates"] + optimized_formatting

    def _optimize_formatting_operations(self, formatting_ops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize formatting operations by batching similar operations."""
        # Simple optimization: sort by operation type for better API performance
        # More advanced optimization could merge adjacent range operations
        return sorted(formatting_ops, key=lambda x: list(x.keys())[0])

    def create_auto_chart(self, spreadsheet_id: str, sheet_name: str,
                         data_range: str, chart_type: str = "COLUMN") -> Optional[Dict[str, Any]]:
        """
        Automatically create a chart based on data analysis.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the worksheet
            data_range: Range for chart data
            chart_type: Type of chart to create

        Returns:
            Chart creation request or None if not applicable
        """
        try:
            # Analyze the data range to determine if charting makes sense
            analysis = self.analyze_data_patterns(spreadsheet_id, sheet_name, data_range)

            if not analysis.get("patterns", {}).get("has_numeric_data"):
                logger.info("No numeric data found - skipping auto chart creation")
                return None

            # Create chart request
            chart_request = {
                "addChart": {
                    "chart": {
                        "spec": {
                            "title": f"Auto-generated {chart_type.title()} Chart",
                            "chartType": chart_type,
                            "sourceRange": {
                                "sources": [{
                                    "sheetId": self._get_sheet_id_by_name(spreadsheet_id, sheet_name),
                                    "startRowIndex": 0,
                                    "endRowIndex": analysis.get("row_count", 10),
                                    "startColumnIndex": 0,
                                    "endColumnIndex": analysis.get("column_count", 5)
                                }]
                            }
                        },
                        "position": {
                            "overlayPosition": {
                                "anchorCell": {"sheetId": self._get_sheet_id_by_name(spreadsheet_id, sheet_name),
                                             "rowIndex": 0, "columnIndex": analysis.get("column_count", 5) + 2},
                                "offsetXPixels": 100,
                                "offsetYPixels": 100
                            }
                        }
                    }
                }
            }

            return chart_request

        except Exception as e:
            logger.error(f"Error creating auto chart: {e}")
            return None

    def _get_sheet_id_by_name(self, spreadsheet_id: str, sheet_name: str) -> Optional[int]:
        """Get sheet ID by name (helper method)."""
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            return None
        except Exception:
            return None
