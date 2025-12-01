# Proactive Notification Panel - Implementation Plan

**Date**: December 1, 2025  
**Status**: 📋 **Implementation Plan** - Stage 1 with JSON-driven mock system  
**Related Documentation**: [`docs/PROACTIVE_NOTIFICATION_PANEL.md`](../docs/PROACTIVE_NOTIFICATION_PANEL.md)

---

## Overview

This plan implements **Stage 1** of the Proactive Notification Panel feature, transforming the system from a reactive chatbot into a proactive conversational command center. The implementation uses a **JSON-driven mock system** that simulates real API responses, making it easy to test different scenarios and transition to real system integration later.

**Key Design Decision**: Instead of hardcoding mock alerts in Python, we'll drive notifications from JSON files that simulate API responses. This approach:
- ✅ Simulates real API structure
- ✅ Easy to modify without code changes
- ✅ Testable with different JSON scenarios
- ✅ Production-ready (swap loader for HTTP client when ready)

---

## Cross-References

- **Feature Documentation**: [`docs/PROACTIVE_NOTIFICATION_PANEL.md`](../docs/PROACTIVE_NOTIFICATION_PANEL.md) - Complete feature specification, UX flow, and evolution stages
- **Architecture Patterns**: [`AI_HANDOFF.md`](../AI_HANDOFF.md) - Core architectural patterns (State-based communication, Prompt-driven reasoning)
- **Chainlit Integration**: [`docs/CHAINLIT_SQLITE_PERSISTENCE.md`](../docs/CHAINLIT_SQLITE_PERSISTENCE.md) - UI persistence considerations

---

## Implementation Checklist

### Phase 1: JSON-Driven Notification System ✅

- [ ] Create `config/notifications/` directory
- [ ] Create `config/notifications/mock_alerts.json` with alert templates
- [ ] Create `src/interface/chainlit/notification_loader.py` module
- [ ] Implement `NotificationLoader` class with streaming/static/replay modes
- [ ] Add JSON validation and error handling
- [ ] Add auto-creation of default JSON if missing

### Phase 2: Background Monitor Integration ✅

- [ ] Update `src/interface/chainlit/handlers.py` with `background_monitor()` function
- [ ] Integrate `NotificationLoader` into background monitor
- [ ] Support multiple playback modes (streaming, static, replay)
- [ ] Add error handling and retry logic
- [ ] Add logging for alert push events

### Phase 3: React Component ✅

- [ ] Create `public/elements/NotificationPanel.jsx` React component
- [ ] Implement alert rendering with severity colors
- [ ] Add click handler for context injection
- [ ] Style alerts with hover effects
- [ ] Display agent emojis and timestamps

### Phase 4: Context Injection ✅

- [ ] Update `main()` function in `handlers.py` to detect `SYSTEM_TRIGGER:` messages
- [ ] Extract context from notification click events
- [ ] Format context-injected messages for Orchestrator
- [ ] Test routing to appropriate agents

### Phase 5: Panel Initialization ✅

- [ ] Update `start()` function in `handlers.py`
- [ ] Create `NotificationPanel` CustomElement on chat start
- [ ] Store panel reference in `cl.user_session`
- [ ] Start background monitor task
- [ ] Test panel appears in right sidebar

---

## File Structure

```
agent_orchestration_poc/
├── config/
│   └── notifications/
│       └── mock_alerts.json          # JSON alert templates (NEW)
├── src/
│   └── interface/
│       └── chainlit/
│           ├── handlers.py           # Updated with background_monitor()
│           └── notification_loader.py  # NEW: JSON loader module
└── public/
    └── elements/
        └── NotificationPanel.jsx     # NEW: React component
```

---

## Detailed Implementation

### 1. JSON Alert Structure

**File**: `config/notifications/mock_alerts.json`

```json
{
  "metadata": {
    "source": "mock_api",
    "version": "1.0",
    "description": "Mock alerts simulating Guardian/Optimizer/Specialist/Pathfinder detection"
  },
  "alerts": [
    {
      "id": "alert_001",
      "agent": "guardian",
      "issue_type": "under_pacing",
      "severity": "warning",
      "message": "Campaign 'Summer_2025' is under-pacing by 40%.",
      "campaign_id": "Summer_2025",
      "deal_id": null,
      "details": "Current spend: $12K of $20K budget. Expected: $16K by now.",
      "timestamp": null,
      "delay_seconds": 5
    },
    {
      "id": "alert_002",
      "agent": "optimizer",
      "issue_type": "bid_too_low",
      "severity": "warning",
      "message": "Deal 12345 has low win rate (2.1%).",
      "campaign_id": null,
      "deal_id": "12345",
      "details": "Win rate below 3% threshold. Consider increasing bid cap.",
      "timestamp": null,
      "delay_seconds": 35
    },
    {
      "id": "alert_003",
      "agent": "specialist",
      "issue_type": "geo_conflict",
      "severity": "critical",
      "message": "Deal 67890: Geo targeting conflict detected.",
      "campaign_id": null,
      "deal_id": "67890",
      "details": "Both buyer and seller have geo-targeting. CTV deal with 68% delivery drop.",
      "timestamp": null,
      "delay_seconds": 65
    },
    {
      "id": "alert_004",
      "agent": "pathfinder",
      "issue_type": "qps_limit",
      "severity": "info",
      "message": "SSP 'PubMatic' approaching QPS limit.",
      "campaign_id": null,
      "deal_id": null,
      "details": "Current: 8.2K QPS of 10K limit. Consider traffic allocation.",
      "timestamp": null,
      "delay_seconds": 95
    }
  ],
  "settings": {
    "mode": "streaming",
    "loop": true,
    "interval_seconds": 30,
    "max_alerts": 10
  }
}
```

**Fields**:
- `id`: Unique alert identifier (can be auto-generated)
- `agent`: Which agent detected the issue (`guardian`, `optimizer`, `specialist`, `pathfinder`)
- `issue_type`: Type of issue (`under_pacing`, `bid_too_low`, `geo_conflict`, `qps_limit`)
- `severity`: Alert severity (`critical`, `warning`, `info`)
- `message`: Human-readable alert message
- `campaign_id`: Optional campaign identifier
- `deal_id`: Optional deal identifier
- `details`: Additional context/details
- `timestamp`: Auto-generated when alert is loaded (set to `null` in JSON)
- `delay_seconds`: For replay mode - delay before showing this alert

**Settings**:
- `mode`: `streaming` (one at a time), `static` (all at once), `replay` (use delay_seconds)
- `loop`: Whether to loop back to start when all alerts shown
- `interval_seconds`: Default interval between alerts (streaming mode)
- `max_alerts`: Maximum number of alerts to show in panel

---

### 2. Notification Loader Module

**File**: `src/interface/chainlit/notification_loader.py`

**Purpose**: Load alerts from JSON files, simulate API responses, support multiple playback modes.

**Key Features**:
- Loads JSON from `config/notifications/mock_alerts.json`
- Auto-creates default JSON if missing
- Supports streaming, static, and replay modes
- Adds dynamic fields (timestamp, ID) at runtime
- Validates JSON structure
- Singleton pattern for efficiency

**API**:
```python
loader = NotificationLoader(json_path=None)  # Uses default path
settings = loader.get_settings()              # Get settings dict
alert = loader.get_next_alert()              # Get next alert (streaming)
alerts = loader.get_all_alerts()             # Get all alerts (static)
loader.reset()                                # Reset to beginning
loader.reload()                               # Reload JSON file
```

**Error Handling**:
- Logs warnings if JSON file missing (creates default)
- Raises `ValueError` if JSON structure invalid
- Logs errors but doesn't crash on load failures

---

### 3. Background Monitor

**File**: `src/interface/chainlit/handlers.py` (add to existing file)

**Function**: `background_monitor()`

**Behavior**:
1. Wait 5 seconds for UI initialization
2. Load `NotificationLoader` singleton
3. Get settings from JSON (mode, interval, max_alerts)
4. Loop based on mode:
   - **Streaming**: Get next alert, push to panel, wait `interval_seconds`
   - **Static**: Load all alerts once, wait 5 minutes
   - **Replay**: Use `delay_seconds` from each alert for precise timing
5. Handle errors gracefully (wait 60s on error)

**Integration Points**:
- Gets panel from `cl.user_session.get("notification_panel")`
- Updates panel via `await panel.update(props={"notifications": [...]})`
- Logs alert push events for debugging

**Error Handling**:
- Checks if panel exists before updating
- Catches exceptions and logs with stack trace
- Continues running even if individual alerts fail

---

### 4. React Component

**File**: `public/elements/NotificationPanel.jsx`

**Purpose**: Render alerts in Chainlit right sidebar.

**Features**:
- Displays alerts with severity-based colors (red=critical, amber=warning, blue=info)
- Shows agent emoji, alert message, campaign/deal IDs
- Click handler sends `SYSTEM_TRIGGER:` message to Orchestrator
- Hover effects for better UX
- Empty state when no alerts

**Props**:
- `notifications`: Array of alert objects from Python

**Context Injection**:
When user clicks alert, sends:
```
SYSTEM_TRIGGER: Focus on {campaign_id|deal_id}. Context: {issue_type}. {details}
```

**Styling**:
- Dark theme (`#1f2937` background)
- Severity-based border colors
- Responsive hover effects
- Clean typography

**Reference**: See [`docs/PROACTIVE_NOTIFICATION_PANEL.md`](../docs/PROACTIVE_NOTIFICATION_PANEL.md#step-a-the-react-frontend) for complete component code.

---

### 5. Context Injection Handler

**File**: `src/interface/chainlit/handlers.py` (update `main()` function)

**Purpose**: Detect `SYSTEM_TRIGGER:` messages from notification clicks and route appropriately.

**Behavior**:
1. Check if `message.content.startswith("SYSTEM_TRIGGER:")`
2. Extract context from trigger message
3. Create human-readable message for chat display
4. Use extracted context as actual message content for graph
5. Graph routes to appropriate agent based on context

**Format**:
```
SYSTEM_TRIGGER: Focus on {entity_id}. Context: {issue_type}. {details}
```

**Example**:
```
SYSTEM_TRIGGER: Focus on Summer_2025. Context: under_pacing. Current spend: $12K of $20K budget. Expected: $16K by now.
```

**Reference**: See [`docs/PROACTIVE_NOTIFICATION_PANEL.md`](../docs/PROACTIVE_NOTIFICATION_PANEL.md#step-c-context-injection-handler) for implementation details.

---

### 6. Panel Initialization

**File**: `src/interface/chainlit/handlers.py` (update `start()` function)

**Changes**:
1. Create `NotificationPanel` CustomElement with empty notifications
2. Store panel reference in `cl.user_session.set("notification_panel", panel)`
3. Start background monitor task: `asyncio.create_task(background_monitor())`
4. Log initialization success

**Timing**:
- Panel created immediately on chat start
- Background monitor waits 5 seconds before first alert
- Alerts appear progressively based on mode

**Reference**: See [`docs/PROACTIVE_NOTIFICATION_PANEL.md`](../docs/PROACTIVE_NOTIFICATION_PANEL.md#update-start-function-in-handlerspy) for code.

---

## Testing Strategy

### Unit Tests

1. **NotificationLoader**:
   - Test JSON loading and validation
   - Test default JSON creation
   - Test streaming mode (get_next_alert)
   - Test static mode (get_all_alerts)
   - Test replay mode (delay_seconds)
   - Test reset() and reload()

2. **Background Monitor**:
   - Test panel update logic
   - Test error handling
   - Test mode switching
   - Test max_alerts limiting

### Integration Tests

1. **End-to-End Flow**:
   - Start chat → Panel appears
   - Wait for alerts → Alerts appear in panel
   - Click alert → Context injected → Agent responds
   - Verify routing to correct agent

2. **Mode Testing**:
   - Test streaming mode (alerts appear one by one)
   - Test static mode (all alerts at once)
   - Test replay mode (precise timing)

### Manual Testing

1. **JSON Modification**:
   - Edit `mock_alerts.json`
   - Reload page → Verify new alerts appear
   - Test different modes
   - Test loop behavior

2. **Error Scenarios**:
   - Delete JSON file → Verify default created
   - Invalid JSON → Verify error handling
   - Missing panel → Verify graceful degradation

---

## Future Enhancements

### Stage 2: Real System Integration

When ready for production, replace `NotificationLoader` with real API client:

```python
class APINotificationLoader:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
    
    async def get_next_alert(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/alerts",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.json()
```

**Migration Path**:
1. Keep `NotificationLoader` interface
2. Create `APINotificationLoader` with same interface
3. Swap loader in `background_monitor()` via config/env var
4. JSON loader remains for testing/demos

### Stage 3: Advanced Features

- **Alert Persistence**: Store alerts in database
- **Alert History**: Show resolved alerts
- **Filtering**: Filter by agent, severity, issue_type
- **Search**: Search alerts by campaign/deal ID
- **Real-time Updates**: WebSocket connection for live alerts

**Reference**: See [`docs/PROACTIVE_NOTIFICATION_PANEL.md`](../docs/PROACTIVE_NOTIFICATION_PANEL.md#evolution-through-stages) for Stage 2-4 evolution.

---

## Dependencies

- **Chainlit**: CustomElement API for React components
- **asyncio**: Background task execution
- **json**: JSON file loading
- **pathlib**: Path handling
- **logging**: Error logging and debugging

**No new dependencies required** - all standard library or existing project dependencies.

---

## Implementation Order

1. ✅ **Create JSON structure** (`config/notifications/mock_alerts.json`)
2. ✅ **Create NotificationLoader** (`src/interface/chainlit/notification_loader.py`)
3. ✅ **Create React component** (`public/elements/NotificationPanel.jsx`)
4. ✅ **Update handlers.py** (add `background_monitor()` and update `start()`)
5. ✅ **Add context injection** (update `main()` function)
6. ✅ **Test end-to-end flow**
7. ✅ **Update documentation** (mark checklist items complete)

---

## Success Criteria

- [ ] Panel appears in right sidebar on chat start
- [ ] Alerts appear automatically based on JSON configuration
- [ ] Clicking alert sends context-injected message to Orchestrator
- [ ] Orchestrator routes to appropriate agent
- [ ] Agent responds with full context
- [ ] Multiple modes work (streaming, static, replay)
- [ ] Error handling graceful (missing JSON, invalid structure)
- [ ] Logging provides visibility into alert push events

---

## Related Documentation

- **Feature Spec**: [`docs/PROACTIVE_NOTIFICATION_PANEL.md`](../docs/PROACTIVE_NOTIFICATION_PANEL.md) - Complete feature documentation
- **Architecture**: [`AI_HANDOFF.md`](../AI_HANDOFF.md) - Core patterns and principles
- **Chainlit Docs**: [`docs/CHAINLIT_SQLITE_PERSISTENCE.md`](../docs/CHAINLIT_SQLITE_PERSISTENCE.md) - UI persistence considerations

---

**Last Updated**: December 1, 2025  
**Status**: 📋 Ready for Implementation

