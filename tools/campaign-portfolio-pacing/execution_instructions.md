# Execution Instructions: analyze_portfolio_pacing

## Context-Aware Guidance

This document provides contextual instructions for using the `analyze_portfolio_pacing` tool. These instructions are injected into the agent's prompt when the tool is about to be called, providing granular guidance based on the user's question.

### When user asks about trends or recent data

**Keywords**: "trend", "last", "recent", "recently", "recent days", "over the last"

**Focus Areas**:
- Emphasize the `daily_trend` array from the tool results
- Provide insights about recent spending patterns
- Compare recent days to historical averages
- Identify patterns or anomalies in recent data

**Example Response Pattern**:
- "Over the last {N} days, spending has..."
- "Looking at recent trends, the portfolio shows..."
- "The daily_trend data reveals..."

**Data to Highlight**:
- Most recent entries in `daily_trend` array
- Comparison between recent days and campaign average
- Trend direction (increasing/decreasing/stable)

---

### When user asks about risk or underdelivery

**Keywords**: "risk", "at risk", "underdelivery", "meet budget", "budget exhaustion", "complete budget"

**Focus Areas**:
- Highlight `pacing_status` (ON_TRACK, SLIGHTLY_BEHIND, BEHIND, AT_RISK)
- Emphasize `budget_projection` percentage
- Compare `required_daily_rate` vs `actual_daily_rate`
- Assess if portfolio is at risk of not meeting budget goals

**Example Response Pattern**:
- "The portfolio is {pacing_status} with a projection of {budget_projection}%"
- "To meet budget goals, the required daily rate is {required_daily_rate}, but actual is {actual_daily_rate}"
- "Risk assessment: {risk_level} - {reasoning}"

**Data to Highlight**:
- `pacing_status` field
- `budget_projection` vs 100%
- `required_daily_rate` vs `actual_daily_rate`
- `remaining_budget` and `days_left`

---

### When user asks for calculations

**Keywords**: "average", "calculate", "compute", "sum", "total", "mean"

**Focus Areas**:
- Use `daily_trend` data for calculations
- Show work step-by-step with specific dates and amounts
- Reference specific days from the trend array
- Provide clear mathematical breakdown

**Example Response Pattern**:
- "To calculate the average over last {N} days:"
- "Step 1: Sum the spend for dates {dates}: {amounts} = {total}"
- "Step 2: Divide by {N}: {total} / {N} = {average}"

**Data to Highlight**:
- Specific dates and amounts from `daily_trend`
- Calculation steps
- Final computed values

---

### When user asks about pacing status

**Keywords**: "pacing", "on track", "behind", "ahead", "pacing status", "pacing rate"

**Focus Areas**:
- Compare `actual_daily_rate` vs `target_daily_rate` vs `required_daily_rate`
- Explain what `pacing_status` means in practical terms
- Provide context about what each rate represents
- Explain implications of current pacing

**Example Response Pattern**:
- "Current pacing is {pacing_status} because..."
- "The target daily rate is {target_daily_rate}, but actual is {actual_daily_rate}"
- "To get back on track, you need to spend {required_daily_rate} per day"

**Data to Highlight**:
- All three daily rates (target, actual, required)
- `pacing_status` interpretation
- Gap analysis between rates

---

### When user asks about budget status

**Keywords**: "budget", "spent", "remaining", "budget status", "budget utilization"

**Focus Areas**:
- Highlight `spend_percentage` and `budget_projection`
- Show `spent_budget` vs `portfolio_budget`
- Calculate `remaining_budget`
- Explain budget health status

**Example Response Pattern**:
- "{spend_percentage}% of budget has been spent"
- "Remaining budget: {remaining_budget} out of {portfolio_budget}"
- "Projected to spend {budget_projection}% by end of campaign"

**Data to Highlight**:
- `budget_status` object fields
- Percentage calculations
- Projections

---

## Common Patterns

### Follow-up questions about same portfolio

**Context Detection**: If conversation history mentions "Eli Lilly", "Lilly", or previous portfolio analysis

**Guidance**:
- Use `account_id="17"` and `advertiser_filter="Lilly"` (same as previous call)
- Reference previous analysis if available
- Build on previous insights rather than starting fresh

### Time-based queries

**Context Detection**: Questions about specific time periods ("last week", "this month", "last 3 days")

**Guidance**:
- Filter `daily_trend` array to relevant date range
- Focus on dates within the specified period
- Compare period performance to overall campaign

### Comparative queries

**Context Detection**: Questions comparing periods, rates, or metrics

**Guidance**:
- Extract relevant metrics from tool results
- Perform comparisons explicitly
- Show differences and percentages
- Explain what comparisons mean

---

## Output Formatting Guidelines

When presenting tool results:

1. **Always provide context**: Explain what the numbers mean
2. **Use specific values**: Reference actual amounts, dates, and percentages from the tool results
3. **Show calculations**: When computing averages or trends, show the math
4. **Highlight key insights**: Emphasize the most important findings
5. **Provide actionable guidance**: If pacing is off, suggest what needs to change

---

## Template Variables

This document supports template variables that are replaced at runtime:
- `{question}` - The current user question
- `{tool_name}` - Name of the tool being called
- `{account_id}` - Account ID being analyzed
- `{advertiser_filter}` - Advertiser filter if specified

