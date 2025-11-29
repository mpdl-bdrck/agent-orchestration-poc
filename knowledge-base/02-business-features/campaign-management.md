# Campaign Management

## Overview

Campaign management in Bedrock Platform provides comprehensive tools for creating, optimizing, and monitoring programmatic advertising campaigns. Our system supports flexible campaign structures, advanced targeting options, and real-time performance optimization.

### Platform Objectives

Bedrock Platform's campaign management follows core objectives designed to support the **Supply → Curate → Activate** workflow:

#### Supply Integration
- **Full creative format support**: Display, Video (with metrics), Native, Audio (with metrics)
- **All device types**: Web, In-App, DOOH (with pDOOH multipliers)
- **Private Marketplace support**: Deal ID targeting, spend allocation, pacing control
- **Programmatic Guaranteed**: Advanced deal functionality
- **Header Bidding**: Direct publisher integration capabilities

#### Curation Capabilities  
- **Multi-deal packaging**: Combine multiple supply deals with partner targeting
- **Fee tracking**: Curation fees and data usage fee monitoring
- **Partner integrations**: Inventory, contextual, audience, and algorithmic integrations
- **Comprehensive reporting**: Curation package performance analysis

#### Activation Features
- **Campaign budget control** with creative assignment to curation packages
- **Bidding parameter control** based on curation package variables
- **Delivery reporting** for campaigns and line items
- **Performance optimization** across the entire activation chain

## Campaign Hierarchy

### Platform Campaign Structure
Based on Bedrock Platform's architecture, campaigns follow a clear hierarchy designed for programmatic advertising efficiency:

```
Account (Agency/Client Organization)
├── Advertiser (Brand/Company)
│   └── Campaign (Time-limited marketing event)
│       └── Line Items (Specific targeting tactics)
│           └── Creatives (Ad assets for display)
```

### Key Components

#### Account Level
- **Organization container** for agencies or large advertisers
- **User management** and access control
- **Billing and financial management**
- **Cross-advertiser reporting** and analytics

#### Advertiser
- **Brand representation** - The company whose ads are being displayed
- **Campaign container** for all marketing efforts for that brand
- **Brand-level settings** and creative guidelines
- **Advertiser-specific reporting** and performance tracking

#### Campaigns
- **Time-limited marketing events** (e.g., "CocaCola Zero new trendy label for autumn 2025")
- **High-level container** for related advertising efforts targeting specific objectives
- **Budget allocation** and overall spend management across all line items
- **Flight dates** defining campaign start and end times
- **Brand safety** and content filtering rules

#### Line Items (Tactics)
- **Specific targeting configurations** (e.g., "UK students", "Germany weekend focus")
- **Granular audience targeting** with distinct configurations for testing specific segments
- **Individual budgets** and pacing controls per tactic
- **Unique bidding strategies** and multipliers
- **Performance tracking** at the most granular level

#### Supply Deals (Inventory Source Configuration)
- **Bedrock Platform entity** created in UI to define inventory sources
- **Two configuration types**:
  - **Private Marketplace (PMP)**: Points to negotiated deal from SSP (BidSwitch, Google AdX, Index Exchange)
  - **Open Exchange**: Uses filter lists to control non-PMP inventory access
- **Required fields**: Name, dates, creative type, inventory type, floor CPM
- **BidSwitch integration**: Only available for PMP-configured Supply Deals
- **Bundling**: Multiple Supply Deals combined into curation packages

**Supply Deal as a Link/Wrapper**:
- Supply Deals are Bedrock's internal representation of inventory sources
- For PMP configuration: Supply Deal wraps/points to external SSP deal
- The `sspDealId` field is the link between internal and external objects
- Tools debug BOTH: Supply Deal config (Bedrock) + external Deal performance (SSP API)

**Example**:
```
Supply Deal #12345 (Bedrock)
  ├─ Name: "Premium CTV UK"
  ├─ Dates: Jul 25 - Sep 30
  ├─ Floor: $2.50
  └─ sspDealId: "724071955398" ───> External BidSwitch Deal #724071955398
                                        ├─ Bid Requests: 35,000
                                        ├─ Impressions: 4,200
                                        └─ Status: Active
```

**Detecting Supply Deal Type** (programmatically):
```python
# From database/API
if supply_deal.sspDealId is not None and supply_deal.sspDealId != "":
    deal_type = "PMP"  # Has SSP deal ID → Private Marketplace
    # Can use BidSwitch API for diagnostics
else:
    deal_type = "OPEN_EXCHANGE"  # No SSP deal ID → Open Exchange
    # Use filter list analysis and internal metrics
```

**API Fields**:
- `sspId`: SSP identifier (optional) - which SSP provides the deal
- `sspDealId`: SSP deal identifier (optional) - the external deal ID
- `allocatedFilterListIds`: Filter lists for Open Exchange traffic control
- `excludedFilterListIds`: Filter lists to exclude from Open Exchange
- `dealType`: "private", "public", or "open" (deal classification)

#### Curation Packages (Inventory Bundling)
- **Bundle multiple Supply Deals** (mix of PMP and Open Exchange allowed)
- **Requirement**: Must contain ≥1 Supply Deal
- **Add targeting and data**: Partner integrations, audience segments, algorithmic signals
- **Assignment**: Line items point to ONE curation package (mandatory)
- **Reusability**: Multiple line items can use same curation package

#### Creatives
- **Ad assets** displayed when line item criteria are matched
- **Multiple creative support** - different sizes and devices per line item
- **Creative reusability** - same creatives can be used across different line items and campaigns
- **Format flexibility** - support for display, video, native, and rich media formats

## Real Campaign Examples

### Sample Line Item Strategies
Based on actual Bedrock Platform configurations, here are 8 common line item strategies used to structure campaigns:

| **Strategy** | **Base Bid** | **Targeting** | **Multipliers** | **Purpose** |
|-------------|-------------|---------------|----------------|-------------|
| **Retargeting** | $2.00 | Retargeted users from Exchange Wire | None | Test audience retargeting effectiveness |
| **Time-Targeted + UK** | $1.00 | UK, Weekdays, 8 AM - 8 PM | 150% during 9 AM - 2 PM | Test time-sensitive bidding during peak engagement |
| **City-Targeted - London** | $1.00 | UK with London focus | 125% for London | Broader UK coverage with London priority |
| **Retargeting + Manchester** | $2.50 | Manchester + Retargeted users | None | Test city-specific retargeting performance |
| **Germany Weekend Focus** | $1.20 | Germany, Weekends, 10 AM - 8 PM | 125% during 3 PM - 7 PM | Country-wide campaigns with weekend optimization |
| **France + Paris Multiplier** | $1.00 | France, Weekdays, 8 AM - 6 PM | 150% for Paris | Multi-city targeting with urban focus |
| **Multi-Country Retargeting** | $1.75 | UK, Germany, France, Italy + Retargeting | None | Test cross-border retargeting effectiveness |
| **NYC Competitive Campaign** | $3.00 | New York City, 9 AM - 9 PM | 200% during 5 PM - 8 PM | Aggressive bidding in competitive markets |

### Advanced Targeting Logic

#### Filter Group Configuration
Bedrock Platform uses **Group IDs** to control logical conditions between different targeting filters:

**Different Group IDs = OR Conditions**
- Filters with different group IDs are interpreted as OR conditions
- Example: Group 1 (Country: India) OR Group 2 (City: London, Manchester)
- **Result**: Target users in either India OR London OR Manchester

**Same Group IDs = AND Conditions**  
- Filters with the same group ID create AND conditions
- Example: Group 1 (Country: UK AND Device: Mobile AND Day: Weekend)
- **Result**: Only bid when ALL conditions are met simultaneously

#### Bidding Strategy Implementation
```json
Line Item Configuration Example:
{
  "baseBid": 1.20,
  "filters": [
    {
      "group": 1,
      "filterType": "country", 
      "values": ["DEU"]
    },
    {
      "group": 1,
      "filterType": "day",
      "values": ["6", "7"]  // Weekend
    }
  ],
  "strategies": [
    {
      "strategyType": "multiplier",
      "value": 1.25,
      "filters": [
        {
          "group": 4,
          "filterType": "hour",
          "values": ["15", "16", "17", "18", "19"]
        }
      ]
    }
  ]
}
```

## Budget Management & Pacing

### Budget Types
- **Total Campaign Budget**: Overall spend limit across all line items
- **Daily Budget Limits**: Maximum spend per day to control pacing
- **Line Item Budgets**: Individual tactic-level spend controls
- **Hourly Pacing**: Real-time spend distribution throughout the day

### Pacing Strategies
- **Even Pacing**: Distribute spend evenly across campaign duration
- **ASAP Pacing**: Spend budget as quickly as possible while respecting caps
- **Custom Pacing**: Define specific spend curves based on business needs
- **Peak Hour Optimization**: Increase bidding during high-performance periods

### Budget Monitoring
- **Real-time spend tracking** with alerts for approaching limits
- **Pace-to-goal indicators** showing projected vs. target spend
- **Budget utilization reports** across campaigns and line items
- **Automatic pause triggers** when budgets are exhausted

## Targeting Capabilities

### Audience Targeting
- **Demographic Targeting**: Age, gender, income, education
- **Geographic Targeting**: Country, region, city, postal code
- **Behavioral Targeting**: Purchase intent, browsing history, interests
- **Contextual Targeting**: Website content, page categories, keywords

### Advanced Targeting Features
- **Retargeting**: Re-engage users who previously interacted with campaigns
- **Lookalike Audiences**: Find users similar to existing customers
- **Custom Segments**: Upload first-party data for precise targeting
- **Exclusion Lists**: Prevent ads from showing to specific audiences

### Technical Targeting
- **Device Targeting**: Desktop, mobile, tablet, connected TV
- **Operating System**: iOS, Android, Windows, macOS
- **Browser Targeting**: Chrome, Safari, Firefox, Edge
- **Connection Type**: WiFi, cellular, broadband

## Frequency Capping

### Frequency Control Options
- **Impression Frequency**: Limit ad exposures per user per time period
- **Click Frequency**: Control click-through rates and user experience
- **Conversion Frequency**: Manage post-conversion ad exposure
- **Cross-Campaign Frequency**: Coordinate exposure across multiple campaigns

### Time-Based Frequency Caps
- **Hourly Caps**: Prevent ad fatigue within short time periods
- **Daily Caps**: Control daily exposure for optimal user experience
- **Weekly/Monthly Caps**: Long-term frequency management
- **Lifetime Caps**: Permanent exposure limits for specific users

### Frequency Optimization
- **Performance-Based Adjustment**: Increase frequency for high-performing segments
- **Fatigue Detection**: Automatically reduce frequency when performance declines
- **Competitive Analysis**: Adjust frequency based on market saturation
- **User Journey Mapping**: Optimize frequency across conversion funnel stages

## Creative Management

### Creative Types Supported
- **Display Banners**: Standard IAB sizes and custom dimensions
- **Video Ads**: Pre-roll, mid-roll, post-roll, and outstream formats
- **Native Ads**: In-feed, recommendation, and sponsored content
- **Rich Media**: Interactive and expandable creative formats

### Creative Optimization
- **A/B Testing**: Compare creative performance across variations
- **Dynamic Creative**: Real-time creative customization based on user data
- **Creative Rotation**: Automatic rotation to prevent ad fatigue
- **Performance-Based Selection**: Serve best-performing creatives more frequently

### Creative Approval Process
- **Automated Screening**: Technical compliance and brand safety checks
- **Manual Review**: Human review for sensitive or complex creatives
- **Publisher Approval**: Platform-specific creative approval workflows
- **Version Control**: Track creative changes and performance history

## Performance Monitoring

### Real-Time Metrics
- **Impressions Delivered**: Total ad exposures across campaigns
- **Click-Through Rate (CTR)**: User engagement with ad creatives
- **Conversion Rate**: Actions taken after ad exposure
- **Cost Per Action (CPA)**: Efficiency of campaign spend

### Advanced Analytics
- **Attribution Modeling**: Multi-touch attribution across user journey
- **Incrementality Testing**: Measure true campaign impact
- **Audience Insights**: Detailed performance by audience segments
- **Competitive Intelligence**: Market share and competitive positioning

### Optimization Recommendations
- **Bid Optimization**: Automated bid adjustments based on performance
- **Audience Expansion**: Identify new high-performing audience segments
- **Creative Recommendations**: Suggest creative improvements based on data
- **Budget Reallocation**: Optimize spend distribution across line items

## Multi-Currency Support

### Currency Features
- **Account-Level Currency**: Set primary currency for billing and reporting
- **Multi-Currency Display**: View performance in local currencies
- **Real-Time Conversion**: Automatic currency conversion for global campaigns
- **Currency-Specific Budgets**: Set budgets in local market currencies

### Supported Currencies
- **USD**: United States Dollar (primary platform currency)
- **EUR**: Euro for European markets
- **GBP**: British Pound for UK campaigns
- **AUD**: Australian Dollar for Australian markets
- **Additional currencies** available based on market requirements

## User Roles & Permissions

### Role-Based Access Control (RBAC)
- **Admin**: Full platform access and user management
- **Campaign Manager**: Campaign creation, editing, and optimization
- **Reporting Manager**: Read-only access to performance data
- **Custom Roles**: Tailored permissions based on organizational needs

### Permission Levels
- **CRUD**: Create, Read, Update, Delete access
- **CRU**: Create, Read, Update (no delete permissions)
- **R**: Read-only access to data and reports
- **N/A**: No access to specific platform areas

## Getting Started with Campaign Management

### Campaign Setup Checklist
1. **Define Campaign Objectives**: Awareness, consideration, conversion
2. **Set Budget Parameters**: Total budget, daily limits, pacing strategy
3. **Configure Targeting**: Audience, geographic, and technical parameters
4. **Upload Creatives**: Ensure compliance and optimization
5. **Set Frequency Caps**: Balance reach and user experience
6. **Launch and Monitor**: Real-time performance tracking and optimization

### Best Practices
- **Start with Conservative Budgets**: Scale successful campaigns gradually
- **Test Multiple Audiences**: Identify highest-performing segments
- **Monitor Frequency Metrics**: Prevent ad fatigue and optimize reach
- **Regular Performance Reviews**: Weekly optimization and strategy adjustments

## Related Topics
- [Reporting and Analytics](reporting-analytics.md)
- [Retargeting Strategies](retargeting.md)
- [Platform Architecture](../03-technical-features/platform-architecture.md)
- [Integration Setup](../05-integrations/integration-overview.md)
