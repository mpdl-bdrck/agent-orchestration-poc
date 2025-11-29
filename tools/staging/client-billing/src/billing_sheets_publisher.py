"""
Billing Sheets Publisher
=========================

Publishes billing data to Google Sheets in the specific template format.
"""

import time
import pandas as pd
from datetime import datetime
from typing import Dict, Any
from googleapiclient.errors import HttpError  # type: ignore

from .google.sheets import get_sheets_service
from .utils.logging import setup_logger


class BillingSheetsPublisher:
    """
    Publishes billing data in the specific template format
    """
    
    def __init__(self):
        """Initialize the billing sheets publisher"""
        self.logger = setup_logger('billing.sheets.publisher')
    
    def publish_billing_sheet(
        self, 
        billing_data: pd.DataFrame, 
        client_config: Dict[str, Any], 
        start_date: str, 
        end_date: str
    ) -> bool:
        """
        Creates sheet with:
        - Header: Client, Start Date, End Date
        - Advertiser sections with campaign rows
        - Proper formatting
        
        Args:
            billing_data: DataFrame with billing rollup data
            client_config: Client config dict (includes spreadsheet_id, client_name, date_format)
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
        
        Returns:
            bool: Success status
        """
        spreadsheet_id = client_config.get('spreadsheet_id')
        client_name = client_config.get('client_name', 'Unknown Client')
        date_format = client_config.get('date_format', 'DD/MM/YYYY')
        worksheet_name = 'Invoice information'
        
        if not spreadsheet_id:
            self.logger.error("No spreadsheet_id found in client config")
            return False
        
        try:
            # Format dates according to client config
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            if date_format == 'DD/MM/YYYY':
                start_date_formatted = start_dt.strftime('%d/%m/%Y')
                end_date_formatted = end_dt.strftime('%d/%m/%Y')
            else:
                # Default to YYYY-MM-DD
                start_date_formatted = start_dt.strftime('%Y-%m-%d')
                end_date_formatted = end_dt.strftime('%Y-%m-%d')
            
            # Build sheet data in template format
            sheet_data = self._format_billing_data(
                billing_data, 
                client_name, 
                start_date_formatted, 
                end_date_formatted
            )
            
            # Publish to worksheet
            success = self._publish_to_worksheet(
                spreadsheet_id,
                worksheet_name,
                sheet_data
            )

            # Skip formatting - users will format manually in the spreadsheet
            # if success:
            #     self._apply_formatting(spreadsheet_id, worksheet_name, len(sheet_data))

            return success
            
        except Exception as e:
            self.logger.error(f"Failed to publish billing sheet: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _format_billing_data(
        self, 
        billing_data: pd.DataFrame, 
        client_name: str, 
        start_date: str, 
        end_date: str
    ) -> list:
        """
        Format billing data into template structure

        Template format:
        Client: [Client Name]
        Start Date: [DD/MM/YYYY]
        End Date: [DD/MM/YYYY]

        Advertiser | [Advertiser Name] |
        Campaign Name | Impressions | Spend
        [campaign data] | [count] | [$$$]
        ...
        """
        sheet_data = []
        
        # Header section
        sheet_data.append(['Client', client_name])
        sheet_data.append(['Start Date', start_date])
        sheet_data.append(['End Date', end_date])
        sheet_data.append([])  # Empty row
        
        if billing_data.empty:
            sheet_data.append(['No billing data available'])
            return sheet_data
        
        # Group by advertiser
        advertisers = billing_data['advertiser_name'].unique()
        
        for advertiser_name in sorted(advertisers):
            advertiser_data = billing_data[billing_data['advertiser_name'] == advertiser_name]
            
            # Check if we need to split by inventory type
            has_inventory_split = 'inventory_type' in advertiser_data.columns
            
            if has_inventory_split:
                # Split into Deals and Marketplace sections
                deals_data = advertiser_data[advertiser_data['inventory_type'] == 'Deals']
                marketplace_data = advertiser_data[advertiser_data['inventory_type'] == 'Marketplace']
                
                # Deals section
                if not deals_data.empty:
                    sheet_data.append(['Advertiser', f'{advertiser_name} - Deals', ''])
                    sheet_data.append(['Campaign Name', 'Impressions', 'Spend'])
                    for _, row in deals_data.iterrows():
                        sheet_data.append([
                            row['campaign_name'],
                            int(row['impressions']),
                            round(float(row['spend']), 2)
                        ])
                    sheet_data.append([])  # Empty row

                # Marketplace section
                if not marketplace_data.empty:
                    sheet_data.append(['Advertiser', f'{advertiser_name} - Marketplace', ''])
                    sheet_data.append(['Campaign Name', 'Impressions', 'Spend'])
                    for _, row in marketplace_data.iterrows():
                        sheet_data.append([
                            row['campaign_name'],
                            int(row['impressions']),
                            round(float(row['spend']), 2)
                        ])
                    sheet_data.append([])  # Empty row
            else:
                # Single section per advertiser (no inventory split)
                sheet_data.append(['Advertiser', f'{advertiser_name}', ''])
                sheet_data.append(['Campaign Name', 'Impressions', 'Spend'])
                for _, row in advertiser_data.iterrows():
                    sheet_data.append([
                        row['campaign_name'],
                        int(row['impressions']),
                        round(float(row['spend']), 2)
                    ])
                sheet_data.append([])  # Empty row
        
        return sheet_data
    
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
                
                # Clear entire worksheet to remove any existing formulas/formatting
                service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range=worksheet_name  # Clear entire worksheet, not just A1
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
    
    def _apply_formatting(
        self, 
        spreadsheet_id: str, 
        worksheet_name: str, 
        num_rows: int
    ):
        """
        Apply formatting to the billing sheet
        
        Args:
            spreadsheet_id: Spreadsheet ID
            worksheet_name: Worksheet name
            num_rows: Number of rows in the sheet
        """
        try:
            service = get_sheets_service()
            
            # Get sheet ID
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet_id = None
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == worksheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                self.logger.warning(f"Could not find sheet ID for '{worksheet_name}'")
                return
            
            requests = []
            
            # Format header row (row 1) - bold
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True}
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat.bold'
                }
            })
            
            # Conservative formatting - only format column headers, not data rows
            # Format specific rows that contain column headers ("Campaign Name", "Impressions", "Spend")
            # These typically appear at: row 6, row 10, row 14, etc. (after section headers)

            column_header_rows = [6, 10, 14, 18, 22, 26, 30]  # Common locations for column headers
            for row_idx in column_header_rows:
                if row_idx < num_rows:
                    requests.append({
                        'repeatCell': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': row_idx,
                                'endRowIndex': row_idx + 1,
                                'startColumnIndex': 0,
                                'endColumnIndex': 3  # Format all 3 columns (Campaign Name, Impressions, Spend)
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'textFormat': {'bold': True}
                                }
                            },
                            'fields': 'userEnteredFormat.textFormat.bold'
                        }
                    })
            
            # Format spend column (column C) as currency
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': num_rows,
                        'startColumnIndex': 2,
                        'endColumnIndex': 3
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'numberFormat': {
                                'type': 'CURRENCY',
                                'pattern': '$#,##0.00'
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.numberFormat'
                }
            })
            
            # Format impressions column (column B) as number with thousand separators
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': num_rows,
                        'startColumnIndex': 1,
                        'endColumnIndex': 2
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'numberFormat': {
                                'type': 'NUMBER',
                                'pattern': '#,##0'
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.numberFormat'
                }
            })
            
            if requests:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': requests}
                ).execute()
                self.logger.info(f"Applied formatting to worksheet '{worksheet_name}'")
                
        except Exception as e:
            self.logger.warning(f"Failed to apply formatting: {e}")
            # Don't fail the whole operation if formatting fails

