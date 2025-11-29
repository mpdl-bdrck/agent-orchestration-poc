# Third-Party Data Integrations

## Overview

Bedrock Platform integrates with multiple third-party data providers to enhance audience targeting capabilities. These integrations enable access to premium audience segments, attention metrics, and specialized data sets that improve campaign performance and targeting precision.

## Supported Data Providers

### Evorra (Live Integration)
- **Status**: Production Ready
- **Type**: Audience Segment Provider
- **Data Source**: S3-based CSV ingestion
- **Specialization**: Publisher-collaborated audience segments

### Anonymised (Live Integration)
- **Status**: Production Ready
- **Type**: Audience Segment Provider
- **Data Source**: GCS-based CSV ingestion
- **Specialization**: Privacy-compliant audience segments with account-specific visibility

### Lumen (Live Integration)
- **Status**: Production Ready
- **Type**: Attention Metrics Provider
- **Specialization**: Attention-based targeting and optimization

## Evorra Integration

### Overview
Evorra is a Data Management Platform (DMP) that collaborates with publishers to provide audience segments for programmatic activation. The integration enhances targeting capabilities by utilizing Evorra's audience data during the bidding process.

### Technical Architecture
**Data Ingestion Pipeline:**
```
Evorra → S3 Bucket → EventBridge → Lambda → AWS Glue → Aerospike + PostgreSQL
```

**AWS Infrastructure:**
- **S3 Bucket**: `bedrock-evorra-integration`
- **EventBridge**: Listens for S3 ObjectCreated events
- **Lambda Function**: Triggers Glue jobs for processing
- **Glue Jobs**: 
  - "Evorra Integration ETL" - processes segments.csv.gz
  - "Taxonomy Data Ingestor ETL" - processes taxonomy.csv.gz

### Data Processing
**File Structure:**
- **segments.csv.gz**: User segment associations (Android ID, iOS ID, IP → segments)
- **taxonomy.csv.gz**: Segment metadata (ID, name, price, description)

**Aerospike Storage:**
```
Namespace: dmp
Set: evorra
Key Formats:
- "iosIds:575BE4AD-E811-4E35-8787-7742D47729C1"
- "androidIds:87c01956-0805-4517-85d0-8c22053db15a"
- "ips:123.23.233"

Data Structure:
{
  "segments": ["a1", "a2", "a4", "a5", "a6"]
}
```

**PostgreSQL Storage (Terminal UI):**
```sql
Table: audienceSegments
Columns:
- audienceSegmentID (auto-generated)
- externalID (Evorra segment code)
- name (segment description + location)
- provider ("Evorra")
- cpmPrice (segment price from taxonomy)
- version (S3 folder name)
- status (1=Active, 2=Inactive, 3=Soft Deleted)
```

### Bid Request Enhancement
**Exchange Enhancement:**
```json
{
  "user": {
    "ext": {
      "evorra": {
        "segments": ["a1", "a2", "a3"]
      }
    }
  }
}
```

**Bidder Processing:**
- **Segment Matching**: OR logic - if any listed segments match, filter passes
- **Price Selection**: Highest-priced segment wins when multiple segments match
- **Bid Calculation**: Segment price deducted from base bid price

### Line Item Configuration
**Audience Targeting Structure:**
```json
{
  "Filters": [{
    "FilterType": "segment",
    "Values": [
      {
        "id": "a1",
        "type": "evorra", 
        "price": "0.1",
        "version": "13205"
      },
      {
        "id": "a2",
        "type": "evorra",
        "price": "0.2", 
        "version": "13205"
      }
    ]
  }]
}
```

### Bid Response Logging
**Matched Segments Structure:**
```json
{
  "ext": {
    "mseg": [{
      "id": "a1",
      "type": "evorra",
      "price": "0.1",
      "version": "13205"
    }]
  }
}
```

## Anonymised Integration

### Overview
Anonymised.io provides privacy-compliant audience segments with account-specific visibility controls. The integration supports private marketplace deals and curation packages for targeted buyer access.

### Technical Architecture
**Data Ingestion Pipeline:**
```
Anonymised → GCS Bucket → Cloud Function → S3 Bucket → EventBridge → Lambda → Glue
```

**Processing Components:**
- **Cloud Function**: Maintained by Anonymised, uploads to our S3 bucket
- **S3 Bucket**: `bedrock-anonymised-integration`
- **Glue Job**: `Anonymised-Segments-ETL`
- **Lambda**: `anonymised-trigger-glue`

### Data Processing
**CSV File Structure:**
```csv
segment_name,segment_price,cohort_id,ttl_days,bedrock_id,bedrock_seat
ANON-999-12345,0.5,56789,30,internal_id,0
```

**Field Definitions:**
- **cohort_id**: Unique segment identifier
- **segment_price**: Currently overridden to 0.0 for all segments
- **ttl_days**: Segment expiration time in days
- **bedrock_id**: Internal Bedrock audience ID
- **bedrock_seat**: Account access control (0=Bedrock, nnn=client)

**Aerospike Storage:**
```
Namespace: dmp
Set: segment_anonymised
Key: cohort_id
TTL: ttl_days from CSV

Data Structure:
{
  "key": "56789",
  "price": "0.5",
  "name": "ANON-999-12345", 
  "version": "1000"
}
```

### Account-Scoped Visibility
**Database Schema:**
```sql
ALTER TABLE "audienceSegments" 
ADD COLUMN "advertiserIds" INT[],
ADD COLUMN "expiresAt" TIMESTAMP;
```

**Visibility Rules:**
- **advertiserIds = NULL**: Segment visible to all accounts
- **advertiserIds = specific_id**: Segment only visible to that account

**API Filtering:**
```sql
WHERE (advertiserIds IS NULL OR advertiserIds = user_account)
```

### TTL Management
**Automated Expiration:**
- **CronJob**: Daily execution at noon UTC
- **Function**: `markExpiredAnonymisedSegments()`
- **SQL**: `UPDATE audienceSegments SET statusId = 2 WHERE provider = 'anonymised' AND expiresAt < now()`

### Bid Request Processing
**Incoming Segment Data:**
```json
{
  "user": {
    "data": [{
      "name": "anonymised.io",
      "segment": [
        {"id": "63865"},
        {"id": "55458"},
        {"id": "33545"}
      ],
      "ext": {
        "segtax": 1000
      }
    }]
  }
}
```

**Enhancement Processing:**
- **Filter Condition**: `name = "anonymised.io"` AND `ext.segtax = 1000`
- **Segment Extraction**: Collect all `segment[].id` values
- **Enhancement**: Add to `user.ext.anonymised.segments`

### Curation Package Workflow
1. **Anonymised Setup**: Creates PMP deal in SSP account with desired segments
2. **Package Creation**: Uses Bedrock account to build curation package linking segments to deal ID
3. **Buyer Selection**: Chooses specific buyer accounts who can access the package
4. **Activation**: Buyers select curation package in line items for targeting

## Lumen Integration

### Overview
Lumen provides attention-based targeting metrics that enhance campaign optimization through attention measurement and targeting capabilities.

### Integration Features
- **Attention Metrics**: Real-time attention scoring for inventory
- **Targeting Enhancement**: Attention-based audience targeting
- **Performance Optimization**: Attention-driven bid optimization

### Data Enhancement
**Bid Request Enhancement:**
```json
{
  "imp": [{
    "ext": {
      "lumen": {
        "apm": "567",
        "viewability": "40.74",
        "viewtime": "1.39",
        "bucket": "low"
      }
    }
  }]
}
```

## Data Provider Integration Framework

### Generic Integration Architecture
**Common Components:**
- **Data Ingestion**: S3/GCS-based file processing
- **ETL Processing**: AWS Glue for data transformation
- **Storage Layer**: Aerospike for real-time access, PostgreSQL for UI
- **Enhancement Pipeline**: Bidder enhancement infrastructure
- **Logging System**: Comprehensive segment tracking and reporting

### Enhancement Pipeline
**Bidder Enhancement Interface:**
```go
type BidRequestEnricher interface {
    EnhanceRequest(request *openrtb.BidRequest) error
    GetProviderName() string
    IsEnabled() bool
}
```

**Generic Enhancement Functions:**
- **extractProviderSegments()**: Extracts segments from `user.ext[provider]`
- **findAllMatchingSegments()**: Matches against line item filters
- **newSegmentFilter()**: Validates required segments for targeting

### Segment Matching Logic
**Universal Matching Rules:**
- **OR Logic**: Any matching segment passes the filter
- **Price Selection**: Highest-priced segment wins
- **Tie Breaking**: Random selection for equal prices
- **Group Selection**: Price comparison within segment groups (bedrock_id)

### Logging & Reporting
**Segment Logging Structure:**
```go
type BidSegment struct {
    ID                  string  `json:"id"`
    Type                string  `json:"type"`
    Price               float64 `json:"price"`
    Version             string  `json:"version"`
    BedrockDataTakeRate float64 `json:"bedrock_data_take_rate"`
}
```

**BidStream Integration:**
```go
type BidStreamItemV2 struct {
    BidSegments        []*BidSegment `json:"bid_segments"`
    BidMatchedSegments []*BidSegment `json:"bid_matched_segments"`
}
```

## Performance Optimization

### Caching Strategy
- **Aerospike**: Sub-millisecond segment lookups
- **Connection Pooling**: Efficient database connections
- **Batch Processing**: Optimized data ingestion
- **TTL Management**: Automatic data expiration

### Latency Optimization
- **Real-Time Access**: Aerospike for bidding-time lookups
- **Parallel Processing**: Concurrent segment matching
- **Efficient Indexing**: Optimized key structures
- **Memory Management**: In-memory caching for frequent data

### Scalability Features
- **Horizontal Scaling**: Linear scalability across nodes
- **Load Distribution**: Even distribution of segment data
- **Auto-Scaling**: Dynamic scaling based on traffic
- **Multi-Region**: Cross-region data replication

## Data Quality & Validation

### Data Validation
- **Schema Validation**: Strict CSV format validation
- **Required Fields**: Validation of mandatory data fields
- **Data Types**: Type checking and conversion
- **Range Validation**: Price and TTL range validation

### Quality Assurance
- **Duplicate Detection**: Identify and handle duplicate segments
- **Completeness Checks**: Validate data completeness
- **Consistency Validation**: Cross-reference segment data
- **Error Logging**: Comprehensive error tracking

### Monitoring & Alerting
- **Processing Metrics**: Track ingestion success rates
- **Data Quality Metrics**: Monitor data quality indicators
- **Performance Metrics**: Track lookup performance
- **Alert Systems**: Automated alerts for data issues

## Reporting & Analytics

### Segment Performance Metrics
- **Impression Tracking**: Segments used per impression
- **Match Rates**: Segment matching success rates
- **Revenue Attribution**: Revenue generated per segment
- **Cost Analysis**: Segment cost vs. performance analysis

### Redshift Reporting
**Overview Table Columns:**
```sql
-- Evorra Metrics
data_evorra_fee DECIMAL(14,5)
data_evorra_imps INTEGER
data_evorra_segments INTEGER
bedrock_data_take_evorra DECIMAL(14,5)

-- Anonymised Metrics  
data_anonymised_fee DECIMAL(14,5)
data_anonymised_imps INTEGER
data_anonymised_segments INTEGER
bedrock_data_take_anonymised DECIMAL(14,5)
```

**ETL Processing:**
- **Segment Filtering**: Extract segments by provider type
- **Fee Calculation**: Convert mCPM to dollars
- **Impression Counting**: Count impressions with matched segments
- **Take Rate Calculation**: Apply Bedrock data take rates

### Business Intelligence
- **Campaign Performance**: Segment-driven campaign analysis
- **Audience Insights**: Segment performance and overlap analysis
- **Revenue Optimization**: Data cost vs. revenue analysis
- **Trend Analysis**: Historical segment performance trends

## Security & Compliance

### Data Protection
- **Privacy Compliance**: GDPR, CCPA compliance for all data providers
- **Data Encryption**: Encryption at rest and in transit
- **Access Controls**: Role-based access to segment data
- **Audit Logging**: Comprehensive audit trails

### Account Isolation
- **Visibility Controls**: Account-specific segment visibility
- **Data Segregation**: Proper data isolation between accounts
- **Permission Management**: Fine-grained access control
- **Compliance Monitoring**: Regular compliance audits

## Best Practices

### Integration Guidelines
- **Standardized Processing**: Consistent data processing patterns
- **Error Handling**: Robust error handling and recovery
- **Performance Testing**: Comprehensive load testing
- **Documentation**: Detailed integration documentation

### Data Management
- **Version Control**: Proper versioning of segment data
- **TTL Management**: Appropriate data expiration policies
- **Quality Monitoring**: Continuous data quality monitoring
- **Backup Procedures**: Regular data backup and recovery

### Optimization Strategies
- **Caching Optimization**: Strategic caching for performance
- **Query Optimization**: Efficient database queries
- **Resource Management**: Optimal resource utilization
- **Monitoring Integration**: Comprehensive monitoring setup

## Related Topics
- [Platform Architecture](../03-technical-features/platform-architecture.md) - Overall system architecture
- [Data Management](../03-technical-features/data-management.md) - Data processing and storage
- [Real-Time Processing](../03-technical-features/real-time-processing.md) - Real-time data access
- [Supply-Side Platforms](supply-side-platforms.md) - SSP integrations and bid request flow
