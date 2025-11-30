"""
Google Sheets API functionality.
"""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from ..utils.credentials import get_credentials_path, SHEETS_SCOPES
from ..utils.logging import setup_logger, get_default_log_path
from ..utils.config import config, initialize_config

# Initialize logger and config
logger = setup_logger('google.sheets', get_default_log_path('sheets'))
initialize_config()

def get_sheets_service():
    """
    Authenticate and build the Google Sheets service.
    
    Returns:
        googleapiclient.discovery.Resource: The Google Sheets service
    """
    try:
        credentials = service_account.Credentials.from_service_account_file(
            get_credentials_path(), scopes=SHEETS_SCOPES)
        
        service = build('sheets', 'v4', credentials=credentials)
        logger.debug("Successfully created Google Sheets service")
        return service
    except Exception as e:
        logger.error(f"Failed to create Google Sheets service: {e}")
        raise

def write_hello_world(spreadsheet_id):
    """
    Write 'Hello World' to cell A1 of the specified spreadsheet.
    
    Args:
        spreadsheet_id (str): The ID of the Google Spreadsheet
        
    Returns:
        dict: The API response
    """
    logger.info(f"Writing 'Hello World' to spreadsheet {spreadsheet_id}")
    
    try:
        service = get_sheets_service()
        
        # Define the range and values
        range_name = 'A1'
        values = [['Hello World']]
        
        # Create the value range object
        value_range_body = {
            'values': values
        }
        
        # Execute the API request
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=value_range_body
        ).execute()
        
        logger.info(f"Successfully wrote to spreadsheet {spreadsheet_id}")
        return result
    except Exception as e:
        logger.error(f"Error writing to spreadsheet {spreadsheet_id}: {e}")
        raise

def write_values(spreadsheet_id, range_name, values, value_input_option='RAW'):
    """
    Write values to a specified range in a Google Spreadsheet.
    
    Args:
        spreadsheet_id (str): The ID of the Google Spreadsheet
        range_name (str): The A1 notation of the range to write to
        values (list): The values to write
        value_input_option (str): How the input should be interpreted
        
    Returns:
        dict: The API response
    """
    logger.info(f"Writing values to range {range_name} in spreadsheet {spreadsheet_id}")
    
    try:
        service = get_sheets_service()
        
        # Create the value range object
        value_range_body = {
            'values': values
        }
        
        # Execute the API request
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=value_range_body
        ).execute()
        
        logger.info(f"Successfully wrote {result.get('updatedCells')} cells to spreadsheet {spreadsheet_id}")
        return result
    except Exception as e:
        logger.error(f"Error writing to spreadsheet {spreadsheet_id}: {e}")
        raise

def read_values(spreadsheet_id, range_name):
    """
    Read values from a specified range in a Google Spreadsheet.
    
    Args:
        spreadsheet_id (str): The ID of the Google Spreadsheet
        range_name (str): The A1 notation of the range to read from
        
    Returns:
        list: The values from the specified range
    """
    logger.info(f"Reading values from range {range_name} in spreadsheet {spreadsheet_id}")
    
    try:
        service = get_sheets_service()
        
        # Execute the API request
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        logger.info(f"Successfully read {len(values)} rows from spreadsheet {spreadsheet_id}")
        return values
    except Exception as e:
        logger.error(f"Error reading from spreadsheet {spreadsheet_id}: {e}")
        raise
