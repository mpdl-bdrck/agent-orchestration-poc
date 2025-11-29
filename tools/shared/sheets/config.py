"""
Configuration management for Google Sheets utilities.

This module handles configuration loading, validation, and management
for Google Sheets operations including spreadsheet IDs, worksheet
configurations, and preset management.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SheetConfig:
    """
    Configuration manager for Google Sheets operations.
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to JSON configuration file
        """
        self.config = self._load_default_config()
        if config_file:
            self.load_config(config_file)

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration values."""
        return {
            "spreadsheet_id": os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", ""),
            "worksheets": {},
            "formatting_preset": "presets/formatting/default.json",
            "summary_config": "presets/summaries/advanced_dashboard.json",
            "credentials_file": "credentials/bdrck-gsheets-key.json"
        }

    def load_config(self, config_file: str) -> None:
        """
        Load configuration from JSON file.

        Args:
            config_file: Path to configuration file
        """
        try:
            config_path = Path(config_file)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                    logger.info(f"Loaded configuration from {config_file}")
            else:
                logger.warning(f"Configuration file not found: {config_file}")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise

    def get_spreadsheet_id(self) -> str:
        """Get the default spreadsheet ID."""
        return self.config.get("spreadsheet_id", "")

    def get_worksheet_config(self, worksheet_name: str) -> Dict[str, Any]:
        """Get configuration for a specific worksheet."""
        return self.config.get("worksheets", {}).get(worksheet_name, {})

    def get_formatting_preset_path(self) -> str:
        """Get path to formatting preset file."""
        return self.config.get("formatting_preset", "")

    def get_summary_config_path(self) -> str:
        """Get path to summary configuration file."""
        return self.config.get("summary_config", "")

    def get_summary_config_path(self) -> str:
        """Get path to summary configuration file."""
        return self.config.get("summary_config", "")

    def get_credentials_file(self) -> str:
        """Get path to credentials file."""
        return self.config.get("credentials_file", "")
