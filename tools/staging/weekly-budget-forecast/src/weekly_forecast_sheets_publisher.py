"""
Weekly Forecast Sheets Publisher
=================================

Publishes weekly budget forecast data to Google Sheets in a readable, presentation-ready format.
"""

import time
import pandas as pd
from datetime import datetime
from typing import Optional
from googleapiclient.errors import HttpError  # type: ignore
import os
import importlib.util

# Import local google.sheets module explicitly to avoid conflict with google-api-python-client
sheets_module_path = os.path.join(os.path.dirname(__file__), 'google', 'sheets.py')
spec = importlib.util.spec_from_file_location("google_sheets", sheets_module_path)
google_sheets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(google_sheets)

from utils.logging import setup_logger

# Alias the function
get_sheets_service = google_sheets.get_sheets_service


class WeeklyForecastSheetsPublisher:
    """
    Publishes weekly budget forecast to Google Sheets
    """
    
    def __init__(self, spreadsheet_id: str):
        """
        Initialize the publisher.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
        """
        self.spreadsheet_id = spreadsheet_id
        self.logger = setup_logger('weekly.forecast.sheets.publisher')
    
    def publish_weekly_forecast(
        self,
        forecast_data: pd.DataFrame,
        report_date: Optional[str] = None
    ) -> bool:
        """
        Creates/updates sheet with weekly budget forecast data.
        
        Args:
            forecast_data: DataFrame with columns: week_start_date, week_end_date, 
                          past_spend, budget_allocated, forecast_spend
            report_date: Report date string (YYYY-MM-DD), defaults to today
        
        Returns:
            bool: Success status
        """
        worksheet_name = 'Weekly Budget Forecast'
        
        if forecast_data.empty:
            self.logger.warning("Forecast data is empty, nothing to publish")
            return False
        
        try:
            # Format data for Google Sheets
            formatted_data = self._format_forecast_data(forecast_data, report_date)
            
            # Publish to worksheet
            success = self._publish_to_worksheet(
                self.spreadsheet_id,
                worksheet_name,
                formatted_data
            )
            
            if success:
                self.logger.info(f"Successfully published weekly budget forecast to '{worksheet_name}'")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to publish weekly budget forecast: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _format_forecast_data(
        self,
        forecast_data: pd.DataFrame,
        report_date: Optional[str] = None
    ) -> list:
        """
        Format forecast data for Google Sheets.
        
        Returns:
            List of lists representing rows for Google Sheets
        """
        if report_date is None:
            report_date = datetime.now().strftime('%Y-%m-%d')
        
        # Header rows
        data = [
            ['Weekly Budget Forecast - All Campaigns'],
            [f'Report Date: {report_date}'],
            [],  # Empty row
            ['Week Start Date', 'Week End Date', 'Past Spend', 'Budget Allocated', 'Forecast Spend']
        ]
        
        # Data rows
        for _, row in forecast_data.iterrows():
            week_start = row['week_start_date']
            week_end = row['week_end_date']
            past_spend = row.get('past_spend')
            budget_allocated = row.get('budget_allocated', 0)
            forecast_spend = row.get('forecast_spend')
            
            # Format dates
            if isinstance(week_start, pd.Timestamp):
                week_start_str = week_start.strftime('%Y-%m-%d')
            elif isinstance(week_start, datetime):
                week_start_str = week_start.strftime('%Y-%m-%d')
            else:
                week_start_str = str(week_start)
            
            if isinstance(week_end, pd.Timestamp):
                week_end_str = week_end.strftime('%Y-%m-%d')
            elif isinstance(week_end, datetime):
                week_end_str = week_end.strftime('%Y-%m-%d')
            else:
                week_end_str = str(week_end)
            
            # Format numbers as raw values (no currency formatting)
            past_spend_val = '' if pd.isna(past_spend) else round(float(past_spend), 2)
            budget_allocated_val = round(float(budget_allocated), 2) if budget_allocated else 0.0
            forecast_spend_val = '' if pd.isna(forecast_spend) else round(float(forecast_spend), 2)
            
            data.append([
                week_start_str,
                week_end_str,
                past_spend_val,
                budget_allocated_val,
                forecast_spend_val
            ])
        
        return data
    
    def _publish_to_worksheet(
        self,
        spreadsheet_id: str,
        worksheet_name: str,
        data: list,
        max_retries: int = 3
    ) -> bool:
        """Publish data to a specific worksheet, creating it if necessary."""
        for attempt in range(max_retries):
            try:
                service = get_sheets_service()
                
                # Get spreadsheet info
                spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
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
                
                # Clear worksheet
                service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range=range_name
                ).execute()
                
                # Update worksheet
                result = service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption='RAW',
                    body={'values': data}
                ).execute()
                
                updated_cells = result.get('updatedCells', 0)
                self.logger.info(f"Published {len(data)} rows ({updated_cells} cells) to worksheet '{worksheet_name}'")
                return True
                
            except (HttpError, Exception) as e:
                error_msg = str(e)
                if "Unable to find the server" in error_msg or "network" in error_msg.lower():
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        self.logger.warning(f"Network error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                self.logger.error(f"Failed to publish to worksheet '{worksheet_name}': {e}")
                return False
        
        return False

