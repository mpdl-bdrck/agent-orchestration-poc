# Campaign Troubleshooting

## Overview

This guide provides comprehensive troubleshooting procedures for common campaign delivery issues, performance problems, and diagnostic techniques. It covers systematic approaches to identify, diagnose, and resolve campaign-related problems in the Bedrock Platform.

## Common Campaign Issues

### Campaign Not Delivering

#### Symptoms
- Zero or very low impression delivery
- No bid responses being sent
- Campaign shows as "Active" but no spend
- Line items not receiving traffic

#### Diagnostic Steps

**1. Check Campaign Status & Configuration**
```sql
-- Verify campaign and line item status
SELECT 
  c."name" AS campaign_name,
  c."status" AS campaign_status,
  c."startDate",
  c."endDate",
  c."totalBudget",
  l."name" AS line_item_name,
  l."status" AS line_item_status,
  l."totalBudget" AS line_item_budget
FROM "campaigns" c
JOIN "lineItems" l ON c."campaignId" = l."campaignId"
WHERE c."campaignId" = 'your_campaign_id';
```

**2. Verify Budget Availability**
```sql
-- Check remaining budget
SELECT 
  l."lineItemId",
  l."name",
  l."totalBudget",
  COALESCE(SUM(o.media_spend), 0) AS spent,
  (l."totalBudget" - COALESCE(SUM(o.media_spend), 0)) AS remaining
FROM "lineItems" l
LEFT JOIN overview o ON l."lineItemUuid" = o.line_item_id
WHERE l."lineItemId" = 'your_line_item_id'
GROUP BY l."lineItemId", l."name", l."totalBudget";
```

**3. Check Targeting Configuration**
- **Geo Targeting**: Verify geographic targeting isn't too restrictive
- **Device Targeting**: Ensure device types are properly configured
- **Time Targeting**: Check day-parting and timezone settings
- **Audience Segments**: Verify segment availability and size
- **Inventory Targeting**: Check supply deal and SSP configurations

#### Common Causes & Solutions

**Budget Exhausted:**
- **Cause**: Line item or campaign budget fully spent
- **Solution**: Increase budget or adjust pacing settings
- **Prevention**: Set up budget alerts and monitoring

**Overly Restrictive Targeting:**
- **Cause**: Targeting parameters too narrow (e.g., very specific geo + device + audience)
- **Solution**: Broaden targeting criteria systematically
- **Testing**: Remove targeting filters one by one to identify bottlenecks

**Geographic Targeting Conflicts:**
- **Cause**: Deal sends traffic from countries not covered by BidSwitch targeting groups
- **Symptoms**: Zero bid requests received, "Too few Requests Sent" in BidSwitch
- **Diagnostic**: Check if deal geography matches targeting groups (8643: EU, 9000: BR)
- **NEW - Double Geo-Targeting Issue (Critical Discovery)**:
  - **Root Cause**: Buyer and seller both applying geo-targeting with different geo-resolution libraries
  - **Impact**: Can reduce delivery by 50-80%, especially severe for CTV deals
  - **Detection**: Check both deal settings (BidSwitch targeting groups) and line item filters for geo restrictions
  - **Symptoms**: High bid request volume but low matches, delivery drop correlates with geo-targeting activation
  - **Industry Solution**: Remove geo-targeting from supply-side, let buyer handle exclusively
  - **Rationale**: Different libraries resolve same location to different codes causing mismatches
  - **Industry Quote**: *"We've seen increasingly over the last 2 to 3 months... delivery gets hammered massively when we on the supply side layer in Geo"* - Benjamin Christie, Gourmet Ads
  - **Prevention**: Document geo-targeting responsibility in deal terms upfront (default: buyer-side only)
  - **Expected Impact**: 60-80% delivery volume restoration (immediate effect)
  - **Tribal Knowledge Note**: This issue took industry leaders months to discover through trial and error
- **Solution**: Verify deal geography using BidSwitch Deals Discovery country filtering
- **Prevention**: Use BidSwitch API for complete deal geographic metadata (requires API access)
- **Immediate Fix**: Create additional targeting groups for deal's source countries OR remove supply-side geo entirely

**Bid Price Too Low:**
- **Cause**: Base bid price below market rates
- **Solution**: Increase bid price or enable bid optimization
- **Analysis**: Check bid floor metrics and win rate data

**Creative Issues:**
- **Cause**: Creatives not approved or incorrect dimensions
- **Solution**: Verify creative approval status and specifications
- **Check**: Ensure creative formats match inventory requirements

### Low Win Rate

#### Symptoms
- High bid request volume but low impressions
- Poor bid-to-impression conversion
- Competitive disadvantage in auctions

#### Diagnostic Approach

**1. Analyze Bid Performance Metrics**
```
Key Metrics to Review:
- Bid Requests: Total opportunities received
- Bid Responses: Bids submitted to auctions
- Win Rate: (Impressions / Bid Responses) * 100
- Response Rate: (Bid Responses / Bid Requests) * 100
```

**2. Check Grafana Dashboards**
Access: `https://grafana.monitoring.bedrockplatform.bid/`
- **Health - Delivery Dashboard**: Monitor real-time bid performance
- **Campaign Performance**: Track win rates by campaign and line item
- **SSP Performance**: Analyze performance by supply source

**3. Price Analysis**
```sql
-- Analyze bid pricing vs. market rates
SELECT 
  DATE(created_at) as date,
  AVG(bid_price) as avg_bid_price,
  AVG(floor_price) as avg_floor_price,
  COUNT(*) as total_bids,
  SUM(CASE WHEN won = true THEN 1 ELSE 0 END) as wins,
  (SUM(CASE WHEN won = true THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as win_rate
FROM bidstream_v2 
WHERE line_item_id = 'your_line_item_id'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

#### Solutions

**Increase Bid Prices:**
- Analyze competitive landscape and adjust base bid prices
- Implement bid multipliers for high-value inventory
- Enable automatic bid optimization features

**Optimize Targeting:**
- Reduce competition by refining audience targeting
- Focus on less competitive inventory sources
- Adjust time-based targeting to avoid peak competition

**Improve Creative Performance:**
- Test different creative formats and sizes
- Optimize creative content for better engagement
- Ensure creative compliance with SSP requirements

### Budget Pacing Issues

#### Under-Pacing (Most Common)

**Symptoms:**
- Campaign spending below target pace
- Budget not being fully utilized
- Poor delivery against flight dates

**Diagnostic Steps:**
1. **Check Pacing Settings**: Verify even vs. ASAP pacing configuration
2. **Analyze Traffic Patterns**: Review available inventory volume
3. **Evaluate Competition**: Assess competitive pressure in target segments
4. **Review Bid Strategy**: Check if bid prices are competitive

**Solutions:**
- **Increase Bid Prices**: Raise base bid or implement bid multipliers
- **Broaden Targeting**: Expand geographic or demographic targeting
- **Adjust Pacing**: Switch from even to ASAP pacing if appropriate
- **Add Inventory Sources**: Include additional SSPs or deal types

#### Over-Pacing (Rare but Critical)

**Symptoms:**
- Campaign spending ahead of target pace
- Budget exhaustion risk before flight end
- Potential billing discrepancies

**Immediate Actions:**
1. **Verify Spend Data**: Compare Looker vs. BidSwitch spend (should be within 10-20%)
2. **Check for Discrepancies**: Investigate unusual spending patterns
3. **Adjust Pacing**: Implement stricter pacing controls
4. **Emergency Stop**: Pause campaign if overspend is severe

### No Bid Responses

#### Symptoms
- High bid request volume but zero bid responses
- Bidder not participating in auctions
- Complete lack of campaign activity

#### Diagnostic Process

**1. Check System Health**
```bash
# Verify bidder service status
kubectl get pods -n production | grep bidder

# Check bidder logs for errors
kubectl logs -f deployment/bidder -n production --tail=100
```

**2. Verify Configuration Sync**
- Check if campaign configuration is properly synced to Aerospike
- Verify line item settings are correctly loaded
- Confirm targeting parameters are valid

**3. Analyze Bid Request Processing**
```
Common Issues:
- Invalid targeting configuration
- Malformed bid request data
- Service connectivity problems
- Aerospike lookup failures
```

#### Solutions

**Configuration Issues:**
- Restart syncer service to refresh configuration
- Verify Aerospike connectivity and data integrity
- Check for invalid targeting parameters

**Service Issues:**
- Restart bidder deployment if in error state
- Scale up bidder replicas if under high load
- Check network connectivity between services

**Data Issues:**
- Verify user segment data availability
- Check frequency capping data integrity
- Validate campaign configuration format

## Performance Diagnostics

### Key Performance Metrics

#### Funnel Analysis
```
Performance Funnel:
1. Bid Requests (Avails) → Total opportunities
2. Bid Responses → Platform participation rate
3. Impressions → Auction win rate
4. Clicks → Creative performance
5. Conversions → Campaign effectiveness
```

#### Critical KPIs
- **Response Rate**: (Bid Responses / Bid Requests) × 100
- **Win Rate**: (Impressions / Bid Responses) × 100
- **CTR**: (Clicks / Impressions) × 100
- **Conversion Rate**: (Conversions / Impressions) × 100
- **eCPM**: (Total Spend / Impressions) × 1000

### Grafana Monitoring

#### Essential Dashboards
**Health - Delivery Dashboard:**
- Real-time bid request volume
- Response rates by service
- Error rates and latency metrics
- System resource utilization

**Campaign Performance Dashboard:**
- Campaign-level delivery metrics
- Line item performance comparison
- Creative performance analysis
- Audience segment effectiveness

#### Alert Thresholds
```yaml
Critical Alerts:
- Bid response rate < 50%
- Win rate < 5%
- Error rate > 10%
- Latency > 200ms

Warning Alerts:
- Bid response rate < 70%
- Win rate < 10%
- Error rate > 5%
- Budget utilization < 80% of pace
```

### Looker Analytics

#### Campaign Analysis
Access: `https://lookerstudio.google.com/reporting/dd6073f1-04b4-482b-8014-5d0edcb42cdd/`

**Key Reports:**
- Campaign delivery summary
- Line item performance breakdown
- Creative performance analysis
- Audience segment effectiveness
- Supply source performance

#### Spend Verification
**Daily Spend Check:**
1. Compare Looker spend data with BidSwitch reporting
2. Acceptable variance: 10-20%
3. Investigate discrepancies > 20%
4. Check for billing or tracking issues

## Emergency Procedures

**System Outage**: Check Grafana dashboard, verify external dependencies (BidSwitch, Aerospike, PostgreSQL), review recent deployments.

**Budget Protection**: Emergency pause via SQL: `UPDATE "campaigns" SET "status" = 'paused' WHERE "campaignId" = 'id';`

> **Note**: Detailed emergency procedures and kubernetes commands available in separate incident response documentation.

## Database Schema Quick Reference

**TerminalDB (PostgreSQL)**: `campaigns` (statusId: 1=Enabled, 2=Disabled, 3=Deleted), `lineItems`, `statuses`

**AggregationDB (Redshift)**: `overview` table (campaign_id, line_item_id, media_spend, impressions)

**MetricsDB (VictoriaMetrics)**: `biddersrv_bidder_avails` (rejection reasons), `biddersrv_bidder_capping` (pacing controls)

> **Note**: Full database schema and API authentication details available in [Database Management](../07-maintenance/database-management.md).

### Critical Diagnostic Guidelines

#### Pacing System Interpretation
```yaml
CRITICAL - Prevents False Alarms:
Normal Behavior:
  - Capping ratios 15-25:1 during mid-campaign budget accumulation
  - 95% bid rejection is healthy pacing behavior
  - System self-corrects as campaign deadline approaches

Timeline-Based Assessment:
  - >14 days remaining: Expect natural self-correction
  - 7-14 days remaining: Monitor acceleration trends  
  - <7 days remaining: Consider intervention if no acceleration

Escalation Criteria:
  - High capping (>20:1) AND <7 days remaining AND declining spend
  - NOT: High capping alone during budget accumulation periods
```

## Diagnostic Tools & Commands

### Database Queries

#### Campaign Health Check
```sql
-- Comprehensive campaign status
SELECT 
  c."name" AS campaign,
  c."status" AS campaign_status,
  c."startDate",
  c."endDate",
  c."totalBudget" AS campaign_budget,
  COUNT(l."lineItemId") AS line_items,
  SUM(l."totalBudget") AS total_line_item_budget,
  COUNT(CASE WHEN l."status" = 'active' THEN 1 END) AS active_line_items
FROM "campaigns" c
LEFT JOIN "lineItems" l ON c."campaignId" = l."campaignId"
WHERE c."accountId" = 'your_account_id'
GROUP BY c."campaignId", c."name", c."status", c."startDate", c."endDate", c."totalBudget"
ORDER BY c."startDate" DESC;
```

#### Performance Analysis
```sql
-- Line item performance summary
SELECT 
  l."name" AS line_item,
  l."totalBudget",
  COALESCE(SUM(o.impressions), 0) AS impressions,
  COALESCE(SUM(o.clicks), 0) AS clicks,
  COALESCE(SUM(o.media_spend), 0) AS spend,
  CASE 
    WHEN SUM(o.impressions) > 0 
    THEN (SUM(o.clicks) * 100.0 / SUM(o.impressions))
    ELSE 0 
  END AS ctr,
  CASE 
    WHEN SUM(o.impressions) > 0 
    THEN (SUM(o.media_spend) * 1000.0 / SUM(o.impressions))
    ELSE 0 
  END AS cpm
FROM "lineItems" l
LEFT JOIN overview o ON l."lineItemUuid" = o.line_item_id
WHERE l."campaignId" = 'your_campaign_id'
  AND o.date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY l."lineItemId", l."name", l."totalBudget"
ORDER BY spend DESC;
```

### Kubernetes Diagnostics

#### Pod Health Check
```bash
# Check all pods status
kubectl get pods -n production

# Check specific service logs
kubectl logs -f deployment/bidder -n production --tail=100

# Check pod resource usage
kubectl top pods -n production

# Describe problematic pod
kubectl describe pod <pod-name> -n production
```

#### Service Connectivity
```bash
# Test internal service connectivity
kubectl exec -it <bidder-pod> -n production -- curl http://exchange:8080/health

# Check service endpoints
kubectl get endpoints -n production

# Verify service configurations
kubectl get configmaps -n production
```

### Aerospike Diagnostics

#### Data Verification
```bash
# Connect to Aerospike
kubectl run -it aerospike-tools-$(whoami) \
  --namespace production \
  --restart=Never \
  --rm \
  --image=aerospike/aerospike-tools \
  --command -- \
  aql \
  -h aerodb-aerospike.production.svc.cluster.local \
  -p 3000 \
  -T 60000

# Check segment data
SELECT * FROM dmp.markers WHERE PK = 'test_marker_id' LIMIT 10;

# Check campaign configuration
SELECT * FROM campaign_config.line_items WHERE PK = 'line_item_id' LIMIT 5;
```

## Automated Diagnostic Agent Workflow

**Agent Decision Flow**:
1. Campaign Selection → Basic Checks (date alignment, budget, bidder activity) → PMP Verification → Timeline Assessment → Escalation Decision

**Escalation Triggers**: Budget >95% exhausted, line items end after campaign, zero bidder activity, deal targeting issues, high capping (<7 days remaining + declining spend).

> **Note**: Full SQL queries and automation scripts available in agent prompt documentation.

## Troubleshooting Workflow

**Standard Process**: Initial Assessment (identify symptoms, check Grafana) → Data Collection (metrics, logs, SQL queries) → Root Cause Analysis → Resolution → Documentation.

**Escalation**: Level 1 (0-30min): Self-service | Level 2 (30-60min): Team support | Level 3 (60min+): Emergency response.

## Best Practices

### Proactive Monitoring
- **Set Up Alerts**: Configure comprehensive alerting for key metrics
- **Regular Health Checks**: Perform daily system health reviews
- **Performance Baselines**: Establish normal performance benchmarks
- **Trend Analysis**: Monitor long-term performance trends

### Documentation
- **Incident Reports**: Document all significant issues and resolutions
- **Runbook Updates**: Keep troubleshooting procedures current
- **Knowledge Sharing**: Share learnings with team members
- **Process Improvement**: Continuously refine diagnostic procedures

### Prevention Strategies
- **Testing Protocols**: Implement thorough testing before deployments
- **Gradual Rollouts**: Use staged deployment strategies
- **Monitoring Coverage**: Ensure comprehensive system monitoring
- **Regular Maintenance**: Perform routine system maintenance

## Related Topics
- [System Monitoring](system-monitoring.md) - Comprehensive monitoring and alerting setup
- [Performance Optimization](performance-optimization.md) - Campaign and system optimization techniques
- [Platform Architecture](../03-technical-features/platform-architecture.md) - Understanding system components
- [Data Quality Management](data-quality-management.md) - Traffic validation and fraud detection
