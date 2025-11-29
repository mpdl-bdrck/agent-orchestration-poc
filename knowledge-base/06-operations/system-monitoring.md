# System Monitoring

## Overview

This guide provides comprehensive system monitoring procedures, health check protocols, and incident response workflows for the Bedrock Platform. It covers infrastructure monitoring, application health checks, alerting systems, and proactive monitoring strategies to ensure optimal platform performance and reliability.

## Monitoring Architecture

### Core Monitoring Stack

#### Infrastructure Components
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization, dashboards, and alerting
- **VictoriaMetrics**: Long-term metrics storage and querying
- **VictoriaLogs**: Centralized log aggregation and analysis
- **AWS CloudWatch**: AWS resource monitoring and native service metrics

#### Application Monitoring
- **Service Metrics**: Custom application metrics from bidder, exchange, tracker
- **Business Metrics**: Campaign performance, spend tracking, bid activity
- **Performance Metrics**: Latency, throughput, error rates, resource utilization
- **Health Endpoints**: Service health checks and readiness probes

### Monitoring Endpoints

#### Grafana Access
- **Primary URL**: `https://grafana.monitoring.bedrockplatform.bid/`
- **Authentication**: AWS Identity Center (SSO)
- **Backup URL**: `https://grafana.monitoring.bedrockplatform.ninja/`

#### Key Dashboard Categories
```yaml
Essential Dashboards:
Infrastructure:
  - Kubernetes / Views / Pods: Pod resource usage and status
  - Pod Overview: Service-grouped pod metrics
  - Karpenter: Node scaling and resource management
  - Cluster Health: Overall cluster status and alerts

Application Performance:
  - Health - Delivery: Real-time bid performance
  - Campaign Performance: Business metrics and KPIs
  - Service Latency: Response time analysis
  - Error Rate Monitoring: Service error tracking

Business Intelligence:
  - Spend Monitoring: Budget utilization and pacing
  - Win Rate Analysis: Auction performance metrics
  - Traffic Patterns: Bid request volume and trends
  - Revenue Tracking: Financial performance metrics
```

## Health Check Procedures

### Service Health Monitoring

#### Core Service Health Endpoints
```yaml
Health Check URLs:
Bidder Service:
  - Health: http://bidder:8070/health
  - Metrics: http://bidder:8070/metrics
  - Ready: http://bidder:8070/ready

Exchange Service:
  - Health: http://exchange:8080/health
  - Metrics: http://exchange:8080/metrics
  - Ready: http://exchange:8080/ready

Tracker Service:
  - Health: http://tracker:8090/health
  - Metrics: http://tracker:8090/metrics
  - Ready: http://tracker:8090/ready

Terminal API:
  - Health: http://terminal:3000/health
  - Metrics: http://terminal:3000/metrics
  - Ready: http://terminal:3000/ready
```

#### Kubernetes Health Checks
```bash
# Check overall cluster health
kubectl get nodes
kubectl get pods -n production
kubectl get services -n production

# Check specific service health
kubectl get pods -n production -l app=bidder
kubectl get pods -n production -l app=exchange
kubectl get pods -n production -l app=tracker

# Check pod logs for errors
kubectl logs -f deployment/bidder -n production --tail=100
kubectl logs -f deployment/exchange -n production --tail=100
kubectl logs -f deployment/tracker -n production --tail=100

# Check resource utilization
kubectl top pods -n production
kubectl top nodes

# Check horizontal pod autoscaler status
kubectl get hpa -n production
```

#### Database Health Checks
```bash
# PostgreSQL connection test
kubectl exec -it deployment/bidder -n production -- \
  psql -h exchange-v2.cta66mm84890.eu-west-1.rds.amazonaws.com \
       -p 5432 -U exchange -d exchange -c "SELECT 1;"

# Check database performance
kubectl exec -it deployment/bidder -n production -- \
  psql -h exchange-v2.cta66mm84890.eu-west-1.rds.amazonaws.com \
       -p 5432 -U exchange -d exchange -c "
  SELECT 
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_live_tup,
    n_dead_tup
  FROM pg_stat_user_tables 
  ORDER BY n_live_tup DESC 
  LIMIT 10;"
```

#### Aerospike Health Checks
```bash
# Connect to Aerospike cluster
kubectl exec -it aerodb-aerospike-0 -n production -- \
  asadm -e "show statistics"

# Check cluster status
kubectl exec -it aerodb-aerospike-0 -n production -- \
  asadm -e "show statistics like cluster"

# Check namespace health
kubectl exec -it aerodb-aerospike-0 -n production -- \
  asadm -e "show statistics namespace"

# Monitor memory usage
kubectl exec -it aerodb-aerospike-0 -n production -- \
  asadm -e "show statistics namespace like memory"

# Check partition distribution
kubectl exec -it aerodb-aerospike-0 -n production -- \
  asadm -e "show statistics like partitions"
```

### Business Logic Health Checks

#### Campaign Activity Monitoring
```sql
-- Check active campaigns and spend
SELECT 
  COUNT(*) as active_campaigns,
  SUM(CASE WHEN l."status" = 'active' THEN 1 ELSE 0 END) as active_line_items,
  SUM(o.media_spend) as total_spend_today
FROM "campaigns" c
JOIN "lineItems" l ON c."campaignId" = l."campaignId"
LEFT JOIN overview o ON l."lineItemUuid" = o.line_item_id 
  AND o.date = CURRENT_DATE
WHERE c."status" = 'active'
  AND c."startDate" <= CURRENT_DATE 
  AND c."endDate" >= CURRENT_DATE;

-- Check recent bid activity
SELECT 
  COUNT(*) as total_bids,
  SUM(CASE WHEN won = true THEN 1 ELSE 0 END) as wins,
  AVG(response_time_ms) as avg_response_time,
  MAX(created_at) as last_bid_time
FROM bidstream_v2 
WHERE created_at >= NOW() - INTERVAL '1 hour';
```

#### Traffic Volume Verification
```bash
# Check recent bid request volume
curl -s "http://grafana.monitoring.bedrockplatform.bid/api/datasources/proxy/1/query?query=rate(biddersrv_bidder_avails[5m])" | jq '.data.result[0].value[1]'

# Check win rate trends
curl -s "http://grafana.monitoring.bedrockplatform.bid/api/datasources/proxy/1/query?query=rate(tracksrv_stat_media_imp[5m])/rate(biddersrv_bidder_yes_bid[5m])" | jq '.data.result[0].value[1]'

# Check error rates
curl -s "http://grafana.monitoring.bedrockplatform.bid/api/datasources/proxy/1/query?query=rate(biddersrv_http_requests_count{status=~\"4..|5..\"}[5m])" | jq '.data.result[0].value[1]'
```

## Alerting System

### Alert Categories

#### Critical Infrastructure Alerts
```yaml
Cluster Health Alerts:
- Kubelet Not Running: Kubelet service failure
- API Server Errors: Kubernetes API issues
- High Disk Usage: Disk usage > 80%
- Node Not Ready: Node unavailable > 5 minutes
- Cluster Node CPU High: CPU > 90%
- Cluster Node Memory Pressure: Memory exhaustion

Workload Alerts:
- Failed Pods: Pods in failed state
- Pending Pods: Pods pending > 10 minutes
- Deployment Not Available: Service unavailability
- High Latency: P95 latency > 1 second
- High Pod CPU/Memory: Resource usage > 80%
- Core Application Downtime: Service down > 2 minutes
- Pod Crash Loops: >3 restarts in 10 minutes

Data Store Alerts:
- Aerospike File Read Errors: Storage issues
- Cannot Write To Aerospike: Write failures
- High Aerospike Disk Usage: Disk > 50%
- Dead/Unavailable Partitions: Data availability issues
```

#### Business Logic Alerts
```yaml
Critical Business Alerts:
- Spend Over Limit: Budget exceeded by >1%
- No Bidding Activity: No bids for 10 minutes
- Exchange Response Errors: Error rate >20%
- Bidder Response Errors: HTTP 4xx/5xx >20%

Warning Business Alerts:
- No Tracking Activity (Imps): No impressions for 1 hour
- No Tracking Activity (Clicks): No clicks for 1 hour
- Win Rate Anomaly: Win rate <5% or >95%
- Sudden Spend Spike: 5x increase in spend rate
```

### Alert Configuration

#### Notification Channels
```yaml
Slack Integration:
- Channel: #grafana-alerts
- Webhook URL: Configured in Grafana contact points
- Message Format: Structured alert with context

PagerDuty Integration:
- Service: Bedrock Platform Production
- Escalation: Automatic escalation after 15 minutes
- Severity Mapping:
  - Critical → P1 (Immediate)
  - Warning → P2 (High)
  - Info → P3 (Medium)
```

#### Alert Thresholds
```yaml
Performance Thresholds:
Response Time:
  - Warning: P95 > 200ms
  - Critical: P95 > 500ms

Error Rate:
  - Warning: >5%
  - Critical: >20%

Resource Usage:
  - Warning: >70%
  - Critical: >90%

Business Metrics:
Win Rate:
  - Warning: <10% or >90%
  - Critical: <5% or >95%

Spend Rate:
  - Warning: >90% of budget
  - Critical: >100% of budget
```

### Alert Management

#### Alert Lifecycle
```yaml
Alert States:
1. Firing: Condition met, alert active
2. Pending: Condition met, waiting for duration
3. Resolved: Condition no longer met
4. Silenced: Manually suppressed
5. Inhibited: Suppressed by higher priority alert

Alert Actions:
- Acknowledge: Mark as seen/being handled
- Silence: Temporarily suppress notifications
- Resolve: Mark as fixed (auto-resolves when condition clears)
- Escalate: Manually escalate to higher severity
```

#### Silence Management
```bash
# Create silence for maintenance window
curl -X POST "http://grafana.monitoring.bedrockplatform.bid/api/alertmanager/grafana/api/v1/silences" \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [{"name": "alertname", "value": "HighLatency", "isRegex": false}],
    "startsAt": "2024-01-15T10:00:00Z",
    "endsAt": "2024-01-15T12:00:00Z",
    "createdBy": "maintenance-team",
    "comment": "Scheduled maintenance window"
  }'

# List active silences
curl "http://grafana.monitoring.bedrockplatform.bid/api/alertmanager/grafana/api/v1/silences"
```

## Performance Monitoring

### Key Performance Indicators

#### System Performance Metrics
```yaml
Infrastructure KPIs:
- CPU Utilization: Average and peak usage per service
- Memory Usage: Current usage and allocation efficiency
- Network I/O: Throughput and latency metrics
- Disk I/O: Read/write operations and queue depth
- Pod Restart Rate: Service stability indicator

Application KPIs:
- Request Rate: Requests per second by service
- Response Time: P50, P95, P99 latency percentiles
- Error Rate: 4xx and 5xx error percentages
- Throughput: Successful operations per second
- Queue Depth: Pending operations in queues
```

#### Business Performance Metrics
```yaml
Campaign Performance:
- Bid Request Volume: Total opportunities per hour
- Bid Response Rate: Participation in auctions
- Win Rate: Auction success percentage
- Spend Rate: Budget utilization velocity
- CTR: Click-through rate performance
- Conversion Rate: Campaign effectiveness

Revenue Metrics:
- Revenue per Hour: Hourly revenue generation
- eCPM: Effective cost per mille
- CPA: Cost per acquisition
- ROAS: Return on ad spend
- Margin: Profit margin percentage
```

### Performance Dashboards

#### Real-Time Monitoring Dashboard
```yaml
Dashboard Panels:
System Health:
  - Service status indicators (green/red)
  - Resource utilization gauges
  - Error rate trends
  - Response time distributions

Business Metrics:
  - Live spend tracking
  - Bid volume and win rate
  - Campaign performance summary
  - Revenue tracking

Alerts Summary:
  - Active alerts count
  - Recent alert history
  - Alert severity distribution
  - Time to resolution metrics
```

#### Historical Analysis Dashboard
```yaml
Trend Analysis:
- 7-day performance trends
- Month-over-month comparisons
- Seasonal pattern analysis
- Capacity planning metrics

Performance Baselines:
- Service level objectives (SLOs)
- Performance benchmarks
- Capacity thresholds
- Growth projections
```

### Automated Monitoring

#### Health Check Automation
```bash
#!/bin/bash
# Automated health check script

# Function to check service health
check_service_health() {
    local service=$1
    local namespace=$2
    
    # Check pod status
    pod_status=$(kubectl get pods -n $namespace -l app=$service -o jsonpath='{.items[*].status.phase}')
    
    if [[ "$pod_status" != *"Running"* ]]; then
        echo "CRITICAL: $service pods not running in $namespace"
        return 1
    fi
    
    # Check service endpoint
    endpoint_check=$(kubectl exec -n $namespace deployment/$service -- curl -f http://localhost:8080/health 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        echo "WARNING: $service health endpoint not responding"
        return 1
    fi
    
    echo "OK: $service healthy in $namespace"
    return 0
}

# Check core services
services=("bidder" "exchange" "tracker")
namespace="production"

for service in "${services[@]}"; do
    check_service_health $service $namespace
done

# Check Aerospike cluster
aerospike_status=$(kubectl exec -it aerodb-aerospike-0 -n production -- asadm -e "show statistics like cluster_size" 2>/dev/null | grep cluster_size)

if [[ "$aerospike_status" == *"cluster_size=3"* ]]; then
    echo "OK: Aerospike cluster healthy"
else
    echo "CRITICAL: Aerospike cluster issues detected"
fi
```

#### Automated Performance Reports
```python
#!/usr/bin/env python3
# Daily performance report generator

import requests
import json
from datetime import datetime, timedelta

def get_grafana_metric(query, start_time, end_time):
    """Query Grafana for metrics data"""
    url = "http://grafana.monitoring.bedrockplatform.bid/api/datasources/proxy/1/query_range"
    params = {
        'query': query,
        'start': start_time.timestamp(),
        'end': end_time.timestamp(),
        'step': '1h'
    }
    
    response = requests.get(url, params=params)
    return response.json()

def generate_daily_report():
    """Generate daily performance report"""
    end_time = datetime.now()
    start_time = end_time - timedelta(days=1)
    
    # Key metrics to report
    metrics = {
        'bid_requests': 'rate(biddersrv_bidder_avails[1h])',
        'win_rate': 'rate(tracksrv_stat_media_imp[1h])/rate(biddersrv_bidder_yes_bid[1h])',
        'error_rate': 'rate(biddersrv_http_requests_count{status=~"4..|5.."}[1h])',
        'avg_latency': 'histogram_quantile(0.95, rate(biddersrv_http_request_duration_seconds_bucket[1h]))'
    }
    
    report = {
        'date': end_time.strftime('%Y-%m-%d'),
        'metrics': {}
    }
    
    for metric_name, query in metrics.items():
        data = get_grafana_metric(query, start_time, end_time)
        # Process and summarize data
        report['metrics'][metric_name] = process_metric_data(data)
    
    return report

def process_metric_data(data):
    """Process metric data and calculate summary statistics"""
    if not data.get('data', {}).get('result'):
        return {'error': 'No data available'}
    
    values = []
    for result in data['data']['result']:
        for timestamp, value in result.get('values', []):
            try:
                values.append(float(value))
            except (ValueError, TypeError):
                continue
    
    if not values:
        return {'error': 'No valid values'}
    
    return {
        'min': min(values),
        'max': max(values),
        'avg': sum(values) / len(values),
        'count': len(values)
    }

if __name__ == "__main__":
    report = generate_daily_report()
    print(json.dumps(report, indent=2))
```

## Incident Response

### Incident Classification

#### Severity Levels
```yaml
Severity 1 (Critical):
- Complete service outage
- Data loss or corruption
- Security breach
- Revenue impact >$10k/hour
- Customer-facing functionality down

Severity 2 (High):
- Partial service degradation
- Performance issues affecting >50% users
- Revenue impact $1k-$10k/hour
- Non-critical feature outages

Severity 3 (Medium):
- Minor performance issues
- Single component failures with redundancy
- Revenue impact <$1k/hour
- Cosmetic or usability issues

Severity 4 (Low):
- Documentation issues
- Enhancement requests
- Monitoring alerts without user impact
```

### Incident Response Procedures

#### Initial Response (0-15 minutes)
```yaml
Immediate Actions:
1. Acknowledge Alert: Confirm receipt and begin investigation
2. Assess Impact: Determine severity and affected systems
3. Notify Team: Alert appropriate team members based on severity
4. Begin Mitigation: Start immediate containment actions
5. Document: Create incident ticket with initial findings

Communication:
- Severity 1: Immediate PagerDuty escalation + Slack notification
- Severity 2: Slack notification + email to on-call team
- Severity 3-4: Slack notification during business hours
```

#### Investigation Phase (15-60 minutes)
```yaml
Diagnostic Steps:
1. Check Recent Changes: Review recent deployments and configuration changes
2. Analyze Metrics: Review Grafana dashboards for anomalies
3. Check Logs: Examine service logs for errors and patterns
4. Test Components: Verify individual service functionality
5. Identify Root Cause: Determine underlying cause of issue

Tools and Commands:
- kubectl logs -f deployment/<service> -n production --tail=100
- kubectl describe pod <pod-name> -n production
- kubectl get events -n production --sort-by='.lastTimestamp'
- Check Grafana dashboards for metric anomalies
- Review recent GitHub commits and deployments
```

#### Resolution Phase (Variable Duration)
```yaml
Resolution Actions:
1. Implement Fix: Apply appropriate solution based on root cause
2. Verify Resolution: Confirm issue is resolved and systems stable
3. Monitor Recovery: Watch metrics for return to normal levels
4. Update Stakeholders: Communicate resolution to affected parties
5. Document Solution: Record fix and lessons learned

Common Resolution Strategies:
- Service Restart: kubectl rollout restart deployment/<service> -n production
- Rollback Deployment: Revert to previous working version
- Scale Resources: Increase replicas or resource limits
- Configuration Fix: Update configuration and restart services
- Database Optimization: Fix queries or add indexes
```

### Post-Incident Activities

#### Post-Mortem Process
```yaml
Post-Mortem Requirements:
- Severity 1-2: Mandatory within 48 hours
- Severity 3: Optional but recommended
- Severity 4: Not required unless pattern emerges

Post-Mortem Components:
1. Incident Summary: What happened and when
2. Timeline: Detailed sequence of events
3. Root Cause Analysis: Why it happened
4. Impact Assessment: Business and technical impact
5. Response Evaluation: What went well and what didn't
6. Action Items: Preventive measures and improvements
7. Follow-up: Assign owners and deadlines for actions
```

#### Continuous Improvement
```yaml
Improvement Areas:
Monitoring Enhancements:
- Add new alerts based on incident patterns
- Improve alert accuracy and reduce false positives
- Enhance dashboard visibility for key metrics

Process Improvements:
- Update runbooks based on lessons learned
- Improve incident response procedures
- Enhance team training and documentation

Technical Improvements:
- Implement additional redundancy
- Improve system resilience and fault tolerance
- Enhance automated recovery mechanisms
```

## Monitoring Best Practices

### Proactive Monitoring

#### Trend Analysis
```yaml
Weekly Reviews:
- Performance trend analysis
- Capacity planning assessments
- Alert pattern identification
- System optimization opportunities

Monthly Reviews:
- Infrastructure cost optimization
- Performance benchmark updates
- Monitoring tool effectiveness
- Team training needs assessment
```

#### Predictive Monitoring
```yaml
Predictive Metrics:
- Resource utilization trends
- Growth pattern analysis
- Capacity threshold forecasting
- Performance degradation indicators

Early Warning Systems:
- Gradual performance degradation alerts
- Resource exhaustion predictions
- Traffic pattern anomaly detection
- Cost optimization opportunities
```

### Monitoring Hygiene

#### Alert Management
```yaml
Alert Optimization:
- Regular review of alert thresholds
- Elimination of noisy or redundant alerts
- Tuning of alert sensitivity
- Documentation of alert response procedures

Alert Lifecycle:
- Monthly alert effectiveness review
- Quarterly alert threshold adjustment
- Annual alert strategy assessment
- Continuous feedback incorporation
```

#### Dashboard Management
```yaml
Dashboard Maintenance:
- Regular dashboard review and updates
- Removal of obsolete metrics and panels
- Addition of new business-critical metrics
- User feedback incorporation

Dashboard Standards:
- Consistent naming conventions
- Standardized color schemes and layouts
- Clear metric definitions and units
- Appropriate time ranges and refresh rates
```

## Related Topics
- [Campaign Troubleshooting](campaign-troubleshooting.md) - Diagnostic procedures for campaign issues
- [Performance Optimization](performance-optimization.md) - System and campaign optimization
- [Platform Architecture](../03-technical-features/platform-architecture.md) - System architecture overview
- [Real-Time Processing](../03-technical-features/real-time-processing.md) - Real-time system monitoring
- [Data Quality Management](data-quality-management.md) - Data validation and monitoring
