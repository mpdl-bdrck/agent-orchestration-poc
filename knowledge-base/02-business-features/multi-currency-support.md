# Multi-Currency Support

## Overview

Bedrock Platform's multi-currency support enables global advertisers to manage campaigns, set budgets, and view reports in their local currencies while maintaining USD as the internal processing standard. This feature simplifies international campaign management through account-level currency configuration, real-time conversion, and localized financial reporting.

## Key Features

### Account-Level Currency Configuration
- **Primary Currency Setting**: Each account configured with `currencyCode` (e.g., AUD, EUR, INR)
- **Conversion Factor**: Account-specific `conversionFactorFromUSD` for accurate currency translation
- **Currency Symbol**: Display symbol (`currencySymbol`) for UI formatting and user experience
- **Flexible Configuration**: Support for new currencies through database configuration updates

### Real-Time Currency Conversion
- **Frontend-Driven Conversion**: All currency conversion handled entirely on the frontend
- **USD Internal Processing**: Backend continues to store and return all monetary values in USD
- **Dynamic Rate Application**: Conversion factors applied at display time using cached account settings
- **Precision Handling**: Safe precision management with proper rounding to avoid floating-point errors

### Localized User Experience
- **Native Currency Display**: All monetary values displayed in account's configured currency
- **Consistent Formatting**: Proper currency symbol placement and thousands separators
- **Input Localization**: Users enter values in their local currency with automatic USD conversion
- **Reporting Localization**: All financial metrics displayed in account currency across dashboards

## Technical Architecture

### Account Configuration Structure

**Database Schema Enhancement:**
```sql
ALTER TABLE accounts ADD COLUMN currencyCode VARCHAR(3);        -- ISO currency code
ALTER TABLE accounts ADD COLUMN conversionFactorFromUSD DECIMAL(10,6);  -- Conversion multiplier
ALTER TABLE accounts ADD COLUMN currencySymbol VARCHAR(5);      -- Display symbol
```

**Example Account Configuration:**
```json
{
  "accountId": "12345",
  "currencyCode": "AUD", 
  "currencySymbol": "$",
  "conversionFactorFromUSD": 1.5
}
```

### Data Flow & Conversion Strategy

#### Frontend Responsibilities
- **Cache Currency Settings**: Store `currencyCode`, `currencySymbol`, and `conversionFactorFromUSD` from login
- **Display Conversion**: Convert USD values to account currency using `valueInCurrency = valueInUSD * conversionFactorFromUSD`
- **Input Conversion**: Convert user input to USD before API submission using `valueInUSD = valueInCurrency / conversionFactorFromUSD`
- **Consistent Formatting**: Apply proper currency formatting across all UI components

#### Backend Responsibilities
- **USD Standard Maintenance**: Continue storing and returning all monetary values in USD
- **Authentication Enhancement**: Include currency configuration in `auth.login` API response
- **No Conversion Logic**: Backend performs no currency conversion, maintaining existing API contracts
- **Configuration Management**: Manage currency settings through account configuration APIs

### Currency Conversion Examples

#### Australian Dollar (AUD) Account
```javascript
// Account Configuration
const account = {
  currencyCode: "AUD",
  currencySymbol: "$", 
  conversionFactorFromUSD: 1.5
};

// Display Conversion (USD to AUD)
const usdValue = 1000;  // From API
const audValue = usdValue * 1.5;  // Display as 1500 AUD

// Input Conversion (AUD to USD)  
const userInput = 4500;  // User enters 4500 AUD
const usdForAPI = userInput / 1.5;  // Send 3000 USD to API
```

#### Euro (EUR) Account
```javascript
// Account Configuration
const account = {
  currencyCode: "EUR",
  currencySymbol: "€",
  conversionFactorFromUSD: 0.85
};

// Display Conversion
const usdSpend = 10000;  // Backend returns 10000 USD
const eurDisplay = usdSpend * 0.85;  // Show as 8500 EUR

// Input Conversion
const eurBudget = 1700;  // User sets 1700 EUR budget
const usdBudget = eurBudget / 0.85;  // Store as 2000 USD
```

## Implementation Process

### Step 1: Account Currency Setup
1. **Account Configuration**: Set `currencyCode`, `conversionFactorFromUSD`, and `currencySymbol` during account creation
2. **Authentication Update**: Modify `auth.login` API to return currency configuration data
3. **Validation**: Ensure conversion factors and currency codes are properly validated and stored
4. **Testing**: Verify currency configuration retrieval and caching in frontend applications

### Step 2: Frontend Integration
1. **Currency Caching**: Implement currency configuration caching on login with proper session management
2. **Conversion Utilities**: Create utility functions for USD-to-local and local-to-USD conversions
3. **UI Component Updates**: Update all monetary display components to use currency conversion and formatting
4. **Input Handling**: Modify form inputs to accept local currency and convert to USD before submission

### Step 3: Reporting Enhancement
1. **Dashboard Updates**: Convert all reporting metrics from USD to account currency for display
2. **Chart Formatting**: Apply proper currency formatting to charts, graphs, and summary cards
3. **Export Functions**: Ensure CSV and Excel exports show values in account currency
4. **Historical Data**: Apply currency conversion to historical reporting data consistently

## Multi-Currency Campaign Management

### Supply Deal Creation
- **Floor CPM Input**: Users enter floor prices in their local currency
- **Target Spend Configuration**: Budget and spend limits set in account currency
- **Automatic Conversion**: System converts local currency inputs to USD for storage
- **Display Consistency**: All monetary fields show values in account currency with proper symbols

### Curation Package Setup  
- **Supply Deal Pricing**: Package pricing displayed and configured in account currency
- **Audience Segment Costs**: Third-party data costs shown in local currency
- **Total Floor Price**: Calculated totals displayed with proper currency formatting
- **Cost Optimization**: Package cost comparisons in familiar currency units

### Campaign Budget Management
- **Budget Setting**: Campaign and line item budgets configured in account currency
- **Spend Tracking**: Real-time spend monitoring in local currency with USD backend tracking
- **Pacing Control**: Budget pacing and spend limits managed in account currency
- **Alert Thresholds**: Budget alerts and notifications triggered based on local currency values

## Reporting & Analytics

### Financial Metrics Display
- **Total Media Spend**: Displayed in account currency with proper formatting
- **Total Spend**: All cost metrics converted and formatted for local currency
- **CPM/CPC/CPA**: Performance metrics shown in account currency for easy interpretation
- **Revenue Tracking**: Revenue and ROAS calculations in familiar currency units

### Reporting Consistency
- **Cross-Report Uniformity**: Consistent currency display across all reporting views
- **Time Series Data**: Historical performance data converted using appropriate exchange rates
- **Drill-Down Views**: Detailed reporting maintains currency consistency at all levels
- **Export Functionality**: Downloaded reports maintain local currency formatting

### Performance Analysis
- **Cost Efficiency**: CPA and ROAS analysis in account currency for better decision-making
- **Budget Utilization**: Spend analysis and budget performance in familiar currency units
- **Trend Analysis**: Performance trends displayed in consistent local currency values
- **Competitive Benchmarking**: Industry benchmarks adjusted for local currency context

## Currency Configuration Examples

### Australian Market (AUD)
```json
{
  "currencyCode": "AUD",
  "currencySymbol": "$",
  "conversionFactorFromUSD": 1.5,
  "example": {
    "userInput": "4500 AUD",
    "storedValue": "3000 USD",
    "displayValue": "4500 AUD"
  }
}
```

### European Market (EUR)
```json
{
  "currencyCode": "EUR", 
  "currencySymbol": "€",
  "conversionFactorFromUSD": 0.85,
  "example": {
    "userInput": "850 EUR",
    "storedValue": "1000 USD", 
    "displayValue": "850 EUR"
  }
}
```

### Indian Market (INR)
```json
{
  "currencyCode": "INR",
  "currencySymbol": "₹", 
  "conversionFactorFromUSD": 83.0,
  "example": {
    "userInput": "83000 INR",
    "storedValue": "1000 USD",
    "displayValue": "83000 INR"
  }
}
```

## Advanced Features

### Precision & Accuracy Management
- **Decimal Precision**: Proper handling of currency precision (2 decimal places for most currencies)
- **Rounding Rules**: Consistent rounding rules applied across all currency conversions
- **Floating Point Safety**: Use of appropriate numeric types to prevent precision loss
- **Validation**: Input validation for currency amounts within acceptable ranges

### Extensibility & Maintenance  
- **Dynamic Currency Support**: New currencies added through database configuration without code changes
- **Conversion Factor Updates**: Account-level conversion factors can be updated as needed
- **Fallback Handling**: Graceful fallback to USD display if currency configuration missing
- **Error Handling**: Proper error handling for invalid currency configurations or conversion failures

### Performance Optimization
- **Frontend Caching**: Currency configuration cached to avoid repeated API calls
- **Conversion Efficiency**: Lightweight conversion calculations with minimal performance impact
- **Batch Processing**: Efficient handling of multiple currency conversions in reporting
- **Memory Management**: Optimal memory usage for currency configuration storage

## Monitoring & Metrics

### Currency Conversion Tracking
```
Metric: config_change
Dimensions: entity="account", field="currency"
Purpose: Detect when account currency configuration is updated

Metric: currency_change_applied_account_to_usd  
Dimensions: accountId, metricName, valueInCurrency, convertedToUSD
Purpose: Log conversions from account currency to USD before storing

Metric: currency_change_applied_usd_to_account
Dimensions: accountId, metricName, valueInUSD, convertedToCurrency  
Purpose: Log conversions from USD to account currency for display
```

### Performance Monitoring
- **Conversion Accuracy**: Monitor conversion calculations for accuracy and consistency
- **Display Performance**: Track frontend performance impact of currency conversion
- **API Response Times**: Ensure currency configuration doesn't impact authentication performance
- **Error Rates**: Monitor currency conversion errors and fallback scenarios

### Alerting & Diagnostics
```
Alert: missing_conversion_factor
Trigger: Account missing conversionFactorFromUSD value
Action: Investigate account setup and ensure factor is configured

Alert: invalid_converted_metrics  
Trigger: Converted metric is zero or negative when it shouldn't be
Action: Validate original USD values and conversion factor logic
```

## Testing & Validation

### Test Scenarios

#### Currency Configuration Testing
1. **Account Setup**: Create test accounts with different currency configurations (AUD, EUR, INR)
2. **Authentication**: Verify currency configuration returned in login API response
3. **Caching**: Validate frontend caching of currency settings across sessions
4. **Fallback**: Test behavior when currency configuration is missing or invalid

#### Conversion Accuracy Testing
1. **Input Conversion**: Test user input conversion from local currency to USD
2. **Display Conversion**: Verify USD values converted correctly to account currency for display
3. **Precision**: Validate precision handling and rounding across different currencies
4. **Edge Cases**: Test extreme values, zero amounts, and boundary conditions

#### End-to-End Campaign Testing
1. **Campaign Creation**: Set up campaigns with non-USD account currency
2. **Budget Management**: Configure budgets in local currency and verify USD storage
3. **Spend Tracking**: Run campaigns and verify spend tracking in both currencies
4. **Reporting**: Validate all reporting metrics display in correct account currency

### Quality Assurance Checklist
- [ ] Account currency configuration properly stored and retrieved
- [ ] Authentication API returns currency settings correctly
- [ ] Frontend caches currency configuration on login
- [ ] All monetary inputs convert correctly from local currency to USD
- [ ] All monetary displays convert correctly from USD to local currency
- [ ] Currency symbols and formatting applied consistently across UI
- [ ] Reporting metrics display in account currency across all views
- [ ] CSV/Excel exports maintain local currency formatting
- [ ] Error handling works for missing or invalid currency configuration
- [ ] Performance impact minimal for currency conversion operations

## Best Practices

### Configuration Management
- **Accurate Conversion Factors**: Ensure conversion factors reflect current market rates
- **Regular Updates**: Periodically review and update conversion factors as needed
- **Documentation**: Maintain clear documentation of currency configuration for each account
- **Validation**: Implement proper validation for currency codes and conversion factors

### User Experience
- **Consistent Display**: Maintain consistent currency formatting across all platform interfaces
- **Clear Indicators**: Always display currency symbols and codes to avoid confusion
- **Input Guidance**: Provide clear guidance on currency expectations in form fields
- **Error Messages**: Clear error messages for currency-related validation failures

### Technical Implementation
- **Precision Handling**: Use appropriate numeric types to maintain precision across conversions
- **Performance Optimization**: Minimize conversion calculations and cache results where appropriate
- **Error Handling**: Implement robust error handling for currency conversion failures
- **Testing Coverage**: Comprehensive testing across different currencies and edge cases

## Troubleshooting

### Common Issues & Solutions

#### Currency Not Displaying Correctly
- **Check Account Configuration**: Verify `currencyCode`, `conversionFactorFromUSD`, and `currencySymbol` are set
- **Validate Authentication**: Ensure currency configuration returned in login API response
- **Frontend Caching**: Check if currency settings properly cached and accessible in UI components
- **Conversion Logic**: Verify conversion calculations using correct formula and factors

#### Conversion Accuracy Problems
- **Precision Issues**: Check for floating-point precision problems in conversion calculations
- **Rounding Errors**: Validate rounding rules and ensure consistent application
- **Factor Validation**: Verify conversion factors are accurate and up-to-date
- **Edge Cases**: Test with extreme values and boundary conditions

#### Performance Issues
- **Conversion Overhead**: Monitor performance impact of currency conversion calculations
- **Caching Efficiency**: Ensure currency configuration properly cached to avoid repeated API calls
- **Batch Processing**: Optimize conversion of multiple values in reporting and analytics
- **Memory Usage**: Monitor memory consumption for currency configuration storage

## Integration Points

### Platform Components
- **Terminal UI**: Currency configuration interface and localized monetary displays
- **Authentication Service**: Currency configuration delivery through login API
- **Campaign Management**: Local currency input handling and USD conversion
- **Reporting Service**: USD to local currency conversion for all financial metrics
- **Analytics Dashboard**: Consistent currency formatting across charts and summaries

### External Systems
- **Billing Systems**: Integration with invoicing systems for multi-currency billing
- **Financial Reporting**: Export capabilities for accounting and financial analysis
- **Exchange Rate Services**: Integration with financial data providers for rate updates
- **Client Reporting**: Multi-currency reporting for international client accounts

## Related Topics
- [Campaign Management](campaign-management.md) - Setting up campaigns with multi-currency budgets
- [Reporting and Analytics](reporting-analytics.md) - Financial reporting in local currencies
- [Platform Architecture](../03-technical-features/platform-architecture.md) - Technical implementation details
- [User Role Management](../06-operations/user-role-management.md) - Access control for currency configuration
