"""
Google Sheets utilities for intelligent data export and formatting.

This module provides tools for:
- Formula-based summary dashboards
- Automated formatting extraction and application
- Dynamic worksheet creation with cross-sheet intelligence
- Configuration-driven Google Sheets management
"""

from .config import SheetConfig

# Google API dependent functions are imported only when needed
# to avoid requiring Google libraries for basic imports

__all__ = [
    'SheetConfig'
]

def get_summary_manager(service=None):
    """
    Get a SummaryManager instance.

    This function imports Google-dependent classes only when called.
    """
    from .summary import SummaryManager
    return SummaryManager(service)

def get_sheets_service(*args, **kwargs):
    """
    Get authenticated Google Sheets service.

    This function imports Google libraries only when called.
    """
    from .credentials import get_sheets_service as _get_service
    return _get_service(*args, **kwargs)
