# BidSwitch Diagnostic Patterns

## Overview

This document defines specific diagnostic patterns, thresholds, and automated rules for BidSwitch deal analysis. These patterns can be directly implemented in code for automated troubleshooting.

## Diagnostic Rule Engine

### Pattern Matching Structure

```python
class DiagnosticPattern:
    def __init__(self, name, condition, severity, message, actions):
        self.name = name
        self.condition = condition  # Function that returns True if pattern matches
        self.severity = severity    # 'HIGH', 'MEDIUM', 'LOW'
        self.message = message      # Human-readable description
        self.actions = actions      # List of recommended actions
```

## Traffic Volume Patterns

### Pattern: No Traffic
```python
{
    "name": "no_traffic",
    "condition": lambda metrics: metrics.get('bid_requests', 0) == 0,
    "severity": "HIGH",
    "message": "No bid requests received for deal",
    "symptoms": ["bid_requests = 0"],
    "root_causes": [
        "Supplier not sending requests with Deal ID",
        "Incorrect wseat value configuration",
        "Deal routing misconfiguration"
    ],
    "actions": [
        "Verify supplier sending bid requests with correct Deal ID",
        "Check if request volume > 1,000/day minimum",
        "Validate wseat value configuration",
        "Contact BidSwitch Support with bid request examples"
    ],
    "escalation": "Contact BidSwitch Support if configuration verified"
}
```

### Pattern: Low Traffic Volume
```python
{
    "name": "low_traffic",
    "condition": lambda metrics: 0 < metrics.get('bid_requests', 0) < 1000,
    "severity": "MEDIUM",
    "message": "Low bid request volume (< 1,000/day)",
    "actions": [
        "Review targeting configuration for over-restriction",
        "Check geo-targeting alignment",
        "Validate inventory type settings"
    ]
}
```

### Pattern: High Invalid Requests
```python
{
    "name": "high_invalid_requests",
    "condition": lambda metrics: (
        metrics.get('invalid_requests', 0) / max(metrics.get('total_requests', 1), 1) > 0.20
    ),
    "severity": "HIGH",
    "message": "High invalid request rate (>20%)",
    "root_causes": [
        "Invalid JSON format in requests",
        "Invalid inventory types (web, in-app)",
        "Invalid content types (display, video, audio, native)",
        "Wrong data center routing"
    ],
    "actions": [
        "Validate JSON format in bid requests",
        "Check inventory type configuration",
        "Verify content type settings",
        "Confirm correct data center routing"
    ]
}
```

## Bidding Performance Patterns

### Pattern: No Bid Responses
```python
{
    "name": "no_bid_responses",
    "condition": lambda metrics: (
        metrics.get('bid_requests', 0) > 0 and metrics.get('yes_bids', 0) == 0
    ),
    "severity": "HIGH",
    "message": "No bid responses despite receiving requests",
    "root_causes": [
        "Buyer not responding with Deal ID",
        "Targeting configuration too restrictive",
        "Bid floor too high",
        "Creative compliance issues"
    ],
    "actions": [
        "Verify buyer responding with correct Deal ID",
        "Review targeting configuration",
        "Check bid floor settings vs buyer bid prices",
        "Validate creative compliance"
    ]
}
```

### Pattern: Low Bid Response Rate
```python
{
    "name": "low_bid_rate",
    "condition": lambda metrics: (
        metrics.get('bid_requests', 0) > 100 and 
        (metrics.get('yes_bids', 0) / metrics.get('bid_requests', 1)) < 0.05
    ),
    "severity": "MEDIUM",
    "message": "Low bid response rate (<5%)",
    "actions": [
        "Review buyer targeting configuration",
        "Check bid floor competitiveness",
        "Analyze geo-targeting alignment",
        "Validate user matching rates"
    ]
}
```

### Pattern: High Timeout Rate
```python
{
    "name": "high_timeouts",
    "condition": lambda metrics: (
        metrics.get('timeout_rate', 0) > 0.10
    ),
    "severity": "HIGH",
    "message": "High timeout rate (>10%)",
    "root_causes": [
        "Insufficient server capacity",
        "Geographic latency issues",
        "Inadequate timeout window (tmax)"
    ],
    "actions": [
        "Increase server capacity",
        "Consider data center relocation closer to BidSwitch",
        "Request increased timeout window from supplier",
        "Optimize bid response processing"
    ]
}
```

## Impression Delivery Patterns

### Pattern: No Impressions
```python
{
    "name": "no_impressions",
    "condition": lambda metrics: (
        metrics.get('yes_bids', 0) > 0 and metrics.get('impressions', 0) == 0
    ),
    "severity": "HIGH",
    "message": "No impressions despite winning bids",
    "root_causes": [
        "Bid below floor price",
        "Creative blocked by BidSwitch",
        "Protocol compliance issues",
        "SSP custom requirements not met"
    ],
    "actions": [
        "Check bid prices vs floor requirements",
        "Validate creative compliance",
        "Review BidSwitch protocol compliance",
        "Verify SSP-specific requirements"
    ]
}
```

### Pattern: Low Win Rate
```python
{
    "name": "low_win_rate",
    "condition": lambda metrics: (
        metrics.get('yes_bids', 0) > 100 and
        (metrics.get('impressions', 0) / metrics.get('yes_bids', 1)) < 0.10
    ),
    "severity": "MEDIUM",
    "message": "Low impression win rate (<10%)",
    "actions": [
        "Increase bid prices to be more competitive",
        "Review and adjust bid floor strategy",
        "Check creative approval status",
        "Analyze auction competition patterns"
    ]
}
```

## Quality and Compliance Patterns

### Pattern: High Non-Human Traffic
```python
{
    "name": "high_bot_traffic",
    "condition": lambda metrics: (
        metrics.get('non_human_traffic_rate', 0) > 0.20
    ),
    "severity": "MEDIUM",
    "message": "High suspected non-human traffic (>20%)",
    "root_causes": [
        "Untrusted traffic sources",
        "Bot traffic infiltration",
        "Inadequate traffic filtering"
    ],
    "actions": [
        "Review traffic source trustworthiness",
        "Implement traffic quality filters",
        "Contact BidSwitch Support with traffic examples",
        "Consider additional fraud detection measures"
    ]
}
```

### Pattern: High Cloud/Proxy Traffic
```python
{
    "name": "high_datacenter_traffic",
    "condition": lambda metrics: (
        metrics.get('cloud_proxy_traffic_rate', 0) > 0.20
    ),
    "severity": "MEDIUM",
    "message": "High cloud/datacenter/proxy traffic (>20%)",
    "actions": [
        "Review traffic source quality",
        "Implement IP filtering for datacenter ranges",
        "Contact BidSwitch Support if traffic appears legitimate",
        "Consider geo-targeting adjustments"
    ]
}
```

## Targeting Alignment Patterns

### Pattern: High User Matching Failure
```python
{
    "name": "high_user_matching_failure",
    "condition": lambda metrics: (
        metrics.get('user_matching_failure_rate', 0) > 0.50
    ),
    "severity": "HIGH",
    "message": "High user matching failure rate (>50%)",
    "root_causes": [
        "Low user sync rates",
        "Supplier sending unmatched user requests",
        "Buyer requiring matched users only"
    ],
    "actions": [
        "Increase user sync frequency",
        "Review user matching requirements",
        "Optimize cookie sync processes",
        "Check user ID mapping configuration"
    ]
}
```

### Pattern: High Geo-Targeting Failure
```python
{
    "name": "high_geo_targeting_failure",
    "condition": lambda metrics: (
        metrics.get('geo_targeting_failure_rate', 0) > 0.50
    ),
    "severity": "HIGH",
    "message": "High geo-targeting failure rate (>50%)",
    "root_causes": [
        "Supplier sending wrong-country traffic",
        "Buyer geo-targeting too restrictive",
        "Deal geo-configuration mismatch"
    ],
    "actions": [
        "Align supplier traffic with buyer geo-targeting",
        "Review and adjust geo-targeting settings",
        "Verify deal geographic configuration",
        "Check country-level performance data"
    ]
}
```

### Pattern: High SmartSwitch Filtering
```python
{
    "name": "high_smartswitch_filtering",
    "condition": lambda metrics: (
        metrics.get('smartswitch_filter_rate', 0) > 0.60
    ),
    "severity": "HIGH",
    "message": "High SmartSwitch filtering rate (>60%)",
    "root_causes": [
        "DSP lacks bidding history on this traffic type",
        "SmartSwitch ML algorithm learned to filter this traffic",
        "Open market deal subject to SmartSwitch optimization",
        "Catch-22: Need bidding volume to get traffic, need traffic to bid"
    ],
    "actions": [
        "Increase purchasing of similar traffic types consistently",
        "Convert to private deal (if possible) to disable SmartSwitch",
        "Replace with private deal if conversion not possible",
        "Build bidding history gradually with similar inventory"
    ],
    "technical_details": {
        "ml_mechanism": "SmartSwitch analyzes 27+ signals to predict bid likelihood",
        "learning_period": "Continuous learning from bidding patterns",
        "exemptions": "Private deals can disable SmartSwitch per SSP"
    }
}
```

### Pattern: Extreme SmartSwitch Filtering  
```python
{
    "name": "extreme_smartswitch_filtering",
    "condition": lambda metrics: (
        metrics.get('smartswitch_filter_rate', 0) > 0.70
    ),
    "severity": "CRITICAL",
    "message": "Extreme SmartSwitch filtering (>70%) - ML blocking traffic",
    "root_causes": [
        "DSP has minimal/zero bidding history on traffic type",
        "SmartSwitch ML strongly predicts no bidding interest", 
        "Deal type incompatible with DSP buying patterns",
        "Severe catch-22: Too filtered to build bidding history"
    ],
    "actions": [
        "IMMEDIATE: Replace deal - current deal unsalvageable",
        "Source private deal to bypass SmartSwitch",
        "Build bidding history on similar traffic before retry",
        "Consider different traffic types aligned with DSP patterns"
    ],
    "business_impact": {
        "traffic_loss": ">70% of potential requests blocked",
        "learning_barrier": "Insufficient traffic to improve ML scoring",
        "strategic_implication": "Deal fundamentally misaligned with buyer"
    }
}
```

## Implementation Framework

### Diagnostic Engine Class
```python
class BidSwitchDiagnostics:
    def __init__(self):
        self.patterns = [
            # Load all diagnostic patterns
        ]
    
    def analyze(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all diagnostic patterns against metrics"""
        findings = []
        
        for pattern in self.patterns:
            if pattern['condition'](metrics):
                findings.append({
                    'pattern': pattern['name'],
                    'severity': pattern['severity'],
                    'message': pattern['message'],
                    'actions': pattern['actions'],
                    'root_causes': pattern.get('root_causes', [])
                })
        
        return sorted(findings, key=lambda x: self._severity_order(x['severity']))
    
    def _severity_order(self, severity: str) -> int:
        return {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}.get(severity, 3)
```

### Metrics Calculation
```python
def calculate_diagnostic_metrics(bidswitch_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate metrics needed for diagnostic patterns"""
    total = bidswitch_data.get('total', {})
    
    return {
        'bid_requests': total.get('dsp_bid_requests', 0),
        'yes_bids': total.get('dsp_yes_bids', 0),
        'impressions': total.get('imps', 0),
        'spend': total.get('dsp_final_price_usd', 0),
        'avg_bid_floor': total.get('average_bidfloor', 0),
        'tech_win_rate': total.get('tech_win_rate', 0),
        
        # Calculated rates (would need additional data)
        'bid_response_rate': total.get('dsp_yes_bids', 0) / max(total.get('dsp_bid_requests', 1), 1),
        'win_rate': total.get('imps', 0) / max(total.get('dsp_yes_bids', 1), 1),
        'fill_rate': total.get('imps', 0) / max(total.get('dsp_bid_requests', 1), 1),
        
        # Quality metrics (would need additional BidSwitch data)
        'timeout_rate': 0,  # Placeholder
        'invalid_request_rate': 0,  # Placeholder
        'non_human_traffic_rate': 0,  # Placeholder
        'cloud_proxy_traffic_rate': 0,  # Placeholder
        'user_matching_failure_rate': 0,  # Placeholder
        'geo_targeting_failure_rate': 0,  # Placeholder
        'smartswitch_filter_rate': 0,  # Placeholder
    }
```

## Usage in Deal Analyzer

### Integration Example
```python
# In deal_performance.py
from bidswitch_diagnostics import BidSwitchDiagnostics, calculate_diagnostic_metrics

class DealPerformanceAnalyzer:
    def __init__(self, bidswitch_client):
        self.bidswitch_client = bidswitch_client
        self.diagnostics = BidSwitchDiagnostics()
    
    def verify_deal_performance(self, deal):
        # Get BidSwitch data
        api_data = self.bidswitch_client.get_deal_performance(...)
        
        # Calculate diagnostic metrics
        metrics = calculate_diagnostic_metrics(api_data)
        
        # Run diagnostic patterns
        diagnostic_findings = self.diagnostics.analyze(metrics)
        
        # Include in results
        return {
            **deal,
            'performance_metrics': metrics,
            'diagnostic_findings': diagnostic_findings,
            'issues': [f['message'] for f in diagnostic_findings],
            'actions': [action for f in diagnostic_findings for action in f['actions']]
        }
```

This structured approach allows for automated, consistent, and comprehensive BidSwitch deal diagnostics based on the official troubleshooting documentation.

---

## Related Documentation

**For complete deal debugging workflow including the Five Common Culprits, see**:
- [Deal Debug Workflow](../../06-operations/deal-debug-workflow.md) - Industry best practices, selection criteria, and resolution patterns
