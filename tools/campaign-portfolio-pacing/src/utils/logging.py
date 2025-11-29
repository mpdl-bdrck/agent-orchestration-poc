"""
Centralized logging configuration for the application.
"""
import logging
import os
import sys
from datetime import datetime

def setup_logger(name, log_file=None, level=logging.INFO):
    """
    Set up a logger with console and optional file handlers.
    
    Args:
        name (str): Logger name
        log_file (str, optional): Path to log file
        level (int): Logging level
        
    Returns:
        logging.Logger: Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log_file is specified
    if log_file:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_default_log_path(module_name):
    """
    Get the default log file path for a module.
    
    Args:
        module_name (str): Name of the module
        
    Returns:
        str: Path to the log file
    """
    # Base directory is the project root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(base_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create a log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    return os.path.join(logs_dir, f"{module_name}_{timestamp}.log")
