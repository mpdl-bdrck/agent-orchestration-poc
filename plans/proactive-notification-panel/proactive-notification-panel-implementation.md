# Proactive Notification Panel - Implementation Plan (DOM Bridge Architecture)

**Date**: December 2, 2025  
**Status**: 📋 **Implementation Plan** - Stage 1 using DOM Bridge Architecture  
**Approach**: **DOM Bridge** - Hidden Message Transport Layer + Custom Sidebar Overlay  
**Related Documentation**: [`docs/features/PROACTIVE_NOTIFICATION_PANEL.md`](../docs/features/PROACTIVE_NOTIFICATION_PANEL.md)

---

## Overview

This plan implements **Stage 1** of the Proactive Notification Panel feature using a **"DOM Bridge" architecture**. Since Chainlit doesn't natively support custom persistent sidebars, we use Chainlit's message system as a transport layer, hide those messages with CSS, and render a custom floating sidebar overlay with JavaScript.

**Key Design Decision**: Side panel is **non-negotiable** - we need a persistent, non-blocking notification HUD that exists independently of the chat flow.

### The DOM Bridge Architecture

1. **Python** sends messages with `author="__NOTIFY__"` containing JSON data
2. **CSS** hides these transport messages from the visual chat stream
3. **JavaScript** observes the DOM, detects hidden messages, parses JSON, and renders "Cards" in a custom HTML sidebar overlay
4. **Cards** are clickable and trigger agent actions by simulating user input

### Why This Approach

✅ **Side Panel**: Custom floating sidebar overlay (non-negotiable requirement)  
✅ **Non-Blocking**: Independent of chat flow, doesn't interfere with conversations  
✅ **Stable**: Uses Chainlit's native message system as transport (no React hacking)  
✅ **Visual**: Cards slide in from right edge with animations  
✅ **Interactive**: Click cards to trigger agent investigations  
✅ **Mobile-Friendly**: Responsive sidebar design

---

## Cross-References

- **Feature Documentation**: [`docs/features/PROACTIVE_NOTIFICATION_PANEL.md`](../docs/features/PROACTIVE_NOTIFICATION_PANEL.md) - Complete feature specification
- **Architecture Patterns**: [`AI_HANDOFF.md`](../AI_HANDOFF.md) - Core architectural patterns
- **Chainlit Integration**: [`docs/guides/CHAINLIT_SQLITE_PERSISTENCE.md`](../docs/guides/CHAINLIT_SQLITE_PERSISTENCE.md) - UI persistence considerations

---

## Implementation Checklist

### Phase 1: Frontend Assets (The Overlay)

- [ ] Create `public/notifications.css` with sidebar styling
- [ ] Hide `__NOTIFY__` transport messages with CSS
- [ ] Style notification cards with severity colors
- [ ] Add slide-in animations
- [ ] Create `public/notifications.js` with DOM observer
- [ ] Implement panel injection on page load
- [ ] Implement MutationObserver to detect hidden messages
- [ ] Implement card rendering function
- [ ] Implement click handler to trigger agent actions
- [ ] Update `.chainlit/config.toml` to load CSS/JS files

### Phase 2: Backend Logic (The Data Source)

- [ ] Create `background_monitor()` async function
- [ ] Integrate `NotificationLoader` to get alerts
- [ ] Format alerts as JSON payloads
- [ ] Send alerts as `cl.Message` with `author="__NOTIFY__"`
- [ ] Wrap JSON in code blocks for easy extraction
- [ ] Support multiple playback modes (streaming, static, replay)
- [ ] Add error handling and retry logic
- [ ] Start monitor in `@cl.on_chat_start`

### Phase 3: JSON-Driven Notification System

- [ ] Create `config/notifications/` directory
- [ ] Create `config/notifications/mock_alerts.json` with alert templates
- [ ] Create `src/interface/chainlit/notification_loader.py` module
- [ ] Implement `NotificationLoader` class with playback modes
- [ ] Add JSON validation and error handling
- [ ] Add auto-creation of default JSON if missing

### Phase 4: Context Injection

- [ ] Implement `triggerAgent()` JavaScript function
- [ ] Simulate user input in chat textarea
- [ ] Format context as `SYSTEM_TRIGGER: @{agent} {context}`
- [ ] Dispatch input events for React compatibility
- [ ] Simulate send button click
- [ ] Test end-to-end flow (alert → card → click → agent response)

### Phase 5: Integration & Testing

- [ ] Test sidebar appears on page load
- [ ] Test cards render from hidden messages
- [ ] Test cards are clickable
- [ ] Test agent actions triggered correctly
- [ ] Test multiple alerts simultaneously
- [ ] Test mobile responsiveness
- [ ] Test error handling (malformed JSON, missing elements)

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
├── public/
│   ├── notifications.css             # NEW: Sidebar styling + message hiding
│   └── notifications.js              # NEW: DOM observer + card rendering
└── .chainlit/
    └── config.toml                   # Updated to load CSS/JS
```

---

## Detailed Implementation

### 1. Frontend: CSS Styling

**File**: `public/notifications.css`

**Purpose**: Hide transport messages and style the floating sidebar overlay.

**Implementation**:

```css
/* 1. HIDE the Data Transport Messages */
/* Target messages where the author is __NOTIFY__ */
.message-row:has(.user-name) .user-name:contains("__NOTIFY__"),
.message-row:has([data-author="__NOTIFY__"]) {
    display: none !important;
}

/* Fallback: Hide rows containing JSON signature */
.message-row:has(.markdown-body:contains('{"agent":')) {
    display: none !important;
}

/* 2. The Floating Sidebar Container */
#custom-notification-panel {
    position: fixed;
    top: 80px; /* Below header */
    right: 20px;
    width: 320px;
    height: calc(100vh - 100px);
    background: transparent;
    z-index: 9999;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
    pointer-events: none; /* Clicks pass through container */
    padding-bottom: 20px;
}

/* 3. The Notification Cards */
.notification-card {
    background: white;
    border-left: 5px solid #0F52BA; /* Corporate Blue */
    padding: 16px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    pointer-events: auto; /* Re-enable clicking on cards */
    transition: all 0.2s ease;
    cursor: pointer;
    opacity: 0;
    animation: slideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    font-family: 'Inter', sans-serif;
    position: relative;
}

.notification-card:hover {
    transform: translateX(-5px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.2);
}

/* Severity Styling */
.notification-card.critical { border-left-color: #ef4444; }
.notification-card.warning { border-left-color: #f59e0b; }
.notification-card.info { border-left-color: #3b82f6; }

@keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}
```

**Reference**: See consultant's plan for complete CSS implementation.

---

### 2. Frontend: JavaScript DOM Observer

**File**: `public/notifications.js`

**Purpose**: Inject panel, watch for hidden messages, render cards, handle clicks.

**Implementation**:

```javascript
// 1. Inject the Panel Container
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('custom-notification-panel')) {
        const panel = document.createElement('div');
        panel.id = 'custom-notification-panel';
        document.body.appendChild(panel);
        console.log('🔔 Notification HUD Mounted');
    }
});

// 2. The "Action Trigger" - Simulates user input
window.triggerAgent = (agent, context) => {
    const prompt = `SYSTEM_TRIGGER: @${agent} ${context}`;
    
    // Find the Chat Input
    const textarea = document.querySelector('textarea#chat-input');
    const sendButton = document.querySelector('button[aria-label="Send"]');
    
    if (textarea && sendButton) {
        // React-friendly value setter
        const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, "value"
        ).set;
        nativeTextAreaValueSetter.call(textarea, prompt);
        
        // Dispatch input event so React knows it changed
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        
        // Simulate Click
        setTimeout(() => sendButton.click(), 100);
    } else {
        console.error("Could not find chat input to trigger agent.");
    }
};

// 3. The "DOM Bridge" (MutationObserver)
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
            if (node.nodeType === 1 && node.classList.contains('message-row')) {
                // Check for __NOTIFY__ signature
                if (node.innerText.includes('"__NOTIFY__"') || 
                    node.innerHTML.includes('__NOTIFY__')) {
                    
                    // Hide the message bubble
                    node.style.display = 'none';
                    node.setAttribute('data-hidden', 'true');
                    
                    // Extract and parse JSON
                    try {
                        const codeBlock = node.querySelector('code') || 
                                         node.querySelector('.markdown-body');
                        if (codeBlock) {
                            const jsonText = codeBlock.innerText;
                            const data = JSON.parse(jsonText);
                            renderCard(data);
                        }
                    } catch (e) {
                        console.error('Failed to parse notification JSON', e);
                    }
                }
            }
        });
    });
});

// Start observing after DOM is ready
setTimeout(() => {
    const chatContainer = document.querySelector('#chat-container') || document.body;
    observer.observe(chatContainer, { childList: true, subtree: true });
}, 2000);

// 4. Render Card Function
function renderCard(data) {
    const panel = document.getElementById('custom-notification-panel');
    if (!panel) return;

    const card = document.createElement('div');
    card.className = `notification-card ${data.severity || 'info'}`;
    card.innerHTML = `
        <div style="font-weight: 700; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 1.2em;">${data.icon}</span> 
            <span>${data.agent}</span>
        </div>
        <div style="font-size: 0.9em; color: #374151; line-height: 1.4;">${data.message}</div>
        <div style="font-size: 0.75em; color: #6b7280; margin-top: 8px; text-transform: uppercase; letter-spacing: 0.05em;">
            Click to Investigate →
        </div>
    `;
    
    card.onclick = (e) => {
        window.triggerAgent(data.agent, data.context);
        // Animate removal
        card.style.transform = 'translateX(120%)';
        setTimeout(() => card.remove(), 300);
    };
    
    panel.appendChild(card);
}
```

**Reference**: See consultant's plan for complete JavaScript implementation.

---

### 3. Backend: Background Monitor

**File**: `src/interface/chainlit/handlers.py` (add `background_monitor()` function)

**Purpose**: Send alerts as hidden transport messages with JSON payloads.

**Implementation**:

```python
import json
import asyncio
import os

async def background_monitor():
    """
    Simulates proactive alerts.
    Sends JSON payloads as 'Hidden Messages' that the JS Frontend intercepts.
    """
    # Wait for UI to load
    await asyncio.sleep(8)
    
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
                    alert = loader.get_next_alert()
                    if alert:
                        await _send_notification_message(alert)
                        await asyncio.sleep(interval_seconds)
                    else:
                        if loop:
                            loader.reset()
                            await asyncio.sleep(interval_seconds)
                        else:
                            break
                
                elif mode == "static":
                    alerts = loader.get_all_alerts()[:max_alerts]
                    for alert in alerts:
                        await _send_notification_message(alert)
                    await asyncio.sleep(300)
                
                elif mode == "replay":
                    alerts = loader.get_all_alerts()[:max_alerts]
                    for alert in alerts:
                        await _send_notification_message(alert)
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


async def _send_notification_message(alert: dict):
    """
    Send an alert as a hidden transport message with JSON payload.
    
    Args:
        alert: Alert dictionary from NotificationLoader
    """
    # Map alert fields to card data structure
    agent_emoji = {
        'guardian': '🛡️',
        'specialist': '🔧',
        'optimizer': '🎯',
        'pathfinder': '🧭'
    }.get(alert.get('agent'), '🤖')
    
    # Build context string for agent trigger
    entity_id = alert.get('campaign_id') or alert.get('deal_id') or 'issue'
    issue_type = alert.get('issue_type', 'issue').replace('_', ' ')
    details = alert.get('details', '')
    context = f"Investigate {issue_type} for {entity_id}. {details}"
    
    # Format as JSON payload
    payload = {
        "agent": alert.get('agent', 'System').capitalize(),
        "icon": agent_emoji,
        "severity": alert.get('severity', 'info'),
        "message": alert.get('message', 'Issue detected'),
        "context": context
    }
    
    # Send as hidden message with JSON in code block
    await cl.Message(
        content=f"```json\n{json.dumps(payload)}\n```",
        author="__NOTIFY__"
    ).send()
    
    logger.info(f"✅ Sent notification message: {alert.get('id')} ({alert.get('agent')} - {alert.get('severity')})")
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

### 4. JSON Alert Structure

**File**: `config/notifications/mock_alerts.json`

**Purpose**: Define alert templates that drive the notification system.

**Structure**:

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

### 5. Chainlit Configuration

**File**: `.chainlit/config.toml`

**Purpose**: Register CSS and JavaScript files for Chainlit to load.

**Update**:

```toml
[UI]
# Existing config...
custom_css = "/public/notifications.css"
custom_js = "/public/notifications.js"
```

**Note**: If `custom_css` or `custom_js` already exist, append to them or replace as needed.

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
   - Test JSON payload formatting
   - Test mode switching
   - Test error handling
   - Test max_alerts limiting

### Integration Tests

1. **End-to-End Flow**:
   - Start chat → Panel appears
   - Alert sent → Card renders in sidebar
   - Click card → Agent investigation triggered
   - Verify routing to correct agent

2. **DOM Observer**:
   - Test panel injection on page load
   - Test message detection and hiding
   - Test JSON parsing
   - Test card rendering
   - Test click handler

3. **Context Injection**:
   - Test `triggerAgent()` function
   - Test textarea population
   - Test React event dispatch
   - Test send button click simulation

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

1. **DOM Dependency**: Relies on Chainlit's DOM structure (may break on updates)
2. **Selector Fragility**: CSS/JS selectors may need adjustment if Chainlit changes
3. **React Compatibility**: Uses React-friendly event dispatch (may need updates)
4. **Mobile Testing**: Requires testing on actual mobile devices

---

## Success Criteria

- [ ] Sidebar panel appears on page load
- [ ] Alerts sent as hidden messages
- [ ] Cards render in sidebar from hidden messages
- [ ] Cards are clickable
- [ ] Clicking card triggers agent investigation
- [ ] Background monitor runs without errors
- [ ] JSON-driven system works for all modes
- [ ] Feature flag enables/disables correctly
- [ ] Mobile-friendly display
- [ ] Visual distinction from regular messages

---

**Last Updated**: December 2, 2025  
**Approach**: DOM Bridge Architecture (Hidden Message Transport + Custom Sidebar Overlay)
