"""
Portfolio Pacing Helper Functions
==================================

Helper functions for portfolio pacing calculations and formatting.
"""
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pytz

logger = logging.getLogger(__name__)


def safe_str(val) -> str:
    """Safely convert any input to string, handling simple lists."""
    if val is None:
        return ""
    if isinstance(val, list) and len(val) > 0:
        return str(val[0]).strip()
    return str(val).strip()


def calculate_rolling_30day_window(client_config: Dict[str, Any] = None) -> tuple[str, str]:
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


def calculate_pacing_analysis(
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
        ]
        
        if len(filtered) == 0:
            return {'error': 'No data in campaign date range'}
        
        # Calculate totals
        total_spend = float(filtered['spend'].sum())
        
        # Find last data date
        last_data_date = filtered['date'].max()
        
        # Calculate days passed
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
        
        full_days = int(days_passed)
        
        # Calculate expected spend
        expected_daily_rate = campaign_budget / total_days
        expected_spend = expected_daily_rate * days_passed
        
        # Calculate actual daily rate
        actual_daily_rate = total_spend / days_passed if days_passed > 0 else 0
        
        # Projected final spend
        projected_final_spend = actual_daily_rate * total_days
        
        # Calculate variance
        spend_variance = total_spend - expected_spend
        variance_pct = (spend_variance / expected_spend * 100) if expected_spend > 0 else 0
        
        # Determine status
        if abs(variance_pct) < 5:
            status = "ON PACE"
            emoji = "🟢"
        elif variance_pct > 0:
            status = "AHEAD"
            emoji = "🟡"
        else:
            status = "BEHIND"
            emoji = "🔴"
        
        # Budget utilization
        budget_utilization_pct = (total_spend / campaign_budget * 100) if campaign_budget > 0 else 0
        remaining_budget = campaign_budget - total_spend
        
        # Required daily rate (not meaningful for rolling 30-day window, but calculate anyway)
        days_remaining = max(0, total_days - days_passed)
        required_daily_rate = (remaining_budget / days_remaining) if days_remaining > 0 else 0
        
        return {
            'total_spend': total_spend,
            'budget': campaign_budget,
            'budget_utilization_pct': budget_utilization_pct,
            'remaining_budget': remaining_budget,
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
            'partial_day_fraction': partial_day_fraction,
            'days_passed': days_passed,
            'full_days': full_days,
            'total_days': total_days,
            'start_date': start_date,
            'end_date': end_date,
            'timezone': tz_str,
            'timezone_display': tz_display
        }
        
    except Exception as e:
        logger.error(f"Error calculating pacing analysis: {e}", exc_info=True)
        return {'error': str(e)}


def generate_portfolio_csv(
    portfolio_daily: pd.DataFrame,
    pacing: Dict[str, Any],
    campaign_start: str,
    campaign_end: str,
    account_id: str
) -> str:
    """
    Generate CSV string from portfolio daily data.
    
    Args:
        portfolio_daily: DataFrame with 'date' and 'spend' columns (and optionally 'impressions')
        pacing: Pacing analysis dict with expected_daily_rate, budget, etc.
        campaign_start: Campaign start date (YYYY-MM-DD)
        campaign_end: Campaign end date (YYYY-MM-DD)
        account_id: Account ID for filename
        
    Returns:
        CSV string with columns: Date, Spend, Impressions, Budget Target, Daily Variance, Status
    """
    try:
        # Create a copy to avoid modifying original
        df = portfolio_daily.copy()
        
        # Ensure date column exists and is formatted
        if 'date' not in df.columns:
            logger.warning("No 'date' column in portfolio_daily DataFrame")
            return ""
        
        # Sort by date descending (most recent first)
        df = df.sort_values('date', ascending=False).reset_index(drop=True)
        
        # Calculate daily budget target
        expected_daily_rate = pacing.get('expected_daily_rate', 0)
        
        # Build CSV rows
        csv_rows = []
        
        # Header
        headers = ['Date', 'Spend', 'Budget Target', 'Daily Variance', 'Status']
        if 'impressions' in df.columns:
            headers.insert(2, 'Impressions')  # Insert after Spend
        
        csv_rows.append(','.join(headers))
        
        # Data rows
        for _, row in df.iterrows():
            date_str = str(row.get('date', ''))
            spend = float(row.get('spend', 0))
            impressions = int(row.get('impressions', 0)) if 'impressions' in df.columns else None
            
            # Calculate variance
            daily_variance = spend - expected_daily_rate
            
            # Determine status
            if abs(daily_variance) < expected_daily_rate * 0.02:  # Within 2% of target
                status = "On Pace"
            elif daily_variance > 0:
                status = "Ahead"
            else:
                status = "Behind"
            
            # Build row
            row_data = [
                date_str,
                f"{spend:.2f}",
                f"{expected_daily_rate:.2f}",
                f"{daily_variance:.2f}",
                status
            ]
            
            # Insert impressions if available
            if impressions is not None:
                row_data.insert(2, str(impressions))
            
            csv_rows.append(','.join(row_data))
        
        return '\n'.join(csv_rows)
        
    except Exception as e:
        logger.error(f"Error generating CSV: {e}", exc_info=True)
        return ""


def format_portfolio_results(
    result_data: dict,
    campaign_start: str,
    campaign_end: str,
    campaign_budget: float,
    client_config: Dict[str, Any] = None,
    account_id: str = "17"
) -> Dict[str, Any]:
    """
    Format analysis results with comprehensive pacing analysis for rolling 30-day window.
    """
    try:
        rollups = result_data.get('rollups', {})
        
        # Get portfolio_daily rollup
        portfolio_daily = rollups.get('portfolio_daily')
        
        if portfolio_daily is None or len(portfolio_daily) == 0:
            return {
                "text": "❌ No portfolio daily data available",
                "csv": None,
                "filename": None
            }
        
        # Calculate pacing analysis
        pacing = calculate_pacing_analysis(
            portfolio_daily=portfolio_daily,
            campaign_start=campaign_start,
            campaign_end=campaign_end,
            campaign_budget=campaign_budget,
            client_config=client_config
        )
        
        if pacing.get('error'):
            return {
                "text": f"❌ Error calculating pacing: {pacing['error']}",
                "csv": None,
                "filename": None
            }
        
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
        
        formatted_text = "\n".join(lines)
        
        # Generate CSV
        csv_data = None
        csv_filename = None
        try:
            csv_data = generate_portfolio_csv(
                portfolio_daily=portfolio_daily,
                pacing=pacing,
                campaign_start=campaign_start,
                campaign_end=campaign_end,
                account_id=account_id
            )
            
            # Only set filename if CSV data was successfully generated
            if csv_data and csv_data.strip():
                # Generate filename: portfolio_daily_{account_id}_{start_date}_to_{end_date}.csv
                csv_filename = f"portfolio_daily_{account_id}_{campaign_start}_to_{campaign_end}.csv"
            else:
                csv_data = None  # Ensure None if empty
        except Exception as e:
            logger.warning(f"Failed to generate CSV: {e}, continuing with text-only output")
            csv_data = None
        
        return {
            "text": formatted_text,
            "csv": csv_data,
            "filename": csv_filename
        }
        
    except Exception as e:
        logger.error(f"Error formatting portfolio results: {e}", exc_info=True)
        return {
            "text": f"❌ Error formatting results: {str(e)}",
            "csv": None,
            "filename": None
        }

