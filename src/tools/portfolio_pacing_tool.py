"""
Portfolio Pacing Tool
====================

Analyzes portfolio pacing and health using CampaignSpendAnalyzer from tools/campaign-portfolio-pacing.

How it works:
1. Discovers campaigns: Queries PostgreSQL to find campaigns for the account/advertiser
2. Collects daily data: Queries Redshift to get daily spend/impression data for those campaigns
3. Performs pandas rollups: Creates 6 rollup views using pandas:
   - line_items_daily: Daily spend/impressions per line item
   - line_items_total: Total spend/impressions per line item
   - campaigns_daily: Daily spend/impressions per campaign
   - campaigns_total: Total spend/impressions per campaign
   - portfolio_daily: Daily spend/impressions at portfolio level
   - portfolio_total: Total spend/impressions at portfolio level

Requires AWS SSO authentication and database connection.
"""
import os
import sys
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pytz
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Import CampaignSpendAnalyzer from tools/campaign-portfolio-pacing
# LAZY LOAD ONLY - don't import at module level to avoid import cache corruption
# This prevents Python's import system from getting corrupted when the import fails
CampaignSpendAnalyzer = None
REAL_DATA_AVAILABLE = False


def _safe_str(val) -> str:
    """Safely convert any input to string, handling simple lists."""
    if val is None:
        return ""
    if isinstance(val, list) and len(val) > 0:
        return str(val[0]).strip()
    return str(val).strip()


def _calculate_rolling_30day_window(client_config: Dict[str, Any] = None) -> tuple[str, str]:
    """
    Calculate rolling 30-day window dates in PST timezone.
    
    Returns:
        (start_date, end_date) as YYYY-MM-DD strings
        Window is inclusive: today - 29 days to today = 30 days total
    """
    # Get timezone from client config (default to PST for Tricoast)
    if client_config:
        tz_str = client_config.get('timezone_full') or client_config.get('timezone', 'America/Los_Angeles')
        tz_map = {
            'PST': 'America/Los_Angeles',
            'PDT': 'America/Los_Angeles',
            'EST': 'America/New_York',
            'EDT': 'America/New_York',
        }
        tz_str = tz_map.get(tz_str.upper(), tz_str)
    else:
        tz_str = 'America/Los_Angeles'
    
    pst_tz = pytz.timezone(tz_str)
    today_pst = datetime.now(pst_tz).date()
    start_date_pst = today_pst - timedelta(days=29)  # 30 days inclusive (today + 29 days back)
    
    return start_date_pst.strftime('%Y-%m-%d'), today_pst.strftime('%Y-%m-%d')


def _calculate_pacing_analysis(
    portfolio_daily: pd.DataFrame,
    campaign_start: str,
    campaign_end: str,
    campaign_budget: float,
    client_config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Calculate pacing analysis accounting for PST timezone and partial days.
    
    Args:
        portfolio_daily: DataFrame with 'date' and 'spend' columns
        campaign_start: Campaign start date (YYYY-MM-DD)
        campaign_end: Campaign end date (YYYY-MM-DD)
        campaign_budget: Total campaign budget
        client_config: Client configuration dict with timezone info
    
    Returns:
        Dict with pacing metrics
    """
    try:
        # Get timezone from client config (default to PST for Tricoast)
        if client_config:
            tz_display = client_config.get('timezone', 'PST')  # For display (PST/PDT/etc)
            tz_str = client_config.get('timezone_full') or client_config.get('timezone', 'America/Los_Angeles')
            tz_map = {
                'PST': 'America/Los_Angeles',
                'PDT': 'America/Los_Angeles',
                'EST': 'America/New_York',
                'EDT': 'America/New_York',
            }
            tz_str = tz_map.get(tz_str.upper(), tz_str)
        else:
            tz_display = 'PST'
            tz_str = 'America/Los_Angeles'
        
        pst_tz = pytz.timezone(tz_str)
        now_pst = datetime.now(pst_tz)
        today_pst = now_pst.date()
        
        # Parse campaign dates
        start_date = datetime.strptime(campaign_start, '%Y-%m-%d').date()
        end_date = datetime.strptime(campaign_end, '%Y-%m-%d').date()
        total_days = (end_date - start_date).days + 1
        
        # Ensure portfolio_daily has date column as date type
        portfolio_daily = portfolio_daily.copy()
        if 'date' in portfolio_daily.columns:
            portfolio_daily['date'] = pd.to_datetime(portfolio_daily['date']).dt.date
        
        # Filter to campaign date range
        filtered = portfolio_daily[
            (portfolio_daily['date'] >= start_date) & 
            (portfolio_daily['date'] <= end_date)
        ].copy()
        
        if len(filtered) == 0:
            return {
                'error': 'No data found in campaign date range'
            }
        
        # Calculate total spend
        total_spend = float(filtered['spend'].sum())
        
        # Get last data date
        last_data_date = filtered['date'].max()
        
        # Determine if last day is partial
        is_partial_day = False
        partial_day_fraction = 0.0
        
        if last_data_date == today_pst:
            # Last day is today - calculate partial day fraction
            hours_elapsed = now_pst.hour + (now_pst.minute / 60.0) + (now_pst.second / 3600.0)
            partial_day_fraction = max(0.0, min(1.0, hours_elapsed / 24.0))  # Clamp between 0 and 1
            is_partial_day = True
            days_passed = (last_data_date - start_date).days + partial_day_fraction
        else:
            # Last day is complete
            days_passed = (last_data_date - start_date).days + 1
        
        # Calculate pacing metrics
        expected_daily_rate = campaign_budget / total_days
        expected_spend = expected_daily_rate * days_passed
        actual_daily_rate = total_spend / days_passed if days_passed > 0 else 0
        projected_final_spend = actual_daily_rate * total_days
        remaining_budget = campaign_budget - total_spend
        budget_utilization_pct = (total_spend / campaign_budget) * 100 if campaign_budget > 0 else 0
        days_remaining = total_days - days_passed
        required_daily_rate = remaining_budget / days_remaining if days_remaining > 0 else 0
        
        # Calculate variance
        spend_variance = total_spend - expected_spend
        variance_pct = ((total_spend - expected_spend) / expected_spend) * 100 if expected_spend > 0 else 0
        
        # Determine pacing status
        if abs(variance_pct) < 2:
            status = "ON PACE"
            emoji = "🟡"
        elif variance_pct > 0:
            status = "AHEAD"
            emoji = "🟢"
        else:
            if abs(variance_pct) < 5:
                status = "SLIGHTLY BEHIND"
            else:
                status = "BEHIND"
            emoji = "🔴"
        
        return {
            'total_spend': total_spend,
            'budget': campaign_budget,
            'remaining_budget': remaining_budget,
            'budget_utilization_pct': budget_utilization_pct,
            'days_passed': days_passed,
            'full_days': int(days_passed),
            'partial_day_fraction': partial_day_fraction,
            'total_days': total_days,
            'days_remaining': days_remaining,
            'expected_daily_rate': expected_daily_rate,
            'expected_spend': expected_spend,
            'actual_daily_rate': actual_daily_rate,
            'projected_final_spend': projected_final_spend,
            'required_daily_rate': required_daily_rate,
            'spend_variance': spend_variance,
            'variance_pct': variance_pct,
            'pacing_status': status,
            'pacing_emoji': emoji,
            'last_data_date': last_data_date,
            'is_partial_day': is_partial_day,
            'start_date': start_date,
            'end_date': end_date,
            'timezone': tz_str,
            'timezone_display': tz_display
        }
        
    except Exception as e:
        logger.error(f"Error calculating pacing analysis: {e}", exc_info=True)
        return {'error': str(e)}


def _format_portfolio_results(
    result_data: dict,
    campaign_start: str,
    campaign_end: str,
    campaign_budget: float,
    client_config: Dict[str, Any] = None
) -> str:
    """
    Format analysis results with comprehensive pacing analysis for rolling 30-day window.
    """
    try:
        rollups = result_data.get('rollups', {})
        
        # Get portfolio_daily rollup
        portfolio_daily = rollups.get('portfolio_daily')
        
        if portfolio_daily is None or len(portfolio_daily) == 0:
            return "❌ No portfolio daily data available"
        
        # Calculate pacing analysis
        pacing = _calculate_pacing_analysis(
            portfolio_daily=portfolio_daily,
            campaign_start=campaign_start,
            campaign_end=campaign_end,
            campaign_budget=campaign_budget,
            client_config=client_config
        )
        
        if pacing.get('error'):
            return f"❌ Error calculating pacing: {pacing['error']}"
        
        # Build comprehensive pacing report
        lines = []
        
        # Header - detect if this is a rolling 30-day window
        start_date_obj = datetime.strptime(campaign_start, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(campaign_end, '%Y-%m-%d').date()
        days_in_range = (end_date_obj - start_date_obj).days + 1
        
        if days_in_range == 30:
            header_text = "📊 30-DAY ROLLING WINDOW PORTFOLIO PACING ANALYSIS"
        else:
            # Fallback for custom date ranges
            month_name = datetime.strptime(campaign_start, '%Y-%m-%d').strftime('%B')
            header_text = f"📊 {month_name.upper()} PORTFOLIO PACING ANALYSIS"
        lines.append(header_text)
        lines.append("═" * 10)
        lines.append("")
        
        # Campaign info
        tz_display = pacing.get('timezone_display', pacing.get('timezone', 'PST'))
        lines.append(f"Campaign Period: {campaign_start} - {campaign_end} ({tz_display})")
        lines.append(f"Total Budget: ${pacing['budget']:,.2f}")
        lines.append("")
        
        # Spend Summary
        spend_header = "💰 SPEND SUMMARY"
        lines.append(spend_header)
        lines.append("─" * 10)
        lines.append(f"Total Spend to Date:        ${pacing['total_spend']:,.2f}")
        lines.append(f"Budget Utilization:          {pacing['budget_utilization_pct']:.1f}%")
        lines.append(f"Remaining Budget:            ${pacing['remaining_budget']:,.2f}")
        lines.append("")
        
        # Timeline Analysis
        timeline_header = "📅 TIMELINE ANALYSIS"
        lines.append(timeline_header)
        lines.append("─" * 10)
        if pacing['is_partial_day']:
            partial_hours = int(pacing['partial_day_fraction'] * 24)
            lines.append(f"Days Passed:                 {pacing['days_passed']:.1f} days ({campaign_start} - {pacing['last_data_date']})")
            lines.append(f"  • Full Days:              {pacing['full_days']} days")
            lines.append(f"  • Partial Day ({pacing['last_data_date']}): {pacing['partial_day_fraction']:.1%} ({partial_hours} hours elapsed in {tz_display})")
        else:
            lines.append(f"Days Passed:                 {pacing['days_passed']:.0f} days ({campaign_start} - {pacing['last_data_date']})")
        # Removed "Days Remaining" - not relevant for rolling 30-day window (always 0)
        lines.append("")
        
        # Pacing Metrics
        pacing_metrics_header = "📈 PACING METRICS"
        lines.append(pacing_metrics_header)
        lines.append("─" * 10)
        lines.append(f"Expected Spend to Date:      ${pacing['expected_spend']:,.2f}")
        lines.append(f"  (Target: ${pacing['expected_daily_rate']:,.2f}/day × {pacing['days_passed']:.1f} days)")
        lines.append(f"Actual Spend to Date:        ${pacing['total_spend']:,.2f}")
        lines.append(f"Spend Variance:              ${pacing['spend_variance']:,.2f} ({pacing['variance_pct']:+.1f}% {'ahead' if pacing['spend_variance'] > 0 else 'behind'} target)")
        lines.append("")
        lines.append(f"Actual Daily Rate:           ${pacing['actual_daily_rate']:,.2f}/day")
        lines.append(f"Projected Final Spend:       ${pacing['projected_final_spend']:,.2f}")
        lines.append(f"  (Based on current daily rate × {pacing['total_days']} days)")
        lines.append("")
        
        # Pacing Status
        pacing_status_header = f"🎯 PACING STATUS: {pacing['pacing_emoji']} {pacing['pacing_status']}"
        lines.append(pacing_status_header)
        lines.append("─" * 10)
        
        # Status explanation
        if pacing['projected_final_spend'] > pacing['budget']:
            overage = pacing['projected_final_spend'] - pacing['budget']
            lines.append(f"Current pace is {abs(pacing['variance_pct']):.1f}% {'ahead' if pacing['variance_pct'] > 0 else 'behind'} target. At current daily rate of")
            lines.append(f"${pacing['actual_daily_rate']:,.2f}/day, the campaign is projected to spend ${pacing['projected_final_spend']:,.2f}")
            lines.append(f"by {campaign_end}, which exceeds the ${pacing['budget']:,.2f} budget by ${overage:,.2f}.")
        else:
            lines.append(f"Current pace is {abs(pacing['variance_pct']):.1f}% {'ahead' if pacing['variance_pct'] > 0 else 'behind'} target. At current daily rate of")
            lines.append(f"${pacing['actual_daily_rate']:,.2f}/day, the campaign is projected to spend ${pacing['projected_final_spend']:,.2f}")
            lines.append(f"by {campaign_end}, which is ${pacing['budget'] - pacing['projected_final_spend']:,.2f} under budget.")
        
        # Removed "Required Daily Rate" - not meaningful for rolling 30-day window (always 0 days remaining)
        lines.append("")
        
        # Recent Daily Spend
        recent_spend_header = "📊 RECENT DAILY SPEND (Last 3 Days)"
        lines.append(recent_spend_header)
        lines.append("─" * 10)
        recent_data = portfolio_daily.head(3)
        for _, row in recent_data.iterrows():
            date_str = str(row.get('date', ''))
            spend = float(row.get('spend', 0))
            if pacing['is_partial_day'] and str(row.get('date', '')) == str(pacing['last_data_date']):
                lines.append(f"{date_str} ({tz_display}): ${spend:,.2f}  (partial day - {int(pacing['partial_day_fraction'] * 24)} hours)")
            else:
                lines.append(f"{date_str} ({tz_display}): ${spend:,.2f}")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error formatting portfolio results: {e}", exc_info=True)
        return f"❌ Error formatting results: {str(e)}"


@tool
def analyze_portfolio_pacing(
    account_id: str = "17",
    advertiser_filter: Optional[str] = None,
    campaign_start: Optional[str] = None,  # None = use rolling 30-day window
    campaign_end: Optional[str] = None,    # None = use rolling 30-day window
    campaign_budget: Optional[float] = 233000.0,
    job_name: Optional[str] = None
) -> str:
    """
    Analyze portfolio pacing and health.
    
    Useful for questions about portfolio health, budget, spend, or status.
    
    CRITICAL USAGE RULES:
    - STRICTLY RESERVED for queries asking for *numbers*, *data*, *status*, or *health* metrics
    - DO NOT USE if the user is just asking who you are or what you do
    - DO NOT USE for introductions, greetings, or general conversation
    - DO NOT USE for role explanations or "who are you?" questions
    - If the input is ambiguous, err on the side of NOT calling this tool
    - This tool is computationally expensive - only use when live data is explicitly required
    
    Default values:
    - account_id: "17" (Tricoast Media LLC)
    - advertiser_filter: None (all advertisers) or "Lilly" if user mentions Eli Lilly
    - campaign_start: None (uses rolling 30-day window: today - 29 days to today, PST)
    - campaign_end: None (uses rolling 30-day window: today, PST)
    - campaign_budget: 233000.0 ($233,000)
    
    Always use account_id="17" unless user specifies a different account.
    If user mentions "Eli Lilly" or "Lilly", use advertiser_filter="Lilly".
    
    Parameters:
    - account_id: Account ID to analyze (default: "17")
    - advertiser_filter: Filter campaigns by advertiser name (default: None for all)
    - campaign_start: Campaign start date for pacing (YYYY-MM-DD, default: None = rolling 30-day window)
    - campaign_end: Campaign end date for pacing (YYYY-MM-DD, default: None = rolling 30-day window)
    - campaign_budget: Total campaign budget for pacing analysis (default: 233000.0)
    - job_name: Job identifier for tracking (optional)
    
    Returns formatted portfolio analysis with metrics including:
    - Campaign discovery and counts
    - Daily spend and impression data
    - Portfolio rollups (6 views: Line Items Daily/Total, Campaigns Daily/Total, Portfolio Daily/Total)
    - Recent daily pacing trends
    """
    try:
        # Clean inputs (handle simple lists from LLM)
        clean_account = _safe_str(account_id) or "17"
        clean_filter = _safe_str(advertiser_filter) if advertiser_filter else None
        
        # Load client config early to calculate rolling window dates with correct timezone
        client_config = None
        try:
            # Import load_client_config from the tool's utils
            # We need to be in the tool directory context for imports
            original_cwd = os.getcwd()
            original_path = sys.path[:]
            try:
                # Get tool_dir
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                tool_dir = os.path.join(project_root, "tools", "campaign-portfolio-pacing")
                
                os.chdir(tool_dir)
                if tool_dir not in sys.path:
                    sys.path.insert(0, tool_dir)
                
                from src.utils.config import load_client_config
                
                # For account_id=17, load Tricoast Media LLC config
                if clean_account == "17":
                    client_name = "Tricoast Media LLC"
                    try:
                        client_config = load_client_config(client_name)
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
        
        # Calculate dates: use rolling 30-day window if not provided
        if campaign_start is None or campaign_end is None:
            clean_start, clean_end = _calculate_rolling_30day_window(client_config)
            logger.info(f"Using rolling 30-day window: {clean_start} to {clean_end}")
        else:
            clean_start = _safe_str(campaign_start)
            clean_end = _safe_str(campaign_end)
        
        budget_value = float(campaign_budget) if campaign_budget else 233000.0
        logger.info(f"Portfolio Pacing Tool executing: Account={clean_account}, Filter={clean_filter}, Date Range={clean_start} to {clean_end}, Budget=${budget_value:,.0f}")
        
        # Lazy load CampaignSpendAnalyzer if not already loaded
        # This ensures path setup happens at call time, not module import time
        global CampaignSpendAnalyzer, REAL_DATA_AVAILABLE
        
        if not REAL_DATA_AVAILABLE or not CampaignSpendAnalyzer:
            # Try to load it now (might have failed at import time due to path issues)
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
                original_path = list(sys.path)  # Copy, don't reference
                try:
                    # CRITICAL: Add tool_dir to sys.path BEFORE changing directory
                    # This ensures Python can find the 'src' package
                    if tool_dir not in sys.path:
                        sys.path.insert(0, tool_dir)
                    
                    os.chdir(tool_dir)
                    
                    # Clear ALL cached src.* modules to force fresh import
                    import importlib
                    import importlib.util
                    
                    # Clear all src.* modules
                    modules_to_clear = [k for k in list(sys.modules.keys()) if k.startswith('src.')]
                    for mod_name in modules_to_clear:
                        del sys.modules[mod_name]
                    
                    # Also clear 'src' itself if cached
                    if 'src' in sys.modules:
                        del sys.modules['src']
                    
                    # CRITICAL: Initialize the src package structure BEFORE importing CampaignSpendAnalyzer
                    # This ensures relative imports (like .utils.logging) resolve correctly
                    # We must import in order: src -> src.utils -> src.utils.logging
                    # This initializes the package namespace properly
                    # NOTE: All imports are optional - we continue even if some fail
                    # Only fail if CampaignSpendAnalyzer itself can't be imported
                    
                    # Step 1: Import src package (creates src namespace) - optional
                    try:
                        import src
                        if not hasattr(src, '__path__'):
                            raise ImportError("src is not a package")
                    except ImportError as e:
                        logger.debug(f"⚠️  src package not available: {e}, continuing anyway")
                    
                    # Step 2: Import src.utils (creates src.utils namespace) - optional
                    try:
                        import src.utils
                        if not hasattr(src.utils, '__path__'):
                            raise ImportError("src.utils is not a package")
                    except ImportError as e:
                        logger.debug(f"⚠️  src.utils not available: {e}, continuing anyway")
                    
                    # Step 3: Import src.utils.logging (optional - may not exist in all setups)
                    try:
                        import src.utils.logging
                        
                        # CRITICAL: Monkey-patch setup_logger BEFORE importing CampaignSpendAnalyzer
                        # This prevents console handlers from being added when DataRollupProcessor.__init__ calls setup_logger()
                        original_setup_logger_func = src.utils.logging.setup_logger
                        
                        def suppressed_setup_logger(name, log_file=None, level=logging.INFO):
                            """Suppressed version of setup_logger that doesn't add console handlers"""
                            logger_obj = logging.getLogger(name)
                            logger_obj.setLevel(logging.CRITICAL)  # Suppress all messages
                            # Don't add console handler - that's what we're preventing
                            # Only add file handler if specified (for debugging, but won't show in console)
                            if log_file:
                                import os
                                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                                file_handler = logging.FileHandler(log_file)
                                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                                file_handler.setFormatter(formatter)
                                logger_obj.addHandler(file_handler)
                            return logger_obj
                        
                        # Monkey-patch the module
                        src.utils.logging.setup_logger = suppressed_setup_logger
                        logger.debug("✅ Monkey-patched setup_logger to suppress console handlers")
                    except ImportError:
                        logger.debug("⚠️  src.utils.logging not available, skipping monkey-patch (will use handler removal instead)")
                    
                    # Step 4: Import src.utils.config (might be needed) - optional
                    try:
                        import src.utils.config
                    except ImportError:
                        pass  # Optional
                    
                    logger.debug("✅ Attempting to import CampaignSpendAnalyzer (package initialization complete or skipped)")
                    logger.debug(f"   Current directory: {os.getcwd()}")
                    logger.debug(f"   tool_dir in sys.path: {tool_dir in sys.path}")
                    logger.debug(f"   tool_dir exists: {os.path.exists(tool_dir)}")
                    logger.debug(f"   src/campaign_analyzer.py exists: {os.path.exists(os.path.join(tool_dir, 'src', 'campaign_analyzer.py'))}")
                    
                    # Now import CampaignSpendAnalyzer - package structure is initialized (or skipped)
                    # This will trigger imports of dependencies, which should now resolve correctly
                    try:
                        from src.campaign_analyzer import CampaignSpendAnalyzer
                        REAL_DATA_AVAILABLE = True
                        logger.info("✅ CampaignSpendAnalyzer loaded successfully (lazy load)")
                    except ImportError as import_err:
                        # Provide more detailed error information
                        import traceback
                        error_details = traceback.format_exc()
                        logger.error(f"Failed to import CampaignSpendAnalyzer: {import_err}")
                        logger.error(f"Import traceback:\n{error_details}")
                        logger.error(f"   sys.path contains: {[p for p in sys.path if 'campaign' in p.lower()]}")
                        raise ImportError(f"Could not import CampaignSpendAnalyzer from src.campaign_analyzer: {import_err}")
                finally:
                    os.chdir(original_cwd)
                    # Don't restore sys.path completely - keep tool_dir for module resolution
                    # The imported modules might still need it
                    if tool_dir not in sys.path:
                        sys.path.insert(0, tool_dir)
            except Exception as e:
                error_msg = f"CampaignSpendAnalyzer not available: {e}"
                logger.error(error_msg)
                raise Exception(error_msg)
        
        # Final check
        if not REAL_DATA_AVAILABLE or not CampaignSpendAnalyzer:
            error_msg = "CampaignSpendAnalyzer not available. Database connection required."
            logger.error(error_msg)
            raise Exception(error_msg)
        
        try:
            logger.info("Running full portfolio analysis using CampaignSpendAnalyzer")
            
            # Client config already loaded earlier (needed for rolling window date calculation)
            # Reuse it here for timezone handling in analysis
            
            # Suppress stdout/stderr to hide internal print statements from CampaignSpendAnalyzer
            # and DatabaseConnector. The Guardian agent will format and display the results,
            # not the raw tool output or internal processing messages.
            # Also suppress logging output from internal components (data.rollup.processor, etc.)
            stdout_capture = StringIO()
            stderr_capture = StringIO()
            
            # Temporarily suppress logging for internal components
            # Remove handlers entirely to prevent any log output during tool execution
            loggers_to_suppress = [
                'data.rollup.processor',
                'campaign.analyzer',
                'database.connector',
                'src.data_rollup_processor',
                'src.campaign_analyzer',
                'src.utils.logging'
            ]
            original_log_levels = {}
            handlers_removed = []  # Track (logger, handler) pairs that were removed
            
            # Monkey-patch setup_logger RIGHT BEFORE calling run_analysis()
            # This prevents handlers from being added when DataRollupProcessor.__init__ calls setup_logger()
            # We need to patch it every time because DataRollupProcessor is created fresh each time
            original_setup_logger_func = None
            logging_module_patched = None
            try:
                # Get tool directory path
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                tool_dir = os.path.join(project_root, "tools", "campaign-portfolio-pacing")
                
                # Try to import and patch setup_logger
                original_cwd = os.getcwd()
                try:
                    os.chdir(tool_dir)
                    if tool_dir not in sys.path:
                        sys.path.insert(0, tool_dir)
                    
                    # Import the logging module (optional - may not exist)
                    try:
                        import src.utils.logging as logging_module
                        original_setup_logger_func = logging_module.setup_logger
                        logging_module_patched = logging_module
                        
                        # Create suppressed version that doesn't add console handlers
                        def suppressed_setup_logger(name, log_file=None, level=logging.INFO):
                            """Suppressed version of setup_logger that doesn't add console handlers"""
                            logger_obj = logging.getLogger(name)
                            logger_obj.setLevel(logging.CRITICAL)  # Suppress all messages
                            # Don't add console handler - that's what we're preventing
                            # Only add file handler if specified (for debugging, but won't show in console)
                            if log_file:
                                import os
                                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                                file_handler = logging.FileHandler(log_file)
                                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                                file_handler.setFormatter(formatter)
                                logger_obj.addHandler(file_handler)
                            return logger_obj
                        
                        # Monkey-patch the module
                        logging_module.setup_logger = suppressed_setup_logger
                        logger.debug("Monkey-patched setup_logger to suppress console handlers")
                    except ImportError:
                        logger.debug("src.utils.logging not available, skipping monkey-patch (will use handler removal instead)")
                        original_setup_logger_func = None
                        logging_module_patched = None
                finally:
                    os.chdir(original_cwd)
            except Exception as e:
                logger.debug(f"Could not monkey-patch setup_logger: {e}, using handler removal instead")
                original_setup_logger_func = None
                logging_module_patched = None
            
            # Also suppress existing loggers (in case they were already created)
            for logger_name in loggers_to_suppress:
                logger_obj = logging.getLogger(logger_name)
                original_log_levels[logger_name] = logger_obj.level
                logger_obj.setLevel(logging.CRITICAL)  # Set very high to suppress all messages
                
                # Temporarily remove all handlers for this logger to prevent any output
                for handler in list(logger_obj.handlers):  # Create copy of list to iterate safely
                    handlers_removed.append((logger_obj, handler))
                    logger_obj.removeHandler(handler)
            
            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    # Initialize analyzer with account, advertiser filter, and client config (for PST timezone)
                    # DatabaseConnector prints connection messages during __init__, so suppress here too
                    analyzer = CampaignSpendAnalyzer(
                        account_id=clean_account,
                        advertiser_filter=clean_filter,
                        client_config=client_config  # Pass client config for PST timezone handling
                    )
                    
                    # Run full analysis (discovers campaigns, collects spend data, generates rollups)
                    # DataRollupProcessor will be created here and will use our patched setup_logger
                    result = analyzer.run_analysis(
                        start_date=clean_start,
                        end_date=clean_end
                    )
            finally:
                # Restore original setup_logger if we monkey-patched it
                if logging_module_patched and original_setup_logger_func:
                    try:
                        logging_module_patched.setup_logger = original_setup_logger_func
                        logger.debug("Restored original setup_logger")
                    except Exception as e:
                        logger.debug(f"Could not restore setup_logger: {e}")
                
                # Restore original log levels
                for logger_name, original_level in original_log_levels.items():
                    logger_obj = logging.getLogger(logger_name)
                    logger_obj.setLevel(original_level)
                
                # Restore handlers
                for logger_obj, handler in handlers_removed:
                    logger_obj.addHandler(handler)
            
            # Log captured output at debug level (for troubleshooting, but not shown to user)
            captured_stdout = stdout_capture.getvalue()
            captured_stderr = stderr_capture.getvalue()
            if captured_stdout:
                logger.debug(f"Suppressed stdout output (length: {len(captured_stdout)} chars)")
            if captured_stderr:
                logger.debug(f"Suppressed stderr output (length: {len(captured_stderr)} chars)")
                
                # Check for errors
                if result.get('error'):
                    error_msg = result.get('error')
                    logger.error(f"Analysis returned error: {error_msg}")
                    raise Exception(f"Portfolio analysis failed: {error_msg}")
                
            # Add account_id to result for formatting
            result['account_id'] = clean_account
            
            # Format results with pacing analysis
            formatted_output = _format_portfolio_results(
                result_data=result,
                campaign_start=clean_start,
                campaign_end=clean_end,
                campaign_budget=float(campaign_budget) if campaign_budget else 233000.0,
                client_config=client_config
            )
            logger.info("✅ Portfolio analysis completed successfully")
            return formatted_output
                
        except Exception as e:
            logger.error(f"Error running portfolio analysis: {e}", exc_info=True)
            raise Exception(f"Portfolio analysis failed: {str(e)}")
        
    except Exception as e:
        logger.error(f"Portfolio pacing tool error: {e}", exc_info=True)
        raise
