#!/usr/bin/env python3
"""
Campaign Diagnostics Module
===========================

Campaign-level diagnostics only - no individual deal analysis.
Focuses on campaign configuration, status, and structural issues.
"""

import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime


class CampaignDiagnostics:
    """Campaign-level diagnostics without individual deal analysis"""
    
    def __init__(self):
        """Initialize diagnostics engine"""
        pass
    
    def check_campaign_level_issues(self, campaign_info: Dict[str, Any], campaign_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for campaign-level issues that affect delivery
        Returns list of campaign-level diagnostic findings
        """
        issues = []
        
        # Check campaign status
        if not campaign_info.get('is_active', True):
            issues.append({
                'pattern': 'CAMPAIGN_DISABLED',
                'severity': 'CRITICAL',
                'confidence': 100,
                'description': f"Campaign is {campaign_info.get('status_name', 'inactive')} - prevents all delivery",
                'recommended_actions': [
                    'Enable campaign (statusId = 1)',
                    'Verify campaign dates and budget',
                    'Check if intentionally paused'
                ],
                'details': {
                    'status_id': campaign_info.get('status_id'),
                    'status_name': campaign_info.get('status_name'),
                    'is_critical_blocker': True
                }
            })
        
        # Check campaign dates
        now = datetime.now()
        start_date = campaign_info.get('start_date')
        end_date = campaign_info.get('end_date')

        if start_date and end_date:
            try:
                # Simple date validation (could be enhanced)
                if end_date < now.date():
                    issues.append({
                        'pattern': 'CAMPAIGN_ENDED',
                        'severity': 'HIGH',
                        'confidence': 95,
                        'description': f"Campaign ended on {end_date} - no future delivery",
                        'recommended_actions': [
                            'Extend campaign end date',
                            'Create new campaign for continued delivery',
                            'Archive completed campaign'
                        ],
                        'details': {
                            'end_date': str(end_date),
                            'days_past_end': (now.date() - end_date).days
                        }
                    })
                elif start_date > now.date():
                    issues.append({
                        'pattern': 'CAMPAIGN_NOT_STARTED',
                        'severity': 'MEDIUM',
                        'confidence': 95,
                        'description': f"Campaign starts on {start_date} - not yet delivering",
                        'recommended_actions': [
                            'Adjust start date if needed',
                            'Monitor campaign readiness'
                        ],
                        'details': {
                            'start_date': str(start_date),
                            'days_until_start': (start_date - now.date()).days
                        }
                    })
            except (AttributeError, TypeError):
                issues.append({
                    'pattern': 'CAMPAIGN_DATE_INVALID',
                    'severity': 'HIGH',
                    'confidence': 90,
                    'description': "Campaign dates are invalid or improperly configured",
                    'recommended_actions': [
                        'Verify campaign start and end dates',
                        'Check date format in database'
                    ]
                })

        # Check budget issues (if spend data available)
        # This would require spend analysis integration

        # Check structural issues
        if campaign_structure.get('total_packages', 0) == 0:
            issues.append({
                'pattern': 'NO_CURATION_PACKAGES',
                'severity': 'CRITICAL',
                'confidence': 100,
                'description': "Campaign has no curation packages - no deals configured",
                'recommended_actions': [
                    'Add curation packages to campaign',
                    'Configure deal relationships',
                    'Verify line item setup'
                ]
            })

        return issues

    def calculate_campaign_health(self, campaign_info: Dict[str, Any],
                                campaign_structure: Dict[str, Any],
                                campaign_issues: List[Dict[str, Any]]) -> str:
        """
        Calculate overall campaign health based on campaign-level factors only
        Returns: CRITICAL, WARNING, or HEALTHY
        """
        # Count issues by severity
        critical_issues = [i for i in campaign_issues if i['severity'] == 'CRITICAL']
        high_issues = [i for i in campaign_issues if i['severity'] == 'HIGH']

        # Campaign health logic
        if critical_issues:
            return "CRITICAL"  # Campaign cannot deliver
        elif high_issues:
            return "WARNING"   # Campaign can deliver but has issues
        else:
            return "HEALTHY"   # Campaign is ready for deal debugging

    def generate_recommendations(self, campaign_issues: List[Dict[str, Any]],
                               campaign_info: Dict[str, Any]) -> List[str]:
        """
        Generate actionable recommendations based on campaign issues
        """
        recommendations = []
        
        # Sort issues by severity (critical first)
        sorted_issues = sorted(campaign_issues, key=lambda x: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].index(x['severity']))

        # Add top recommendations from each issue
        for issue in sorted_issues[:3]:  # Limit to top 3 issues
            if issue.get('recommended_actions'):
                recommendations.extend(issue['recommended_actions'][:2])  # 2 actions per issue

        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                unique_recommendations.append(rec)
                seen.add(rec)

        return unique_recommendations[:5]  # Limit to 5 total recommendations
