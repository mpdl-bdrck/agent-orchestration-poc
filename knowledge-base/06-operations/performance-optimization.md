# Performance Optimization

## Overview

Strategies for optimizing campaign performance, bid efficiency, and system throughput. Focuses on actionable optimizations for campaign managers and troubleshooting agents.

---

## Key Performance Indicators

**Primary Metrics**:
- CTR: (Clicks / Impressions) × 100
- Conversion Rate: (Conversions / Impressions) × 100
- Win Rate: (Impressions / Bid Responses) × 100
- eCPM: (Total Spend / Impressions) × 1000
- CPA: Total Spend / Conversions
- ROAS: Revenue / Total Spend

---

## Win Rate Benchmarks

| Win Rate | Status | Action Required |
|----------|--------|-----------------|
| **< 1%** | CRITICAL | Immediate bid optimization, check targeting |
| **1-3%** | Below benchmark | Monitor closely, consider bid increases |
| **3-7%** | Healthy | Continue monitoring, optimize efficiency |
| **7-15%** | Excellent | Monitor for overbidding |
| **> 15%** | Investigate | Review cost efficiency, verify inventory quality |

**Context Matters**:
- Prospecting campaigns: 1-5% acceptable
- Retargeting campaigns: 5-15% expected
- Premium publishers: 2-8% typical
- Open exchange: 3-12% typical
- PMP deals: 5-20% typical

---

## Campaign Optimization

### Structure Best Practices

**Segment by**:
- Device type (desktop, mobile, tablet)
- Creative format (display, video, native)
- Audience type (prospecting vs. retargeting)
- Geographic regions (high-value vs. expansion)
- Inventory quality (premium vs. open exchange)

### Budget Allocation

**Performance-Based Rules**:
- High performers: Increase 20-50%
- Underperformers: Reduce 30-50% or pause if CPA > target by 100%
- Testing budget: Allocate 10-20% for new tests

---

## Bid Strategy Optimization

### Bid Price Components
```
Base Bid + Data Fees + Multipliers - Margin (20%) - Hedge (6%) = Final Bid to SSP
```

### Bid Multipliers (Examples)
- **Device**: Desktop 1.0x, Mobile 0.8x, Tablet 1.2x
- **Time**: Peak hours (9-17) 1.3x, Evening 1.1x, Overnight 0.7x
- **Geography**: Tier 1 cities 1.5x, Tier 2 1.0x, Rural 0.6x
- **Inventory**: Premium publishers 2.0x, Verified 1.2x, Open 1.0x

### Optimization Triggers

**Increase Bids When**:
- Win rate < 3% AND budget remaining
- Strong conversion despite low win rate
- Competitive analysis shows room for increase

**Decrease Bids When**:
- Win rate > 15% AND cost efficiency declining
- Inventory quality concerns
- Budget pacing ahead of schedule

**Maintain When**:
- Win rate 3-7% with healthy metrics
- Meeting campaign objectives
- Stable competitive environment

---

## Audience Optimization

### Segmentation Strategy

**By Intent Level**:
- **High Intent**: Recent converters, cart abandoners, product viewers (last 3 days)
- **Medium Intent**: Category browsers (last 14 days), email subscribers, social engagers
- **Low Intent**: Brand aware (last 30 days), lookalikes, demographic targets

### Frequency Optimization

**Optimal Frequency by Campaign Type**:
- Brand Awareness: 3 daily, 15 weekly, 50 lifetime
- Performance: 5 daily, 25 weekly, 100 lifetime
- Retargeting: 8 daily, 40 weekly, 200 lifetime

---

## Creative Optimization

### Testing Framework

**Test Variables**: Headlines, CTAs, colors, image vs. video, sizes/formats

**Requirements**: Minimum 1000 impressions per creative, 95% statistical significance, 7-14 days duration

### Performance Hierarchy

**By Format**:
1. Native ads (highest engagement)
2. Video ads (engaging)
3. Rich media (interactive)
4. Standard display
5. Text-only (lowest)

**By Size** (Desktop):
- 728x90 (Leaderboard): High availability
- 300x250 (Medium Rectangle): Best CTR
- 160x600 (Wide Skyscraper): Premium placements

**By Size** (Mobile):
- 320x50 (Mobile Banner): Standard
- 300x250 (Mobile Rectangle): Cross-device
- 320x480 (Interstitial): High impact

---

## System Performance

### Bid Response Optimization

**Latency Targets**:
- Bid processing: <50ms (target), <100ms (acceptable)
- Database queries: <10ms
- Enrichment pipeline: <100ms total

**Optimization Techniques**:
- Connection pooling (50-100 connections)
- Query caching (5-15 minute TTL)
- Async processing for non-critical operations
- Geographic CDN distribution

### Database Performance

**Query Optimization**:
- Index critical fields (campaign_id, line_item_id, date)
- Use covering indexes where possible
- Partition large tables by date
- Regular VACUUM and ANALYZE operations

**Aerospike Optimization**:
- Set appropriate TTL for all records
- Use batch operations (100-1000 records)
- Monitor namespace memory usage
- Configure replication factor appropriately

---

## Performance Monitoring

### Grafana Dashboards

**Essential Dashboards**:
- **Health - Delivery**: Real-time bid volume, response rates, error rates
- **Campaign Performance**: Campaign/line item delivery, win rates, creative performance
- **SSP Performance**: Performance by supply source

**Access**: `https://grafana.monitoring.bedrockplatform.bid/`

### Alert Thresholds

**Critical Alerts**:
- Bid response rate < 50%
- Win rate < 1%
- Error rate > 10%
- Latency > 200ms

**Warning Alerts**:
- Bid response rate < 70%
- Win rate < 3%
- Error rate > 5%
- Budget utilization < 80% of pace

---

## Continuous Optimization

### Weekly Cycle

1. **Monday**: Review weekend performance, adjust budgets
2. **Wednesday**: Mid-week check, optimize underperformers
3. **Friday**: Weekly analysis, plan next week strategy

### Monthly Review

- Analyze month-over-month trends
- Review benchmark achievement
- Adjust strategic priorities
- Test new optimization approaches

---

## Best Practices

**Campaign Optimization**:
- Test multiple audiences (identify top performers)
- A/B test creatives continuously
- Monitor frequency metrics (prevent fatigue)
- Regular bid strategy reviews

**Technical Optimization**:
- Monitor system health daily
- Optimize slow queries weekly
- Review database performance monthly
- Maintain connection pools and caching

**Data-Driven**:
- Weekly performance reviews with data
- Statistical significance before changes
- Document optimization results
- Build institutional knowledge

---

## Related Topics

- [Campaign Troubleshooting](campaign-troubleshooting.md) - Issue diagnosis and resolution
- [Deal Debug Workflow](deal-debug-workflow.md) - Deal-specific optimization
- [System Monitoring](system-monitoring.md) - Monitoring and alerting setup
