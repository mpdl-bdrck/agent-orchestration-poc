#!/usr/bin/env python3
"""
Deal Performance Analyzer
==========================

Analyzes deal performance data and implements the 3-step verification process.
Extracted from bidswitch_deal_verifier.py for modularity.
"""

from datetime import datetime
from typing import Dict, List, Any
from bidswitch_client import BidSwitchClient


class DealPerformanceAnalyzer:
    """Analyzes deal performance using BidSwitch data"""
    
    def __init__(self, bidswitch_client: BidSwitchClient):
        self.bidswitch_client = bidswitch_client
    
    def verify_deal_performance(self, deal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: Verify individual deal performance using BidSwitch API
        Implements the exact 3-step check process from the agent prompt
        """
        
        # Handle date range - use provided dates or default to recent period
        if 'line_item_start_date' in deal and 'line_item_end_date' in deal:
            start_date = deal['line_item_start_date'].strftime('%Y-%m-%d')
            end_date = deal['line_item_end_date'].strftime('%Y-%m-%d')
        else:
            # For direct deal analysis, use a recent 30-day period
            from datetime import timedelta
            today = datetime.now().date()
            start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        
        # Ensure end_date is not in the future
        today = datetime.now().date()
        if datetime.strptime(end_date, '%Y-%m-%d').date() > today:
            end_date = today.strftime('%Y-%m-%d')
        
        print(f"   Checking deal {deal['ssp_deal_id']} ({start_date} to {end_date})...")
        
        try:
            # Get performance data from BidSwitch API with date range
            api_data = self.bidswitch_client.get_deal_performance(
                deal['ssp_deal_id'], start_date, end_date
            )
            
            # Handle real BidSwitch API response structure from data-sources.md
            # Response format: {"deals": [...], "total": {"dsp_bid_requests": 5803200, ...}}
            total_data = api_data.get('total', {})
            deals_data = api_data.get('deals', [])
            
            # Extract metrics from real API response structure
            bid_requests = total_data.get('dsp_bid_requests', 0)
            yes_bids = total_data.get('dsp_yes_bids', 0)
            impressions = total_data.get('imps', 0)
            avg_bid_floor = total_data.get('average_bidfloor', 0.0)
            spend = total_data.get('dsp_final_price_usd', 0.0)
            
            # Get SSP name from deals array if available
            ssp_name = deals_data[0].get('name_external', 'Unknown') if deals_data else 'Unknown'
            
            # Calculate rates
            fill_rate = (impressions / bid_requests * 100) if bid_requests > 0 else 0.0
            win_rate = (impressions / yes_bids * 100) if yes_bids > 0 else 0.0
            tech_win_rate = total_data.get('tech_win_rate', 0.0)
            
            # Perform the 3-step verification process
            issues, actions, status = self._analyze_performance_metrics(
                bid_requests, yes_bids, impressions, win_rate, avg_bid_floor
            )
            
            return {
                **deal,
                'ssp_name_external': ssp_name,
                'bid_requests': bid_requests,
                'yes_bids': yes_bids,
                'impressions': impressions,
                'spend_usd': spend,
                'avg_bid_floor': avg_bid_floor,
                'fill_rate': round(fill_rate, 4),
                'win_rate': round(win_rate, 4),
                'tech_win_rate': round(tech_win_rate * 100, 4),  # Convert to percentage
                'status': status,
                'issues': issues,
                'actions': actions,
                'api_response_received': True
            }
            
        except Exception as e:
            return self._create_error_result(deal, f"Performance analysis error: {e}")
    
    def _analyze_performance_metrics(self, bid_requests: int, yes_bids: int, 
                                   impressions: int, win_rate: float, 
                                   avg_bid_floor: float) -> tuple:
        """
        Perform the 3-step verification process:
        1. Verify bid request volume
        2. Validate bid response rate
        3. Analyze impression delivery
        """
        issues = []
        actions = []
        status = 'HEALTHY'
        
        # Check 1: Verify bid request volume
        if bid_requests == 0:
            issues.append('No bid requests received for deal')
            actions.append('Review BidSwitch targeting groups configuration')
            status = 'NO_TRAFFIC'
        elif bid_requests < 1000:  # Minimal traffic threshold
            issues.append('Low bid request volume')
            actions.append('Review BidSwitch targeting groups configuration')
            status = 'LOW_TRAFFIC'
        
        # Check 2: Validate bid response rate (only if we have traffic)
        elif yes_bids < 100:  # Low bid count threshold
            issues.append('Low bid response rate')
            actions.append('Review line item targeting configuration')
            status = 'LOW_BID_RATE'
        
        # Check 3: Analyze impression delivery (only if we're bidding)
        elif impressions == 0:
            issues.append('Low impression win rate')
            actions.append(f'Consider increasing base bid price (current floor: ${avg_bid_floor:.2f})')
            status = 'LOW_WIN_RATE'
        elif win_rate < 3.43:  # Below industry benchmark
            issues.append('Win rate below industry benchmark (3.43%)')
            actions.append('Consider optimizing bid strategy')
            status = 'BELOW_BENCHMARK'
        
        return issues, actions, status
    
    def _create_error_result(self, deal: Dict[str, Any], error_message: str) -> Dict[str, Any]:
        """Create error result for failed performance analysis"""
        return {
            **deal,
            'bid_requests': 0,
            'yes_bids': 0,
            'impressions': 0,
            'fill_rate': 0.0,
            'win_rate': 0.0,
            'status': 'ERROR',
            'issues': [error_message],
            'actions': ['Check BidSwitch connectivity and credentials']
        }
