# Retargeting

## Overview

Retargeting enables advertisers to reach users who have previously interacted with their website or content. The Bedrock Platform provides comprehensive retargeting capabilities through pixel tracking, audience segmentation, and targeted campaign delivery using advanced user sync technology and real-time bidding integration.

## Key Features

### Pixel Generation & Management
- **Custom Retargeting Pixel Creation**: Users can generate custom retargeting pixels through the UI
- **Easy Website Implementation**: Simple pixel code placement on advertiser websites
- **Real-time User Tracking**: Automatic user identification and segment assignment
- **Segment Monitoring**: Track active user counts for each retargeting segment through dedicated UI

### Audience Segmentation
- **Automatic Segment Creation**: Segments created from pixel firing data stored in Aerospike
- **Custom Segment Definitions**: Define audience rules based on user behavior patterns
- **Segment Size Analytics**: Monitor how many active users belong to each segment in real-time
- **TTL Management**: Configure time-to-live settings for segment membership (7, 14, 30, 90 days, or lifetime)

### Campaign Targeting
- **Segment-Based Targeting**: Target specific retargeting segments in line items with JSON configuration
- **Combined Targeting**: Integrate with other targeting parameters (geo, device, contextual)
- **Advanced Bidding**: Specialized bidding strategies for retargeted users with multipliers
- **Curation Package Integration**: Apply retargeting to curated inventory packages

## Technical Architecture

**Core Flow**: User visits site → Pixel fires → BidSwitch user sync → Aerospike segment storage → Bidder enriches bid requests → Targeted delivery.

**Key Components**: Sync endpoint (`sync.bedrockplatform.bid`), Aerospike (markers & counters), EnrichmentPipeline (100ms timeout), BidSwitch integration (dsp_id=503).

> **Note**: Full technical architecture details in [Platform Architecture](../03-technical-features/platform-architecture.md).

## Implementation Process

1. **Pixel Setup**: Generate pixel in Terminal UI, place on advertiser pages, configure BidSwitch user sync, define segments with TTL
2. **Audience Building**: Monitor pixel firing, track segment population via `getsize` API, manage TTL refresh
3. **Campaign Targeting**: Create line items with segment filters (JSON config), set bid multipliers, allocate budget

## Line Item Configuration Example

```json
{
  "Filters": [{
    "FilterType": "segment",
    "Group": 1,
    "Values": [{"id": "segment_uuid", "type": "bedrock_retargeting"}]
  }],
  "BaseBidPrice": 0.85
}
```

## Segment Management & Analytics

### TTL Configuration Options
- **Lifetime Segments**: Permanent user assignment (TTL = -1)
- **Short-Term Segments**: 7-day windows for immediate retargeting
- **Medium-Term Segments**: 14-30 day windows for nurture campaigns  
- **Long-Term Segments**: 90-day windows for brand awareness
- **Custom TTL**: Configurable based on specific campaign objectives

### Segment Size Monitoring
- **Real-Time API**: `audiencesegment.getsize` method provides current segment population
- **Daily Aggregation**: Rolling counters track segment growth and decay over time
- **UI Dashboard**: Terminal interface shows active user counts per segment with trends
- **Performance Metrics**: Track segment match rates, bid success, and conversion performance

### Data Refresh Mechanism
- **Sync-Based Refresh**: User return visits trigger TTL extension for relevant segments
- **Independent Refresh**: Each segment refreshes separately based on individual user behavior
- **Counter Updates**: Automatic adjustment of daily segment counters during refresh
- **Version Management**: Incremental versioning for segment data structure updates

## Advanced Retargeting Strategies

### Behavioral Segments
- **Product Category Viewers**: Users who browsed specific product categories
- **Cart Abandoners**: Users who added items but didn't complete purchase  
- **Previous Customers**: Users who completed purchases in specified time windows
- **High-Value Prospects**: Users who viewed premium products or spent significant time on site
- **Repeat Visitors**: Users with multiple site visits but no conversion

### Sequential Retargeting
- **Awareness Stage**: Brand introduction for first-time visitors
- **Consideration Stage**: Product-focused messaging for engaged users
- **Decision Stage**: Incentive-based offers for users near conversion
- **Retention Stage**: Cross-sell and upsell to existing customers

### Cross-Device Retargeting
- **BidSwitch Integration**: Leverage cross-device user matching capabilities
- **Multi-Platform Reach**: Target users across web, mobile web, and in-app environments
- **Consistent Messaging**: Maintain campaign continuity across device types
- **Attribution Tracking**: Track conversions across multiple devices and touchpoints

## Performance Optimization

### Key Performance Indicators
- **Segment Match Rate**: Percentage of bid requests with successful segment matches
- **Retargeting Lift**: Performance improvement vs. prospecting campaigns
- **Conversion Rate**: Percentage of retargeted users completing desired actions
- **Cost Efficiency**: CPA comparison between retargeting and acquisition campaigns
- **Frequency Distribution**: Optimal exposure levels for different audience segments

### Optimization Strategies
- **Segment Refinement**: Continuously improve segment definitions based on performance data
- **Bid Multiplier Testing**: Test different bid adjustments for various retargeting segments
- **Creative Personalization**: Develop segment-specific creative messaging and offers
- **Frequency Management**: Implement optimal frequency caps to prevent ad fatigue
- **Cross-Campaign Coordination**: Coordinate retargeting with other marketing channels

### Monitoring & Alerting
**Key Metrics Tracked:**
- `matched_users`: Exchange metric tracking BidSwitch user ID matches by region
- `segment_match_total`: Bidder metric logging successful segment matches (provider = bedrock_retargeting)
- `bedrock_user_not_found`: Bidder metric indicating user sync issues or TTL problems

**Performance Alerts:**
- Segment size drops below minimum thresholds
- Match rate decreases indicating sync issues
- TTL configuration problems affecting segment population
- Pixel firing failures or implementation issues

## Privacy & Compliance

### Data Protection Framework
- **GDPR Compliance**: Respect consent parameters in all tracking and sync activities
- **User Consent Management**: Implement proper consent collection and validation
- **Data Minimization**: Collect only necessary data for retargeting purposes
- **Retention Policies**: Align segment TTL with privacy policy commitments and legal requirements

### User Rights & Controls
- **Opt-Out Mechanisms**: Provide clear methods for users to opt out of retargeting
- **Data Access**: Enable users to request information about their segment membership
- **Data Deletion**: Implement processes for removing user data upon request
- **Transparency**: Clear disclosure of retargeting practices and data usage

### Technical Privacy Implementation
- **Anonymization**: Remove personally identifiable information from tracking data
- **Secure Storage**: Encrypt user data in Aerospike with appropriate access controls
- **Audit Logging**: Track all data access and modification activities
- **Cross-Border Compliance**: Ensure data handling meets requirements across all operating regions

## Troubleshooting & Diagnostics

### Common Issues & Solutions

#### Low Segment Population
- **Pixel Implementation**: Verify pixel firing correctly across all target pages
- **Traffic Volume**: Ensure sufficient website traffic to build meaningful audiences (minimum 1,000 users)
- **Segment Criteria**: Review and adjust overly restrictive segment definitions
- **TTL Configuration**: Check if segment expiration is too aggressive for campaign objectives

#### User Sync Problems
- **BidSwitch Integration**: Verify sync endpoint configuration and parameter passing
- **User ID Mapping**: Check Aerospike for proper marker-to-segment relationships
- **GDPR Compliance**: Ensure consent parameters are properly handled in sync requests
- **Cross-Domain Issues**: Validate pixel functionality across all advertiser domains

#### Performance Issues
- **Match Rate Drops**: Investigate segment data availability during bid processing
- **Bidder Enrichment**: Check enrichment pipeline timeout and error handling
- **Counter Accuracy**: Validate daily segment counter updates and aggregation
- **Reporting Discrepancies**: Compare segment match logs with campaign performance data

### Diagnostic Tools & Methods
- **Segment Size API**: Use `getsize` method to validate current segment populations
- **Aerospike Queries**: Direct database queries to investigate user-segment mappings
- **Bid Request Logging**: Analyze enrichment pipeline performance and segment injection
- **Pixel Testing**: Validate pixel firing and user sync across different browsers and devices

## Getting Started Guide

### Initial Setup Checklist
1. **Pixel Generation**: Create retargeting pixel in Terminal UI with appropriate segment configuration
2. **Website Integration**: Implement pixel code on all relevant advertiser pages
3. **Segment Definition**: Configure behavioral triggers, TTL settings, and audience criteria
4. **User Sync Validation**: Test BidSwitch integration and user ID mapping
5. **Campaign Creation**: Set up line items with retargeting segment filters
6. **Performance Monitoring**: Implement tracking for key metrics and segment health

### Success Metrics & Benchmarks
- **Audience Growth**: Steady increase in retargeting segment populations over 2-4 weeks
- **Match Rate**: 60%+ of eligible bid requests successfully matched with segments
- **Performance Lift**: 20-40% improvement in CTR and conversion rates vs. prospecting
- **Cost Efficiency**: 15-30% lower CPA for retargeting campaigns vs. acquisition campaigns

## Integration Points

### Platform Components
- **Terminal UI**: Segment creation, monitoring, campaign setup, and performance analytics
- **User Sync Service**: Manages pixel firing, BidSwitch integration, and user identification
- **Aerospike Database**: Stores user-segment mappings with TTL management and counter tracking
- **Bidder Service**: Processes segment targeting during real-time auctions with enrichment pipeline
- **Tracker Service**: Records impressions, clicks, and conversions for retargeted users
- **Exchange Service**: Logs segment matches and performance data for reporting

### External Integrations
- **BidSwitch**: User matching and cross-platform synchronization
- **Supply Partners**: Segment data passing through OpenRTB bid requests
- **Analytics Platforms**: Integration with advertiser analytics for attribution tracking
- **Tag Management**: Coordination with existing pixel and tag management systems

## Related Topics
- [Campaign Management](campaign-management.md) - Setting up retargeting campaigns and line items
- [Frequency Capping](frequency-capping.md) - Managing ad exposure for retargeted users
- [Platform Architecture](../03-technical-features/platform-architecture.md) - Technical implementation details
- [Reporting and Analytics](reporting-analytics.md) - Performance tracking and optimization
- [User Role Management](../06-operations/user-role-management.md) - Access control for retargeting features