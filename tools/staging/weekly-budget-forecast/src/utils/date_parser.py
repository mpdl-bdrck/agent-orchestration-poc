"""
Date parsing utilities for handling various date formats.
"""
from datetime import datetime
from typing import Optional


def parse_date(date_str: Optional[str]) -> Optional[datetime.date]:
    """
    Parse a date string that may be in various formats:
    - YYYY-MM-DD
    - YYYY-MM-DDTHH:MM:SS (ISO datetime)
    - YYYY-MM-DDTHH:MM:SS.ssssss (ISO datetime with microseconds)
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        datetime.date object or None if parsing fails
    """
    if not date_str:
        return None
    
    # Remove timestamp if present (e.g., "2024-12-16T00:00:00" -> "2024-12-16")
    if 'T' in date_str:
        date_str = date_str.split('T')[0]
    
    # Try parsing as date-only format
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None

