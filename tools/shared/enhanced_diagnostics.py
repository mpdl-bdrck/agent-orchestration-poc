#!/usr/bin/env python3
"""
Enhanced Deal Diagnostic Engine
===============================

Comprehensive BidSwitch deal diagnosis combining:
- Deals Sync API (deal status and configuration)
- Performance API (metrics and performance data)
- Troubleshooting knowledge base (diagnostic patterns)
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from bidswitch_client import BidSwitchClient


@dataclass
class DiagnosticResult:
    """Structured diagnostic result"""
    primary_issue: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    confidence: float  # 0.0 to 1.0
    symptoms: List[str]
    root_causes: List[str]
    recommended_actions: List[str]
    supporting_data: Dict[str, Any]


class EnhancedDealDiagnostics:
    """Enhanced diagnostic engine for BidSwitch deals"""
    
    def __init__(self, bidswitch_client: BidSwitchClient):
        self.client = bidswitch_client
        self.diagnostic_rules = self._load_diagnostic_rules()
    
    def diagnose_deal(self, deal_id: str) -> DiagnosticResult:
        """
        Comprehensive deal diagnosis using multiple data sources
        
        Args:
            deal_id: BidSwitch deal identifier
            
        Returns:
            DiagnosticResult with detailed diagnosis
        """
        print(f"🔍 Enhanced Diagnostic Analysis for Deal {deal_id}")
        print("=" * 60)
        
        # Step 1: Collect comprehensive data
        deal_data = self._collect_deal_data(deal_id)
        
        # Step 2: Apply diagnostic rules
        diagnosis = self._apply_diagnostic_rules(deal_data)
        
        # Step 3: Enrich with contextual analysis
        diagnosis = self._enrich_diagnosis(diagnosis, deal_data)
        
        return diagnosis
    
    def _collect_deal_data(self, deal_id: str) -> Dict[str, Any]:
        """Collect data from multiple BidSwitch APIs"""
        print("📊 Collecting comprehensive deal data...")
        
        data = {
            'deal_id': deal_id,
            'collection_timestamp': datetime.now().isoformat()
        }
        
        # 1. Check if deal exists in Deals Sync API (active deals)
        print("   🔍 Checking deal status in Deals Sync API...")
        try:
            sync_data = self._get_deal_sync_data(deal_id)
            data['deal_sync'] = sync_data
            data['deal_exists_in_sync'] = len(sync_data.get('deals', [])) > 0
            
            if data['deal_exists_in_sync']:
                deal_info = sync_data['deals'][0]
                data['deal_status'] = deal_info.get('status', 'unknown')
                data['ssp_name'] = deal_info.get('ssp_name', 'Unknown')
                data['creation_date'] = deal_info.get('creation_date')
                
                # Get latest revision info
                revisions = deal_info.get('revisions', [])
                if revisions:
                    latest_revision = revisions[-1]
                    data['dsp_status'] = latest_revision.get('dsp_status', 'unknown')
                    data['ssp_status'] = latest_revision.get('ssp_status', 'unknown')
                    data['start_time'] = latest_revision.get('start_time')
                    data['end_time'] = latest_revision.get('end_time')
                    data['price'] = latest_revision.get('price', 0)
                    data['currency'] = latest_revision.get('currency_code', 'USD')
                    data['display_name'] = latest_revision.get('display_name', '')  # Add for geographic analysis
                    
                print(f"   ✅ Deal found in Sync API - Status: {data['deal_status']}")
            else:
                print(f"   ⚠️  Deal NOT found in Deals Sync API (inactive/expired)")
                data['deal_status'] = 'INACTIVE_OR_EXPIRED'
                
        except Exception as e:
            print(f"   ❌ Deals Sync API error: {e}")
            data['deal_sync_error'] = str(e)
            data['deal_exists_in_sync'] = False
        
        # 2. Get performance data (works for both active and historical deals)
        print("   📈 Getting performance data...")
        try:
            # Use recent date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            perf_data = self.client.get_deal_performance(
                deal_id, 
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            data['performance'] = perf_data
            
            # Extract key metrics
            if 'total' in perf_data:
                total = perf_data['total']
                data['bid_requests'] = total.get('dsp_bid_requests', 0)
                data['yes_bids'] = total.get('dsp_yes_bids', 0)
                data['impressions'] = total.get('imps', 0)
                data['spend'] = total.get('dsp_final_price_usd', 0)
                data['avg_floor'] = total.get('average_bidfloor', 0)
                data['tech_win_rate'] = total.get('tech_win_rate', 0)
                
                # Calculate derived metrics
                data['bid_response_rate'] = (data['yes_bids'] / data['bid_requests'] * 100) if data['bid_requests'] > 0 else 0
                data['win_rate'] = (data['impressions'] / data['yes_bids'] * 100) if data['yes_bids'] > 0 else 0
                
                print(f"   ✅ Performance data: {data['bid_requests']} requests, {data['yes_bids']} bids, {data['impressions']} imps")
            
            # Extract SSP info from deals array
            if 'deals' in perf_data and perf_data['deals']:
                deal_perf = perf_data['deals'][0]
                data['ssp_name_external'] = deal_perf.get('name_external', 'Unknown')
                data['private_auction'] = deal_perf.get('private_auction', False)
                
        except Exception as e:
            print(f"   ❌ Performance API error: {e}")
            data['performance_error'] = str(e)
        
        return data
    
    def _get_deal_sync_data(self, deal_id: str) -> Dict[str, Any]:
        """Get deal data from Deals Sync API"""
        import requests
        import os
        
        # Get DSP ID from environment
        dsp_seat_id = os.getenv('DSP_SEAT_ID')
        if not dsp_seat_id:
            raise ValueError("DSP_SEAT_ID must be configured in environment variables")
            
        api_url = f"https://my.bidswitch.com/api/v2/dsp/{dsp_seat_id}/deals/"
        params = {"deal_id": deal_id}
        headers = {
            "Authorization": f"Bearer {self.client.bidswitch_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(api_url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise ValueError(f"Deals Sync API returned status {response.status_code}")
    
    def _apply_diagnostic_rules(self, data: Dict[str, Any]) -> DiagnosticResult:
        """Apply diagnostic rules to determine primary issue"""
        print("🧠 Applying diagnostic rules...")
        
        # Rule 1: Deal Status Issues (Highest Priority)
        if not data.get('deal_exists_in_sync', False):
            return DiagnosticResult(
                primary_issue="DEAL_INACTIVE",
                severity="CRITICAL",
                confidence=0.95,
                symptoms=["Deal not found in active deals list"],
                root_causes=[
                    "Deal has expired or been deactivated",
                    "Deal was paused or rejected by SSP/DSP",
                    "Deal configuration was removed"
                ],
                recommended_actions=[
                    "Check deal end date and extend if needed",
                    "Verify deal status with SSP",
                    "Reactivate deal if paused",
                    "Review deal configuration"
                ],
                supporting_data=data
            )
        
        # Rule 2: Deal Status Problems
        deal_status = data.get('deal_status', '').lower()
        if deal_status in ['paused', 'broken', 'rejected']:
            return self._diagnose_deal_status_issue(data)
        
        # Rule 3: Zero Bid Response (High Priority)
        bid_requests = data.get('bid_requests', 0)
        yes_bids = data.get('yes_bids', 0)
        
        if bid_requests > 0 and yes_bids == 0:
            return self._diagnose_zero_bid_response(data)
        
        # Rule 4: Low Performance Issues
        if bid_requests > 0 and yes_bids > 0:
            return self._diagnose_performance_issues(data)
        
        # Rule 5: No Traffic
        if bid_requests == 0:
            return self._diagnose_no_traffic(data)
        
        # Default: Healthy or Unknown
        return DiagnosticResult(
            primary_issue="HEALTHY" if bid_requests > 0 and yes_bids > 0 else "UNKNOWN",
            severity="LOW",
            confidence=0.5,
            symptoms=["No clear issues detected"],
            root_causes=["Deal appears to be functioning normally"],
            recommended_actions=["Continue monitoring performance"],
            supporting_data=data
        )
    
    def _diagnose_deal_status_issue(self, data: Dict[str, Any]) -> DiagnosticResult:
        """Diagnose deal status-related issues"""
        deal_status = data.get('deal_status', '').lower()
        dsp_status = data.get('dsp_status', '').lower()
        ssp_status = data.get('ssp_status', '').lower()
        
        if deal_status == 'paused':
            if dsp_status == 'paused':
                root_cause = "Deal paused on DSP (buyer) side"
                actions = ["Reactivate deal in DSP platform", "Check campaign/line item status"]
            elif ssp_status == 'paused':
                root_cause = "Deal paused on SSP (supplier) side"
                actions = ["Contact SSP to reactivate deal", "Check deal terms compliance"]
            else:
                root_cause = "Deal paused (status unclear)"
                actions = ["Check both DSP and SSP deal status", "Contact BidSwitch support"]
            
            return DiagnosticResult(
                primary_issue="DEAL_PAUSED",
                severity="HIGH",
                confidence=0.9,
                symptoms=[f"Deal status: {deal_status}", f"DSP status: {dsp_status}", f"SSP status: {ssp_status}"],
                root_causes=[root_cause],
                recommended_actions=actions,
                supporting_data=data
            )
        
        elif deal_status == 'broken':
            return DiagnosticResult(
                primary_issue="DEAL_BROKEN",
                severity="CRITICAL",
                confidence=0.95,
                symptoms=["Deal marked as broken in BidSwitch"],
                root_causes=[
                    "Deal configuration error",
                    "SSP/DSP integration issue",
                    "Protocol compliance problem"
                ],
                recommended_actions=[
                    "Check deal configuration for errors",
                    "Verify SSP integration status",
                    "Contact BidSwitch support for details",
                    "Review bid response compliance"
                ],
                supporting_data=data
            )
        
        elif deal_status == 'rejected':
            return DiagnosticResult(
                primary_issue="DEAL_REJECTED",
                severity="HIGH",
                confidence=0.9,
                symptoms=["Deal rejected by one or both parties"],
                root_causes=[
                    "Deal terms not acceptable to buyer/seller",
                    "Negotiation failed",
                    "Compliance issues"
                ],
                recommended_actions=[
                    "Review deal terms and negotiate changes",
                    "Contact counterparty for rejection reason",
                    "Create new deal with revised terms"
                ],
                supporting_data=data
            )
        
        return DiagnosticResult(
            primary_issue="DEAL_STATUS_ISSUE",
            severity="MEDIUM",
            confidence=0.7,
            symptoms=[f"Unusual deal status: {deal_status}"],
            root_causes=["Deal status indicates potential issue"],
            recommended_actions=["Investigate deal status with BidSwitch"],
            supporting_data=data
        )
    
    def _diagnose_zero_bid_response(self, data: Dict[str, Any]) -> DiagnosticResult:
        """Diagnose zero bid response issues with enhanced geographic and BidSwitch pattern analysis"""
        bid_requests = data.get('bid_requests', 0)
        avg_floor = data.get('avg_floor', 0)
        ssp_name = data.get('ssp_name_external', 'Unknown')
        display_name = data.get('display_name', '')
        
        # Enhanced analysis with geographic detection
        geographic_analysis = self._analyze_geographic_targeting(display_name, data)
        bidswitch_pattern = self._identify_bidswitch_troubleshooting_pattern(data, geographic_analysis)
        
        # Check for bid floor issues first (higher priority)
        if avg_floor > 10:  # High floor price threshold
            return DiagnosticResult(
                primary_issue="BID_BELOW_FLOOR",
                severity="HIGH",
                confidence=0.85,
                symptoms=[
                    f"{bid_requests:,} bid requests received",
                    "Zero bid responses sent",
                    f"High average floor price: ${avg_floor:.2f}",
                    f"SSP: {ssp_name}"
                ],
                root_causes=[
                    f"Bid prices below floor price (${avg_floor:.2f})",
                    "Bidding strategy too conservative for this inventory",
                    "Floor price set too high by supplier",
                    "BidSwitch fee not accounted for in bidding"
                ],
                recommended_actions=[
                    f"Increase base bid prices above ${avg_floor:.2f}",
                    "Review bidding strategy and profit margins",
                    "Negotiate lower floor prices with supplier",
                    "Check campaign budget allocation and pacing",
                    "Account for BidSwitch fees in bid calculation"
                ],
                supporting_data={
                    **data,
                    'geographic_analysis': geographic_analysis,
                    'bidswitch_pattern': bidswitch_pattern,
                    'diagnostic_details': {
                        'primary_trigger': 'high_floor_price',
                        'floor_threshold': 10.0,
                        'actual_floor': avg_floor
                    }
                }
            )
        
        # Geographic targeting mismatch analysis
        if geographic_analysis['likely_geographic_issue']:
            return DiagnosticResult(
                primary_issue="GEOGRAPHIC_TARGETING_MISMATCH",
                severity="CRITICAL",
                confidence=geographic_analysis['confidence'],
                symptoms=[
                    f"{bid_requests:,} bid requests received",
                    "Zero bid responses sent (100% filtered)",
                    f"Deal geography: {geographic_analysis['detected_geography']}",
                    f"SSP: {ssp_name}",
                    "BidSwitch pattern: 'Failed DSP Geo targeting'"
                ],
                root_causes=[
                    f"Deal sends traffic from {geographic_analysis['detected_geography']} regions",
                    f"Current targeting groups only cover: {', '.join(geographic_analysis['covered_regions'])}",
                    "100% of bid requests filtered before reaching bidder",
                    "Geographic configuration mismatch in BidSwitch targeting groups",
                    geographic_analysis['specific_mismatch_reason']
                ],
                recommended_actions=[
                    f"Check deal's country breakdown in BidSwitch UI for {geographic_analysis['detected_geography']} countries",
                    f"Create targeting group for missing countries: {geographic_analysis['likely_missing_countries']}",
                    "Verify deal geography using BidSwitch Deals Discovery country filtering",
                    "Contact BidSwitch support to add missing geographic targeting",
                    "Consider using BidSwitch API for complete deal geographic metadata",
                    "Review other EMEA deals for similar geographic mismatches"
                ],
                supporting_data={
                    **data,
                    'geographic_analysis': geographic_analysis,
                    'bidswitch_pattern': bidswitch_pattern,
                    'diagnostic_details': {
                        'primary_trigger': 'geographic_mismatch',
                        'bidswitch_troubleshooting_category': 'Failed DSP Geo targeting (>50%)',
                        'filtering_stage': 'pre_bidder_targeting_groups'
                    }
                }
            )
        
        # General targeting mismatch (fallback)
        return DiagnosticResult(
            primary_issue="TARGETING_MISMATCH",
            severity="HIGH",
            confidence=0.7,
            symptoms=[
                f"{bid_requests:,} bid requests received",
                "Zero bid responses sent",
                f"SSP: {ssp_name}",
                f"Average floor price: ${avg_floor:.2f}"
            ],
            root_causes=[
                "Device/inventory type targeting conflict",
                "Audience targeting too restrictive", 
                "Deal routing configuration error",
                "Creative format mismatch",
                "Bid request filtering before reaching bidder"
            ],
            recommended_actions=[
                "Review device and inventory type targeting settings",
                "Verify audience targeting configuration",
                "Confirm deal ID routing setup in BidSwitch",
                "Check creative formats match deal requirements",
                "Test with broader targeting settings",
                "Contact BidSwitch support with bid request examples"
            ],
            supporting_data={
                **data,
                'geographic_analysis': geographic_analysis,
                'bidswitch_pattern': bidswitch_pattern,
                'diagnostic_details': {
                    'primary_trigger': 'general_targeting_mismatch',
                    'bidswitch_troubleshooting_category': 'Multiple targeting issues'
                }
            }
        )
    
    def _analyze_geographic_targeting(self, display_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze potential geographic targeting issues based on deal name and configuration"""
        
        # Geographic region detection patterns
        geographic_patterns = {
            'EMEA': {
                'regions': ['Europe', 'Middle East', 'Africa'],
                'likely_countries': ['AE', 'SA', 'ZA', 'NG', 'EG', 'KE', 'MA'],  # Middle East & Africa
                'covered_by_targeting': ['FR', 'DE', 'IT', 'ES', 'GB'],  # EU targeting group 8643
                'targeting_group': '8643 (EU only)'
            },
            'APAC': {
                'regions': ['Asia', 'Pacific', 'Australia'],
                'likely_countries': ['AU', 'JP', 'SG', 'HK', 'IN', 'TH', 'MY'],
                'covered_by_targeting': [],
                'targeting_group': 'None'
            },
            'LATAM': {
                'regions': ['Latin America', 'South America'],
                'likely_countries': ['MX', 'AR', 'CL', 'CO', 'PE'],
                'covered_by_targeting': ['BR'],  # Brazil targeting group 9000
                'targeting_group': '9000 (BR only)'
            },
            'AMERICAS': {
                'regions': ['North America', 'South America'],
                'likely_countries': ['US', 'CA', 'MX'],
                'covered_by_targeting': [],
                'targeting_group': 'None'
            },
            'EU': {
                'regions': ['European Union'],
                'likely_countries': ['FR', 'DE', 'IT', 'ES', 'GB'],
                'covered_by_targeting': ['FR', 'DE', 'IT', 'ES', 'GB'],
                'targeting_group': '8643 (EU)'
            }
        }
        
        # Detect geographic region from deal name
        detected_region = None
        for region, config in geographic_patterns.items():
            if region in display_name.upper():
                detected_region = region
                break
        
        if not detected_region:
            return {
                'likely_geographic_issue': False,
                'detected_geography': 'Unknown',
                'confidence': 0.3,
                'covered_regions': ['EU (FR,DE,IT,ES,GB)', 'Brazil'],
                'analysis': 'No clear geographic indicators in deal name'
            }
        
        region_config = geographic_patterns[detected_region]
        
        # Calculate mismatch likelihood
        likely_missing = set(region_config['likely_countries']) - set(region_config['covered_by_targeting'])
        coverage_ratio = len(region_config['covered_by_targeting']) / len(region_config['likely_countries']) if region_config['likely_countries'] else 0
        
        # Determine if this is likely a geographic issue
        is_geographic_issue = len(likely_missing) > 0 and coverage_ratio < 1.0
        confidence = 0.9 if detected_region == 'EMEA' else 0.7  # EMEA is most common mismatch
        
        # Generate specific mismatch reason
        if detected_region == 'EMEA':
            mismatch_reason = "EMEA includes Middle East and Africa, but targeting group 8643 only covers EU countries"
        elif detected_region == 'LATAM':
            mismatch_reason = "LATAM includes multiple countries, but targeting group 9000 only covers Brazil"
        else:
            mismatch_reason = f"{detected_region} region not covered by current targeting groups"
        
        return {
            'likely_geographic_issue': is_geographic_issue,
            'detected_geography': detected_region,
            'confidence': confidence,
            'covered_regions': [f"EU (FR,DE,IT,ES,GB)", f"Brazil"],
            'likely_missing_countries': ', '.join(likely_missing) if likely_missing else 'None identified',
            'coverage_ratio': coverage_ratio,
            'specific_mismatch_reason': mismatch_reason,
            'targeting_group_analysis': {
                'current_groups': ['8643 (EU)', '9000 (BR)', '8642/8999 (Open Exchange)'],
                'deal_targeting_group': region_config['targeting_group'],
                'mismatch_detected': region_config['targeting_group'] in ['None', '8643 (EU only)'] and detected_region != 'EU'
            }
        }
    
    def _identify_bidswitch_troubleshooting_pattern(self, data: Dict[str, Any], geographic_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Map the issue to specific BidSwitch troubleshooting patterns"""
        
        bid_requests = data.get('bid_requests', 0)
        yes_bids = data.get('yes_bids', 0)
        
        # Pattern identification based on BidSwitch troubleshooting documentation
        if bid_requests > 0 and yes_bids == 0:
            if geographic_analysis['likely_geographic_issue']:
                return {
                    'pattern_name': 'Failed DSP Geo targeting (>50%)',
                    'pattern_category': 'Targeting Issues',
                    'bidswitch_diagnostic': 'Geographic targeting misalignment',
                    'typical_percentage': '>50% (in this case: 100%)',
                    'bidswitch_ui_indicator': 'Too few Requests Sent',
                    'escalation_needed': False,
                    'documentation_reference': 'BidSwitch Deals Management § Targeting Issues'
                }
            else:
                return {
                    'pattern_name': 'Deal not associated with the DSP',
                    'pattern_category': 'Bidding Issues', 
                    'bidswitch_diagnostic': 'Deal cannot route to correct buyer',
                    'typical_percentage': 'Variable',
                    'bidswitch_ui_indicator': 'Deal not associated with the Buyer > 0',
                    'escalation_needed': True,
                    'documentation_reference': 'BidSwitch Deals Management § Bidding Issues'
                }
        
        return {
            'pattern_name': 'Unknown pattern',
            'pattern_category': 'General',
            'bidswitch_diagnostic': 'Pattern not clearly identified',
            'escalation_needed': True
        }
    
    def _diagnose_performance_issues(self, data: Dict[str, Any]) -> DiagnosticResult:
        """Diagnose performance-related issues"""
        bid_response_rate = data.get('bid_response_rate', 0)
        win_rate = data.get('win_rate', 0)
        
        if bid_response_rate < 5:  # Less than 5% bid response rate
            return DiagnosticResult(
                primary_issue="LOW_BID_RATE",
                severity="MEDIUM",
                confidence=0.8,
                symptoms=[f"Low bid response rate: {bid_response_rate:.1f}%"],
                root_causes=[
                    "Partial targeting mismatch",
                    "Budget constraints",
                    "Bidding logic filtering requests"
                ],
                recommended_actions=[
                    "Review targeting configuration",
                    "Check campaign budget status",
                    "Analyze bidding logic filters"
                ],
                supporting_data=data
            )
        
        if win_rate < 10:  # Less than 10% win rate
            return DiagnosticResult(
                primary_issue="LOW_WIN_RATE",
                severity="MEDIUM",
                confidence=0.7,
                symptoms=[f"Low win rate: {win_rate:.1f}%"],
                root_causes=[
                    "Bid prices too low for competitive auctions",
                    "High competition in target inventory",
                    "Creative quality issues"
                ],
                recommended_actions=[
                    "Increase bid prices for better competitiveness",
                    "Review creative performance and quality",
                    "Analyze competitor bidding patterns"
                ],
                supporting_data=data
            )
        
        return DiagnosticResult(
            primary_issue="HEALTHY",
            severity="LOW",
            confidence=0.9,
            symptoms=["Deal performing within normal parameters"],
            root_causes=["No significant issues detected"],
            recommended_actions=["Continue monitoring performance"],
            supporting_data=data
        )
    
    def _diagnose_no_traffic(self, data: Dict[str, Any]) -> DiagnosticResult:
        """Diagnose no traffic issues"""
        return DiagnosticResult(
            primary_issue="NO_TRAFFIC",
            severity="CRITICAL",
            confidence=0.9,
            symptoms=["Zero bid requests received"],
            root_causes=[
                "Deal not sending traffic to BidSwitch",
                "SmartSwitch filtering all requests",
                "Geographic targeting complete mismatch",
                "Deal configuration error"
            ],
            recommended_actions=[
                "Verify deal is active on supplier side",
                "Check SmartSwitch filtering rates",
                "Review geographic targeting alignment",
                "Contact supplier to verify traffic flow",
                "Check deal ID configuration"
            ],
            supporting_data=data
        )
    
    def _enrich_diagnosis(self, diagnosis: DiagnosticResult, data: Dict[str, Any]) -> DiagnosticResult:
        """Enrich diagnosis with additional context"""
        # Add SSP-specific insights
        ssp_name = data.get('ssp_name_external', '').lower()
        
        if 'google' in ssp_name and diagnosis.primary_issue == "BID_BELOW_FLOOR":
            diagnosis.root_causes.append("Google AdX has dynamic floor pricing")
            diagnosis.recommended_actions.append("Monitor floor price trends for Google inventory")
        
        # Add time-based context
        if data.get('deal_exists_in_sync', False):
            end_time = data.get('end_time')
            if end_time:
                try:
                    end_date = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    if end_date < datetime.now(end_date.tzinfo):
                        diagnosis.symptoms.append("Deal end date has passed")
                        diagnosis.recommended_actions.insert(0, "Extend deal end date")
                except:
                    pass
        
        return diagnosis
    
    def _load_diagnostic_rules(self) -> Dict[str, Any]:
        """Load diagnostic rules configuration"""
        # This could be loaded from a config file in the future
        return {
            'thresholds': {
                'high_floor_price': 10.0,
                'low_bid_response_rate': 5.0,
                'low_win_rate': 10.0,
                'high_timeout_rate': 10.0
            }
        }


def format_diagnosis_report(diagnosis: DiagnosticResult) -> str:
    """Format diagnosis as a readable report"""
    severity_icons = {
        'CRITICAL': '🚨',
        'HIGH': '⚠️',
        'MEDIUM': '⚠️',
        'LOW': 'ℹ️'
    }
    
    confidence_bar = '█' * int(diagnosis.confidence * 10) + '░' * (10 - int(diagnosis.confidence * 10))
    
    report = f"""
🔍 DEAL DIAGNOSTIC REPORT
========================

{severity_icons.get(diagnosis.severity, '❓')} PRIMARY ISSUE: {diagnosis.primary_issue}
   Severity: {diagnosis.severity}
   Confidence: {confidence_bar} {diagnosis.confidence:.0%}

📋 SYMPTOMS:
{chr(10).join(f'   • {symptom}' for symptom in diagnosis.symptoms)}

🔍 ROOT CAUSES:
{chr(10).join(f'   • {cause}' for cause in diagnosis.root_causes)}

🔧 RECOMMENDED ACTIONS:
{chr(10).join(f'   {i+1}. {action}' for i, action in enumerate(diagnosis.recommended_actions))}
"""
    
    return report
