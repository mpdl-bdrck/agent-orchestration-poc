"""
Google Sheets API credentials and service management.

This module handles authentication and service creation for Google Sheets API operations.
"""

import os
import logging
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def get_sheets_service(credentials_file: Optional[str] = None, scopes: Optional[list] = None):
    """
    Create and return authenticated Google Sheets API service.

    Args:
        credentials_file: Path to service account credentials JSON file
        scopes: List of OAuth scopes (defaults to Sheets and Drive)

    Returns:
        Google Sheets API service instance
    """
    if scopes is None:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

    if credentials_file is None:
        # Try to find credentials file in common locations
        possible_paths = [
            "credentials/bdrck-gsheets-key.json",
            "../credentials/bdrck-gsheets-key.json",
            os.path.expanduser("~/credentials/bdrck-gsheets-key.json")
        ]

        for path in possible_paths:
            if os.path.exists(path):
                credentials_file = path
                break

        if credentials_file is None:
            raise FileNotFoundError("Google Sheets credentials file not found")

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=scopes
        )

        service = build('sheets', 'v4', credentials=credentials)
        logger.info("Successfully created Google Sheets service")
        return service

    except Exception as e:
        logger.error(f"Failed to create Google Sheets service: {e}")
        raise


def validate_credentials(service) -> bool:
    """
    Validate that the service credentials work by making a test call.

    Args:
        service: Google Sheets API service instance

    Returns:
        True if credentials are valid, False otherwise
    """
    try:
        # Make a minimal API call to test credentials
        service.spreadsheets().get(spreadsheetId="1").execute()
        return True
    except Exception as e:
        if "PERMISSION_DENIED" in str(e):
            logger.warning("Credentials file exists but lacks proper permissions")
        else:
            logger.error(f"Credentials validation failed: {e}")
        return False
