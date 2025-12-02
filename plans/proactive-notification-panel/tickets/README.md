# Proactive Notification Panel - JIRA-Style Tickets

**Epic**: Proactive Notification Panel Implementation  
**Status**: 📋 Planning  
**Approach**: **DOM Bridge Architecture** (Hidden Message Transport + Custom Sidebar Overlay)  
**Total Tickets**: 20

---

## Ticket Status Summary

- 🔴 **To Do**: 20 tickets
- 🟡 **In Progress**: 0 tickets
- 🟢 **Done**: 0 tickets

---

## Phase Breakdown

### Phase 1: Frontend Assets - The Overlay (6 tickets)
- PNP-001: Create public/notifications.css with sidebar styling
- PNP-002: Hide __NOTIFY__ transport messages with CSS
- PNP-003: Style notification cards with severity colors and animations
- PNP-004: Create public/notifications.js with DOM observer
- PNP-005: Implement panel injection and card rendering
- PNP-006: Implement click handler to trigger agent actions

### Phase 2: Backend Logic - The Data Source (5 tickets)
- PNP-007: Create background_monitor() async function
- PNP-008: Integrate NotificationLoader into background monitor
- PNP-009: Format alerts as JSON payloads
- PNP-010: Send alerts as cl.Message with author="__NOTIFY__"
- PNP-011: Support multiple playback modes and error handling

### Phase 3: JSON-Driven Notification System (6 tickets)
- PNP-012: Create config/notifications/ directory
- PNP-013: Create mock_alerts.json with alert templates
- PNP-014: Create notification_loader.py module
- PNP-015: Implement NotificationLoader class with playback modes
- PNP-016: Add JSON validation and error handling
- PNP-017: Add auto-creation of default JSON if missing

### Phase 4: Context Injection (2 tickets)
- PNP-018: Implement triggerAgent() JavaScript function
- PNP-019: Test end-to-end flow (alert → card → click → agent response)

### Phase 5: Integration & Configuration (1 ticket)
- PNP-020: Update .chainlit/config.toml and start background monitor

---

## Related Documentation

- **Implementation Plan**: [`../proactive-notification-panel-implementation.md`](../proactive-notification-panel-implementation.md)
- **Feature Documentation**: [`../../docs/features/PROACTIVE_NOTIFICATION_PANEL.md`](../../docs/features/PROACTIVE_NOTIFICATION_PANEL.md)
- **Vision Integration**: [`../../docs/vision/PROGRESSIVE_AUTONOMY.md`](../../docs/vision/PROGRESSIVE_AUTONOMY.md)

---

## ⚠️ Important Notes

**APPROACH**: **DOM Bridge Architecture** - Side panel is **non-negotiable**. This approach:
- ✅ Uses Chainlit's message system as transport layer (stable)
- ✅ Hides transport messages with CSS
- ✅ Renders custom sidebar overlay with JavaScript
- ✅ Independent of chat flow (non-blocking)
- ✅ Cards slide in from right edge with animations
- ✅ Clickable cards trigger agent investigations

**Architecture**: Python → Hidden Messages → CSS Hides → JS Observes → Cards Render → User Clicks → Agent Triggered

---

## Ticket Status Legend

- 🔴 **To Do**: Not started
- 🟡 **In Progress**: Currently being worked on
- 🟢 **Done**: Completed and verified

---

**Last Updated**: December 2, 2025  
**Approach**: DOM Bridge Architecture (Hidden Message Transport + Custom Sidebar Overlay)
