# Analytics Platforms Integration

## Overview

Bedrock Platform provides comprehensive analytics and measurement capabilities through integrated reporting systems, external analytics platform connections, and advanced tracking infrastructure. These integrations enable detailed performance analysis, attribution modeling, and business intelligence across all campaign activities.

## Core Analytics Architecture

### Internal Analytics Stack
- **Redshift Data Warehouse**: Primary analytics database for aggregated reporting data
- **BigQuery (GCP)**: Regional analytics processing for APAC data center
- **Looker Integration**: Business intelligence and visualization platform
- **Custom Reporting APIs**: Programmatic access to performance data
- **Real-Time Dashboards**: Live campaign performance monitoring

### Data Processing Pipeline
```
Raw Events → Fluentd → S3/GCS → AWS Glue → Redshift → Looker/APIs
     ↓           ↓        ↓         ↓         ↓         ↓
Bid Requests  Logging  Storage   ETL     Analytics  Reporting
Impressions   Pipeline  Layer   Jobs    Database   Interface
Clicks        Buffer   Archive  Process  Queries   Dashboard
Conversions   Format   Backup   Transform Aggregate Visualize
```

## Reporting & Business Intelligence

### Looker Integration
**Business Intelligence Platform:**
- **Connection**: Direct Redshift connection for real-time data access
- **Dashboards**: Pre-built campaign performance dashboards
- **Custom Reports**: Ad-hoc reporting and analysis capabilities
- **Data Exploration**: Self-service analytics for campaign managers

**Key Reporting Dimensions:**
- **Activation Objects**: Advertiser → Campaign → Line Item → Creative
- **Curation Objects**: Curation packages and data provider performance
- **Supply Objects**: SSP performance, deal analysis, inventory quality
- **Time Dimensions**: Hour, day, week, month with timezone support

### Performance Metrics
**Core KPIs:**
- **Bids**: Number of bid responses sent
- **Win Rate**: Impressions / bids percentage
- **Impressions**: Served impressions (GIVT filtered)
- **CPM**: Cost per mille (spend / impressions * 1000)
- **Clicks**: Click events (GIVT filtered)
- **CTR**: Click-through rate (clicks / impressions)
- **CPC**: Cost per click (spend / clicks)
- **Conversions**: Conversion events tracked
- **CVR**: Conversion rate (conversions / impressions)

**Advanced Metrics:**
- **Media Spend**: USD amount spent on media based on win notices
- **Media Margin**: USD amount from media margin calculations
- **Data Spend**: USD amount for data provider charges
- **Quality Scores**: Traffic quality and fraud detection metrics

### Custom Reporting APIs
**RESTful Reporting Endpoints:**
```http
GET /v1/reports/performance
Authorization: Bearer <api_key>
Content-Type: application/json

Parameters:
- start_date: YYYY-MM-DD
- end_date: YYYY-MM-DD
- group_by: advertiser,campaign,line_item,day
- metrics: impressions,clicks,spend,conversions
- filters: campaign_ids,advertiser_ids
```

**Response Structure:**
```json
{
  "data": [
    {
      "date": "2025-09-14",
      "campaign_id": "camp123",
      "campaign_name": "Summer Campaign",
      "impressions": 10000,
      "clicks": 150,
      "spend": 250.00,
      "conversions": 12,
      "ctr": 1.50,
      "cpm": 25.00,
      "cvr": 0.12
    }
  ],
  "pagination": {
    "total_records": 1,
    "has_more": false
  }
}
```

## Tracking & Measurement Infrastructure

### Event Tracking System
**Tracker Service Architecture:**
- **Win Notifications**: `/nurl` endpoint for auction win events
- **Impression Tracking**: `/imp` endpoint for ad impression events
- **Click Tracking**: `/clk` endpoint for click-through events
- **Conversion Tracking**: Custom pixel-based conversion tracking

**Tracking URLs:**
```
Win: https://tracker.bedrockplatform.bid/nurl?a={auction_id}&ab={bid_id}&ap={auction_price}
Impression: https://tracker.bedrockplatform.bid/imp?a={auction_id}&ab={bid_id}&ai={imp_id}
Click: https://tracker.bedrockplatform.bid/clk?ab={bid_id}&crid={creative_id}&cid={campaign_id}
```

### Macro Substitution System
**Auction Macros:**
| Macro | Parameter | Description |
|-------|-----------|-------------|
| `${AUCTION_ID}` | `a` | Bid request identifier |
| `${AUCTION_BID_ID}` | `ab` | Bid response identifier |
| `${AUCTION_IMP_ID}` | `ai` | Impression identifier |
| `${AUCTION_PRICE}` | `ap` | Encrypted winning price |
| `${AUCTION_CURRENCY}` | `ac` | Currency code (USD) |

**Campaign Tracking Macros:**
| Macro | Parameter | Description |
|-------|-----------|-------------|
| `${CAMPAIGN_ID}` | `cid` | Campaign identifier |
| `${CREATIVE_ID}` | `crid` | Creative identifier |
| `${PUBLISHER_ID}` | `si` | Publisher/seller identifier |
| `${TACTIC_ID}` | `lid` | Line item identifier |

**Privacy Compliance Macros:**
| Macro | Description | Source |
|-------|-------------|--------|
| `${GDPR}` | GDPR compliance flag | `request.Regs.GDPR` |
| `${GDPR_CONSENT}` | Consent string | `request.User.Consent` |
| `${US_PRIVACY}` | CCPA compliance string | `request.Regs.USPrivacy` |
| `${COPPA}` | COPPA compliance flag | `request.Regs.COPPA` |

### Conversion Tracking
**Pixel-Based Tracking:**
- **Conversion Pixels**: Custom tracking pixels for conversion events
- **Retargeting Pixels**: User segment assignment during ad serving
- **Cross-Domain Tracking**: User identification across domains
- **Attribution Windows**: Configurable attribution windows for conversions

**Conversion Pixel Implementation:**
```html
<!-- Conversion Tracking Pixel -->
<img src="https://tracker.bedrockplatform.bid/conv?
  cid={campaign_id}&
  lid={line_item_id}&
  crid={creative_id}&
  conv_type=purchase&
  conv_value=99.99&
  currency=USD" 
  width="1" height="1" style="display:none;" />
```

## External Analytics Integrations

### Third-Party Analytics Platforms
**Supported Integrations:**
- **Google Analytics**: Enhanced e-commerce tracking and attribution
- **Adobe Analytics**: Advanced segmentation and customer journey analysis
- **Facebook Analytics**: Cross-platform attribution and audience insights
- **Custom Analytics**: Webhook-based integration for proprietary systems

### Attribution & Measurement
**Attribution Models:**
- **Last-Click Attribution**: Standard last-click conversion attribution
- **First-Click Attribution**: First-touch attribution modeling
- **Multi-Touch Attribution**: Distributed attribution across touchpoints
- **Custom Attribution**: Configurable attribution windows and models

**Cross-Platform Measurement:**
- **Cross-Device Tracking**: User journey across multiple devices
- **Cross-Channel Attribution**: Attribution across paid, owned, earned media
- **Offline Conversion Tracking**: Integration with offline conversion data
- **Customer Lifetime Value**: Long-term customer value measurement

### Data Export & Integration
**Export Capabilities:**
- **CSV Export**: Scheduled and on-demand CSV data exports
- **API Integration**: Real-time data feeds to external systems
- **Webhook Notifications**: Event-driven data delivery
- **SFTP Transfer**: Secure file transfer for large datasets

**Data Formats:**
```json
// Standard Event Export Format
{
  "event_type": "impression",
  "timestamp": "2025-09-14T10:30:00Z",
  "campaign_id": "camp123",
  "line_item_id": "li456",
  "creative_id": "cre789",
  "user_id": "user123",
  "device_type": "mobile",
  "geo_country": "US",
  "spend": 0.025,
  "data_fees": 0.005,
  "segments_matched": ["seg1", "seg2"]
}
```

## Data Warehouse & ETL

### Redshift Analytics Database
**Schema Architecture:**
```sql
-- Overview aggregation table
CREATE TABLE overview (
  date DATE,
  hour INTEGER,
  advertiser_id VARCHAR(50),
  campaign_id VARCHAR(50),
  line_item_id VARCHAR(50),
  creative_id VARCHAR(50),
  
  -- Performance metrics
  bids INTEGER,
  impressions INTEGER,
  clicks INTEGER,
  conversions INTEGER,
  
  -- Financial metrics
  media_spend DECIMAL(14,5),
  media_margin DECIMAL(14,5),
  data_spend DECIMAL(14,5),
  
  -- Data provider metrics
  data_evorra_fee DECIMAL(14,5),
  data_anonymised_fee DECIMAL(14,5),
  bedrock_data_take_evorra DECIMAL(14,5),
  bedrock_data_take_anonymised DECIMAL(14,5)
);
```

**Aggregation Strategy:**
- **Hourly Aggregation**: Real-time hourly data aggregation
- **Daily Rollups**: Daily summary tables for performance
- **Monthly Archives**: Long-term storage with compression
- **Cost Optimization**: Store only aggregated data in Redshift

### ETL Processing
**AWS Glue Jobs:**
- **Impression Aggregation**: Process impression and win events
- **Click Aggregation**: Process click-through events
- **Conversion Aggregation**: Process conversion tracking events
- **Data Quality**: Validation and GIVT filtering

**Processing Pipeline:**
```python
# ETL processing example
def process_impression_data(spark, input_path, output_path):
    # Read raw impression logs
    df = spark.read.json(input_path)
    
    # Apply GIVT filtering
    filtered_df = df.filter(df.quality_score > 0.8)
    
    # Aggregate by dimensions
    aggregated_df = filtered_df.groupBy(
        "date", "hour", "campaign_id", "line_item_id"
    ).agg(
        count("*").alias("impressions"),
        sum("spend").alias("total_spend"),
        sum("data_fees").alias("total_data_fees")
    )
    
    # Write to Redshift
    aggregated_df.write.mode("append").format("redshift").save(output_path)
```

## Real-Time Analytics

### Live Dashboards
**Grafana Integration:**
- **Real-Time Metrics**: Live campaign performance monitoring
- **System Health**: Platform performance and uptime monitoring
- **Alert Management**: Automated alerts for performance issues
- **Custom Dashboards**: Configurable dashboards for different user roles

**Key Dashboard Metrics:**
- **QPS Monitoring**: Queries per second across all services
- **Win Rate Tracking**: Real-time auction win rate monitoring
- **Spend Tracking**: Live budget utilization and pacing
- **Error Rate Monitoring**: System error rates and performance issues

### Performance Monitoring
**Real-Time KPIs:**
- **Bid Response Rate**: Percentage of bid requests that receive responses
- **Latency Metrics**: P50, P95, P99 response time percentiles
- **Quality Metrics**: Traffic quality scores and fraud detection
- **Revenue Metrics**: Real-time revenue and margin tracking

## Data Quality & Validation

### GIVT Filtering
**General Invalid Traffic Detection:**
- **Bot Detection**: Automated bot and non-human traffic filtering
- **Fraud Prevention**: Advanced fraud detection algorithms
- **Quality Scoring**: Traffic source quality assessment
- **Whitelist Management**: Trusted traffic source management

**Quality Metrics:**
- **Pre-GIVT Metrics**: Raw event counts before filtering
- **Post-GIVT Metrics**: Filtered event counts for reporting
- **Quality Scores**: Numerical quality assessment (0.0-1.0)
- **Filter Reasons**: Detailed reasons for traffic filtering

### Data Validation
**Validation Processes:**
- **Schema Validation**: Ensure data conforms to expected schemas
- **Range Validation**: Validate metric values within expected ranges
- **Completeness Checks**: Verify all required fields are present
- **Consistency Validation**: Cross-validate related metrics

## Privacy & Compliance

### Privacy-Compliant Analytics
**Consent Management:**
- **GDPR Compliance**: European data protection regulation adherence
- **CCPA Compliance**: California privacy law compliance
- **Consent Validation**: Proper consent string processing
- **Data Minimization**: Collect only necessary data for analytics

**Data Anonymization:**
- **User ID Hashing**: Hash user identifiers for privacy
- **IP Address Masking**: Mask IP addresses for geo-targeting only
- **Data Aggregation**: Aggregate data to prevent individual identification
- **Retention Policies**: Automatic data deletion based on retention rules

### Audit & Compliance
**Audit Capabilities:**
- **Data Lineage**: Track data from source to reporting
- **Access Logging**: Log all data access and modifications
- **Change Tracking**: Track all configuration and data changes
- **Compliance Reporting**: Generate compliance reports for audits

## Performance Optimization

### Query Optimization
**Redshift Optimization:**
- **Columnar Storage**: Optimized for analytical queries
- **Compression**: Advanced compression algorithms
- **Distribution Keys**: Optimal data distribution across nodes
- **Sort Keys**: Optimized sorting for query performance

**Query Performance:**
- **Materialized Views**: Pre-computed aggregations for fast queries
- **Query Caching**: Intelligent caching of frequently executed queries
- **Parallel Processing**: Leverage parallel processing for large datasets
- **Index Optimization**: Optimized indexes for query performance

### Scalability Features
- **Auto-Scaling**: Dynamic scaling based on query load
- **Load Balancing**: Distribute query load across cluster nodes
- **Resource Management**: Optimal resource allocation for queries
- **Performance Monitoring**: Continuous performance monitoring and optimization

## Best Practices

### Analytics Implementation
- **Data Consistency**: Ensure consistent data across all analytics platforms
- **Performance Monitoring**: Continuous monitoring of analytics performance
- **Quality Assurance**: Regular data quality audits and validation
- **Documentation**: Comprehensive documentation of analytics processes

### Integration Guidelines
- **API Standards**: Consistent API design across all integrations
- **Error Handling**: Robust error handling and recovery mechanisms
- **Security**: Secure data transmission and storage
- **Scalability**: Design for current and future scalability requirements

## Related Topics
- [Platform Architecture](../03-technical-features/platform-architecture.md) - Overall system architecture
- [Data Management](../03-technical-features/data-management.md) - Data processing and storage
- [API Documentation](../03-technical-features/api-documentation.md) - API specifications and usage
- [Reporting and Analytics](../02-business-features/reporting-analytics.md) - Business reporting features
