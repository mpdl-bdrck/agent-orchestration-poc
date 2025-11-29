# Platform Architecture

## System Overview

Bedrock Platform is built on a modern, cloud-native architecture designed for high-performance real-time bidding, scalable campaign management, and comprehensive data processing. Our system handles up to 100,000 bid requests per second while maintaining sub-100ms response times.

### Production Environment Endpoints

| **Component** | **Production Endpoint** | **Staging Endpoint** |
|---------------|------------------------|---------------------|
| **Customer UI** | [app.bedrockplatform.com](http://app.bedrockplatform.com) | [staging.bedrockplatform.com](https://staging.bedrockplatform.com/) |
| **Terminal API** | [terminal.bedrockplatform.bid/vt/](https://terminal.bedrockplatform.bid/vt/) | [terminal-stage.bedrockplatform.bid/vt/](https://terminal-stage.bedrockplatform.bid/vt/) |
| **Exchange** | [exchange.bedrockplatform.bid/v3/](https://exchange.bedrockplatform.bid/v3/) | Available for testing |
| **Tracker** | [tracker.bedrockplatform.bid/](https://tracker.bedrockplatform.bid/) | Integrated with staging |
| **User Syncing** | [sync.bedrockplatform.bid/](https://sync.bedrockplatform.bid/) | Cross-environment sync |
| **Monitoring** | [grafana.monitoring.bedrockplatform.bid/](https://grafana.monitoring.bedrockplatform.bid/) | Real-time dashboards |

## Core Components

### OpenRTB Exchange
- **Real-time bid processing** for programmatic advertising auctions
- **High-throughput handling** of bid requests and responses (up to 100k RPS)
- **Integration with multiple SSPs** including BidSwitch as primary partner
- **Auction logic and pricing** optimization with macro substitution

#### Exchange Integration Details
**BidSwitch Integration**: Primary SSP connection
- **Endpoint**: `exchange.bedrockplatform.bid/v3?selleraccountid=0f9956fc-b6af-4e9b-9377-d565b386e111`
- **Request Structure**: Follows [BidSwitch OpenRTB standards](https://docs.bidswitch.com/standards/bidrequest.html)
- **Bid Request Processing**: POST requests with structured JSON bid request body
- **Response Handling**: Real-time bid response generation with macro substitution

### Terminal (Campaign Management)
- **Campaign configuration** and line item management via JSON-RPC API
- **User interface** for campaign managers and advertisers
- **Reporting and analytics** dashboard with real-time data
- **User authentication** and role-based access control

#### Terminal API Structure
- **Production API**: `terminal.bedrockplatform.bid/vt/`
- **Staging API**: `terminal-stage.bedrockplatform.bid/vt/`
- **Protocol**: JSON-RPC for all campaign management operations
- **Authentication**: Secure token-based authentication system

### Bidder Engine
- **Custom bidding logic** tailored to client requirements
- **Machine learning models** for bid optimization
- **Real-time decision making** based on campaign parameters (sub-100ms)
- **Budget and pacing enforcement** with real-time spend tracking

### Tracker Service
- **Event tracking** for impressions, clicks, and conversions
- **Attribution modeling** across user journey touchpoints
- **Performance data collection** for reporting and optimization
- **Fraud detection** and traffic quality monitoring

#### Tracker Endpoints
| **Event Type** | **Endpoint** | **Purpose** |
|----------------|--------------|-------------|
| **Win Notifications** | `tracker.bedrockplatform.bid/nurl` | Auction win tracking |
| **Impression Tracking** | `tracker.bedrockplatform.bid/imp` | Ad impression recording |
| **Click Tracking** | `tracker.bedrockplatform.bid/clk` | User click event tracking |

### Macro Substitution System

#### Auction Macros (Platform-Generated)
The platform automatically substitutes these macros during bid processing:

| **Macro** | **Source** | **Description** |
|-----------|------------|-----------------|
| `${AUCTION_IMP_ID}` | `bid.ImpID` | Impression identifier from bid |
| `${AUCTION_CURRENCY}` | `response.Cur` | Currency from bid response |
| `${AUCTION_BID_ID}` | `response.ID` | Bid response identifier |
| `${AUCTION_SEAT_ID}` | `seatBid.Seat` | Bidder seat identifier |
| `${AUCTION_ID}` | `request.ID` | Original bid request ID |
| `${AUCTION_AD_ID}` | `bid.AdID` | Advertisement identifier |
| `${CAMPAIGN_ID}` | `bid.CID` | Campaign identifier |
| `${CREATIVE_ID}` | `bid.CrID` | Creative asset identifier |
| `${PUBLISHER_ID}` | `request.Site.Publisher.ID` | Publisher identifier |
| `${ADVERTISER_ID}` | `bid.Ext["advertiser_id"]` | Advertiser identifier |
| `${DEAL_ID}` | `bid.DealID` | Private marketplace deal ID |

#### Privacy & Compliance Macros
| **Macro** | **Source** | **Description** |
|-----------|------------|-----------------|
| `${GDPR}` | `request.Regs.GDPR` | GDPR compliance flag |
| `${GDPR_CONSENT}` | `request.User.Consent` | User consent string |
| `${ADDTL_CONSENT}` | `request.User.Ext["addtl_consent"]` | Additional consent data |
| `${US_PRIVACY}` | `request.Regs.USPrivacy` | CCPA compliance string |
| `${COPPA}` | `request.Regs.COPPA` | COPPA compliance flag |

#### Tracker-Specific Macros
When SSPs call tracker URLs, additional macro substitutions occur:

**Click Redirection Macros**:
- `${CLICK_REF}` → Bid ID for click attribution
- `${DOMAIN:ENC}` → Encoded referring domain
- `${SOURCE:ENC}` → Encoded referrer URL
- `${TACTIC_ID}` → Line item (tactic) identifier

**Impression Tracking Macros**:
- `${AUCTION_PRICE}` / `%%AUCTION_PRICE%%` → Final auction price
- `${ENCODED_BID_VALUE}` → Blowfish-encrypted bid value for VAST

### URL Construction & Parameters

#### Standard URL Parameters
| **Parameter** | **Description** | **Example** |
|---------------|-----------------|-------------|
| `si` | Seller Account ID | Account identifier for publisher |
| `bi` | Buyer Account ID | Account identifier for advertiser |
| `a` | Auction ID | Bid request identifier |
| `apb` | Encrypted Bid Value | Blowfish-encrypted bid amount |
| `bfe` | Buyer Fee | Encoded buyer-side fees |
| `sfe` | Seller Fee | Encoded seller-side fees |
| `lid` | Line Item ID | Tactic/line item identifier |
| `cid` | Campaign ID | Campaign identifier |
| `crid` | Creative ID | Creative asset identifier |
| `lu` | Lumen Data Fee | Data provider fee type |
| `sf` | Segment Fee | Audience segment fees |
| `at` | Auction Type | Type of auction conducted |

### User Syncing & Identity Management

#### User Sync Endpoints
The platform maintains user identity synchronization across different partners and data providers:

| **Partner** | **Sync Endpoint** | **Purpose** |
|-------------|-------------------|-------------|
| **ExchangeWire** | `sync.bedrockplatform.bid/user/identify/019248ab-f296-70ed-9283-50724edcc81a` | Cross-platform user identification |
| **Bedrock Platform** | `sync.bedrockplatform.bid/user/identify/19bea1ee-5c9a-4b68-bb12-60ede7a0b382` | Internal user tracking |

#### Privacy-Compliant Sync Parameters
All user sync endpoints include privacy compliance parameters:
- `sync=0` → Synchronization mode flag
- `consent=${GDPR_CONSENT}` → User consent string for GDPR compliance
- `gdpr=${GDPR}` → GDPR applicability flag

#### Identity Resolution Process
1. **User Identification**: Platform receives user identifier from partner
2. **Privacy Validation**: Check GDPR/CCPA compliance requirements
3. **Consent Verification**: Validate user consent for data processing
4. **Cross-Platform Mapping**: Map user across different partner systems
5. **Audience Segmentation**: Update user profiles for targeting purposes

## Technology Stack

### Backend Services
- **Go (Golang)**: Primary backend language for high-performance services
- **PostgreSQL**: Primary database for campaign and user data
- **Aerospike**: High-speed NoSQL database for real-time data
- **Redis**: Caching layer for frequently accessed data

### Cloud Infrastructure
- **AWS**: Primary cloud provider with multi-region deployment
- **Kubernetes (EKS)**: Container orchestration for scalable deployments
- **Docker**: Containerization for consistent deployment environments
- **Terraform**: Infrastructure as Code for reproducible deployments

### Data Processing
- **AWS Glue**: ETL jobs for data transformation and processing
- **AWS Lambda**: Serverless functions for event-driven processing
- **EventBridge**: Event routing and processing coordination
- **S3**: Object storage for logs, reports, and data files

### Monitoring & Observability
- **Grafana**: Real-time monitoring dashboards and alerting at `grafana.monitoring.bedrockplatform.bid`
- **Prometheus**: Metrics collection and time-series database for system metrics
- **Victoria Metrics**: High-performance time-series database for large-scale metrics storage
- **CloudWatch**: AWS-native monitoring and log aggregation
- **Custom alerting**: Business-specific monitoring and notifications via Slack (#grafana-alerts)

#### Monitoring Architecture
**Infrastructure Monitoring**:
- **System Health**: Pipelines, servers, databases functional availability monitoring
- **Performance Metrics**: Resource usage, response times, throughput analysis
- **Data Quality**: Data formatting, integrity checks, threshold breach detection
- **Multi-Customer Monitoring**: Extensive monitoring across all Bedrock customer instances

**Business Monitoring**:
- **Campaign Performance**: Real-time campaign delivery and spend tracking
- **Bid Stream Health**: Auction participation rates, win rates, response times
- **Revenue Tracking**: Financial metrics and billing accuracy monitoring
- **SLA Compliance**: Service level agreement monitoring and reporting

#### Operational Requirements
**Monitoring Standards**:
- **Qualitative Checks**: Data formatting validation, integrity verification
- **Threshold Monitoring**: Automated alerts for value breaches and anomalies
- **Multi-Instance Coverage**: Monitoring across shared infrastructure and customer instances
- **Fix Delivery SLA**: Defined process for rolling out fixes, especially multi-customer impacts

## Data Flow Architecture

### Bid Request Processing
```
SSP → Exchange → Bidder → Response → SSP
  ↓      ↓        ↓        ↓
Logs → Processing → Analytics → Reports
```

### Campaign Data Flow
```
Terminal UI → API → Database → Bidder Config
     ↓         ↓       ↓          ↓
  User Actions → Audit → Cache → Real-time Bidding
```

## Regional Deployment

### Multi-Region Architecture
- **US East (Virginia)**: Primary region for North American traffic
- **EU West (Ireland)**: European traffic processing and data residency
- **APAC (Singapore)**: Asia-Pacific traffic with local data processing

### Regional Components
- **Exchange instances** in each region for low-latency bidding
- **Shared Aerospike** deployment across regions for data consistency
- **Regional PostgreSQL** instances with cross-region replication
- **Local caching layers** for optimal performance

### Traffic Distribution
- **Geographic routing** based on request origin
- **Load balancing** across regional instances
- **Failover mechanisms** for high availability
- **Performance monitoring** per region

## Security & Compliance

### Data Security
- **Encryption at rest** for all stored data
- **TLS encryption** for all network communications
- **API authentication** using secure token-based systems
- **Role-based access control** for platform features

### Privacy Compliance
- **GDPR compliance** for European user data
- **CCPA compliance** for California privacy regulations
- **Cookie consent management** and user opt-out mechanisms
- **Data retention policies** and automated cleanup

### Infrastructure Security
- **VPC isolation** for network security
- **Security groups** and firewall rules
- **Regular security audits** and penetration testing
- **Compliance monitoring** and reporting

## Performance Characteristics

### Latency Requirements
- **Bid response time**: <100ms for 95th percentile
- **UI response time**: <2 seconds for dashboard loading
- **Report generation**: <30 seconds for standard reports
- **Data processing**: Real-time for critical path operations

### Throughput Capacity
- **Bid requests**: 100,000+ QPS (Queries Per Second)
- **Event tracking**: 1M+ events per minute
- **Database operations**: 10,000+ transactions per second
- **Report queries**: 100+ concurrent analytical queries

### Scalability Features
- **Horizontal scaling** for all major components
- **Auto-scaling policies** based on traffic patterns
- **Resource optimization** for cost-effective operations
- **Capacity planning** and performance forecasting

## Integration Architecture

### External Integrations
- **BidSwitch**: Primary SSP integration for bid request flow
- **Index Exchange**: Premium inventory access and optimization
- **Evorra**: Data enrichment and audience segmentation
- **Lumen**: Data curation and segment pricing

### API Architecture
- **RESTful APIs** for campaign management and reporting
- **GraphQL endpoints** for flexible data querying
- **Webhook support** for real-time event notifications
- **Rate limiting** and API security controls

### Data Synchronization
- **Real-time sync** for critical campaign data
- **Batch processing** for historical data and reports
- **Event-driven updates** using message queues
- **Conflict resolution** for concurrent data modifications

## Development & Deployment

### Development Environment
- **Local development setup** with Docker Compose
- **Staging environment** with production-like configuration
- **Feature flags** for controlled feature rollouts
- **Automated testing** including unit, integration, and load tests

### Deployment Pipeline
- **GitOps workflow** with automated CI/CD
- **Blue-green deployments** for zero-downtime releases
- **Rollback capabilities** for quick issue resolution
- **Deployment monitoring** and health checks

### Quality Assurance
- **Code review processes** and automated quality checks
- **Performance testing** before production deployment
- **Security scanning** for vulnerabilities
- **Compliance validation** for regulatory requirements

## Troubleshooting & Operations

### Monitoring & Alerting
- **Real-time dashboards** for system health monitoring
- **Automated alerting** for critical system issues
- **Performance metrics** tracking and analysis
- **Business metrics** monitoring for campaign performance

### Emergency Procedures
- **On-call rotation** for 24/7 system monitoring
- **Incident response** procedures and escalation paths
- **Emergency scaling** procedures for traffic spikes
- **Disaster recovery** plans and backup procedures

### Maintenance Operations
- **Regular system updates** and security patches
- **Database maintenance** and optimization
- **Capacity planning** and resource allocation
- **Performance tuning** and optimization

## Related Topics
- [Campaign Management](../02-business-features/campaign-management.md)
- [Integration Overview](../05-integrations/integration-overview.md)
- [Operations Procedures](../06-operations/daily-operations.md)
- [Troubleshooting Guide](../06-operations/troubleshooting.md)
