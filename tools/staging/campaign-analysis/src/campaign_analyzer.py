#!/usr/bin/env python3
"""
Campaign Analyzer - Main Orchestrator
=====================================

Simple 3-step workflow that coordinates campaign analysis using proven components.
REAL DATA ONLY - no fake test data ever.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from campaign_discovery import CampaignDiscovery
from campaign_diagnostics import CampaignDiagnostics
from campaign_deal_breakdown import CampaignDealBreakdown


class CampaignAnalyzer:
    """
    Main orchestrator - dead simple 3-step workflow
    Builds on proven components, focuses on real business value
    """
    
    def __init__(self, campaign_id: str):
        """Initialize with campaign ID"""
        self.campaign_id = campaign_id
        self.discovery = CampaignDiscovery()
        self.diagnostics = CampaignDiagnostics()
        self.deal_breakdown = CampaignDealBreakdown()
        
    def run_analysis(self) -> Dict[str, Any]:
        """
        Campaign-focused workflow:
        1. Discover campaign data (PostgreSQL + Redshift)
        2. Analyze campaign structure and deal relationships (leverage deal breakdown)
        3. Run campaign-level diagnostics only (no individual deal analysis)
        4. Generate report for agent decision-making
        """
        print(f"\n🔍 Campaign Analysis: {self.campaign_id}")
        print("=" * 60)
        
        try:
            # Step 1: Discover campaign data and structure
            print("\n📊 STEP 1: Discovering campaign data and structure...")
            print("-" * 40)

            campaign_info = self.discovery.get_campaign_info(self.campaign_id)
            deals = self.discovery.discover_deals(self.campaign_id)
            spend_data = self.discovery.get_spend_data(
                campaign_info['campaign_uuid'],
                campaign_info['budget']
            )

            # Step 2: Analyze campaign structure and relationships
            print("\n🔗 STEP 2: Analyzing campaign structure...")
            print("-" * 40)

            campaign_structure = self.deal_breakdown.analyze_campaign_structure(self.campaign_id)

            print(f"\n✅ Campaign Analysis Complete:")
            print(f"   📋 Campaign: {campaign_info['name']}")
            print(f"   💰 Budget: ${campaign_info['budget']:,.2f}")
            print(f"   🎯 Deal Relationships: {len(deals)}")
            print(f"   📦 Curation Packages: {campaign_structure.get('total_packages', 0)}")
            print(f"   🎨 Line Items: {campaign_structure.get('total_line_items', 0)}")
            print(f"   🔄 Duplication Factor: {campaign_structure.get('duplication_factor', 0):.1f}x")
            
            # Step 3: Run campaign-level diagnostics only
            print(f"\n🔍 STEP 3: Running campaign diagnostics...")
            print("-" * 40)

            # Check for campaign-level issues (status, budget, dates, etc.)
            campaign_issues = self.diagnostics.check_campaign_level_issues(campaign_info, campaign_structure)

            # Calculate campaign health based on campaign-level factors only
            campaign_health = self.diagnostics.calculate_campaign_health(campaign_info, campaign_structure, campaign_issues)

            print(f"\n✅ Campaign Diagnostics Complete:")
            print(f"   📊 Campaign Health: {campaign_health}")
            print(f"   🚨 Issues Found: {len(campaign_issues)}")

            # Step 4: Generate agent-ready report
            print(f"\n📄 STEP 4: Generating agent report...")
            print("-" * 40)

            results = self._generate_agent_report(
                campaign_info, campaign_structure, spend_data,
                campaign_issues, campaign_health
            )

            # Save results
            self._save_results(results)

            print(f"\n🎉 Campaign Analysis Complete!")
            print("=" * 60)
            print(f"🎯 Campaign: {results['campaign_name']}")
            print(f"🎯 Health: {results['campaign_health']}")
            print(f"🎯 Deal Relationships: {results['total_relationships']}")
            print(f"🎯 Unique Deals: {results['unique_deals']}")
            print(f"🎯 Issues: {len(results['campaign_issues'])} campaign-level issues")

            if results['recommended_actions']:
                print(f"\n🔧 Recommended Actions:")
                for i, action in enumerate(results['recommended_actions'][:3], 1):
                    print(f"   {i}. {action}")

            return results

        except Exception as e:
            print(f"\n❌ Campaign analysis failed: {e}")
            # Return minimal error result
            return {
                "campaign_id": int(self.campaign_id),
                "campaign_name": f"Campaign {self.campaign_id}",
                "campaign_health": "ERROR",
                "analysis_timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    def _generate_agent_report(self, campaign_info: Dict[str, Any], campaign_structure: Dict[str, Any],
                              spend_data: Dict[str, Any], campaign_issues: List[Dict[str, Any]],
                              campaign_health: str) -> Dict[str, Any]:
        """
        Generate agent-ready report with deal identification for downstream debugging
        """
        # Extract deal information for agent decision-making
        unique_deals = []
        deal_relationships = []

        for package in campaign_structure.get('packages', []):
            for deal in package.get('deals', []):
                deal_id = deal.get('deal_id')
                if deal_id and deal_id not in unique_deals:
                    unique_deals.append(deal_id)

                deal_relationships.append({
                    'deal_id': deal_id,
                    'package_name': package.get('package_name'),
                    'line_item_count': len(package.get('line_items', [])),
                    'deal_status': deal.get('status'),
                    'ssp': deal.get('ssp_name')
                })

        # Calculate metrics
        total_relationships = len(deal_relationships)
        unique_deal_count = len(unique_deals)
        duplication_factor = total_relationships / unique_deal_count if unique_deal_count > 0 else 0

        # Generate recommendations based on campaign health
        recommendations = []
        if campaign_health == "CRITICAL":
            recommendations.append("Address critical campaign issues before deal debugging")
        elif campaign_health == "WARNING":
            recommendations.append("Review campaign settings for optimization opportunities")
        else:
            recommendations.append("Campaign healthy - proceed with targeted deal debugging")

        return {
            "campaign_id": int(self.campaign_id),
            "campaign_name": campaign_info['name'],
            "campaign_health": campaign_health,
            "analysis_timestamp": datetime.now().isoformat(),

            # Deal identification for agent decision-making
            "unique_deals": unique_deals,
            "deal_relationships": deal_relationships,
            "total_relationships": total_relationships,
            "duplication_factor": duplication_factor,

            # Campaign structure summary
            "campaign_structure": {
                "total_line_items": campaign_structure.get('total_line_items', 0),
                "total_packages": campaign_structure.get('total_packages', 0),
                "ssp_breakdown": campaign_structure.get('ssp_breakdown', {}),
                "duplication_analysis": campaign_structure.get('duplication_analysis', {})
            },

            # Campaign-level diagnostics only
            "campaign_issues": campaign_issues,

            # Agent guidance
            "agent_guidance": {
                "campaign_ready_for_deal_debugging": campaign_health in ["HEALTHY", "WARNING"],
                "deals_needing_attention": unique_deals,  # Agent can filter based on patterns
                "recommended_next_steps": recommendations
            },

            # Campaign metadata
            "campaign_data": {
                "campaign_uuid": campaign_info['campaign_uuid'],
                "budget": campaign_info['budget'],
                "start_date": campaign_info['start_date'],
                "end_date": campaign_info['end_date'],
                "status_id": campaign_info['status_id'],
                "status_name": campaign_info.get('status_name', 'Unknown'),
                "is_active": campaign_info.get('is_active', False)
            },

            "spend_analysis": spend_data,
            "recommended_actions": recommendations
        }
            
    def _save_results(self, results: Dict[str, Any]):
        """Save real results only - NO FAKE DATA EVER"""
        os.makedirs("../reports", exist_ok=True)
        
        # Clean filename based on campaign ID and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"../reports/campaign_{self.campaign_id}_analysis.json"
        
        # Ensure no fake data in output
        if any(str(key).startswith('TEST-') for key in str(results)):
            raise ValueError("FAKE DATA DETECTED! Aborting save to prevent pollution.")
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            file_size = os.path.getsize(filename)
            print(f"✅ Results saved: {filename} ({file_size:,} bytes)")
            
        except Exception as e:
            print(f"❌ Failed to save results: {e}")
            raise


def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python campaign_analyzer.py <campaign_id>")
        print("Example: python campaign_analyzer.py 89")
        sys.exit(1)
    
    campaign_id = sys.argv[1]
    
    try:
        analyzer = CampaignAnalyzer(campaign_id)
        results = analyzer.run_analysis()
        
        # Quick summary for command line
        print(f"\n📋 QUICK SUMMARY")
        print(f"   Campaign: {results['campaign_name']}")
        print(f"   Health: {results['campaign_health']}")
        unique_deals_count = len(results['unique_deals'])
        deduplication_savings = results['total_relationships'] - unique_deals_count
        print(f"   Unique Deals: {unique_deals_count}")
        print(f"   Total Relationships: {results['total_relationships']}")
        print(f"   Deduplication Savings: {deduplication_savings} analyses avoided")

        if results['campaign_issues']:
            print(f"\n🚨 ISSUES DETECTED:")
            for issue in results['campaign_issues']:
                print(f"   • {issue['description']} ({issue['severity']})")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
