"""
Google Sheets API functionality for weekly budget forecast tool.
"""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from utils.credentials import get_credentials_path, SHEETS_SCOPES
from utils.logging import setup_logger, get_default_log_path

# Initialize logger
logger = setup_logger('google.sheets', get_default_log_path('sheets'))

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

