# Proactive Notification Panel - Implementation Plan (Revised)

**Date**: December 2, 2025  
**Status**: 📋 **Implementation Plan** - Stage 1 using Native Chainlit Messages + Actions  
**Approach**: **Native Chainlit APIs** (cl.Message + cl.Action) - No CustomElement hacking  
**Related Documentation**: [`docs/features/PROACTIVE_NOTIFICATION_PANEL.md`](../docs/features/PROACTIVE_NOTIFICATION_PANEL.md)

---

## Overview

This plan implements **Stage 1** of the Proactive Notification Panel feature using **Chainlit's native APIs** (`cl.Message` + `cl.Action`). Instead of fighting Chainlit's React context isolation with CustomElement, we leverage the framework's built-in capabilities.

**Key Design Decision**: Use **"In-Stream" Notification Strategy** - notifications appear as high-priority messages in the chat feed with action buttons, not in a separate side panel.

### Why This Approach

✅ **Stable**: Uses standard Chainlit APIs (`cl.Message`, `cl.Action`)  
✅ **No React Hacking**: Avoids Chainlit's strict React context isolation  
✅ **Mobile Friendly**: Native messages scale perfectly  
✅ **History Persistence**: Alerts become part of chat history (audit trail)  
✅ **Production Ready**: Easy to extend with real API integration

---

## Cross-References

- **Feature Documentation**: [`docs/features/PROACTIVE_NOTIFICATION_PANEL.md`](../docs/features/PROACTIVE_NOTIFICATION_PANEL.md) - Complete feature specification
- **Architecture Patterns**: [`AI_HANDOFF.md`](../AI_HANDOFF.md) - Core architectural patterns
- **Chainlit Integration**: [`docs/guides/CHAINLIT_SQLITE_PERSISTENCE.md`](../docs/guides/CHAINLIT_SQLITE_PERSISTENCE.md) - UI persistence considerations

---

## Implementation Checklist

### Phase 1: JSON-Driven Notification System

- [ ] Create `config/notifications/` directory
- [ ] Create `config/notifications/mock_alerts.json` with alert templates
- [ ] Create `src/interface/chainlit/notification_loader.py` module
- [ ] Implement `NotificationLoader` class with streaming/static/replay modes
- [ ] Add JSON validation and error handling
- [ ] Add auto-creation of default JSON if missing

### Phase 2: Background Monitor (Native Messages)

- [ ] Create `background_monitor()` async function in `handlers.py`
- [ ] Integrate `NotificationLoader` to get alerts
- [ ] Send alerts as `cl.Message` with `author="System"`
- [ ] Add visual distinction (🚨 emoji, formatted content)
- [ ] Support multiple playback modes (streaming, static, replay)
- [ ] Add error handling and retry logic
- [ ] Start monitor task in `@cl.on_chat_start`

### Phase 3: Action Buttons

- [ ] Create `cl.Action` buttons for each alert ("Fix Issue", "Dismiss")
- [ ] Attach actions to alert messages
- [ ] Include alert payload in action for context injection
- [ ] Style actions appropriately (icons, labels)

### Phase 4: Action Callbacks

- [ ] Create `@cl.action_callback("fix_alert")` handler
- [ ] Extract alert payload from action
- [ ] Send acknowledgment message
- [ ] Inject context into Orchestrator (trigger investigation)
- [ ] Create `@cl.action_callback("dismiss_alert")` handler
- [ ] Remove action buttons after handling

### Phase 5: Context Injection

- [ ] Update `main()` function to handle context-injected messages
- [ ] Format alert context as natural language prompt
- [ ] Route to appropriate agent via Orchestrator
- [ ] Test end-to-end flow (alert → action → investigation)

### Phase 6: Styling (Optional)

- [ ] Add CSS rules for System alert messages
- [ ] Style alert messages with colored borders
- [ ] Ensure mobile-friendly display
- [ ] Test visual distinction from regular messages

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
│           ├── handlers.py           # Updated with background_monitor() + action callbacks
│           └── notification_loader.py  # NEW: JSON loader module
└── public/
    └── custom.css                     # Updated with alert styling (optional)
```

**Note**: No React components, no CustomElement, no `public/elements/` directory needed.

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

**Reference**: See [`docs/features/PROACTIVE_NOTIFICATION_PANEL.md`](../docs/features/PROACTIVE_NOTIFICATION_PANEL.md#json-alert-structure) for complete structure.

---

### 2. Background Monitor

**File**: `src/interface/chainlit/handlers.py` (add `background_monitor()` function)

**Purpose**: Simulates proactive alerts by sending `cl.Message` objects with action buttons.

**Implementation**:

```python
async def background_monitor():
    """
    Background task that monitors for alerts and sends them as Chainlit messages.
    
    Supports three playback modes:
    - streaming: Alerts appear one at a time
    - static: All alerts appear at once
    - replay: Uses delay_seconds from each alert for precise timing
    """
    # Wait for UI initialization
    await asyncio.sleep(10)
    
    # Check if feature is enabled
    if not os.getenv("NOTIFICATION_PANEL_ENABLED", "false").lower() == "true":
        logger.debug("Notification panel disabled via feature flag")
        return
    
    if _notification_loader is None:
        logger.warning("NotificationLoader not available, skipping background monitor")
        return
    
    try:
        # Load NotificationLoader singleton
        loader = _notification_loader.get_instance()
        settings = loader.get_settings()
        mode = settings.get("mode", "streaming")
        loop = settings.get("loop", True)
        interval_seconds = settings.get("interval_seconds", 30)
        max_alerts = settings.get("max_alerts", 10)
        
        logger.info(f"🔔 Background monitor started (mode: {mode}, interval: {interval_seconds}s)")
        
        while True:
            try:
                if mode == "streaming":
                    # Get next alert
                    alert = loader.get_next_alert()
                    if alert:
                        await _send_alert_message(alert)
                        await asyncio.sleep(interval_seconds)
                    else:
                        if loop:
                            loader.reset()
                            await asyncio.sleep(interval_seconds)
                        else:
                            break
                
                elif mode == "static":
                    # Load all alerts at once
                    alerts = loader.get_all_alerts()[:max_alerts]
                    for alert in alerts:
                        await _send_alert_message(alert)
                    await asyncio.sleep(300)  # Wait 5 minutes
                
                elif mode == "replay":
                    # Use delay_seconds from each alert
                    alerts = loader.get_all_alerts()[:max_alerts]
                    for alert in alerts:
                        await _send_alert_message(alert)
                        delay = alert.get("delay_seconds", interval_seconds)
                        await asyncio.sleep(delay)
                    
                    if loop:
                        loader.reset()
                        await asyncio.sleep(interval_seconds)
                    else:
                        break
                
            except Exception as e:
                logger.error(f"Error in background monitor loop: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    except Exception as e:
        logger.error(f"Background monitor failed: {e}", exc_info=True)


async def _send_alert_message(alert: dict):
    """
    Send an alert as a Chainlit message with action buttons.
    
    Args:
        alert: Alert dictionary from NotificationLoader
    """
    # Format message content
    agent_emoji = {
        'guardian': '🛡️',
        'specialist': '🔧',
        'optimizer': '🎯',
        'pathfinder': '🧭'
    }.get(alert.get('agent'), '🤖')
    
    severity_emoji = {
        'critical': '🚨',
        'warning': '⚠️',
        'info': 'ℹ️'
    }.get(alert.get('severity'), '📢')
    
    agent_name = alert.get('agent', 'System').capitalize()
    issue_type = alert.get('issue_type', 'issue').replace('_', ' ').title()
    
    # Build message content
    content = f"{severity_emoji} **ALERT: {alert.get('message', 'Issue detected')}**\n\n"
    content += f"**Agent**: {agent_emoji} {agent_name}\n"
    content += f"**Type**: {issue_type}\n"
    
    if alert.get('campaign_id'):
        content += f"**Campaign**: `{alert['campaign_id']}`\n"
    if alert.get('deal_id'):
        content += f"**Deal**: `{alert['deal_id']}`\n"
    
    if alert.get('details'):
        content += f"\n{alert['details']}"
    
    # Create action buttons
    actions = [
        cl.Action(
            name="fix_alert",
            value="fix",
            label="🔧 Fix Issue",
            payload=alert  # Include full alert for context injection
        ),
        cl.Action(
            name="dismiss_alert",
            value="dismiss",
            label="❌ Dismiss",
            payload={"alert_id": alert.get('id')}
        )
    ]
    
    # Send message
    await cl.Message(
        content=content,
        author="System",
        actions=actions
    ).send()
    
    logger.info(f"✅ Sent alert message: {alert.get('id')} ({alert.get('agent')} - {alert.get('severity')})")
```

**Integration**: Start monitor in `@cl.on_chat_start`:

```python
@cl.on_chat_start
async def start():
    # ... existing setup ...
    
    # Start background monitor (if enabled)
    if os.getenv("NOTIFICATION_PANEL_ENABLED", "false").lower() == "true":
        asyncio.create_task(background_monitor())
        logger.info("✅ Background monitor task started")
```

---

### 3. Action Callbacks

**File**: `src/interface/chainlit/handlers.py` (add action callback handlers)

**Purpose**: Handle user interactions with alert action buttons.

**Implementation**:

```python
@cl.action_callback("fix_alert")
async def on_fix_alert(action: cl.Action):
    """
    Handle "Fix Issue" button click - injects context and triggers investigation.
    """
    payload = action.payload  # Contains full alert dictionary
    
    # 1. Acknowledge action
    await cl.Message(
        content=f"✅ Investigating {payload.get('campaign_id') or payload.get('deal_id') or 'issue'}...",
        author="System"
    ).send()
    
    # 2. Build context-injected prompt
    entity_id = payload.get('campaign_id') or payload.get('deal_id') or 'issue'
    issue_type = payload.get('issue_type', 'issue').replace('_', ' ')
    details = payload.get('details', '')
    
    user_prompt = f"Investigate {issue_type} for {entity_id}. {details}"
    
    # 3. Trigger investigation by calling main() with context-injected message
    # This simulates the user asking about the alert
    await main(cl.Message(content=user_prompt, author="User"))
    
    # 4. Remove action buttons (optional - keeps UI clean)
    await action.remove()
    
    logger.info(f"✅ Alert investigation triggered: {payload.get('id')}")


@cl.action_callback("dismiss_alert")
async def on_dismiss_alert(action: cl.Action):
    """
    Handle "Dismiss" button click - removes alert from view.
    """
    alert_id = action.payload.get('alert_id', 'unknown')
    
    await cl.Message(
        content=f"❌ Alert dismissed",
        author="System"
    ).send()
    
    await action.remove()
    
    logger.info(f"✅ Alert dismissed: {alert_id}")
```

---

### 4. Context Injection Handler

**File**: `src/interface/chainlit/handlers.py` (update `main()` function)

**Purpose**: Ensure context-injected messages from alerts are properly handled.

**Implementation**: The `main()` function already handles `cl.Message` objects, so alert-triggered investigations will flow through the normal Orchestrator routing. No changes needed unless you want to add special handling for alert-triggered messages.

**Optional Enhancement**: Add a flag to distinguish alert-triggered messages:

```python
@cl.on_message
async def main(message: cl.Message):
    # Check if this is an alert-triggered investigation
    is_alert_triggered = message.content.startswith("Investigate")
    
    # ... existing message handling ...
    # Orchestrator will route appropriately based on content
```

---

### 5. Styling (Optional)

**File**: `public/custom.css`

**Purpose**: Make alert messages visually distinct from regular chat messages.

**Implementation**:

```css
/* Style System Alert Messages */
.message-system {
    border-left: 4px solid #ef4444 !important; /* Red border for alerts */
    background-color: #fef2f2 !important; /* Light red background */
    padding: 12px !important;
    border-radius: 8px !important;
    margin: 8px 0 !important;
}

/* Style action buttons for alerts */
.message-system .action-button {
    margin-top: 8px;
}
```

**Note**: CSS selectors may need adjustment based on Chainlit's actual DOM structure. Inspect the rendered HTML to find exact selectors.

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
   - Test alert message creation
   - Test action button attachment
   - Test mode switching
   - Test error handling
   - Test max_alerts limiting

### Integration Tests

1. **End-to-End Flow**:
   - Start chat → Alerts appear as messages
   - Click "Fix Issue" → Investigation triggered
   - Click "Dismiss" → Alert removed
   - Verify routing to correct agent

2. **Mode Testing**:
   - Test streaming mode (alerts appear one by one)
   - Test static mode (all alerts at once)
   - Test replay mode (precise timing)

---

## Feature Flag

**Environment Variable**: `NOTIFICATION_PANEL_ENABLED`

- **Default**: `false` (disabled)
- **Enable**: Set to `true` in `.env` or environment
- **Usage**: Controls background monitor startup

---

## Migration Path to Production

When ready to integrate with real system:

1. **Replace NotificationLoader**:
   - Keep same interface (`get_next_alert()`, `get_all_alerts()`)
   - Swap JSON file loading for HTTP API calls
   - Add authentication/authorization

2. **Real-Time Updates**:
   - Replace polling loop with WebSocket listener
   - Or use Chainlit's built-in event system

3. **Alert Persistence**:
   - Store alerts in database
   - Track alert state (new, acknowledged, dismissed, resolved)

---

## Known Limitations

1. **No Side Panel**: Alerts appear in chat feed (by design - more stable)
2. **Message History**: Alerts become part of chat history (feature, not bug)
3. **CSS Styling**: May need DOM inspection to find exact selectors
4. **Action Persistence**: Action buttons removed after click (keeps UI clean)

---

## Success Criteria

- [ ] Alerts appear as messages in chat feed
- [ ] Action buttons ("Fix Issue", "Dismiss") work correctly
- [ ] Clicking "Fix Issue" triggers agent investigation
- [ ] Clicking "Dismiss" removes alert
- [ ] Background monitor runs without errors
- [ ] JSON-driven system works for all modes
- [ ] Feature flag enables/disables correctly
- [ ] Mobile-friendly display
- [ ] Visual distinction from regular messages

---

**Last Updated**: December 2, 2025  
**Approach**: Native Chainlit Messages + Actions (No CustomElement)
