"""
Dashboard formatting for Google Sheets.

This module handles formatting for summary dashboards including
number formats, conditional formatting, and styling.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class DashboardFormatter:
    """
    Apply formatting to dashboard worksheets.
    """

    def __init__(self, service):
        """
        Initialize dashboard formatter.

        Args:
            service: Google Sheets API service instance
        """
        self.service = service

    def apply_pacing_formatting(self, spreadsheet_id: str, sheet_id: int, campaign_config: Dict[str, Any]) -> None:
        """Apply formatting to pacing dashboard."""
        try:
            requests = []

            # Format headers (Column A) - bold
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 22,
                        "startColumnIndex": 0,
                        "endColumnIndex": 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {"bold": True}
                        }
                    },
                    "fields": "userEnteredFormat.textFormat.bold"
                }
            })

            # Format section headers (rows 3, 11, 17)
            section_rows = [2, 10, 16]  # 0-indexed
            for row_idx in section_rows:
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row_idx,
                            "endRowIndex": row_idx + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 2
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 0.9, "green": 0.95, "blue": 1.0},
                                "textFormat": {"bold": True}
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)"
                    }
                })

            # Format numbers in column B
            number_formats = [
                {"startRow": 11, "endRow": 15, "pattern": "$#,##0"},    # Budget amounts (B12-B15)
                {"startRow": 17, "endRow": 20, "pattern": "$#,##0.00"}, # Daily rates (B18-B20)
                {"startRow": 21, "endRow": 22, "pattern": "0.0%"}       # Budget % Projection (B22)
            ]

            for fmt in number_formats:
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": fmt["startRow"],
                            "endRowIndex": fmt["endRow"],
                            "startColumnIndex": 1,
                            "endColumnIndex": 2
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {
                                    "type": "NUMBER",
                                    "pattern": fmt["pattern"]
                                }
                            }
                        },
                        "fields": "userEnteredFormat.numberFormat"
                    }
                })

            # Apply conditional formatting for pacing status
            requests.extend(self._create_pacing_conditional_formatting(sheet_id))

            # Execute formatting requests
            if requests:
                batch_size = 50
                for i in range(0, len(requests), batch_size):
                    batch = requests[i:i + batch_size]
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={"requests": batch}
                    ).execute()

        except Exception as e:
            logger.warning(f"Error applying pacing formatting: {e}")

    def _create_pacing_conditional_formatting(self, sheet_id: int) -> List[Dict[str, Any]]:
        """Create conditional formatting rules for pacing dashboard."""
        rules = []

        # Pacing status color coding (B21)
        rules.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 1, "endColumnIndex": 2}],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_CONTAINS",
                            "values": [{"userEnteredValue": "🟢 AHEAD"}]
                        },
                        "format": {
                            "backgroundColor": {"red": 0.8, "green": 1.0, "blue": 0.8},
                            "textFormat": {"bold": True}
                        }
                    }
                },
                "index": 0
            }
        })

        rules.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 1, "endColumnIndex": 2}],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_CONTAINS",
                            "values": [{"userEnteredValue": "🔴 BEHIND"}]
                        },
                        "format": {
                            "backgroundColor": {"red": 1.0, "green": 0.8, "blue": 0.8},
                            "textFormat": {"bold": True}
                        }
                    }
                },
                "index": 1
            }
        })

        rules.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 1, "endColumnIndex": 2}],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_CONTAINS",
                            "values": [{"userEnteredValue": "🟡 ON PACE"}]
                        },
                        "format": {
                            "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.8},
                            "textFormat": {"bold": True}
                        }
                    }
                },
                "index": 2
            }
        })

        return rules

