# Client Integrations

## Overview

Bedrock Platform provides comprehensive client integration capabilities including pixel-based tracking, user synchronization, retargeting implementation, and cross-domain user identification. These integrations enable clients to implement advanced audience targeting, conversion tracking, and campaign optimization.

## Integration Architecture

### Core Integration Components
- **User Sync Service**: Cross-domain user identification and synchronization
- **Pixel Tracking System**: Conversion and retargeting pixel implementation
- **Retargeting Engine**: Custom audience segment creation and targeting
- **Cross-Domain Tracking**: User journey tracking across multiple domains
- **Privacy Compliance**: GDPR, CCPA, and COPPA compliant tracking

### Integration Endpoints
```
User Sync: https://sync.bedrockplatform.bid/
Pixel Tracking: https://tracker.bedrockplatform.bid/
Retargeting: https://sync.bedrockplatform.bid/user/identify/
Conversion Tracking: https://tracker.bedrockplatform.bid/conv
```

## User Synchronization

### Cross-Domain User Sync
**User Sync Architecture:**
- **BidSwitch Integration**: Automatic user ID synchronization with BidSwitch
- **Cross-Domain Cookies**: User identification across client domains
- **Privacy Compliance**: GDPR consent management and validation
- **TTL Management**: Configurable user data retention periods

### BidSwitch User Matching
**Sync Endpoint Configuration:**
```
https://sync.bedrockplatform.bid/user/sync/ssps?
  sync=0&
  sourceId=0f9956fc-b6af-4e9b-9377-d565b386e111&
  userId=${BSW_PARAM}&
  gdpr=${GDPR}&
  consent=${GDPR_CONSENT}&
  rurl=https%3A%2F%2Fx.bidswitch.net%2Fsync%3F
    dsp_id%3D503%26
    user_id%3D${USER}%26
    expires%3D5%26
    ssp%3D${SSP}%26
    bsw_param%3D${BSW_PARAM}
```

**Key Parameters:**
- **user_id**: Buyer user ID from Bedrock platform
- **bsw_param**: BidSwitch user ID for synchronization
- **sourceId**: Fixed identifier for BidSwitch integration
- **dsp_id**: Set to `503` for Bedrock integration

### User Identification Endpoints
**Partner-Specific Sync URLs:**
| Partner | Endpoint |
|---------|----------|
| ExchangeWire | `/user/identify/019248ab-f296-70ed-9283-50724edcc81a` |
| Bedrock Platform | `/user/identify/19bea1ee-5c9a-4b68-bb12-60ede7a0b382` |

**Sync URL Format:**
```
https://sync.bedrockplatform.bid/user/identify/{segment_id}?
  sync=0&
  consent=${GDPR_CONSENT}&
  gdpr=${GDPR}
```

## Retargeting Implementation

### Custom Retargeting Pixels
**Pixel Generation Process:**
1. **Segment Creation**: Client creates custom audience segment in Terminal UI
2. **Pixel Generation**: System generates unique tracking pixel for segment
3. **Website Implementation**: Client places pixel on relevant website pages
4. **User Assignment**: Users visiting pages are automatically assigned to segment
5. **Campaign Targeting**: Segments available for targeting in campaign setup

### Retargeting Pixel Structure
**Basic Retargeting Pixel:**
```html
<!-- Retargeting Pixel Implementation -->
<img src="https://sync.bedrockplatform.bid/user/identify/{segment_id}?
  sync=0&
  consent=${GDPR_CONSENT}&
  gdpr=${GDPR}&
  marker_id={unique_user_id}" 
  width="1" height="1" style="display:none;" />
```

**JavaScript Implementation:**
```javascript
// Advanced retargeting pixel with consent management
(function() {
  // Check for GDPR consent
  var gdprConsent = getGDPRConsent(); // Client's consent management function
  var gdprFlag = hasGDPRApplies() ? '1' : '0';
  
  if (gdprConsent || gdprFlag === '0') {
    var pixel = new Image();
    pixel.src = 'https://sync.bedrockplatform.bid/user/identify/{segment_id}?' +
      'sync=0&' +
      'consent=' + encodeURIComponent(gdprConsent) + '&' +
      'gdpr=' + gdprFlag + '&' +
      'marker_id=' + generateUniqueId();
    pixel.width = 1;
    pixel.height = 1;
    pixel.style.display = 'none';
    document.body.appendChild(pixel);
  }
})();
```

### Aerospike Data Structure
**Marker to Segments Mapping:**
```
Namespace: dmp
Set: markers
Key: marker_id

Record Structure:
{
  "version": 1,
  "segments": {
    "seg_12345": {
      "ttl": 1721779200,
      "last_updated": 1721692800
    },
    "seg_67890": {
      "ttl": 1721865600,
      "last_updated": 1721779200
    }
  }
}
```

**Segment Counters:**
```
Namespace: dmp
Set: segment_counters
Key: "{segment_id}:{date_timestamp}"

Record Structure:
{
  "segment_id": "seg_12345",
  "date": "20250825",
  "count": 45,
  "ttl": segment_ttl_seconds
}
```

### TTL Management
**Segment Expiration:**
- **Individual TTL**: Each segment has configurable TTL (7, 30, 90 days)
- **Automatic Cleanup**: Expired segments automatically removed from user records
- **Refresh Mechanism**: User visits refresh segment TTL for that specific segment
- **Counter Updates**: Daily counters updated when segments are refreshed

## Conversion Tracking

### Conversion Pixel Implementation
**Standard Conversion Pixel:**
```html
<!-- Conversion Tracking Pixel -->
<img src="https://tracker.bedrockplatform.bid/conv?
  cid={campaign_id}&
  lid={line_item_id}&
  crid={creative_id}&
  conv_type=purchase&
  conv_value=99.99&
  currency=USD&
  order_id={unique_order_id}" 
  width="1" height="1" style="display:none;" />
```

**JavaScript Conversion Tracking:**
```javascript
// Enhanced conversion tracking with validation
function trackConversion(conversionData) {
  // Validate required parameters
  if (!conversionData.campaign_id || !conversionData.line_item_id) {
    console.error('Missing required conversion parameters');
    return;
  }
  
  // Build tracking URL
  var trackingUrl = 'https://tracker.bedrockplatform.bid/conv?' +
    'cid=' + encodeURIComponent(conversionData.campaign_id) + '&' +
    'lid=' + encodeURIComponent(conversionData.line_item_id) + '&' +
    'crid=' + encodeURIComponent(conversionData.creative_id || '') + '&' +
    'conv_type=' + encodeURIComponent(conversionData.type || 'conversion') + '&' +
    'conv_value=' + encodeURIComponent(conversionData.value || '0') + '&' +
    'currency=' + encodeURIComponent(conversionData.currency || 'USD') + '&' +
    'order_id=' + encodeURIComponent(conversionData.order_id || '');
  
  // Fire tracking pixel
  var pixel = new Image();
  pixel.src = trackingUrl;
  pixel.width = 1;
  pixel.height = 1;
  pixel.style.display = 'none';
  document.body.appendChild(pixel);
}

// Usage example
trackConversion({
  campaign_id: 'camp123',
  line_item_id: 'li456',
  creative_id: 'cre789',
  type: 'purchase',
  value: '149.99',
  currency: 'USD',
  order_id: 'order_12345'
});
```

### Conversion Types
**Supported Conversion Events:**
- **Purchase**: E-commerce transactions with value
- **Lead**: Lead generation form submissions
- **Signup**: User registration events
- **Download**: File or app downloads
- **Custom**: Client-defined conversion events

### Attribution Windows
**Configurable Attribution:**
- **Post-Click Attribution**: 1-30 days (configurable)
- **Post-View Attribution**: 1-7 days (configurable)
- **Cross-Device Attribution**: User-level attribution across devices
- **Multi-Touch Attribution**: Distributed attribution across touchpoints

## Retargeting During Ad Serving

### Dynamic Segment Assignment
**Ad Serving Retargeting:**
- **Impression-Based Assignment**: Assign users to segments when serving ads
- **Line Item Configuration**: Configure segment assignment per line item
- **Real-Time Processing**: Immediate segment assignment during ad delivery
- **Campaign Integration**: Seamless integration with existing campaign targeting

### Implementation Flow
**Ad Serving Retargeting Process:**
1. **Line Item Setup**: Configure retargeting segment in line item settings
2. **Ad Delivery**: User sees ad impression from configured line item
3. **Segment Assignment**: User automatically assigned to retargeting segment
4. **Future Targeting**: User becomes targetable for retargeting campaigns
5. **Performance Tracking**: Track segment assignment and subsequent performance

**Line Item Configuration:**
```json
{
  "line_item_id": "li123",
  "retargeting_config": {
    "assign_segment": "retarget_segment_456",
    "ttl_days": 30,
    "assignment_trigger": "impression"
  },
  "targeting": {
    "segments": ["existing_segment_123"]
  }
}
```

## Cross-Domain Tracking

### Multi-Domain User Journey
**Cross-Domain Implementation:**
- **First-Party Cookies**: Domain-specific user identification
- **Third-Party Sync**: Cross-domain user synchronization
- **Privacy Compliance**: Consent-based cross-domain tracking
- **Data Consistency**: Unified user profiles across domains

### Implementation Guide
**Step 1: Primary Domain Setup**
```html
<!-- Primary domain pixel implementation -->
<script>
(function() {
  var bedrockSync = {
    domain: 'sync.bedrockplatform.bid',
    segmentId: 'your_segment_id',
    
    init: function() {
      this.setUserId();
      this.syncUser();
    },
    
    setUserId: function() {
      var userId = this.getCookie('bedrock_user_id');
      if (!userId) {
        userId = this.generateUserId();
        this.setCookie('bedrock_user_id', userId, 365);
      }
      return userId;
    },
    
    syncUser: function() {
      var userId = this.getCookie('bedrock_user_id');
      var pixel = new Image();
      pixel.src = 'https://' + this.domain + '/user/identify/' + this.segmentId + 
        '?sync=0&user_id=' + encodeURIComponent(userId);
    }
  };
  
  bedrockSync.init();
})();
</script>
```

**Step 2: Secondary Domain Sync**
```html
<!-- Secondary domain sync implementation -->
<script>
(function() {
  // Sync with primary domain user ID
  var iframe = document.createElement('iframe');
  iframe.src = 'https://sync.bedrockplatform.bid/cross-domain-sync?' +
    'domain=' + encodeURIComponent(window.location.hostname) + '&' +
    'segment_id=your_segment_id';
  iframe.style.display = 'none';
  document.body.appendChild(iframe);
})();
</script>
```

## Privacy & Compliance

### GDPR Compliance
**Consent Management:**
- **Consent String Processing**: IAB TCF v2.0 consent string support
- **Granular Consent**: Purpose-specific consent validation
- **Consent Refresh**: Automatic consent validation and refresh
- **Data Subject Rights**: Support for data deletion and portability requests

**GDPR Implementation:**
```javascript
// GDPR-compliant tracking implementation
function initBedrockTracking() {
  // Check if GDPR applies
  var gdprApplies = checkGDPRApplies(); // Client implementation
  
  if (gdprApplies) {
    // Get consent string
    var consentString = getConsentString(); // Client implementation
    
    // Validate consent for advertising purposes
    if (validateAdvertisingConsent(consentString)) {
      initializeTracking(consentString);
    } else {
      console.log('User has not consented to advertising tracking');
    }
  } else {
    // GDPR doesn't apply, proceed with tracking
    initializeTracking('');
  }
}

function initializeTracking(consentString) {
  // Initialize all tracking pixels with consent string
  var trackingParams = '&consent=' + encodeURIComponent(consentString) + 
                      '&gdpr=' + (checkGDPRApplies() ? '1' : '0');
  
  // Apply to all tracking calls
  trackRetargeting(trackingParams);
  trackConversions(trackingParams);
}
```

### CCPA Compliance
**California Privacy Rights:**
- **Do Not Sell**: Respect "Do Not Sell My Personal Information" requests
- **Opt-Out Mechanisms**: Provide clear opt-out options
- **Data Transparency**: Clear disclosure of data collection practices
- **Consumer Rights**: Support for data access and deletion requests

### Cookie Management
**Cookie Strategy:**
- **First-Party Cookies**: Domain-specific user identification
- **Secure Cookies**: HTTPS-only cookie transmission
- **SameSite Policies**: Appropriate SameSite cookie attributes
- **Expiration Management**: Configurable cookie expiration periods

## Integration Testing

### Testing Framework
**Test Environment Setup:**
- **Staging Environment**: `https://staging.bedrockplatform.com/`
- **Test Pixels**: Non-production pixel endpoints for testing
- **Debug Mode**: Detailed logging for integration debugging
- **Validation Tools**: Pixel firing validation and verification

### Testing Checklist
**Pre-Launch Validation:**
- [ ] Pixel implementation fires correctly
- [ ] GDPR consent properly validated
- [ ] User IDs generated and stored correctly
- [ ] Cross-domain sync functioning
- [ ] Conversion tracking accurate
- [ ] Segment assignment working
- [ ] TTL management operational
- [ ] Privacy compliance verified

### Debug Tools
**Integration Debugging:**
```javascript
// Debug mode for pixel testing
window.bedrockDebug = {
  enabled: true,
  logLevel: 'verbose',
  
  log: function(message, data) {
    if (this.enabled) {
      console.log('[Bedrock Debug]', message, data);
    }
  },
  
  validatePixel: function(pixelUrl) {
    this.log('Firing pixel:', pixelUrl);
    
    // Test pixel firing
    var testPixel = new Image();
    testPixel.onload = function() {
      bedrockDebug.log('Pixel fired successfully');
    };
    testPixel.onerror = function() {
      bedrockDebug.log('Pixel firing failed');
    };
    testPixel.src = pixelUrl;
  }
};
```

## Performance Optimization

### Loading Optimization
**Asynchronous Loading:**
- **Non-Blocking Implementation**: Pixels load asynchronously
- **Error Handling**: Graceful degradation on tracking failures
- **Timeout Management**: Prevent tracking from blocking page load
- **Batch Processing**: Efficient batch pixel firing

### Caching Strategy
**Client-Side Caching:**
- **User ID Caching**: Cache user IDs to reduce sync calls
- **Consent Caching**: Cache consent decisions for session
- **Segment Caching**: Cache segment assignments locally
- **Performance Monitoring**: Track pixel loading performance

## Best Practices

### Implementation Guidelines
- **Progressive Enhancement**: Tracking should not break core functionality
- **Error Handling**: Robust error handling for all tracking calls
- **Performance Impact**: Minimize impact on page load performance
- **Privacy First**: Always respect user privacy preferences

### Security Considerations
- **HTTPS Only**: All tracking calls over secure connections
- **Data Validation**: Validate all tracking parameters
- **XSS Prevention**: Prevent cross-site scripting attacks
- **Content Security Policy**: Compatible with CSP implementations

### Maintenance & Monitoring
- **Regular Testing**: Periodic validation of tracking implementation
- **Performance Monitoring**: Monitor tracking performance and errors
- **Compliance Audits**: Regular privacy compliance reviews
- **Documentation Updates**: Keep integration documentation current

## Related Topics
- [Platform Architecture](../03-technical-features/platform-architecture.md) - Overall system architecture
- [User Role Management](../06-operations/user-role-management.md) - Access control and permissions
- [Analytics Platforms](analytics-platforms.md) - Analytics and measurement integration
- [Data Management](../03-technical-features/data-management.md) - Data processing and privacy compliance
