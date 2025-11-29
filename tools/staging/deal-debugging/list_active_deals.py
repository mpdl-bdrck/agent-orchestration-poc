#!/usr/bin/env python3
"""
BidSwitch Active Deals Lister
==============================

Lists all currently active deals from BidSwitch Deals Sync API.
Uses the same authentication and API endpoints as the deal analysis tool.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any

# Add the shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))
from bidswitch_client import BidSwitchClient


class ActiveDealsLister:
    """Lists all active deals from BidSwitch"""
    
    def __init__(self):
        self.client = BidSwitchClient()
        
    def list_all_active_deals(self) -> Dict[str, Any]:
        """
        Get all active deals from BidSwitch Deals Sync API
        
        Returns:
            Dictionary with deals list and summary information
        """
        print("🔍 Fetching All Active Deals from BidSwitch")
        print("=" * 50)
        
        try:
            # Get DSP ID from environment
            dsp_seat_id = os.getenv('DSP_SEAT_ID')
            if not dsp_seat_id:
                raise ValueError("DSP_SEAT_ID must be configured in environment variables")
            
            # BidSwitch Deals Sync API endpoint (without deal_id parameter to get all deals)
            import requests
            api_url = f"https://my.bidswitch.com/api/v2/dsp/{dsp_seat_id}/deals/"
            
            headers = {
                "Authorization": f"Bearer {self.client.bidswitch_token}",
                "Content-Type": "application/json"
            }
            
            print(f"📡 Calling BidSwitch Deals Sync API...")
            print(f"   Endpoint: {api_url}")
            
            response = requests.get(api_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return self._process_deals_response(data)
            else:
                raise ValueError(f"BidSwitch API returned status {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Failed to fetch active deals: {e}")
            return {
                'error': str(e),
                'deals': [],
                'summary': {'total': 0, 'active': 0, 'paused': 0, 'other': 0}
            }
    
    def _process_deals_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the API response and categorize deals"""
        
        deals = data.get('deals', [])
        processed_deals = []
        
        # Counters for summary
        total_count = len(deals)
        active_count = 0
        paused_count = 0
        other_count = 0
        
        print(f"✅ Found {total_count} total deals")
        
        for deal in deals:
            # Extract basic deal info
            deal_info = {
                'deal_id': deal.get('deal_id'),
                'ssp_name': deal.get('ssp_name', 'Unknown'),
                'status': deal.get('status', 'unknown'),
                'creation_date': deal.get('creation_date'),
                'updated': deal.get('updated'),
                'contract_type': deal.get('contract_type', 'unknown'),
                'is_created_from_deals_discovery': deal.get('is_created_from_deals_discovery', False)
            }
            
            # Get latest revision details if available
            revisions = deal.get('revisions', [])
            if revisions:
                latest_revision = revisions[-1]  # Most recent revision
                deal_info.update({
                    'display_name': latest_revision.get('display_name', 'Unknown'),
                    'dsp_status': latest_revision.get('dsp_status', 'unknown'),
                    'ssp_status': latest_revision.get('ssp_status', 'unknown'),
                    'price': latest_revision.get('price', 0),
                    'currency_code': latest_revision.get('currency_code', 'USD'),
                    'creative_type': latest_revision.get('creative_type', 'unknown'),
                    'start_time': latest_revision.get('start_time'),
                    'end_time': latest_revision.get('end_time'),
                    'inventory_source': latest_revision.get('inventory_source', [])
                })
            
            # Categorize by status
            status = deal_info['status'].lower()
            if status == 'active':
                active_count += 1
            elif status == 'paused':
                paused_count += 1
            else:
                other_count += 1
            
            processed_deals.append(deal_info)
        
        # Sort deals by status (active first) and then by deal_id
        processed_deals.sort(key=lambda x: (x['status'] != 'active', x['deal_id']))
        
        summary = {
            'total': total_count,
            'active': active_count,
            'paused': paused_count,
            'other': other_count,
            'fetch_timestamp': datetime.now().isoformat()
        }
        
        # Print summary
        print(f"\n📊 Deal Summary:")
        print(f"   Total Deals: {total_count}")
        print(f"   Active: {active_count}")
        print(f"   Paused: {paused_count}")
        print(f"   Other Status: {other_count}")
        
        return {
            'deals': processed_deals,
            'summary': summary,
            'raw_response': data  # Include raw response for debugging
        }
    
    def save_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"active_deals_{timestamp}.json"
        
        # Ensure reports directory exists
        os.makedirs("../reports", exist_ok=True)
        filepath = os.path.join("../reports", filename)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Results saved to: {filepath}")
        return filepath
    
    def print_active_deals_table(self, deals: List[Dict[str, Any]]):
        """Print a formatted table of active deals"""
        active_deals = [d for d in deals if d['status'].lower() == 'active']
        
        if not active_deals:
            print("\n⚠️  No active deals found")
            return
        
        print(f"\n🟢 Active Deals ({len(active_deals)} total):")
        print("-" * 120)
        print(f"{'Deal ID':<20} {'SSP':<15} {'Display Name':<40} {'Type':<10} {'Price':<10}")
        print("-" * 120)
        
        for deal in active_deals[:20]:  # Show first 20 active deals
            deal_id = deal['deal_id'] or 'N/A'
            ssp_name = deal['ssp_name'][:14] if deal['ssp_name'] else 'Unknown'
            display_name = deal.get('display_name', 'Unknown')[:39]
            creative_type = deal.get('creative_type', 'unknown')[:9]
            price = f"${deal.get('price', 0)}"
            
            print(f"{deal_id:<20} {ssp_name:<15} {display_name:<40} {creative_type:<10} {price:<10}")
        
        if len(active_deals) > 20:
            print(f"... and {len(active_deals) - 20} more active deals")


def main():
    """Main execution function"""
    print("🚀 BidSwitch Active Deals Lister")
    print("=" * 40)
    
    # Check for help flag
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("Usage: python list_active_deals.py [--save-file filename.json]")
        print("")
        print("This tool lists all active deals from BidSwitch Deals Sync API")
        print("Options:")
        print("  --save-file FILENAME  Save results to specific filename")
        print("  --help, -h           Show this help message")
        return
    
    # Parse command line arguments
    save_filename = None
    if len(sys.argv) > 2 and sys.argv[1] == '--save-file':
        save_filename = sys.argv[2]
    
    try:
        lister = ActiveDealsLister()
        results = lister.list_all_active_deals()
        
        if 'error' in results:
            print(f"❌ Error: {results['error']}")
            sys.exit(1)
        
        # Print active deals table
        lister.print_active_deals_table(results['deals'])
        
        # Save results
        filepath = lister.save_results(results, save_filename)
        
        print(f"\n✅ Active deals listing completed!")
        print(f"📁 Results saved to: {filepath}")
        
    except Exception as e:
        print(f"❌ Failed to list active deals: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
