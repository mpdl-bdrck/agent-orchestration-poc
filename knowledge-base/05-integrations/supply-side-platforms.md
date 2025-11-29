# Supply-Side Platform Integrations

## Overview

Bedrock Platform integrates with multiple Supply-Side Platforms (SSPs) to access premium programmatic inventory. Our SSP integrations enable real-time bidding on high-quality ad inventory while maintaining strict quality standards and performance optimization.

## Supported SSP Partners

### BidSwitch (Primary Integration)
- **Status**: Live Production
- **Integration Type**: OpenRTB 2.5 compliant
- **Seller Account ID**: `0f9956fc-b6af-4e9b-9377-d565b386e111`
- **Endpoint**: `https://exchange.bedrockplatform.bid/v3?selleraccountid=0f9956fc-b6af-4e9b-9377-d565b386e111`
- **Features**: Full OpenRTB support, discrepancy reporting, supply-side fees

### Index Exchange
- **Status**: Integration in Progress
- **Integration Type**: OpenRTB 2.5 compliant
- **Seller Account ID**: `d983b9f0-8bf2-11e6-8521-8b154a4c005a`
- **Features**: Premium inventory access, video VAST support, geo-targeting optimization

### Google Ad Manager (Planned)
- **Status**: Planned Integration
- **Integration Type**: Google RTB API
- **Features**: YouTube inventory, Google properties, advanced targeting

## BidSwitch Integration

### Technical Implementation
**OpenRTB Protocol Support:**
- **Version**: OpenRTB 2.5
- **Request Format**: JSON-encoded bid requests
- **Response Format**: JSON bid responses with proper HTTP status codes
- **Timeout**: 120ms default response time
- **Compression**: Gzip compression supported

**Bid Request Flow:**
```
BidSwitch → Exchange Service → Bidder Service → Bid Response → BidSwitch
     ↓              ↓               ↓              ↓           ↓
Request Validation  Routing    Strategy Engine   Price Calc   Win/Loss
     ↓              ↓               ↓              ↓           ↓
Quality Filtering  Enhancement  Audience Match   Fee Calc    Tracking
```

### Request Enhancement
**Geo-Location Processing:**
- **Country Codes**: ISO-3 format conversion (GB→GBR, DE→DEU, FR→FRA)
- **Region Codes**: ISO-3166-2 format for US states and regions
- **City Codes**: UN/LOCODE format for precise location targeting
- **IP Geolocation**: Real-time IP to location mapping

**User Data Enhancement:**
- **User Syncing**: Cross-domain user identification
- **Segment Matching**: Real-time audience segment lookup
- **Privacy Compliance**: GDPR, CCPA, and COPPA compliance handling
- **Consent Management**: Proper consent string processing

### Response Optimization
**Bid Response Structure:**
```json
{
  "id": "bid-request-123",
  "seatbid": [{
    "bid": [{
      "id": "bid456",
      "impid": "imp1",
      "price": 2.50,
      "adm": "<html>...</html>",
      "adomain": ["advertiser.com"],
      "crid": "creative123",
      "attr": [1, 2, 3],
      "burl": "https://tracker.bedrockplatform.bid/nurl?..."
    }]
  }],
  "cur": "USD"
}
```

**Macro Substitution:**
- **${AUCTION_PRICE}**: Encrypted winning price from BidSwitch
- **${AUCTION_ID}**: Bid request identifier
- **${AUCTION_BID_ID}**: Bid response identifier
- **${AUCTION_IMP_ID}**: Impression identifier

### Quality Controls
**Traffic Quality Management:**
- **GIVT Filtering**: General Invalid Traffic detection and blocking
- **Bot Detection**: Advanced bot and non-human traffic filtering
- **Fraud Prevention**: Real-time fraud detection algorithms
- **Quality Scoring**: Traffic source quality assessment

**Inventory Controls:**
- **Domain Filtering**: Allow/block lists for publisher domains
- **App Filtering**: Mobile app allow/block list management
- **Category Filtering**: IAB category-based inventory filtering
- **Deal Management**: Private marketplace deal handling

### Discrepancy Reporting
**Daily Reporting Requirements:**
- **Legal Compliance**: Contractual requirement for daily discrepancy reporting
- **Data Upload**: Automated daily upload of impression and spend data
- **Historical Data**: Upload last 5 days of data for discrepancy detection
- **Aggregation**: Data aggregated by original SSP for comprehensive reporting

### Deal Selection & Geographic Compatibility

#### Pre-Campaign Deal Validation Challenge
**Problem**: Bedrock's internal databases (TerminalDB, AggregationDB, ImpressionDB) only contain geographic data **after** receiving bid requests and winning impressions. This creates a critical gap when selecting deals for campaigns - we cannot determine which countries a deal sends traffic from before adding it to curation packages.

#### Current Targeting Group Configuration
Bedrock maintains **targeting groups** in BidSwitch that define which geographic regions we can accept traffic from:
- **8643**: EU Targeting (FR, DE, IT, ES, GB)  
- **9000**: Brazil Only (BR)
- **8642/8999**: Open Exchange Only (no deals allowed)

#### Geographic Mismatch Consequences
When deals send traffic from countries not covered by our targeting groups:
- **100% request filtering**: All bid requests are filtered out before reaching our bidder
- **Diagnostic pattern**: BidSwitch reports "Too few Requests Sent"
- **Zero delivery**: Campaign shows as active but receives no traffic
- **Resource waste**: Campaign setup and optimization efforts yield no results

#### BidSwitch UI Limitations (Admin Access)
**Admin users can:**
- Filter deals by country in Deals Discovery interface
- Find deals that send traffic from specific countries (e.g., UK)
- View basic deal metadata and performance history

**Admin users cannot:**
- View complete country list for individual deals
- Access comprehensive deal geographic metadata
- Prevent geo-targeting conflicts before deal selection

#### API-Based Solution (Requires API Access)
**BidSwitch API Endpoint**: `https://protocol.bidswitch.com/api/v2/deals-targeting.html`
- **Access Level**: Requires API user account (not Admin)
- **Capability**: Complete deal geographic metadata before traffic
- **Integration Need**: Should be integrated into campaign planning workflow
- **Data Available**: Full country lists, targeting parameters, inventory forecasts

#### Recommended Workflow
1. **Pre-Selection**: Query BidSwitch API for deal geographic data
2. **Compatibility Check**: Verify deal countries match available targeting groups
3. **Conflict Prevention**: Only select deals with compatible geography
4. **Campaign Optimization**: Avoid zero-delivery scenarios from geo mismatches
5. **Targeting Group Expansion**: Create new groups for valuable geographic opportunities

#### Current Workaround
Until API access is available:
- Use BidSwitch UI country filtering to find deals for specific regions
- Select deals known to send traffic from supported countries (UK, EU, Brazil)
- Monitor campaign delivery closely for geo-targeting issues
- Create additional targeting groups for new geographic requirements
- Test deals with small budgets to validate geographic compatibility

## Performance Monitoring

### Reporting Process
```python
# Daily cronjob at noon UTC
SELECT
  to_date(year::text || '-' || lpad(month::text, 2, '0') || '-' || lpad(day::text, 2, '0'), 'YYYY-MM-DD') AS d,
  original_ssp_id,
  nurl_count,
  imp_total_spend
FROM "bedrock"."public".overview_view
WHERE ssp_id = '0f9956fc-b6af-4e9b-9377-d565b386e111'
```

## Index Exchange Integration

### Integration Status
**Current Implementation:**
- **Seller Module**: Index Exchange specific handling in exchange service
- **Price Decryption**: HMAC-SHA1 price decryption implementation
- **Geo Conversion**: ISO-3 country code transformation
- **BURL Support**: Billing URL with `${AUCTION_PRICE:IEX}` macro

### Technical Requirements
**OpenRTB Compliance:**
- **Content-Length**: Required in HTTP responses
- **Seat Bid Array**: Full seat bid array support
- **Bid Response Fields**: Complete bid response structure
- **HTTPS**: Secure communication required
- **Compression**: Gzip compression support

**Index Exchange Specific Features:**
```json
{
  "burl": "https://tracker.bedrockplatform.bid/nurl?ap=${AUCTION_PRICE:IEX}&...",
  "ext": {
    "dsa": {...},  // EU Digital Services Act compliance
    "skadn": {...} // iOS SKAdNetwork support
  }
}
```

### Price Decryption
**Encryption Handling:**
- **Algorithm**: HMAC-SHA1 with Index Exchange keys
- **Key Management**: Kubernetes secrets for encryption keys
- **Price Conversion**: Micro USD to dollars (÷1,000,000)
- **Security**: Hex-encoded 32-byte keys stored securely

**Decryption Implementation:**
```go
// Price decryption module
func DecryptIndexExchangePrice(encryptedPrice string, keys *IndexExchangeKeys) (float64, error) {
    // Decrypt using HMAC-SHA1
    decryptedMicroUSD := hmacSHA1Decrypt(encryptedPrice, keys.EncryptionKey)
    // Convert micro USD to dollars
    return float64(decryptedMicroUSD) / 1000000.0, nil
}
```

### Video Support
**VAST Handling:**
- **VAST URL Support**: External VAST URL references
- **Inline VAST**: Direct VAST XML in bid response
- **Video Billing**: BURL-based billing for video impressions
- **Format Support**: Multiple video formats and protocols

## Google Ad Manager Integration (Planned)

### Integration Scope
**Google RTB API Features:**
- **Real-Time Bidding**: 80-1000ms latency requirements
- **Creative Review**: Automated creative approval process
- **Frequency Capping**: Google-specific frequency capping
- **Audience Targeting**: Google audience segments

**Technical Requirements:**
- **Authentication**: OAuth 2.0 with service accounts
- **Encryption**: Price encryption/decryption handling
- **Macros**: Google-specific macro substitution
- **Reporting**: Google-specific reporting requirements

## SSP Configuration Management

### Seller Configuration
**Configuration Structure:**
```toml
[[SSP]]
ID = "0f9956fc-b6af-4e9b-9377-d565b386e111"
Name = "BidSwitch"
Active = true
Timeout = 120
Fee = 0.10
SupplyFee = 0.05
QualityThreshold = 0.8

[[SSP]]
ID = "d983b9f0-8bf2-11e6-8521-8b154a4c005a"
Name = "Index Exchange"
Active = true
Timeout = 120
Fee = 0.12
```

### Dynamic Configuration
- **Real-Time Updates**: Configuration updates without service restart
- **A/B Testing**: Traffic splitting for testing new configurations
- **Performance Monitoring**: Real-time performance tracking per SSP
- **Automatic Optimization**: Algorithm-based configuration optimization

## Performance Optimization

### Latency Optimization
**Response Time Targets:**
- **BidSwitch**: <100ms average response time
- **Index Exchange**: <120ms average response time
- **Google Ad Manager**: <200ms average response time

**Optimization Strategies:**
- **Connection Pooling**: Persistent HTTP connections
- **Request Batching**: Efficient request processing
- **Caching**: Strategic caching of frequently accessed data
- **Geographic Routing**: Route requests to nearest data center

### Quality Optimization
**Bid Quality Metrics:**
- **Win Rate**: Percentage of bids that win auctions
- **Fill Rate**: Percentage of requests that receive bids
- **Revenue per Mille**: Revenue optimization per thousand impressions
- **Quality Score**: Overall traffic quality assessment

**Optimization Techniques:**
- **Bid Shading**: Optimal bid price calculation
- **Audience Targeting**: Precise audience segment matching
- **Inventory Selection**: High-quality inventory prioritization
- **Real-Time Adjustments**: Dynamic bid strategy optimization

## Monitoring & Analytics

### Real-Time Monitoring
**Key Performance Indicators:**
- **Request Volume**: Requests per second by SSP
- **Response Latency**: Average and percentile response times
- **Win Rate**: Auction win percentage by SSP
- **Revenue**: Revenue generated per SSP partner

**Monitoring Dashboards:**
- **SSP Performance**: Individual SSP performance metrics
- **Quality Metrics**: Traffic quality and fraud detection
- **Revenue Analytics**: Revenue optimization and trends
- **System Health**: Technical performance and uptime

### Alerting System
**Critical Alerts:**
- **High Latency**: Response time threshold breaches
- **Low Win Rate**: Significant win rate drops
- **Quality Issues**: Traffic quality degradation
- **Integration Failures**: SSP connection or authentication failures

**Alert Configuration:**
```yaml
alerts:
  - name: "High SSP Latency"
    condition: "avg_response_time > 150ms"
    severity: "warning"
    notification: "slack, email"
  
  - name: "SSP Integration Failure"
    condition: "error_rate > 5%"
    severity: "critical"
    notification: "pagerduty, slack"
```

## Security & Compliance

### Data Protection
**Privacy Compliance:**
- **GDPR**: European data protection compliance
- **CCPA**: California privacy law compliance
- **COPPA**: Children's privacy protection
- **Consent Management**: Proper consent handling and validation

**Security Measures:**
- **Encryption**: All data encrypted in transit and at rest
- **Authentication**: Secure API authentication and authorization
- **Access Control**: Role-based access to SSP configurations
- **Audit Logging**: Comprehensive audit trails for all operations

### Compliance Monitoring
- **Privacy Audits**: Regular privacy compliance audits
- **Security Assessments**: Ongoing security vulnerability assessments
- **Compliance Reporting**: Automated compliance reporting
- **Incident Response**: Rapid response to security or privacy incidents

## Best Practices

### Integration Guidelines
- **OpenRTB Compliance**: Strict adherence to OpenRTB specifications
- **Error Handling**: Robust error handling and recovery mechanisms
- **Performance Testing**: Comprehensive load and performance testing
- **Documentation**: Detailed integration documentation and procedures

### Optimization Strategies
- **Continuous Monitoring**: Real-time performance monitoring and optimization
- **A/B Testing**: Regular testing of configuration changes and optimizations
- **Quality Focus**: Prioritize traffic quality over volume
- **Revenue Optimization**: Balance performance with revenue maximization

## Related Topics
- [Real-Time Processing](../03-technical-features/real-time-processing.md) - Real-time bidding architecture
- [Platform Architecture](../03-technical-features/platform-architecture.md) - Overall system architecture
- [API Documentation](../03-technical-features/api-documentation.md) - API specifications and usage
- [Data Management](../03-technical-features/data-management.md) - Data processing and storage
