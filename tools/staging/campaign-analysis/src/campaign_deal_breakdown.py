#!/usr/bin/env python3
"""
Campaign Deal Breakdown Analyzer
===============================

Provides detailed breakdown of deals, curation packages, and line items
for a specific campaign. Shows the many-to-many relationships and explains
why we see duplicate deals in campaign analysis.

Usage: python campaign_deal_breakdown.py <campaign_id>
Example: python campaign_deal_breakdown.py 89
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

# Add shared directory to path for database_connector  
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from database_connector import DatabaseConnector


class CampaignDealBreakdown:
    """Analyzes the complex relationships between campaigns, line items, curation packages, and deals"""
    
    def __init__(self):
        """Initialize with shared database connector"""
        self.db = DatabaseConnector()
        
    def analyze_campaign_structure(self, campaign_id: str) -> Dict[str, Any]:
        """
        Comprehensive analysis of campaign structure showing all relationships
        """
        print(f"\n🔍 Campaign Deal Breakdown Analysis: {campaign_id}")
        print("=" * 80)
        
        # Step 1: Get campaign info
        campaign_info = self._get_campaign_info(campaign_id)
        
        # Step 2: Get line items
        line_items = self._get_line_items(campaign_id)
        
        # Step 3: Get curation packages
        curation_packages = self._get_curation_packages(line_items)
        
        # Step 4: Get deals with full relationships
        deal_relationships = self._get_deal_relationships(line_items)
        
        # Step 5: Analyze the structure
        analysis = self._analyze_relationships(campaign_info, line_items, curation_packages, deal_relationships)
        
        return analysis
        
    def _get_campaign_info(self, campaign_id: str) -> Dict[str, Any]:
        """Get basic campaign information"""
        print(f"\n📋 STEP 1: Campaign Information")
        print("-" * 40)
        
        campaign_query = '''
            SELECT "campaignId", "campaignUuid", "name", "startDate", "endDate", 
                   "totalBudget", "statusId"
            FROM "campaigns" 
            WHERE "campaignId" = %s
        '''
        
        results = self.db.execute_postgres_query(campaign_query, (int(campaign_id),))
        if not results:
            raise ValueError(f"Campaign {campaign_id} not found")
            
        row = results[0]
        campaign_info = {
            'campaign_id': row[0],
            'campaign_uuid': row[1], 
            'name': row[2],
            'start_date': row[3].isoformat() if row[3] else None,
            'end_date': row[4].isoformat() if row[4] else None,
            'budget': float(row[5]) if row[5] else 0.0,
            'status_id': row[6]
        }
        
        print(f"✅ Campaign: {campaign_info['name']}")
        print(f"   Budget: ${campaign_info['budget']:,.2f}")
        print(f"   Status: {campaign_info['status_id']}")
        
        return campaign_info
        
    def _get_line_items(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Get all line items for the campaign"""
        print(f"\n📊 STEP 2: Line Items Discovery")
        print("-" * 40)
        
        line_items_query = '''
            SELECT "lineItemId", "lineItemUuid", "name", "statusId", "curationPackageId",
                   "startDate", "endDate", "totalBudget"
            FROM "lineItems" 
            WHERE "campaignId" = %s
            ORDER BY "lineItemId"
        '''
        
        results = self.db.execute_postgres_query(line_items_query, (int(campaign_id),))
        
        line_items = []
        for row in results:
            line_item = {
                'line_item_id': row[0],
                'line_item_uuid': row[1],
                'name': row[2],
                'status_id': row[3],
                'curation_package_id': row[4],
                'start_date': row[5].isoformat() if row[5] else None,
                'end_date': row[6].isoformat() if row[6] else None,
                'budget': float(row[7]) if row[7] else 0.0
            }
            line_items.append(line_item)
            
        print(f"✅ Found {len(line_items)} line items")
        for li in line_items:
            print(f"   • {li['line_item_id']}: {li['name']} (Package: {li['curation_package_id']})")
            
        return line_items
        
    def _get_curation_packages(self, line_items: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """Get curation package details"""
        print(f"\n📦 STEP 3: Curation Packages Analysis")
        print("-" * 40)
        
        # Get unique curation package IDs
        package_ids = list(set([li['curation_package_id'] for li in line_items if li['curation_package_id']]))
        
        if not package_ids:
            print("⚠️  No curation packages found")
            return {}
            
        placeholders = ','.join(['%s'] * len(package_ids))
        packages_query = f'''
            SELECT "curationPackageId", "name", "includedSupplyDealIDs", "statusId"
            FROM "curationPackages"
            WHERE "curationPackageId" IN ({placeholders})
            ORDER BY "curationPackageId"
        '''
        
        results = self.db.execute_postgres_query(packages_query, package_ids)
        
        packages = {}
        for row in results:
            package_id = row[0]
            packages[package_id] = {
                'package_id': package_id,
                'name': row[1],
                'deal_ids': row[2] if row[2] else [],
                'status_id': row[3],
                'deal_count': len(row[2]) if row[2] else 0
            }
            
        print(f"✅ Found {len(packages)} curation packages")
        for pkg_id, pkg in packages.items():
            print(f"   • Package {pkg_id}: {pkg['name']} ({pkg['deal_count']} deals)")
            
        return packages
        
    def _get_deal_relationships(self, line_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get full deal relationships with line items and packages"""
        print(f"\n🔗 STEP 4: Deal Relationships Mapping")
        print("-" * 40)
        
        line_item_ids = [str(li['line_item_id']) for li in line_items]
        line_item_ids_str = ','.join(line_item_ids)
        
        # Comprehensive query showing all relationships
        relationships_query = f'''
            SELECT l."lineItemId", l."name" as line_item_name,
                   l."curationPackageId", cp."name" as package_name,
                   d."sspDealID", d."sspID", s."name" as ssp_name, 
                   d."dealId", d."statusId" as deal_status_id
            FROM "lineItems" l
            JOIN "curationPackages" cp ON cp."curationPackageId" = l."curationPackageId"
            JOIN (
              SELECT cp."curationPackageId",
                     UNNEST(cp."includedSupplyDealIDs") as "dealId"
              FROM "curationPackages" cp
            ) c ON c."curationPackageId" = l."curationPackageId"
            JOIN "deals" d ON d."dealId" = c."dealId"
            JOIN "ssps" s ON s."sspId" = d."sspID"
            WHERE l."lineItemId" IN ({line_item_ids_str})
            ORDER BY l."lineItemId", d."sspDealID"
        '''
        
        results = self.db.execute_postgres_query(relationships_query)
        
        relationships = []
        for row in results:
            relationship = {
                'line_item_id': row[0],
                'line_item_name': row[1],
                'curation_package_id': row[2],
                'package_name': row[3],
                'ssp_deal_id': row[4],
                'ssp_id': row[5],
                'ssp_name': row[6],
                'deal_id': row[7],
                'deal_status_id': row[8]
            }
            relationships.append(relationship)
            
        print(f"✅ Found {len(relationships)} deal-line item relationships")
        
        return relationships
        
    def _analyze_relationships(self, campaign_info: Dict[str, Any], 
                             line_items: List[Dict[str, Any]], 
                             curation_packages: Dict[int, Dict[str, Any]], 
                             deal_relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze and summarize the complex relationships"""
        print(f"\n📈 STEP 5: Relationship Analysis")
        print("-" * 40)
        
        # Group relationships by various dimensions
        deals_by_line_item = defaultdict(list)
        line_items_by_deal = defaultdict(list)
        deals_by_package = defaultdict(set)
        packages_by_deal = defaultdict(set)
        
        unique_deals = set()
        unique_ssps = set()
        
        for rel in deal_relationships:
            deals_by_line_item[rel['line_item_id']].append(rel)
            line_items_by_deal[rel['ssp_deal_id']].append(rel)
            deals_by_package[rel['curation_package_id']].add(rel['ssp_deal_id'])
            packages_by_deal[rel['ssp_deal_id']].add(rel['curation_package_id'])
            unique_deals.add(rel['ssp_deal_id'])
            unique_ssps.add(rel['ssp_name'])
            
        # Calculate duplicates
        deal_frequency = defaultdict(int)
        for rel in deal_relationships:
            deal_frequency[rel['ssp_deal_id']] += 1
            
        duplicated_deals = {deal_id: count for deal_id, count in deal_frequency.items() if count > 1}
        
        analysis = {
            'campaign_info': campaign_info,
            'summary': {
                'total_line_items': len(line_items),
                'total_curation_packages': len(curation_packages),
                'total_relationships': len(deal_relationships),
                'unique_deals': len(unique_deals),
                'unique_ssps': len(unique_ssps),
                'duplicated_deals': len(duplicated_deals),
                'duplication_ratio': len(deal_relationships) / len(unique_deals) if unique_deals else 0
            },
            'line_items': line_items,
            'curation_packages': curation_packages,
            'deal_relationships': deal_relationships,
            'analysis': {
                'deals_by_line_item': dict(deals_by_line_item),
                'line_items_by_deal': dict(line_items_by_deal),
                'deals_by_package': {k: list(v) for k, v in deals_by_package.items()},
                'packages_by_deal': {k: list(v) for k, v in packages_by_deal.items()},
                'deal_frequency': dict(deal_frequency),
                'duplicated_deals': duplicated_deals,
                'unique_deals': list(unique_deals),
                'unique_ssps': list(unique_ssps)
            }
        }
        
        # Print summary
        print(f"✅ Analysis Complete:")
        print(f"   📊 {len(line_items)} line items")
        print(f"   📦 {len(curation_packages)} curation packages")  
        print(f"   🔗 {len(deal_relationships)} total relationships")
        print(f"   🎯 {len(unique_deals)} unique deals")
        print(f"   🏢 {len(unique_ssps)} unique SSPs")
        print(f"   🔄 {len(duplicated_deals)} deals appear multiple times")
        print(f"   📈 {analysis['summary']['duplication_ratio']:.1f}x average duplication")
        
        return analysis
        
    def generate_breakdown_report(self, analysis: Dict[str, Any]) -> str:
        """Generate detailed breakdown report"""
        print(f"\n📄 STEP 6: Generating Detailed Report")
        print("-" * 40)
        
        campaign_id = analysis['campaign_info']['campaign_id']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"../reports/campaign_{campaign_id}_deal_breakdown.json"
        
        # Ensure reports directory exists
        os.makedirs("../reports", exist_ok=True)
        
        # Save detailed JSON report
        with open(filename, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
            
        file_size = os.path.getsize(filename)
        print(f"✅ Detailed report saved: {filename} ({file_size:,} bytes)")
        
        # Generate human-readable summary
        self._print_human_readable_summary(analysis)
        
        return filename
        
    def _print_human_readable_summary(self, analysis: Dict[str, Any]):
        """Print human-readable summary of the analysis"""
        print(f"\n" + "=" * 80)
        print(f"📋 CAMPAIGN DEAL BREAKDOWN SUMMARY")
        print(f"=" * 80)
        
        campaign = analysis['campaign_info']
        summary = analysis['summary']
        
        print(f"\n🎯 CAMPAIGN: {campaign['name']}")
        print(f"   ID: {campaign['campaign_id']}")
        print(f"   Budget: ${campaign['budget']:,.2f}")
        
        print(f"\n📊 STRUCTURE OVERVIEW:")
        print(f"   • Line Items: {summary['total_line_items']}")
        print(f"   • Curation Packages: {summary['total_curation_packages']}")
        print(f"   • Unique Deals: {summary['unique_deals']}")
        print(f"   • Total Relationships: {summary['total_relationships']}")
        print(f"   • Duplication Factor: {summary['duplication_ratio']:.1f}x")
        
        print(f"\n🔄 DUPLICATION ANALYSIS:")
        duplicated_deals = analysis['analysis']['duplicated_deals']
        if duplicated_deals:
            print(f"   {len(duplicated_deals)} deals appear multiple times:")
            for deal_id, count in sorted(duplicated_deals.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   • {deal_id}: {count} times")
            if len(duplicated_deals) > 10:
                print(f"   ... and {len(duplicated_deals) - 10} more")
        else:
            print(f"   No duplicated deals found")
            
        print(f"\n🏢 SSP BREAKDOWN:")
        for ssp in analysis['analysis']['unique_ssps']:
            ssp_deals = [r for r in analysis['deal_relationships'] if r['ssp_name'] == ssp]
            unique_ssp_deals = len(set([r['ssp_deal_id'] for r in ssp_deals]))
            print(f"   • {ssp}: {unique_ssp_deals} unique deals ({len(ssp_deals)} relationships)")
            
        print(f"\n📦 CURATION PACKAGE DETAILS:")
        for pkg_id, pkg in analysis['curation_packages'].items():
            line_items_using_pkg = [li for li in analysis['line_items'] if li['curation_package_id'] == pkg_id]
            print(f"   • Package {pkg_id}: {pkg['name']}")
            print(f"     - {pkg['deal_count']} deals")
            print(f"     - Used by {len(line_items_using_pkg)} line items")


def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python campaign_deal_breakdown.py <campaign_id>")
        print("Example: python campaign_deal_breakdown.py 89")
        sys.exit(1)
    
    campaign_id = sys.argv[1]
    
    try:
        analyzer = CampaignDealBreakdown()
        analysis = analyzer.analyze_campaign_structure(campaign_id)
        report_file = analyzer.generate_breakdown_report(analysis)
        
        print(f"\n🎉 Campaign Deal Breakdown Complete!")
        print(f"📁 Detailed report: {report_file}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
