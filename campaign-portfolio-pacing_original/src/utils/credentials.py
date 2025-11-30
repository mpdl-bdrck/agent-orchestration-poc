"""
Shared credential handling for Google and YouTube services.
"""
import os

# Path to the credentials file
CREDENTIALS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'credentials', 'bdrck-gsheets-key.json'
)

# Scopes for different APIs
SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_credentials_path():
    """
    Returns the path to the credentials file.
    
    Returns:
        str: Path to the credentials file
    """
    return CREDENTIALS_FILE
