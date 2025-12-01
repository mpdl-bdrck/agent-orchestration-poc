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
import logging
import json
from typing import Optional
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from langchain_core.tools import tool

from .portfolio_pacing_helpers import (
    safe_str,
    calculate_rolling_30day_window,
    format_portfolio_results
)
from .portfolio_pacing_loader import (
    load_client_config,
    get_analyzer
)

logger = logging.getLogger(__name__)


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
        clean_account = safe_str(account_id) or "17"
        clean_filter = safe_str(advertiser_filter) if advertiser_filter else None
        
        # Load client config early to calculate rolling window dates with correct timezone
        client_config = load_client_config(clean_account)
        
        # Calculate dates: use rolling 30-day window if not provided
        if campaign_start is None or campaign_end is None:
            clean_start, clean_end = calculate_rolling_30day_window(client_config)
            logger.info(f"Using rolling 30-day window: {clean_start} to {clean_end}")
        else:
            clean_start = safe_str(campaign_start)
            clean_end = safe_str(campaign_end)
        
        budget_value = float(campaign_budget) if campaign_budget else 233000.0
        logger.info(f"Portfolio Pacing Tool executing: Account={clean_account}, Filter={clean_filter}, Date Range={clean_start} to {clean_end}, Budget=${budget_value:,.0f}")
        
        # Get analyzer class (lazy loads if needed)
        CampaignSpendAnalyzer = get_analyzer()
        
        # Suppress stdout/stderr and logging during analysis
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        
        loggers_to_suppress = [
            'data.rollup.processor',
            'campaign.analyzer',
            'database.connector',
            'src.data_rollup_processor',
            'src.campaign_analyzer',
            'src.utils.logging'
        ]
        original_log_levels = {}
        handlers_removed = []
        
        # Suppress existing loggers
        for logger_name in loggers_to_suppress:
            logger_obj = logging.getLogger(logger_name)
            original_log_levels[logger_name] = logger_obj.level
            logger_obj.setLevel(logging.CRITICAL)
            for handler in list(logger_obj.handlers):
                handlers_removed.append((logger_obj, handler))
                logger_obj.removeHandler(handler)
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Initialize analyzer with account, advertiser filter, and client config (for PST timezone)
                analyzer = CampaignSpendAnalyzer(
                    account_id=clean_account,
                    advertiser_filter=clean_filter,
                    client_config=client_config
                )
                
                # Run full analysis
                result = analyzer.run_analysis(
                    start_date=clean_start,
                    end_date=clean_end
                )
        finally:
            # Restore log levels and handlers
            for logger_name, original_level in original_log_levels.items():
                logging.getLogger(logger_name).setLevel(original_level)
            for logger_obj, handler in handlers_removed:
                logger_obj.addHandler(handler)
        
        # Check for errors
        if result.get('error'):
            error_msg = result.get('error')
            logger.error(f"Analysis returned error: {error_msg}")
            raise Exception(f"Portfolio analysis failed: {error_msg}")
        
        # Add account_id to result for formatting
        result['account_id'] = clean_account
        
        # Format results with pacing analysis
        formatted_result = format_portfolio_results(
            result_data=result,
            campaign_start=clean_start,
            campaign_end=clean_end,
            campaign_budget=budget_value,
            client_config=client_config,
            account_id=clean_account
        )
        
        # Return JSON string if CSV is available, otherwise return text-only (backward compatible)
        if isinstance(formatted_result, dict) and formatted_result.get('csv'):
            logger.info("✅ Portfolio analysis completed successfully (with CSV)")
            return json.dumps(formatted_result)
        elif isinstance(formatted_result, dict):
            logger.info("✅ Portfolio analysis completed successfully (text-only)")
            return formatted_result.get('text', str(formatted_result))
        else:
            logger.info("✅ Portfolio analysis completed successfully")
            return str(formatted_result)
            
    except Exception as e:
        logger.error(f"Portfolio pacing tool error: {e}", exc_info=True)
        raise
