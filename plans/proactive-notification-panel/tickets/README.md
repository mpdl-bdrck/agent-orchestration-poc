# Proactive Notification Panel - JIRA-Style Tickets

**Epic**: Proactive Notification Panel Implementation  
**Status**: 📋 Planning  
**Total Tickets**: 25

---

## Ticket Status Summary

- 🔴 **To Do**: 25 tickets
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

### Phase 2: Background Monitor Integration (5 tickets)
- PNP-007: Update handlers.py with background_monitor() function
- PNP-008: Integrate NotificationLoader into background monitor
- PNP-009: Support multiple playback modes in background monitor
- PNP-010: Add error handling and retry logic
- PNP-011: Add logging for alert push events

### Phase 3: React Component (5 tickets)
- PNP-012: Create NotificationPanel.jsx React component
- PNP-013: Implement alert rendering with severity colors
- PNP-014: Add click handler for context injection
- PNP-015: Style alerts with hover effects
- PNP-016: Display agent emojis and timestamps

### Phase 4: Context Injection (4 tickets)
- PNP-017: Update main() function to detect SYSTEM_TRIGGER messages
- PNP-018: Extract context from notification click events
- PNP-019: Format context-injected messages for Orchestrator
- PNP-020: Test routing to appropriate agents

### Phase 5: Panel Initialization (5 tickets)
- PNP-021: Update start() function in handlers.py
- PNP-022: Create NotificationPanel CustomElement on chat start
- PNP-023: Store panel reference in cl.user_session
- PNP-024: Start background monitor task
- PNP-025: Test panel appears in right sidebar

---

## Related Documentation

- **Implementation Plan**: [`../proactive-notification-panel-implementation.md`](../proactive-notification-panel-implementation.md)
- **Feature Documentation**: [`../../docs/features/PROACTIVE_NOTIFICATION_PANEL.md`](../../docs/features/PROACTIVE_NOTIFICATION_PANEL.md)
- **Vision Integration**: [`../../docs/vision/PROGRESSIVE_AUTONOMY.md`](../../docs/vision/PROGRESSIVE_AUTONOMY.md)

---

## Ticket Status Legend

- 🔴 **To Do**: Not started
- 🟡 **In Progress**: Currently being worked on
- 🟢 **Done**: Completed and verified

---

**Last Updated**: December 2, 2025

