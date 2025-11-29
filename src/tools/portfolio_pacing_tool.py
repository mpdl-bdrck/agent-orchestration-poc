"""
Portfolio Pacing Tool Wrapper for Guardian Agent
================================================

Wraps campaign-portfolio-pacing tool by calling the shell script (which handles AWS SSO).
"""
import subprocess
import json
import os
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def analyze_portfolio_pacing(
    account_id: str,
    advertiser_filter: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    campaign_start: Optional[str] = None,
    campaign_end: Optional[str] = None,
    campaign_budget: Optional[float] = None
) -> str:
    """
    Analyze portfolio pacing by calling the shell script (which handles AWS SSO).
    
    Args:
        account_id: Account ID to analyze
        advertiser_filter: Optional advertiser name filter
        start_date: Optional start date for data collection
        end_date: Optional end date for data collection
        campaign_start: Campaign start date for pacing calculations
        campaign_end: Campaign end date for pacing calculations
        campaign_budget: Total campaign budget for pacing calculations
    
    Returns:
        JSON string with portfolio insights
    """
    # Get absolute path to the shell script
    tools_dir = (Path(__file__).parent.parent.parent / "tools").resolve()
    script_path = tools_dir / "campaign-portfolio-pacing" / "run_campaign_portfolio_pacing.sh"
    
    if not script_path.exists():
        return json.dumps({
            "status": "error",
            "error": "Script not found",
            "message": f"Portfolio analysis script not found at {script_path}"
        })
    
    # Build command - use --no-publish-sheets to skip Sheets publishing
    cmd = [str(script_path), account_id]
    
    if advertiser_filter:
        cmd.append(advertiser_filter)
    
    if start_date:
        cmd.extend(["--start-date", start_date])
    
    if end_date:
        cmd.extend(["--end-date", end_date])
    
    if campaign_start:
        cmd.extend(["--campaign-start", campaign_start])
    
    if campaign_end:
        cmd.extend(["--campaign-end", campaign_end])
    
    if campaign_budget:
        cmd.extend(["--campaign-budget", str(campaign_budget)])
    
    # Skip Sheets publishing - we just want the CSV data
    cmd.append("--no-publish-sheets")
    
    try:
        # Run the script - change to script directory so relative paths work
        script_dir = script_path.parent
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(script_dir),
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            # Combine stdout and stderr for error detection
            combined_output = result.stdout + result.stderr

            # Check errors in order of specificity (most specific first)

            # 1. Check if it's a missing module/dependency error (most specific)
            if "ModuleNotFoundError" in combined_output or "ImportError" in combined_output or "No module named" in combined_output:
                return json.dumps({
                    "status": "error",
                    "error": "Missing Python dependencies",
                    "message": "The portfolio analysis tool is missing required Python modules. Please ensure all dependencies are installed in the virtual environment.",
                    "user_message": "I'm unable to analyze your portfolio because some required components are missing. Please check the tool installation or contact support.",
                    "technical_details": combined_output[:500]
                })

            # 2. Check if it's a database error
            if ("database" in combined_output.lower() or
                "connection" in combined_output.lower() or
                "PostgreSQL" in combined_output or
                "NoneType" in combined_output or
                "cursor" in combined_output):
                return json.dumps({
                    "status": "error",
                    "error": "Database connection required",
                    "message": "I cannot analyze the portfolio at this time because the database connection is not available. The portfolio analysis tool requires a PostgreSQL database connection to retrieve campaign data. Please ensure the database is running and properly configured.",
                    "user_message": "I'm unable to analyze your portfolio right now because the database connection is unavailable. This tool requires access to the campaign database to retrieve portfolio data. Please check your database configuration or contact support.",
                    "technical_details": combined_output[:500]
                })

            # 3. Generic error fallback
            return json.dumps({
                "status": "error",
                "error": f"Script execution failed (exit code {result.returncode})",
                "message": f"Portfolio analysis script failed. Please check the tool configuration and dependencies.",
                "user_message": f"I encountered an issue while analyzing your portfolio. The analysis tool reported an error.",
                "technical_details": combined_output[:500]
            })
        
        # Parse CSV outputs from reports directory
        # Reports are written to tools/reports/ (relative to project root)
        # script_dir is tools/campaign-portfolio-pacing/, so reports are at tools/reports/
        # Get the tools directory (parent of script_dir)
        tools_dir = script_dir.parent
        reports_dir = tools_dir / "reports"
        
        if not reports_dir.exists():
            return json.dumps({
                "status": "error",
                "error": "Reports directory not found",
                "message": "Analysis completed but no reports directory was created"
            })
        
        # Load portfolio rollup CSVs
        portfolio_total_path = reports_dir / "portfolio_total.csv"
        portfolio_daily_path = reports_dir / "portfolio_daily.csv"
        
        portfolio_total = None
        portfolio_daily = None
        
        if portfolio_total_path.exists():
            try:
                portfolio_total = pd.read_csv(portfolio_total_path)
            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "error": f"Failed to parse portfolio_total.csv: {str(e)}",
                    "message": "Analysis completed but failed to parse results"
                })
        
        if portfolio_daily_path.exists():
            try:
                portfolio_daily = pd.read_csv(portfolio_daily_path)
            except Exception as e:
                # Non-critical - daily data might not be available
                pass
        
        # Extract insights from CSV data
        insights = _extract_portfolio_insights(
            portfolio_total=portfolio_total,
            portfolio_daily=portfolio_daily,
            campaign_start=campaign_start,
            campaign_end=campaign_end,
            campaign_budget=campaign_budget
        )
        
        # Get advertiser name from portfolio_total if available
        advertiser_name = advertiser_filter or "Unknown"
        campaigns_analyzed = 0
        
        if portfolio_total is not None and not portfolio_total.empty:
            # Try to extract advertiser name and campaign count from the data
            if 'advertiser_name' in portfolio_total.columns:
                advertiser_name = str(portfolio_total.iloc[0]['advertiser_name'])
            if 'campaign_count' in portfolio_total.columns:
                campaigns_analyzed = int(portfolio_total.iloc[0]['campaign_count'])
        
        # Determine date range
        date_range = "Unknown"
        if start_date and end_date:
            date_range = f"{start_date} to {end_date}"
        elif start_date:
            date_range = f"{start_date} to today"
        elif portfolio_daily is not None and not portfolio_daily.empty and 'date' in portfolio_daily.columns:
            dates = portfolio_daily['date'].dropna()
            if len(dates) > 0:
                date_range = f"{dates.min()} to {dates.max()}"
        
        return json.dumps({
            "status": "success",
            "account_id": account_id,
            "advertiser": advertiser_name,
            "campaigns_analyzed": campaigns_analyzed,
            "date_range": date_range,
            "insights": insights
        }, indent=2)
        
    except subprocess.TimeoutExpired:
        return json.dumps({
            "status": "error",
            "error": "Script execution timeout",
            "message": "Portfolio analysis took too long to complete (exceeded 5 minute timeout)",
            "user_message": "The portfolio analysis is taking longer than expected. Please try again or contact support."
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        
        # Check if it's a database connection error
        if 'NoneType' in error_msg or 'cursor' in error_msg or 'database' in error_msg.lower() or 'connection' in error_msg.lower():
            return json.dumps({
                "status": "error",
                "error": "Database connection required",
                "message": "I cannot analyze the portfolio at this time because the database connection is not available. The portfolio analysis tool requires a PostgreSQL database connection to retrieve campaign data. Please ensure the database is running and properly configured.",
                "user_message": "I'm unable to analyze your portfolio right now because the database connection is unavailable. This tool requires access to the campaign database to retrieve portfolio data. Please check your database configuration or contact support.",
                "technical_details": error_msg
            })
        
        return json.dumps({
            "status": "error",
            "error": error_msg,
            "traceback": error_traceback,
            "message": "Portfolio analysis failed"
        })


def _extract_portfolio_insights(
    portfolio_total: Optional[pd.DataFrame],
    portfolio_daily: Optional[pd.DataFrame],
    campaign_start: Optional[str],
    campaign_end: Optional[str],
    campaign_budget: Optional[float]
) -> Dict[str, Any]:
    """
    Extract dashboard-style insights from CSV rollup data.
    
    Returns insights matching the Google Sheets dashboard format.
    """
    insights = {}
    
    # Portfolio Total Insights
    if portfolio_total is not None and not portfolio_total.empty:
        try:
            row = portfolio_total.iloc[0]
            
            # Extract budget and spend data
            total_budget_from_data = float(row.get('total_budget', 0) if pd.notna(row.get('total_budget', 0)) else 0)
            total_spend = float(row.get('total_spend', 0) if pd.notna(row.get('total_spend', 0)) else 0)
            
            # Use campaign_budget parameter if provided, otherwise use data budget
            # This allows overriding the actual portfolio budget for pacing calculations
            # When campaign_budget is provided, use it as the portfolio_budget for display
            portfolio_budget = campaign_budget if campaign_budget is not None else total_budget_from_data
            
            # Calculate spend percentage based on the budget we're using
            spend_percentage = (total_spend / portfolio_budget * 100) if portfolio_budget > 0 else 0
            
            insights['budget_status'] = {
                'portfolio_budget': round(portfolio_budget, 2),
                'spent_budget': round(total_spend, 2),
                'remaining_budget': round(portfolio_budget - total_spend, 2),
                'spend_percentage': round(spend_percentage, 2)
            }
            
            # Calculate "should have spent" based on days elapsed
            if campaign_start and campaign_end and campaign_budget:
                start_dt = datetime.strptime(campaign_start, '%Y-%m-%d')
                end_dt = datetime.strptime(campaign_end, '%Y-%m-%d')
                today = datetime.now().date()
                
                total_days = (end_dt.date() - start_dt.date()).days + 1
                days_passed = max(0, (today - start_dt.date()).days + 1)
                
                if days_passed > 0 and total_days > 0:
                    should_have_spent = (campaign_budget / total_days) * days_passed
                    insights['budget_status']['should_have_spent'] = round(should_have_spent, 2)
                    
                    # Budget projection
                    if days_passed > 0:
                        daily_rate = total_spend / days_passed
                        remaining_days = max(0, (end_dt.date() - today).days + 1)
                        if remaining_days > 0:
                            projected_total = total_spend + (daily_rate * remaining_days)
                            budget_projection = (projected_total / campaign_budget) * 100 if campaign_budget > 0 else 0
                            insights['budget_status']['budget_projection'] = round(budget_projection, 2)
        except Exception as e:
            # Fallback if DataFrame access fails
            pass
    
    # Timeline Insights
    if campaign_start and campaign_end:
        start_dt = datetime.strptime(campaign_start, '%Y-%m-%d')
        end_dt = datetime.strptime(campaign_end, '%Y-%m-%d')
        today = datetime.now().date()
        
        total_days = (end_dt.date() - start_dt.date()).days + 1
        days_passed = max(0, (today - start_dt.date()).days + 1)
        days_left = max(0, (end_dt.date() - today).days + 1)
        
        insights['timeline'] = {
            'start_date': campaign_start,
            'end_date': campaign_end,
            'today': today.strftime('%Y-%m-%d'),
            'total_days': total_days,
            'days_passed': days_passed,
            'days_left': days_left
        }
    
    # Daily Pacing Insights
    if campaign_start and campaign_end and campaign_budget:
        start_dt = datetime.strptime(campaign_start, '%Y-%m-%d')
        end_dt = datetime.strptime(campaign_end, '%Y-%m-%d')
        today = datetime.now().date()
        
        total_days = (end_dt.date() - start_dt.date()).days + 1
        days_passed = max(0, (today - start_dt.date()).days + 1)
        days_left = max(0, (end_dt.date() - today).days + 1)
        
        # Target daily rate (constant)
        target_daily_rate = campaign_budget / total_days if total_days > 0 else 0
        
        # Actual daily rate (from portfolio_total)
        if portfolio_total is not None and not portfolio_total.empty:
            try:
                row = portfolio_total.iloc[0]
                total_spend = float(row.get('total_spend', 0) if pd.notna(row.get('total_spend', 0)) else 0)
                actual_daily_rate = total_spend / days_passed if days_passed > 0 else 0
                
                # Required daily rate (catch-up rate)
                # Use portfolio_budget from insights (which uses campaign_budget if provided)
                effective_budget = insights.get('budget_status', {}).get('portfolio_budget', campaign_budget)
                remaining_budget = effective_budget - total_spend
                required_daily_rate = remaining_budget / days_left if days_left > 0 else 0
                
                # Pacing status
                if actual_daily_rate >= target_daily_rate * 0.95:  # Within 5% of target
                    pacing_status = "ON_TRACK"
                elif actual_daily_rate >= target_daily_rate * 0.80:  # Within 20% of target
                    pacing_status = "SLIGHTLY_BEHIND"
                else:
                    pacing_status = "BEHIND"
                
                insights['daily_pacing'] = {
                    'target_daily_rate': round(target_daily_rate, 2),
                    'actual_daily_rate': round(actual_daily_rate, 2),
                    'required_daily_rate': round(required_daily_rate, 2),
                    'pacing_status': pacing_status,
                    'budget_projection': insights.get('budget_status', {}).get('budget_projection', 0)
                }
            except Exception:
                pass
    
    # Portfolio Daily Trend (for chart visualization)
    if portfolio_daily is not None and not portfolio_daily.empty:
        try:
            daily_trend = []
            for _, row in portfolio_daily.iterrows():
                date_val = row.get('date', '')
                spend_val = row.get('spend', 0)
                impressions_val = row.get('impressions', 0)
                
                daily_trend.append({
                    'date': str(date_val) if pd.notna(date_val) else '',
                    'spend': float(spend_val) if pd.notna(spend_val) else 0.0,
                    'impressions': int(impressions_val) if pd.notna(impressions_val) else 0
                })
            insights['daily_trend'] = daily_trend
        except Exception:
            pass
    
    return insights
