# Frequency Capping

## Overview

Frequency capping ensures that individual users don't see the same ad from particular line items too frequently, preventing ad fatigue and optimizing campaign performance. The Bedrock Platform implements sophisticated frequency controls using Aerospike storage and real-time bidding logic to manage impression limits across multiple time periods.

## Key Features

### Multi-Period Capping
- **Lifetime Capping**: Total impression limits for the entire campaign duration (frequency = -1)
- **Time-Based Periods**: Daily (86400s), hourly (3600s), weekly (604800s), and monthly (2592000s) frequency controls
- **Independent Limits**: Multiple time spans can be configured simultaneously and enforced independently
- **Granular Control**: Different limits for different line items and user segments

### User Identification
- **Primary ID**: Bedrock user ID for logged-in or cookied users
- **Fallback ID**: IFA (Identifier for Advertising) for mobile app environments
- **Cross-Device Tracking**: Consistent frequency management across user devices
- **Privacy Compliance**: Respects user consent and privacy preferences

### Real-Time Processing
- **Bidder Integration**: Frequency checks during bid request processing with Aerospike lookups
- **High-Performance Storage**: Aerospike database for sub-millisecond impression counting
- **Tracker Updates**: Real-time impression recording and counter updates on win notifications
- **TTL Management**: Automatic expiration of frequency data based on configured time periods

## Technical Architecture

### Frequency Capping Flow

1. **Bid Request Processing**: Bidder receives OpenRTB request from exchange
2. **Campaign Filtering**: System identifies eligible campaigns and line items with targeting match
3. **Frequency Check**: Bidder queries Aerospike for user's impression history across all configured time periods
4. **Capping Decision**: If any frequency limit exceeded, bid is suppressed and `capping` metric incremented
5. **Impression Tracking**: Tracker receives win notification and updates frequency counters
6. **TTL Management**: Appropriate TTL set on records based on longest configured capping policy

### Aerospike Data Structure

**Frequency Counter Storage:**
```
Namespace: frequency_capping
Set: user_impressions

Key Format Examples:
- "user-id:123123-123-12312312:232314123-2134123-234:lifetime"
- "user-id:123123-123-12312312:232314123-2134123-234:86400"  // daily
- "ifa:23123-123-12312312:232314123-2134123-234:3600"       // hourly

Record Structure:
- Value: Integer (current impression count)
- TTL: Matches the time span configuration (seconds)
```

### Configuration Format

**Terminal JSON Configuration:**
```json
{
  "cappings": [
    {
      "frequency": -1,      // Lifetime (-1 = permanent)
      "value": 200          // Maximum 200 impressions lifetime
    },
    {
      "frequency": 2592000, // Monthly (30 days in seconds)
      "value": 100          // Maximum 100 impressions per month
    },
    {
      "frequency": 604800,  // Weekly (7 days in seconds)
      "value": 30           // Maximum 30 impressions per week
    },
    {
      "frequency": 86400,   // Daily (24 hours in seconds)
      "value": 5            // Maximum 5 impressions per day
    },
    {
      "frequency": 3600,    // Hourly (1 hour in seconds)
      "value": 2            // Maximum 2 impressions per hour
    }
  ]
}
```

### Time Period Definitions

| **Period** | **Frequency Value** | **Duration** | **Use Case** |
|------------|-------------------|--------------|--------------|
| Lifetime | -1 | Campaign duration | Brand awareness, reach campaigns |
| Monthly | 2592000 | 30 days | Long-term engagement campaigns |
| Weekly | 604800 | 7 days | Regular promotion cycles |
| Daily | 86400 | 24 hours | High-frequency campaigns |
| Hourly | 3600 | 1 hour | Time-sensitive promotions |

## Implementation

1. **Configure in Terminal UI**: Set capping parameters (JSON format), validate alignment with campaign goals
2. **System Sync**: Terminal → Syncer → Aerospike → Bidder processes updated configs
3. **Tracking**: Tracker records impressions, updates Aerospike counters with TTL, monitor via Grafana

## Frequency Capping Strategies

**By Campaign Type**:
- Brand Awareness: 50-100 lifetime, 3-5 daily (maximize reach)
- Performance: 20-30 lifetime, 2-3 daily, 1 hourly (optimize conversions)
- Retargeting: 15-25 lifetime, 1-2 daily (prevent fatigue)

**By User Segment**: High-value (8-12 daily), new users (2-3 daily), converted (1 daily or exclude)

## Performance Monitoring

**Metrics**: `capping` (by campaign, lineitem, reason), capping rate, reach vs. frequency, conversion impact.

**Optimization**: Analyze performance by frequency level, find optimal sweet spot, manage cross-campaign exposure.

**Advanced**: Account-level capping, engagement-based adjustments, device-specific controls, privacy-compliant (GDPR, consent-based, IFA fallback).

## Testing & Validation

**Test Scenarios**: Single user (verify caps enforced), multiple periods (independent enforcement), performance (load testing, latency measurement).

**QA Checklist**: Terminal config correct, Syncer writes to Aerospike, Bidder checks limits, Tracker updates counters with TTL, metrics track properly, privacy maintained.

## Troubleshooting

**Common Issues**: Caps not working (verify Terminal UI config, Aerospike connectivity, user ID consistency), over/under-aggressive capping, bidder latency, counter sync problems.

**Diagnostics**: Query Aerospike (`frequency_capping.user_impressions`), monitor capping metrics, analyze performance correlation.

## Best Practices

**Configuration**: Start conservative, test incrementally, use segment-specific caps, coordinate with creative rotation.

**Optimization**: Regular review, A/B testing, cross-campaign analysis, monitor for ad fatigue.

**Maintenance**: Monitor Aerospike performance, audit configurations, analyze metrics trends.

## Integration Points

### Platform Components
- **Terminal UI**: Frequency cap configuration interface and campaign management dashboard
- **Syncer Service**: Transfers frequency capping configuration from Terminal to Aerospike database
- **Bidder Service**: Real-time frequency checking during bid request processing with sub-millisecond lookups
- **Tracker Service**: Impression recording and frequency counter updates on win notifications
- **Aerospike Database**: High-performance storage for frequency counters with TTL management and cleanup

### External Systems
- **Supply Partners**: Frequency data consideration in bid request processing and auction participation
- **Analytics Platforms**: Frequency impact analysis, performance correlation, and optimization recommendations
- **Reporting Systems**: Frequency capping metrics integration for campaign analysis and client reporting
- **Monitoring Tools**: System performance monitoring, database health tracking, and alerting systems

## Related Topics
- [Campaign Management](campaign-management.md) - Setting up campaigns with frequency controls and optimization
- [Retargeting](retargeting.md) - Frequency management for retargeted audiences and sequential messaging
- [Platform Architecture](../03-technical-features/platform-architecture.md) - Technical implementation details and system integration
- [Reporting and Analytics](reporting-analytics.md) - Frequency impact analysis, performance tracking, and optimization
- [User Role Management](../06-operations/user-role-management.md) - Access control for frequency capping configuration and management
