"""
Timezone Handler
================

Shared module for handling timezone conversion for date ranges.
Used by both billing and campaign-portfolio-pacing tools.
"""

from datetime import datetime
import pytz


class TimezoneHandler:
    """
    Handles timezone conversion for date ranges using client config.
    """
    
    def __init__(self, client_config=None):
        """
        Initialize with client config dictionary.
        
        Args:
            client_config (dict, optional): Client configuration dictionary
                Expected keys: 'timezone', 'timezone_full'
        """
        self.client_config = client_config or {}
        self.client_timezone = (
            self.client_config.get('timezone_full') or 
            self.client_config.get('timezone', 'UTC')
        )
    
    def _parse_timezone(self, tz_string):
        """
        Parse timezone string to pytz timezone object.
        
        Args:
            tz_string (str): Timezone string (e.g., "PST", "America/Los_Angeles")
            
        Returns:
            pytz.timezone: Timezone object
        """
        # Map common abbreviations to full timezone names
        tz_map = {
            'PST': 'America/Los_Angeles',
            'PDT': 'America/Los_Angeles',
            'EST': 'America/New_York',
            'EDT': 'America/New_York',
            'UTC': 'UTC',
        }
        
        # Try mapping first
        tz_name = tz_map.get(tz_string.upper(), tz_string)
        
        try:
            return pytz.timezone(tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            # Fallback to UTC if timezone is unknown
            return pytz.UTC
    
    def convert_date_range(self, start_date, end_date, from_tz=None, to_tz='UTC'):
        """
        Convert date boundaries from client timezone to UTC (or specified timezone).
        Important for counting impressions across day boundaries.
        
        Args:
            start_date (str): Start date string (YYYY-MM-DD)
            end_date (str): End date string (YYYY-MM-DD)
            from_tz (str, optional): Source timezone (defaults to client config timezone)
            to_tz (str): Target timezone (default: 'UTC')
        
        Returns:
            tuple: (adjusted_start_date, adjusted_end_date) in YYYY-MM-DD format
        """
        if from_tz is None:
            from_tz = self.client_timezone
        
        from_tz_obj = self._parse_timezone(from_tz)
        to_tz_obj = self._parse_timezone(to_tz)
        
        # Parse dates and create datetime objects at start/end of day in source timezone
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        start_dt = from_tz_obj.localize(start_dt.replace(hour=0, minute=0, second=0))
        
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        end_dt = from_tz_obj.localize(end_dt.replace(hour=23, minute=59, second=59))
        
        # Convert to target timezone
        start_dt_converted = start_dt.astimezone(to_tz_obj)
        end_dt_converted = end_dt.astimezone(to_tz_obj)
        
        # Extract date boundaries
        adjusted_start_date = start_dt_converted.strftime('%Y-%m-%d')
        adjusted_end_date = end_dt_converted.strftime('%Y-%m-%d')
        
        return adjusted_start_date, adjusted_end_date

