"""
Shared credential handling for Google and YouTube services.
"""
import os

# Path to the credentials file
# Go up from utils/ -> src/ -> weekly-budget-forecast/ -> tools/ -> project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script_dir))))
project_credentials = os.path.join(project_root, 'credentials', 'bdrck-gsheets-key.json')

# Fallback: try campaign-portfolio-pacing credentials if not found at project root
if os.path.exists(project_credentials):
    CREDENTIALS_FILE = project_credentials
else:
    # Use credentials from campaign-portfolio-pacing as fallback
    tools_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    fallback_path = os.path.join(tools_dir, 'campaign-portfolio-pacing', 'credentials', 'bdrck-gsheets-key.json')
    if os.path.exists(fallback_path):
        CREDENTIALS_FILE = fallback_path
    else:
        # Last resort: use project root path anyway (will fail with clear error)
        CREDENTIALS_FILE = project_credentials

# Scopes for different APIs
SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_credentials_path():
    """
    Returns the path to the credentials file.
    
    Returns:
        str: Path to the credentials file
    """
    return CREDENTIALS_FILE

