"""
Google Sheets Publisher
========================

Handles publishing campaign data and rollups to Google Sheets.
"""

import time
import pandas as pd  # type: ignore
from typing import Dict, Any, Optional
from googleapiclient.errors import HttpError  # type: ignore

from .google.sheets import get_sheets_service
from .utils.config import initialize_config, config
from .utils.logging import setup_logger
from .daily_rates_trend import DailyRatesTrendCalculator


class GoogleSheetsPublisher:
    """Handles publishing campaign data to Google Sheets."""

    def __init__(self):
        """Initialize the Google Sheets publisher."""
        self.logger = setup_logger('campaign.sheets.publisher')
        initialize_config()
        self._sheet_existed_before_creation = False

    def publish_all_rollups(self, rollups, advertiser_name, account_id, rollup_csv_paths=None):
        """
        Publish all 6 rollup views to separate worksheets in Google Sheets.

        Args:
            rollups: Dictionary with all 6 rollup datasets (DataFrames)
            advertiser_name: Name of the advertiser
            account_id: Account ID
            rollup_csv_paths: Optional dict mapping rollup keys to CSV paths

        Returns:
            bool: Success status
        """
        try:
            spreadsheet_id = config.get('google_sheets', 'default_spreadsheet_id')
            worksheets_config = config.get('google_sheets', 'worksheets', {})

            if not spreadsheet_id:
                self.logger.error("No spreadsheet ID configured")
                return False

            self.logger.info(f"Publishing 6 rollup views to spreadsheet {spreadsheet_id}")
            if rollup_csv_paths:
                self.logger.info(f"Using CSV snapshots from {len(rollup_csv_paths)} rollups as ground truth")

            rollup_order = ['line_items_daily', 'line_items_total', 'campaigns_daily', 'campaigns_total', 'portfolio_daily', 'portfolio_total']

            for rollup_key in rollup_order:
                if rollup_key not in rollups:
                    self.logger.warning(f"Rollup '{rollup_key}' not found in data, skipping")
                    continue

                df = rollups[rollup_key]
                worksheet_name = worksheets_config.get(rollup_key, rollup_key)

                if not isinstance(df, pd.DataFrame) or df.empty:
                    self.logger.warning(f"Rollup {rollup_key} is empty or invalid, skipping")
                    continue

                csv_source = (rollup_csv_paths or {}).get(rollup_key) if rollup_csv_paths else None
                if csv_source:
                    self.logger.info(f"Publishing {rollup_key} ({len(df)} records) to worksheet '{worksheet_name}' from CSV {csv_source}")
                else:
                    self.logger.info(f"Publishing {rollup_key} ({len(df)} records) to worksheet '{worksheet_name}'")

                formatted_data = self._format_rollup_dataframe(rollup_key, df)
                if not formatted_data:
                    self.logger.warning(f"No formatted data for {rollup_key}, skipping")
                    continue

                success = self._publish_to_worksheet(spreadsheet_id, worksheet_name, formatted_data)
                if not success:
                    self.logger.error(f"Failed to publish {rollup_key} to worksheet {worksheet_name}")
                    return False

            self.logger.info("Successfully published all 6 rollup views to Google Sheets")
            return True

        except Exception as e:
            self.logger.error(f"Failed to publish comprehensive rollups: {e}")
            return False

    def _format_rollup_dataframe(self, rollup_key, df):
        """Convert DataFrame to raw values for Google Sheets (preserve data types, identical to CSV)."""
        if df.empty:
            return []

        column_configs = {
            'line_items_daily': ['date', 'campaign_id', 'campaign_name', 'line_item_id', 'line_item_name', 'impressions', 'spend', 'prev_day_spend_ratio'],
            'line_items_total': ['campaign_id', 'campaign_name', 'line_item_id', 'line_item_name', 'total_spend', 'spend_percentage', 'total_impressions'],
            'campaigns_daily': ['date', 'campaign_id', 'campaign_name', 'impressions', 'spend', 'prev_day_spend_ratio'],
            'campaigns_total': ['campaign_id', 'campaign_name', 'campaign_budget', 'total_spend', 'spend_percentage', 'total_impressions'],
            'portfolio_daily': ['date', 'total_campaigns', 'impressions', 'spend', 'prev_day_spend_ratio'],
            'portfolio_total': ['total_budget', 'total_spend', 'spend_percentage', 'avg_daily_spend', 'total_impressions', 'avg_daily_impressions', 'date_range']
        }

        columns = column_configs.get(rollup_key)
        if not columns:
            self.logger.error(f"No column config for rollup_key: {rollup_key}")
            return []

        # Select only available columns
        available_cols = [col for col in columns if col in df.columns]
        df_selected = df[available_cols].copy()

        # Round float columns to match CSV export
        float_cols = ['spend', 'total_spend', 'spend_percentage', 'prev_day_spend_ratio', 'avg_daily_spend', 'campaign_budget', 'total_budget']
        for col in float_cols:
            if col in df_selected.columns:
                # Use 4 decimal places for spend_percentage, 2 for others
                decimal_places = 4 if col == 'spend_percentage' else 2
                df_selected[col] = df_selected[col].round(decimal_places)

        # Define column types - preserve numeric types for Google Sheets
        numeric_cols = [
            'campaign_id', 'line_item_id', 'spend', 'total_spend', 'spend_percentage', 'prev_day_spend_ratio',
            'impressions', 'total_impressions', 'total_campaigns', 'avg_daily_spend', 'avg_daily_impressions',
            'campaign_budget', 'total_budget'
        ]

        # Build result preserving data types (no unnecessary string conversion)
        result = [df_selected.columns.tolist()]
        for row in df_selected.itertuples(index=False):
            processed_row = []
            for i, val in enumerate(row):
                col_name = df_selected.columns[i]
                if pd.isna(val) or val is None:
                    # Empty string for NaN/None values (first day, division by zero, etc.)
                    processed_row.append('')
                elif col_name in numeric_cols:
                    # Keep as numeric type (int/float) - no string conversion
                    processed_row.append(val)
                else:
                    # Only string columns get converted to strings
                    processed_row.append(str(val))
            result.append(processed_row)

        return result


    def _publish_to_worksheet(self, spreadsheet_id, worksheet_name, data, max_retries=3):
        """Publish data to a specific worksheet, creating it if necessary."""
        for attempt in range(max_retries):
            try:
                service = get_sheets_service()

                # Get spreadsheet info with retry
                spreadsheet = None
                for get_attempt in range(max_retries):
                    try:
                        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                        break
                    except (HttpError, Exception) as e:
                        if "Unable to find the server" in str(e) or "network" in str(e).lower():
                            if get_attempt < max_retries - 1:
                                wait_time = 2 ** get_attempt
                                self.logger.warning(f"Network error getting spreadsheet (attempt {get_attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                                time.sleep(wait_time)
                                continue
                        raise

                sheets = spreadsheet.get('sheets', [])
                sheet_names = [sheet['properties']['title'] for sheet in sheets]

                if worksheet_name not in sheet_names:
                    requests = [{
                        'addSheet': {
                            'properties': {'title': worksheet_name}
                        }
                    }]
                    service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={'requests': requests}
                    ).execute()
                    self.logger.info(f"Created new worksheet: {worksheet_name}")

                range_name = f'{worksheet_name}!A1'
                
                # Clear worksheet with retry
                for clear_attempt in range(max_retries):
                    try:
                        service.spreadsheets().values().clear(
                            spreadsheetId=spreadsheet_id,
                            range=range_name
                        ).execute()
                        break
                    except (HttpError, Exception) as e:
                        if "Unable to find the server" in str(e) or "network" in str(e).lower():
                            if clear_attempt < max_retries - 1:
                                wait_time = 2 ** clear_attempt
                                self.logger.warning(f"Network error clearing worksheet (attempt {clear_attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                                time.sleep(wait_time)
                                continue
                        raise

                # Update worksheet with retry
                result = None
                for update_attempt in range(max_retries):
                    try:
                        result = service.spreadsheets().values().update(
                            spreadsheetId=spreadsheet_id,
                            range=range_name,
                            valueInputOption='RAW',
                            body={'values': data}
                        ).execute()
                        break
                    except (HttpError, Exception) as e:
                        if "Unable to find the server" in str(e) or "network" in str(e).lower():
                            if update_attempt < max_retries - 1:
                                wait_time = 2 ** update_attempt
                                self.logger.warning(f"Network error updating worksheet (attempt {update_attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                                time.sleep(wait_time)
                                continue
                        raise

                updated_cells = result.get('updatedCells', 0)
                self.logger.info(f"Published {len(data)-1} records ({updated_cells} cells) to worksheet '{worksheet_name}'")
                return True

            except (HttpError, Exception) as e:
                error_msg = str(e)
                if "Unable to find the server" in error_msg or "network" in error_msg.lower():
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        self.logger.warning(f"Network error publishing to '{worksheet_name}' (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"Failed to publish to worksheet '{worksheet_name}' after {max_retries} attempts: Network connectivity issue - {error_msg}")
                        self.logger.error("Please check your internet connection and firewall settings")
                        return False
                else:
                    self.logger.error(f"Failed to publish to worksheet '{worksheet_name}': {e}")
                    return False
        
        return False

    def publish_daily_rates_trend_sheet(self, spreadsheet_id: str, campaign_config: Dict[str, Any] = None) -> bool:
        """
        Create and populate Daily Rates Trend sheet.

        Uses DailyRatesTrendCalculator to generate data for each day of the campaign.
        Reads campaign config from Summary tab if not provided.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            campaign_config: Optional campaign configuration (reads from Summary if not provided)

        Returns:
            bool: Success status
        """
        try:
            # Ensure service is available
            if not hasattr(self, 'service') or self.service is None:
                self.service = get_sheets_service()

            trend_sheet_name = "Daily Rates Trend"

            # Use calculator to generate trend data
            calculator = DailyRatesTrendCalculator(self.service)
            data = calculator.generate_trend_data(spreadsheet_id, campaign_config)

            if not data:
                self.logger.error("Failed to generate daily rates trend data")
                return False

            # Publish to worksheet
            result = self._publish_to_worksheet(spreadsheet_id, trend_sheet_name, data)
            self.logger.info(f"Published Daily Rates Trend with {len(data)} rows")

            return result

        except Exception as e:
            self.logger.error(f"Failed to publish daily rates trend: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def _sheet_exists(self, spreadsheet_id: str, sheet_name: str) -> bool:
        """Check if a sheet exists in the spreadsheet."""
        try:
            service = get_sheets_service()
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet_names = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
            return sheet_name in sheet_names
        except Exception as e:
            self.logger.error(f"Error checking if sheet exists: {e}")
            return False

    def _create_sheet(self, spreadsheet_id: str, sheet_name: str) -> bool:
        """Create a new sheet in the spreadsheet."""
        try:
            service = get_sheets_service()
            request = {
                "addSheet": {
                    "properties": {
                        "title": sheet_name
                    }
                }
            }
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": [request]}
            ).execute()
            return True
        except Exception as e:
            self.logger.error(f"Error creating sheet {sheet_name}: {e}")
            return False

    def _get_sheet_id_by_name(self, spreadsheet_id: str, sheet_name: str) -> Optional[int]:
        """Get sheet ID by name."""
        try:
            service = get_sheets_service()
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            return None
        except Exception as e:
            self.logger.error(f"Error getting sheet ID for {sheet_name}: {e}")
            return None



def publish_daily_rates_trend(spreadsheet_id: str, campaign_config: Dict[str, Any]) -> bool:
    """Create and populate Daily Rates Trend sheet with pacing data."""
    publisher = GoogleSheetsPublisher()
    return publisher.publish_daily_rates_trend_sheet(spreadsheet_id, campaign_config)


def publish_comprehensive_rollups(rollups, advertiser_name, account_id, rollup_csv_paths=None):
    """Publish all comprehensive rollup views to multiple Google Sheets worksheets."""
    publisher = GoogleSheetsPublisher()
    return publisher.publish_all_rollups(rollups, advertiser_name, account_id, rollup_csv_paths)

