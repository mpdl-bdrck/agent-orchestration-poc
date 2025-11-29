"""
Centralized configuration management for the weekly budget forecast tool.
"""
import os
import json
import logging
from pathlib import Path

# Default configuration values
DEFAULT_CONFIG = {
    'google_sheets': {
        'worksheets': {
            'forecast': 'Weekly Budget Forecast'
        }
    },
    'logging': {
        'level': 'INFO',
        'log_to_file': True,
        'log_dir': 'logs',
    }
}

class Config:
    """Configuration manager for the weekly budget forecast tool."""
    
    def __init__(self, config_file=None):
        """
        Initialize the configuration manager.
        
        Args:
            config_file (str, optional): Path to the configuration file
        """
        self.config = DEFAULT_CONFIG.copy()
        self.config_file = config_file
        
        if config_file:
            self.load_config(config_file)
    
    def load_config(self, config_file):
        """
        Load configuration from a file.
        
        Args:
            config_file (str): Path to the configuration file
        """
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                
                # Update the default config with user values
                self._update_nested_dict(self.config, user_config)
        except Exception as e:
            logging.warning(f"Failed to load config from {config_file}: {e}")
    
    def _update_nested_dict(self, d, u):
        """
        Update a nested dictionary with values from another dictionary.
        
        Args:
            d (dict): Dictionary to update
            u (dict): Dictionary with new values
        """
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._update_nested_dict(d[k], v)
            else:
                d[k] = v
    
    def get(self, section, key, default=None):
        """
        Get a configuration value.
        
        Args:
            section (str): Configuration section
            key (str): Configuration key
            default: Default value if the key is not found
            
        Returns:
            The configuration value or the default
        """
        try:
            return self.config[section][key]
        except KeyError:
            return default
    
    def save_config(self, config_file=None):
        """
        Save the current configuration to a file.
        
        Args:
            config_file (str, optional): Path to the configuration file
        """
        file_path = config_file or self.config_file
        
        if file_path:
            try:
                # Ensure the directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'w') as f:
                    json.dump(self.config, f, indent=4)
            except Exception as e:
                logging.error(f"Failed to save config to {file_path}: {e}")

# Create a singleton instance
config = Config()

def get_project_root():
    """
    Get the absolute path to the project root directory.
    
    Returns:
        str: Path to the project root
    """
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_config_path():
    """
    Get the path to the configuration file.
    
    Returns:
        str: Path to the configuration file
    """
    return os.path.join(get_project_root(), 'config.json')

def initialize_config():
    """
    Initialize the configuration system.
    
    Returns:
        Config: The configuration manager instance
    """
    config_path = get_config_path()
    global config
    config = Config(config_path)
    return config

def get_spreadsheet_id():
    """
    Get the spreadsheet ID from the main config file.
    
    Returns:
        str: Spreadsheet ID for the weekly budget forecast report
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        KeyError: If spreadsheet_id not found in config
    """
    config_path = get_config_path()
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            f"Please create config.json with spreadsheet_id"
        )
    
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    if 'spreadsheet_id' not in config_data:
        raise KeyError(
            f"spreadsheet_id not found in {config_path}. "
            f"Please add spreadsheet_id to config.json"
        )
    
    return config_data['spreadsheet_id']

