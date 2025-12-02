# Proactive Notification Panel - JIRA-Style Tickets

**Epic**: Proactive Notification Panel Implementation  
**Status**: 📋 Planning  
**Approach**: **Native Chainlit Messages + Actions** (No CustomElement)  
**Total Tickets**: 20

---

## Ticket Status Summary

- 🔴 **To Do**: 20 tickets
- 🟡 **In Progress**: 0 tickets
- 🟢 **Done**: 0 tickets

---

## Phase Breakdown

### Phase 1: JSON-Driven Notification System (6 tickets)
- PNP-001: Create config/notifications/ directory
- PNP-002: Create mock_alerts.json with alert templates
- PNP-003: Create notification_loader.py module
- PNP-004: Implement NotificationLoader class with playback modes
- PNP-005: Add JSON validation and error handling
- PNP-006: Add auto-creation of default JSON if missing

### Phase 2: Background Monitor - Native Messages (5 tickets)
- PNP-007: Create background_monitor() async function
- PNP-008: Integrate NotificationLoader into background monitor
- PNP-009: Send alerts as cl.Message with System author
- PNP-010: Add visual distinction (emoji, formatting) to alert messages
- PNP-011: Support multiple playback modes and error handling

### Phase 3: Action Buttons (4 tickets)
- PNP-012: Create cl.Action buttons for alerts ("Fix Issue", "Dismiss")
- PNP-013: Attach actions to alert messages with payload
- PNP-014: Style action buttons appropriately
- PNP-015: Test action button display and interaction

### Phase 4: Action Callbacks (3 tickets)
- PNP-016: Create @cl.action_callback("fix_alert") handler
- PNP-017: Create @cl.action_callback("dismiss_alert") handler
- PNP-018: Implement context injection for "Fix Issue" action

### Phase 5: Integration & Styling (2 tickets)
- PNP-019: Start background monitor in @cl.on_chat_start
- PNP-020: Add CSS styling for alert messages (optional)

---

## Related Documentation

- **Implementation Plan**: [`../proactive-notification-panel-implementation.md`](../proactive-notification-panel-implementation.md)
- **Feature Documentation**: [`../../docs/features/PROACTIVE_NOTIFICATION_PANEL.md`](../../docs/features/PROACTIVE_NOTIFICATION_PANEL.md)
- **Vision Integration**: [`../../docs/vision/PROGRESSIVE_AUTONOMY.md`](../../docs/vision/PROGRESSIVE_AUTONOMY.md)

---

## ⚠️ Important Notes

**APPROACH CHANGE**: This implementation uses **Native Chainlit APIs** (`cl.Message` + `cl.Action`) instead of CustomElement. This approach is:
- ✅ More stable (no React context isolation issues)
- ✅ Mobile-friendly
- ✅ Production-ready
- ✅ Easier to maintain

**No CustomElement, no React components, no side panel** - alerts appear as messages in the chat feed.

---

## Ticket Status Legend

- 🔴 **To Do**: Not started
- 🟡 **In Progress**: Currently being worked on
- 🟢 **Done**: Completed and verified

---

**Last Updated**: December 2, 2025  
**Approach**: Native Chainlit Messages + Actions
