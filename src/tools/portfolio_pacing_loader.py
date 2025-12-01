"""
Portfolio Pacing Analyzer Loader
=================================

Handles lazy loading and path setup for CampaignSpendAnalyzer.
"""
import os
import sys
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Global state
CampaignSpendAnalyzer = None
REAL_DATA_AVAILABLE = False


def load_client_config(account_id: str) -> Optional[Dict[str, Any]]:
    """
    Load client configuration for the given account ID.
    
    Args:
        account_id: Account ID (e.g., "17" for Tricoast Media LLC)
        
    Returns:
        Client config dict or None if loading fails
    """
    client_config = None
    try:
        # Import load_client_config from the tool's utils
        original_cwd = os.getcwd()
        original_path = sys.path[:]
        try:
            # Get tool_dir
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            tool_dir = os.path.join(project_root, "tools", "campaign-portfolio-pacing")
            
            os.chdir(tool_dir)
            if tool_dir not in sys.path:
                sys.path.insert(0, tool_dir)
            
            from src.utils.config import load_client_config as _load_client_config
            
            # For account_id=17, load Tricoast Media LLC config
            if account_id == "17":
                client_name = "Tricoast Media LLC"
                try:
                    client_config = _load_client_config(client_name)
                    logger.info(f"✅ Loaded client config for {client_name}: timezone={client_config.get('timezone')} ({client_config.get('timezone_full', '')})")
                except FileNotFoundError:
                    logger.warning(f"Client config not found for {client_name}, using PST timezone")
                except Exception as e:
                    logger.warning(f"Could not load client config: {e}, using PST timezone")
        finally:
            os.chdir(original_cwd)
            sys.path[:] = original_path
    except Exception as e:
        logger.warning(f"Could not import load_client_config: {e}, using PST timezone")
    
    # Ensure client_config is set to PST defaults when import fails
    if client_config is None:
        client_config = {'timezone': 'PST', 'timezone_full': 'America/Los_Angeles'}
        logger.info(f"✅ Using default PST timezone: {client_config}")
    
    return client_config


def ensure_analyzer_loaded() -> bool:
    """
    Ensure CampaignSpendAnalyzer is loaded and available.
    
    Returns:
        True if analyzer is available, False otherwise
    """
    global CampaignSpendAnalyzer, REAL_DATA_AVAILABLE
    
    if REAL_DATA_AVAILABLE and CampaignSpendAnalyzer:
        return True
    
    try:
        # Set up paths to tools/campaign-portfolio-pacing
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        tool_dir = os.path.join(project_root, "tools", "campaign-portfolio-pacing")
        tool_src = os.path.join(tool_dir, "src")
        
        if not os.path.exists(tool_src) or not os.path.exists(os.path.join(tool_src, "campaign_analyzer.py")):
            raise ImportError(f"tools/campaign-portfolio-pacing not found at {tool_src}")
        
        # Set up paths for dependencies
        shared_path = os.path.join(project_root, "tools", "shared")
        campaign_analysis_src = os.path.join(project_root, "tools", "staging", "campaign-analysis", "src")
        
        # Add paths for dependencies first
        if os.path.exists(shared_path) and shared_path not in sys.path:
            sys.path.insert(0, shared_path)
        if os.path.exists(campaign_analysis_src) and campaign_analysis_src not in sys.path:
            sys.path.insert(0, campaign_analysis_src)
        
        # Add tool_dir to path FIRST so src package can be found
        if os.path.exists(tool_dir) and tool_dir not in sys.path:
            sys.path.insert(0, tool_dir)
        
        # Change to tool directory so relative imports work properly
        original_cwd = os.getcwd()
        original_path = list(sys.path)
        try:
            if tool_dir not in sys.path:
                sys.path.insert(0, tool_dir)
            
            os.chdir(tool_dir)
            
            # Clear ALL cached src.* modules to force fresh import
            import importlib
            modules_to_clear = [k for k in list(sys.modules.keys()) if k.startswith('src.')]
            for mod_name in modules_to_clear:
                del sys.modules[mod_name]
            
            if 'src' in sys.modules:
                del sys.modules['src']
            
            # Initialize package structure (optional imports)
            try:
                import src
                if not hasattr(src, '__path__'):
                    raise ImportError("src is not a package")
            except ImportError:
                logger.debug("⚠️  src package not available, continuing anyway")
            
            try:
                import src.utils
                if not hasattr(src.utils, '__path__'):
                    raise ImportError("src.utils is not a package")
            except ImportError:
                logger.debug("⚠️  src.utils not available, continuing anyway")
            
            # Patch logging if available
            try:
                import src.utils.logging as logging_module
                original_setup_logger_func = logging_module.setup_logger
                
                def suppressed_setup_logger(name, log_file=None, level=logging.INFO):
                    """Suppressed version that doesn't add console handlers"""
                    logger_obj = logging.getLogger(name)
                    logger_obj.setLevel(logging.CRITICAL)
                    if log_file:
                        import os
                        os.makedirs(os.path.dirname(log_file), exist_ok=True)
                        file_handler = logging.FileHandler(log_file)
                        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                        file_handler.setFormatter(formatter)
                        logger_obj.addHandler(file_handler)
                    return logger_obj
                
                logging_module.setup_logger = suppressed_setup_logger
                logger.debug("✅ Monkey-patched setup_logger to suppress console handlers")
            except ImportError:
                logger.debug("⚠️  src.utils.logging not available, skipping monkey-patch")
            
            # Import CampaignSpendAnalyzer
            from src.campaign_analyzer import CampaignSpendAnalyzer
            REAL_DATA_AVAILABLE = True
            logger.info("✅ CampaignSpendAnalyzer loaded successfully (lazy load)")
            return True
            
        finally:
            os.chdir(original_cwd)
            if tool_dir not in sys.path:
                sys.path.insert(0, tool_dir)
                
    except Exception as e:
        error_msg = f"CampaignSpendAnalyzer not available: {e}"
        logger.error(error_msg)
        return False
    
    return False


def get_analyzer():
    """Get the loaded CampaignSpendAnalyzer class."""
    global CampaignSpendAnalyzer
    if not ensure_analyzer_loaded():
        raise Exception("CampaignSpendAnalyzer not available. Database connection required.")
    return CampaignSpendAnalyzer

