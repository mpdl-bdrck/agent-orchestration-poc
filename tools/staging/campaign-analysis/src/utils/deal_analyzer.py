#!/usr/bin/env python3
"""
Deal Analyzer - Enhanced with Diagnostic Engine
===============================================

Analyzes BidSwitch deal performance with comprehensive diagnostics.
Uses enhanced diagnostic engine for root cause analysis.
"""

import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))
from bidswitch_client import BidSwitchClient
from enhanced_diagnostics import EnhancedDealDiagnostics, format_diagnosis_report


class DealAnalyzer:
    """Enhanced deal analyzer with comprehensive diagnostics"""
    
    def __init__(self, deal_id: str):
        self.deal_id = deal_id
        
        # Initialize BidSwitch components
        self.bidswitch_client = BidSwitchClient()
        self.diagnostics_engine = EnhancedDealDiagnostics(self.bidswitch_client)
    
    def run_analysis(self) -> Dict[str, Any]:
        """
        Run comprehensive deal analysis with enhanced diagnostics
        """
        print(f"🔍 Enhanced BidSwitch Deal Analysis for Deal {self.deal_id}")
        print("=" * 70)
        
        try:
            # Run enhanced diagnostics
            diagnosis = self.diagnostics_engine.diagnose_deal(self.deal_id)
            
            # Format results with comprehensive performance summary
            results = {
                'deal_id': self.deal_id,
                'analysis_timestamp': datetime.now().isoformat(),
                
                # Diagnosis section
                'diagnosis': {
                    'primary_issue': diagnosis.primary_issue,
                    'severity': diagnosis.severity,
                    'confidence': diagnosis.confidence,
                    'symptoms': diagnosis.symptoms,
                    'root_causes': diagnosis.root_causes,
                    'recommended_actions': diagnosis.recommended_actions
                },
                
                # Performance summary (easily accessible)
                'performance_summary': self._extract_performance_summary(diagnosis.supporting_data),
                
                # Deal configuration summary
                'deal_configuration': self._extract_deal_config(diagnosis.supporting_data),
                
                # Complete supporting data
                'supporting_data': diagnosis.supporting_data,
                'status': 'SUCCESS'
            }
            
            # Print formatted report
            print(format_diagnosis_report(diagnosis))
            
        except Exception as e:
            print(f"❌ Analysis failed for deal {self.deal_id}: {e}")
            results = {
                'deal_id': self.deal_id,
                'analysis_timestamp': datetime.now().isoformat(),
                'error': str(e),
                'status': 'ERROR'
            }
        
        # Save results
        self._save_results(results)
        
        return results
    
    def _save_results(self, results: Dict[str, Any]):
        """Save results to reports directory"""
        import os
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        output_file = f"{reports_dir}/deal_{self.deal_id}_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Analysis saved to: {output_file}")
    
    def _extract_performance_summary(self, supporting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key performance metrics for easy access"""
        summary = {
            'api_data_available': 'performance' in supporting_data and 'performance_error' not in supporting_data,
            'deal_active_status': supporting_data.get('deal_exists_in_sync', False),
            'ssp_name': supporting_data.get('ssp_name_external', supporting_data.get('ssp_name', 'Unknown'))
        }
        
        if summary['api_data_available']:
            # Performance metrics
            summary.update({
                'bid_requests': supporting_data.get('bid_requests', 0),
                'yes_bids': supporting_data.get('yes_bids', 0),
                'impressions': supporting_data.get('impressions', 0),
                'spend_usd': supporting_data.get('spend', 0),
                'average_floor_price': supporting_data.get('avg_floor', 0),
                'bid_response_rate_percent': supporting_data.get('bid_response_rate', 0),
                'win_rate_percent': supporting_data.get('win_rate', 0),
                'tech_win_rate': supporting_data.get('tech_win_rate', 0),
                'private_auction': supporting_data.get('private_auction', False)
            })
        else:
            # No performance data available
            error_msg = supporting_data.get('performance_error', 'Performance data not available')
            summary['performance_error'] = error_msg
            
        return summary
    
    def _extract_deal_config(self, supporting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract deal configuration details for easy access"""
        config = {
            'deal_exists_in_sync_api': supporting_data.get('deal_exists_in_sync', False),
            'deal_status': supporting_data.get('deal_status', 'Unknown')
        }
        
        if config['deal_exists_in_sync_api']:
            # Deal configuration from Deals Sync API
            config.update({
                'ssp_name': supporting_data.get('ssp_name', 'Unknown'),
                'creation_date': supporting_data.get('creation_date'),
                'start_time': supporting_data.get('start_time'),
                'end_time': supporting_data.get('end_time'),
                'price': supporting_data.get('price'),
                'currency': supporting_data.get('currency', 'USD'),
                'dsp_status': supporting_data.get('dsp_status', 'Unknown'),
                'ssp_status': supporting_data.get('ssp_status', 'Unknown'),
                'contract_type': 'Unknown',  # Could extract from deal_sync data
                'creative_type': 'Unknown'   # Could extract from deal_sync data
            })
            
            # Extract additional details from deal_sync if available
            deal_sync = supporting_data.get('deal_sync', {})
            if deal_sync.get('deals'):
                deal_info = deal_sync['deals'][0]
                config['contract_type'] = deal_info.get('contract_type', 'Unknown')
                
                revisions = deal_info.get('revisions', [])
                if revisions:
                    latest_revision = revisions[-1]
                    config['creative_type'] = latest_revision.get('creative_type', 'Unknown')
                    config['display_name'] = latest_revision.get('display_name', 'Unknown')
                    config['inventory_source'] = latest_revision.get('inventory_source', [])
                    
        return config


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Enhanced BidSwitch Deal Analysis Tool')
    parser.add_argument('deal_id', help='Deal ID to analyze')
    
    args = parser.parse_args()
    
    try:
        analyzer = DealAnalyzer(args.deal_id)
        results = analyzer.run_analysis()
        
        if results['status'] == 'SUCCESS':
            diagnosis = results['diagnosis']
            print(f"\n✅ Enhanced deal analysis completed!")
            print(f"🎯 Primary Issue: {diagnosis['primary_issue']} ({diagnosis['severity']})")
            print(f"🎯 Confidence: {diagnosis['confidence']:.0%}")
            return 0
        else:
            print(f"\n❌ Enhanced deal analysis failed!")
            return 1
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())