# API Documentation

## Overview

Bedrock Platform provides comprehensive REST APIs for campaign management, real-time bidding, tracking, and reporting. The API architecture follows RESTful principles with JSON payloads, proper HTTP status codes, and standardized error handling across all endpoints.

## API Architecture

### Core API Components
- **Terminal API**: Campaign management, configuration, and administrative operations
- **Exchange API**: Real-time bidding and OpenRTB protocol handling
- **Tracker API**: Event tracking for impressions, clicks, and conversions
- **User Sync API**: User identification and cross-domain synchronization
- **Reporting API**: Analytics data access and report generation

### API Design Principles
- **RESTful Design**: Standard HTTP methods (GET, POST, PUT, DELETE) with resource-based URLs
- **JSON Communication**: All request and response payloads use JSON format
- **Stateless Operations**: Each API request contains all necessary information
- **Consistent Error Handling**: Standardized error responses across all endpoints

## Authentication & Authorization

### Authentication Methods
**API Key Authentication:**
```http
Authorization: Bearer <api_key>
Content-Type: application/json
```

**Session-Based Authentication:**
```http
Cookie: session_id=<session_token>
Content-Type: application/json
```

### Authorization Levels
- **Super User**: Full platform access across all accounts
- **Account Admin**: Full access within assigned accounts
- **Campaign Manager**: Campaign and line item management permissions
- **Read-Only User**: View-only access to campaigns and reports

### Role-Based Access Control
```json
{
  "user_id": "user123",
  "roles": ["campaign_manager"],
  "permissions": [
    "campaigns:read",
    "campaigns:write",
    "line_items:read",
    "line_items:write"
  ],
  "account_access": ["account456", "account789"]
}
```

## Platform Endpoints

### Production Environment
| Component | Endpoint | Purpose |
|-----------|----------|---------|
| Customer UI | `https://app.bedrockplatform.com` | Web interface for campaign management |
| Terminal API | `https://terminal.bedrockplatform.bid/vt/` | Campaign management API |
| Exchange | `https://exchange.bedrockplatform.bid/v3/` | Real-time bidding endpoint |
| Tracker | `https://tracker.bedrockplatform.bid/` | Event tracking endpoints |
| User Sync | `https://sync.bedrockplatform.bid/` | User identification and syncing |
| Grafana | `https://grafana.monitoring.bedrockplatform.bid/` | Monitoring and analytics |

### Staging Environment
| Component | Endpoint | Purpose |
|-----------|----------|---------|
| Customer UI | `https://staging.bedrockplatform.com/` | Staging web interface |
| Terminal API | `https://terminal-stage.bedrockplatform.bid/vt/` | Staging API endpoint |

## Terminal API

### Base URL
```
Production: https://terminal.bedrockplatform.bid/vt/
Staging: https://terminal-stage.bedrockplatform.bid/vt/
```

### Campaign Management APIs

#### Create Campaign
```http
POST /v1/campaigns
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "name": "Summer Campaign 2025",
  "advertiser_id": "adv123",
  "start_date": "2025-06-01T00:00:00Z",
  "end_date": "2025-08-31T23:59:59Z",
  "budget": 10000.00,
  "currency": "USD",
  "status": "active"
}
```

**Response:**
```json
{
  "id": "camp456",
  "name": "Summer Campaign 2025",
  "advertiser_id": "adv123",
  "start_date": "2025-06-01T00:00:00Z",
  "end_date": "2025-08-31T23:59:59Z",
  "budget": 10000.00,
  "currency": "USD",
  "status": "active",
  "created_at": "2025-09-14T10:30:00Z",
  "updated_at": "2025-09-14T10:30:00Z"
}
```

#### Get Campaign
```http
GET /v1/campaigns/{campaign_id}
Authorization: Bearer <api_key>
```

#### Update Campaign
```http
PUT /v1/campaigns/{campaign_id}
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "budget": 15000.00,
  "status": "paused"
}
```

#### List Campaigns
```http
GET /v1/campaigns?limit=50&offset=0&status=active
Authorization: Bearer <api_key>
```

### Line Item Management APIs

#### Create Line Item
```http
POST /v1/line_items
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "campaign_id": "camp456",
  "name": "Mobile Display Line Item",
  "bid_price": 2.50,
  "budget": 5000.00,
  "targeting": {
    "geo": ["US", "CA"],
    "device_types": ["mobile"],
    "operating_systems": ["iOS", "Android"]
  },
  "frequency_cap": {
    "impressions": 3,
    "period": "day"
  }
}
```

#### Get Line Item
```http
GET /v1/line_items/{line_item_id}
Authorization: Bearer <api_key>
```

#### Update Line Item Targeting
```http
PUT /v1/line_items/{line_item_id}/targeting
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "geo": ["US", "CA", "UK"],
  "device_types": ["mobile", "tablet"],
  "audience_segments": ["seg123", "seg456"]
}
```

### Creative Management APIs

#### Upload Creative
```http
POST /v1/creatives
Content-Type: multipart/form-data
Authorization: Bearer <api_key>

{
  "name": "Banner Creative 300x250",
  "advertiser_id": "adv123",
  "width": 300,
  "height": 250,
  "format": "image/jpeg",
  "file": <binary_data>
}
```

#### Get Creative Status
```http
GET /v1/creatives/{creative_id}/status
Authorization: Bearer <api_key>
```

**Response:**
```json
{
  "creative_id": "cre789",
  "status": "approved",
  "review_status": {
    "platform_policy": "approved",
    "deals_policy": "approved",
    "network_policy": "approved"
  },
  "last_reviewed": "2025-09-14T09:15:00Z"
}
```

## Exchange API

### Real-Time Bidding Endpoint
```http
POST /v3?selleraccountid={seller_id}
Content-Type: application/json

{
  "id": "bid-request-123",
  "imp": [{
    "id": "imp1",
    "banner": {
      "w": 300,
      "h": 250
    },
    "bidfloor": 0.50
  }],
  "site": {
    "domain": "example.com",
    "page": "https://example.com/article"
  },
  "user": {
    "id": "user123"
  },
  "device": {
    "ua": "Mozilla/5.0...",
    "ip": "192.168.1.1"
  }
}
```

**Bid Response:**
```json
{
  "id": "bid-request-123",
  "seatbid": [{
    "bid": [{
      "id": "bid123",
      "impid": "imp1",
      "price": 2.50,
      "adm": "<html>...</html>",
      "crid": "cre789",
      "w": 300,
      "h": 250
    }]
  }],
  "cur": "USD"
}
```

### BidSwitch Integration
```http
POST /v3?selleraccountid=0f9956fc-b6af-4e9b-9377-d565b386e111
Content-Type: application/json
```

## Tracker API

### Event Tracking Endpoints

#### Win Notification
```http
GET /nurl?a={auction_id}&ab={bid_id}&ap={auction_price}&...
```

#### Impression Tracking
```http
GET /imp?a={auction_id}&ab={bid_id}&ai={imp_id}&ap={auction_price}&...
```

#### Click Tracking
```http
GET /clk?ab={bid_id}&crid={creative_id}&cid={campaign_id}&...
```

### Macro Substitution

#### Auction Macros
| Macro | Description | Source |
|-------|-------------|--------|
| `${AUCTION_ID}` | Bid request ID | `request.ID` |
| `${AUCTION_BID_ID}` | Bid response ID | `response.ID` |
| `${AUCTION_IMP_ID}` | Impression ID | `bid.ImpID` |
| `${AUCTION_PRICE}` | Winning price | Encrypted price from SSP |
| `${AUCTION_CURRENCY}` | Currency code | `response.Cur` |
| `${CAMPAIGN_ID}` | Campaign identifier | `bid.CID` |
| `${CREATIVE_ID}` | Creative identifier | `bid.CrID` |

#### Privacy Macros
| Macro | Description | Source |
|-------|-------------|--------|
| `${GDPR}` | GDPR flag | `request.Regs.GDPR` |
| `${GDPR_CONSENT}` | Consent string | `request.User.Consent` |
| `${US_PRIVACY}` | CCPA string | `request.Regs.USPrivacy` |
| `${COPPA}` | COPPA flag | `request.Regs.COPPA` |

## User Sync API

### User Identification
```http
GET /user/identify/{segment_id}?sync=0&consent=${GDPR_CONSENT}&gdpr=${GDPR}
```

### Sync Endpoints by Partner
| Partner | Endpoint |
|---------|----------|
| ExchangeWire | `/user/identify/019248ab-f296-70ed-9283-50724edcc81a` |
| Bedrock Platform | `/user/identify/19bea1ee-5c9a-4b68-bb12-60ede7a0b382` |

## Reporting API

### Performance Reports
```http
GET /v1/reports/performance?start_date=2025-09-01&end_date=2025-09-14&group_by=campaign,day
Authorization: Bearer <api_key>
```

**Response:**
```json
{
  "data": [
    {
      "date": "2025-09-14",
      "campaign_id": "camp456",
      "campaign_name": "Summer Campaign 2025",
      "impressions": 10000,
      "clicks": 150,
      "spend": 250.00,
      "ctr": 1.50,
      "cpm": 25.00
    }
  ],
  "total_records": 1,
  "pagination": {
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

### Custom Reports
```http
POST /v1/reports/custom
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "name": "Weekly Performance Report",
  "dimensions": ["campaign", "line_item", "day"],
  "metrics": ["impressions", "clicks", "spend", "conversions"],
  "filters": {
    "date_range": {
      "start": "2025-09-01",
      "end": "2025-09-14"
    },
    "campaign_ids": ["camp456", "camp789"]
  }
}
```

## Rate Limiting

### Rate Limit Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1694692800
```

### Rate Limit Policies
- **Terminal API**: 1000 requests per hour per API key
- **Reporting API**: 100 requests per hour per API key
- **Exchange API**: No rate limiting (real-time bidding)
- **Tracker API**: No rate limiting (event tracking)

### Rate Limit Exceeded Response
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "details": {
      "limit": 1000,
      "reset_time": "2025-09-14T11:00:00Z"
    }
  }
}
```

## Error Handling

### Standard Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "budget",
      "reason": "Budget must be greater than 0"
    },
    "request_id": "req_123456789"
  }
}
```

### HTTP Status Codes
| Status Code | Description | Usage |
|-------------|-------------|-------|
| 200 | OK | Successful GET, PUT requests |
| 201 | Created | Successful POST requests |
| 204 | No Content | Successful DELETE requests |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource conflict (duplicate) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |

### Common Error Codes
| Error Code | Description | Resolution |
|------------|-------------|------------|
| `INVALID_API_KEY` | API key is missing or invalid | Provide valid API key |
| `INSUFFICIENT_PERMISSIONS` | User lacks required permissions | Contact admin for access |
| `RESOURCE_NOT_FOUND` | Requested resource doesn't exist | Verify resource ID |
| `VALIDATION_ERROR` | Request validation failed | Check request parameters |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Wait and retry |

## API Versioning

### Version Strategy
- **URL Versioning**: Version specified in URL path (`/v1/`, `/v2/`)
- **Backward Compatibility**: Previous versions supported for 12 months
- **Deprecation Notice**: 6-month notice before version retirement

### Current Versions
- **Terminal API**: v1 (current), v2 (beta)
- **Exchange API**: v3 (current)
- **Tracker API**: v1 (current)
- **Reporting API**: v1 (current)

## SDK and Integration

### Official SDKs
- **JavaScript/Node.js**: `npm install @bedrock/platform-sdk`
- **Python**: `pip install bedrock-platform-sdk`
- **Go**: `go get github.com/bedrockplatform/go-sdk`
- **PHP**: `composer require bedrock/platform-sdk`

### SDK Example (JavaScript)
```javascript
const BedrockSDK = require('@bedrock/platform-sdk');

const client = new BedrockSDK({
  apiKey: 'your-api-key',
  environment: 'production' // or 'staging'
});

// Create campaign
const campaign = await client.campaigns.create({
  name: 'My Campaign',
  advertiser_id: 'adv123',
  budget: 10000
});

// Get performance data
const performance = await client.reports.performance({
  start_date: '2025-09-01',
  end_date: '2025-09-14',
  group_by: ['campaign', 'day']
});
```

## Webhooks

### Webhook Events
- **campaign.created**: New campaign created
- **campaign.updated**: Campaign modified
- **line_item.budget_exhausted**: Line item budget depleted
- **creative.approved**: Creative approved for serving
- **creative.rejected**: Creative rejected by review

### Webhook Configuration
```http
POST /v1/webhooks
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "url": "https://your-app.com/webhooks/bedrock",
  "events": ["campaign.created", "creative.approved"],
  "secret": "webhook_secret_key"
}
```

### Webhook Payload
```json
{
  "event": "campaign.created",
  "timestamp": "2025-09-14T10:30:00Z",
  "data": {
    "campaign_id": "camp456",
    "name": "Summer Campaign 2025",
    "status": "active"
  },
  "signature": "sha256=..."
}
```

## Testing & Development

### Sandbox Environment
- **Base URL**: `https://sandbox-terminal.bedrockplatform.bid/vt/`
- **Test Data**: Pre-populated test campaigns and line items
- **No Billing**: All operations are free in sandbox
- **Rate Limits**: Relaxed rate limits for testing

### Test Traffic
**Test Request Flags:**
```json
{
  "ext": {
    "bedrock_t": 1,
    "bedrock_tid": "test_campaign_validation"
  }
}
```

### API Testing Tools
- **Postman Collection**: Available for download
- **OpenAPI Specification**: Swagger documentation
- **Test Credentials**: Sandbox API keys for testing

## Best Practices

### API Usage Guidelines
- **Use HTTPS**: Always use secure connections
- **Handle Errors**: Implement proper error handling
- **Respect Rate Limits**: Implement backoff strategies
- **Cache Responses**: Cache static data to reduce API calls
- **Validate Input**: Validate all input parameters

### Performance Optimization
- **Batch Operations**: Use batch endpoints when available
- **Pagination**: Use pagination for large result sets
- **Compression**: Enable gzip compression for responses
- **Connection Pooling**: Reuse HTTP connections

### Security Best Practices
- **Secure API Keys**: Store API keys securely
- **Rotate Keys**: Regularly rotate API keys
- **Monitor Usage**: Monitor API usage for anomalies
- **Validate Webhooks**: Verify webhook signatures

## Related Topics
- [Platform Architecture](platform-architecture.md) - Overall system architecture
- [Real-Time Processing](real-time-processing.md) - Real-time bidding and processing
- [User Role Management](../06-operations/user-role-management.md) - Authentication and authorization
- [Integration Guides](../05-integrations/) - Third-party integrations and setup
