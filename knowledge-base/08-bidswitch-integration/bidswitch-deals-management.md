# BidSwitch Deals Management & Troubleshooting

## Overview

This document provides comprehensive guidance on BidSwitch deal management, troubleshooting insights, and diagnostic patterns. This knowledge is essential for the deal analysis tool and campaign troubleshooting agent.

## Deal Lifecycle Management

### Deal Statuses

| Status | Description | Action Required |
|--------|-------------|-----------------|
| **Active** | Deal trading as expected | Monitor performance |
| **Avails** | Too few avails available | Check geo-targeting, traffic filters |
| **eCPM** | Deal's eCPM too low | Investigate bidder performance |
| **Impressions** | Too few impressions served | Investigate deal performance |
| **Requests Sent** | Too few bid requests sent | Check targeting alignment |
| **Yes Bids** | Too few bid responses | Review buyer bidding logic |
| **Broken** | Deal has delivery issues | Check Delivery Status field |
| **Conditionally Completed** | Passed end date, targets not met | Extend end date |
| **Created in BidSwitch** | Ready for buyer sync | Wait for buyer system sync |
| **Counting** | Awaiting metrics collection | Wait 24 hours |
| **Paused** | Deal paused by party | Reactivate deal |
| **Pending** | Awaiting review | Complete review process |
| **Planned** | Accepted, waiting start date | Monitor for start |
| **Review** | Revision under review | Complete revision review |

### Quick Actions by Status

| Problem Status | Immediate Action |
|----------------|------------------|
| **No Trading** | Ensure deal accepted and active by both sides |
| **Too Few Avails** | Check geo-targeting and traffic filters |
| **Too Few Requests Sent** | Review targeting configuration |
| **Too Few Yes Bids** | Check buyer bidding logic |
| **Too Few Impressions** | Investigate deal performance |
| **Too Low eCPM** | Investigate bidder performance |
| **Out of Time Frame** | Adjust deal time range |
| **Inactive/Paused** | Set deal to active state |
| **Archived** | Adjust time range and activate |

## Troubleshooting Diagnostic Patterns

### Traffic Volume Issues

#### No Requests from Supplier
**Symptoms**: Zero bid requests received
**Diagnostic Steps**:
1. Verify supplier sending bid requests with correct Deal ID
2. Check if request volume > 1,000/day
3. Contact BidSwitch Support with bid request examples

#### Invalid Requests (>20%)
**Symptoms**: High invalid request percentage
**Root Causes**:
- Invalid JSON format
- Invalid inventory types (web, in-app)
- Invalid content types (display, video, audio, native)
- Wrong data center routing

#### Potential DSP Requests = 0
**Symptoms**: Supplier sends requests but DSP receives none
**Root Causes**:
- Incorrect `wseat` value
- Wrong Deal ID specification
- Deal routing configuration issues

### Bidding Issues

#### Deal Not Associated with DSP
**Symptoms**: Deal cannot route to correct buyer
**Root Causes**:
- Missing or incorrect `wseat` value
- Incorrect Deal ID in bid request
- Buyer hasn't updated Deal ID list

#### Yes-Bids with Target Deal = 0
**Symptoms**: Buyer not responding with Deal ID
**Diagnostic Steps**:
1. Verify buyer responding with correct Deal ID
2. Check buyer targeting configuration
3. Request example bid requests from BidSwitch Support

#### Yes-Bids with Different Deal
**Symptoms**: Buyer responds to different Deal ID
**Causes**:
- Multiple deals in request, buyer prefers different one
- Non-private deals: buyer prefers open auction
- Buyer responds without Deal ID

### Response Quality Issues

#### Malformed Responses
**Symptoms**: Invalid bid response format
**Actions**:
1. Check buyer logs for internal errors
2. Contact BidSwitch Support if logs appear normal

#### Wrong/Missing Deal ID
**Symptoms**: Incorrect or absent Deal ID in response
**Actions**:
1. Verify buyer responds with correct Deal ID
2. Ensure private deals include Deal ID
3. Contact BidSwitch Support if configuration correct

#### Blocked Creative
**Symptoms**: Creative blocked by BidSwitch
**Actions**:
1. Change creative being used
2. Review creative compliance requirements

#### Bid Below Floor
**Symptoms**: Buyer bidding below minimum price
**Root Causes**:
- Not respecting `imp.bidfloor` (open auctions)
- Not respecting `deals.bidfloor` (private deals)
- Not accounting for BidSwitch fees

### Protocol Compliance Issues

#### Bid Not Compliant with SSP Requirements
**Symptoms**: Response missing required supplier fields
**Actions**:
1. Review supplier-specific requirements
2. Include all required bid response fields

#### Bid Not Compliant with BidSwitch Protocol
**Symptoms**: Protocol violation errors
**Actions**:
1. Ensure full BidSwitch protocol compliance
2. Review protocol documentation

### Performance Issues

#### High Timeouts (>10%)
**Symptoms**: Excessive response timeouts
**Root Causes**:
- Insufficient server capacity
- Geographic latency (data center distance)
- Inadequate timeout window (`tmax`)

**Solutions**:
1. Increase server capacity
2. Move data center closer to BidSwitch
3. Request increased timeout window from supplier

#### High Invalid Requests (>20%)
**Symptoms**: Excessive request validation failures
**Diagnostic Areas**:
- JSON format validation
- Inventory type validation
- Content type validation
- Data center routing

#### Suspected Non-Human Traffic (>20%)
**Symptoms**: High bot/invalid traffic percentage
**Actions**:
1. Review traffic source trustworthiness
2. Implement traffic quality filters
3. Contact BidSwitch Support with examples

#### Invalid Cloud/Proxy IP Traffic (>20%)
**Symptoms**: High percentage of datacenter/proxy traffic
**Actions**:
1. Review traffic source quality
2. Implement IP filtering
3. Contact BidSwitch Support if legitimate

#### Blocked Publisher/Site (>20%)
**Symptoms**: High percentage of blocked inventory
**Actions**:
1. Check BidSwitch publisher blocklist
2. Review No Bid Reason data
3. Contact BidSwitch Support with examples

### Targeting Issues

#### Failed DSP User Matching (>50%)
**Symptoms**: High unmatched user percentage
**Root Causes**:
- Supplier sending unmatched user requests
- Buyer requiring matched users only
- Low user sync rates

**Solutions**:
1. Increase user sync frequency
2. Review user matching requirements
3. Optimize cookie sync processes

#### Failed DSP Geo Targeting (>50%)
**Symptoms**: Geographic targeting misalignment
**Root Causes**:
- Supplier sending wrong-country traffic
- Buyer geo-targeting too restrictive
- Deal geo-configuration mismatch

**Solutions**:
1. Align supplier traffic with buyer geo-targeting
2. Review and adjust geo-targeting settings
3. Verify deal geographic configuration

#### Filtered by SmartSwitch (>60%)
**Symptoms**: High SmartSwitch filtering rate
**Root Causes**:
- Buyer not purchasing similar traffic types
- Non-private deal subject to SmartSwitch

**Solutions**:
1. Increase similar traffic purchasing
2. Convert to private deal (SmartSwitch exempt)
3. Review traffic type alignment

## Integration with Deal Analysis Tool

### Diagnostic Workflow

1. **Status Check**: Identify current deal status
2. **Performance Metrics**: Analyze bid requests, responses, impressions
3. **Quality Assessment**: Check timeout rates, invalid percentages
4. **Targeting Analysis**: Review geo-targeting and user matching
5. **Protocol Compliance**: Verify bid response compliance
6. **Actionable Recommendations**: Provide specific fix actions

### Automated Diagnostics

The deal analysis tool should automatically:

- **Flag Performance Issues**: Identify patterns matching troubleshooting criteria
- **Suggest Root Causes**: Map symptoms to documented root causes
- **Recommend Actions**: Provide specific remediation steps
- **Escalation Triggers**: Identify when to contact BidSwitch Support

### Agent Knowledge Integration

The campaign troubleshooting agent should:

- **Pattern Recognition**: Match observed issues to documented patterns
- **Contextual Analysis**: Consider deal type, buyer, and supplier context
- **Progressive Diagnosis**: Follow diagnostic decision trees
- **Actionable Outputs**: Provide implementable recommendations

## Key Metrics Thresholds

| Metric | Threshold | Action Level |
|--------|-----------|--------------|
| **Timeouts** | >10% | High Priority |
| **Invalid Requests** | >20% | High Priority |
| **Non-Human Traffic** | >20% | Medium Priority |
| **Cloud/Proxy Traffic** | >20% | Medium Priority |
| **Blocked Publishers** | >20% | Medium Priority |
| **Failed User Matching** | >50% | High Priority |
| **Failed Geo Targeting** | >50% | High Priority |
| **SmartSwitch Filtering** | >60% | Medium Priority |

## Documentation Usage

This knowledge base should be:

1. **Referenced by Tools**: Deal analyzer and country analyzer
2. **Used by Agents**: Campaign troubleshooting prompts
3. **Updated Regularly**: As BidSwitch documentation evolves
4. **Cross-Referenced**: With campaign analysis workflows

## Next Steps

1. **Tool Enhancement**: Integrate diagnostic patterns into deal analyzer
2. **Agent Training**: Update troubleshooting prompts with this knowledge
3. **Automated Alerting**: Implement threshold-based alerts
4. **Reporting Integration**: Include diagnostic insights in analysis reports
