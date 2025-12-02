# Proactive Notification Panel - The Conversational Command Center

**Date**: December 1, 2025  
**Status**: 🎯 **North Star Feature** - Transforming from reactive chatbot to proactive command center  
**Current Stage**: Stage 1 (Notification Only)  
**Vision**: Autonomous → Human-in-the-Loop workflow

> **Vision Integration**: This document describes the UI implementation of the [Progressive Autonomy Model](../vision/PROGRESSIVE_AUTONOMY.md). The notification panel is how users interact with each stage of progressive autonomy evolution.

---

## Overview

The **Proactive Notification Panel** is the "killer feature" that transforms the Bedrock Agent Orchestration POC from a **reactive chatbot** into a **proactive conversational command center**.

### The Transformation

**Before (Reactive)**:
- User asks question → Agent responds
- User must know what to ask
- No visibility into system health
- Manual monitoring required

**After (Proactive)**:
- System detects issues → Panel updates automatically
- User sees alerts without asking
- Full system visibility in real-time
- One-click context injection for agent investigation

---

## The Progressive Autonomy Model

This feature evolves through four stages, aligned with our [Progressive Autonomy Model](vision/PROGRESSIVE_AUTONOMY.md):

### Stage 1: Diagnosis & Alert (Current)
**Agent Capability**: Detect issues, generate alerts  
**Human Involvement**: 100% (human investigates and fixes)  
**Panel Behavior**: Shows alerts with context, user clicks to investigate

### Stage 2: Recommendation & Logging
**Agent Capability**: Detect + recommend specific fixes  
**Human Involvement**: 100% execution (human follows recommendation)  
**Panel Behavior**: Shows alerts with recommended actions, user clicks to approve/reject

### Stage 3: Approval-Based Action
**Agent Capability**: Detect + recommend + request approval  
**Human Involvement**: Approve/reject (agent executes)  
**Panel Behavior**: Shows approval requests with success rate data, user clicks to approve

### Stage 4: Autonomous Action
**Agent Capability**: Detect + execute autonomously  
**Human Involvement**: Oversight only  
**Panel Behavior**: Shows executed actions with outcomes, user clicks for details

---

## Architecture: The "Push" Loop

### Core Components

1. **React Component** (`NotificationPanel.jsx`): Renders alerts in right sidebar
2. **Python Background Task**: Async loop checking for alerts (simulating autonomous jobs)
3. **Context Injection**: Clicking notification sends prompt-injected message to Orchestrator
4. **Mock Data Generator**: Simulates proactive alerts (Stage 1 implementation)

### Data Flow

```
Background Monitor (Python)
    ↓
Detects Issue / Generates Alert
    ↓
Updates Notification Panel (React)
    ↓
User Clicks Alert
    ↓
Context-Injected Message Sent to Orchestrator
    ↓
Orchestrator Routes to Appropriate Agent
    ↓
Agent Responds with Full Context
```

---

## Stage 1 Implementation: Notification Panel with Mock Data

### Step A: The React Frontend

**File**: `public/elements/NotificationPanel.jsx`

```jsx
import { useRecoilValue } from 'recoil';
import { clientState } from '@chainlit/react-client';

export default function NotificationPanel({ notifications }) {
  // 'notifications' prop will be passed from Python
  
  const handleClick = (alert) => {
    // MAGIC: Send a context-injected message to the Orchestrator
    // This gives the agent full context about the issue
    const contextMessage = `SYSTEM_TRIGGER: Focus on ${alert.campaign_id || alert.deal_id || 'issue'}. Context: ${alert.issue_type}. ${alert.details || ''}`;
    
    // Use Chainlit's global API to send this message
    if (window.chainlit && window.chainlit.sendMessage) {
      window.chainlit.sendMessage({
        content: contextMessage,
        author: "System"
      });
    } else {
      // Fallback: trigger Chainlit's message handler
      const event = new CustomEvent('chainlit-send-message', {
        detail: { content: contextMessage }
      });
      window.dispatchEvent(event);
    }
  };
  
  const getSeverityColor = (severity) => {
    switch(severity) {
      case 'critical': return '#ef4444'; // red
      case 'warning': return '#f59e0b'; // amber
      case 'info': return '#3b82f6'; // blue
      default: return '#6b7280'; // gray
    }
  };
  
  const getAgentEmoji = (agent) => {
    const emojis = {
      'guardian': '🛡️',
      'specialist': '🔧',
      'optimizer': '🎯',
      'pathfinder': '🧭'
    };
    return emojis[agent] || '🤖';
  };
  
  return (
    <div style={{ padding: '16px' }}>
      <h3 style={{ marginTop: 0, marginBottom: '16px', fontSize: '18px', fontWeight: '600' }}>
        Active Alerts
      </h3>
      
      {notifications.length === 0 ? (
        <div style={{ 
          padding: '24px', 
          textAlign: 'center', 
          color: '#6b7280',
          fontSize: '14px'
        }}>
          No active alerts
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {notifications.map((alert, index) => (
            <div
              key={alert.id || index}
              onClick={() => handleClick(alert)}
              style={{
                padding: '12px',
                border: `2px solid ${getSeverityColor(alert.severity)}`,
                borderRadius: '8px',
                cursor: 'pointer',
                backgroundColor: '#1f2937',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#374151';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#1f2937';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span style={{ fontSize: '20px' }}>
                  {getAgentEmoji(alert.agent)}
                </span>
                <span style={{ 
                  fontWeight: '600', 
                  fontSize: '14px',
                  color: getSeverityColor(alert.severity)
                }}>
                  {alert.agent ? alert.agent.charAt(0).toUpperCase() + alert.agent.slice(1) : 'System'} Alert
                </span>
                <span style={{ 
                  marginLeft: 'auto',
                  fontSize: '12px',
                  color: '#9ca3af'
                }}>
                  {alert.timestamp || 'Just now'}
                </span>
              </div>
              
              <div style={{ fontSize: '13px', color: '#d1d5db', marginBottom: '4px' }}>
                {alert.message}
              </div>
              
              {alert.campaign_id && (
                <div style={{ fontSize: '12px', color: '#9ca3af' }}>
                  Campaign: {alert.campaign_id}
                </div>
              )}
              
              {alert.deal_id && (
                <div style={{ fontSize: '12px', color: '#9ca3af' }}>
                  Deal: {alert.deal_id}
                </div>
              )}
              
              <div style={{ 
                marginTop: '8px',
                fontSize: '11px',
                color: '#6b7280',
                fontStyle: 'italic'
              }}>
                Click to investigate →
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

### Step B: The Python Backend

**File**: `src/interface/chainlit/handlers.py` (add to existing file)

```python
import asyncio
import random
from datetime import datetime, timedelta

# Mock alert generator for Stage 1
def generate_mock_alert():
    """Generate a mock alert simulating Guardian/Agent detection."""
    alert_types = [
        {
            "agent": "guardian",
            "issue_type": "under_pacing",
            "severity": "warning",
            "message": "Campaign 'Summer_2025' is under-pacing by 40%.",
            "campaign_id": "Summer_2025",
            "details": "Current spend: $12K of $20K budget. Expected: $16K by now."
        },
        {
            "agent": "optimizer",
            "issue_type": "bid_too_low",
            "severity": "warning",
            "message": "Deal 12345 has low win rate (2.1%).",
            "deal_id": "12345",
            "details": "Win rate below 3% threshold. Consider increasing bid cap."
        },
        {
            "agent": "specialist",
            "issue_type": "geo_conflict",
            "severity": "critical",
            "message": "Deal 67890: Geo targeting conflict detected.",
            "deal_id": "67890",
            "details": "Both buyer and seller have geo-targeting. CTV deal with 68% delivery drop."
        },
        {
            "agent": "pathfinder",
            "issue_type": "qps_limit",
            "severity": "info",
            "message": "SSP 'PubMatic' approaching QPS limit.",
            "details": "Current: 8.2K QPS of 10K limit. Consider traffic allocation."
        }
    ]
    
    alert = random.choice(alert_types)
    alert["id"] = f"alert_{datetime.now().timestamp()}"
    alert["timestamp"] = datetime.now().strftime("%H:%M:%S")
    return alert


async def background_monitor():
    """Background task that simulates proactive alert detection."""
    await asyncio.sleep(5)  # Wait for UI to initialize
    
    while True:
        try:
            # Simulate alert detection (every 30 seconds in demo, every 5 minutes in production)
            await asyncio.sleep(30)
            
            # Generate mock alert
            new_alert = generate_mock_alert()
            
            # Get the notification panel from session
            panel = cl.user_session.get("notification_panel")
            if not panel:
                continue
            
            # Get current notifications
            current_notifications = panel.props.get("notifications", [])
            
            # Add new alert (limit to 10 most recent)
            current_notifications.insert(0, new_alert)
            current_notifications = current_notifications[:10]
            
            # Update the panel
            await panel.update(props={"notifications": current_notifications})
            
            logger.info(f"✅ Proactive alert pushed: {new_alert['message']}")
            
        except Exception as e:
            logger.error(f"Error in background monitor: {e}", exc_info=True)
            await asyncio.sleep(60)  # Wait longer on error
```

**Update `start()` function in `handlers.py`**:

```python
@cl.on_chat_start
async def start():
    """Initialize session when user starts chat."""
    try:
        context_id = cl.user_session.get("context_id", "bedrock_kb")
        
        graph = create_chainlit_graph(context_id=context_id)
        cl.user_session.set("graph", graph)
        cl.user_session.set("history", [])
        cl.user_session.set("context_id", context_id)
        cl.user_session.set("active_messages", {})
        
        # Create the Notification Panel (Stage 1: Empty initially)
        panel = cl.CustomElement(
            name="NotificationPanel",
            props={"notifications": []},
            display="side"
        )
        await panel.send()
        cl.user_session.set("notification_panel", panel)
        
        # Start the background monitor (proactive alert detection)
        # Run in background without blocking
        asyncio.create_task(background_monitor())
        
        logger.debug("✅ Notification Panel initialized")
        logger.debug("✅ Avatar system: Chainlit will auto-load avatars from /public/avatars/")
    except Exception as e:
        logger.error(f"Failed to initialize Chainlit session: {e}", exc_info=True)
        await cl.Message(
            content=f"❌ **Error initializing orchestrator:** {str(e)}\n\n"
                   "Please check your configuration and try again.",
            author="System"
        ).send()
```

### Step C: Context Injection Handler

**Update `main()` function in `handlers.py`** to handle SYSTEM_TRIGGER messages:

```python
@cl.on_message
async def main(message: cl.Message):
    """Handle user message and stream graph events."""
    try:
        # Check if this is a system-triggered message (from notification panel)
        is_system_trigger = message.content.startswith("SYSTEM_TRIGGER:")
        
        if is_system_trigger:
            # Extract context from SYSTEM_TRIGGER message
            # Format: "SYSTEM_TRIGGER: Focus on {id}. Context: {issue_type}. {details}"
            trigger_content = message.content.replace("SYSTEM_TRIGGER: ", "")
            
            # Create a human-readable message for the chat
            user_message = cl.Message(
                content=f"🔔 **Proactive Alert Investigation**\n\n{trigger_content}",
                author="User"
            )
            await user_message.send()
            
            # Use trigger_content as the actual message content
            message_content = trigger_content
        else:
            message_content = message.content
        
        graph = cl.user_session.get("graph")
        if not graph:
            await cl.Message(
                content="❌ Graph not initialized. Please refresh the page.",
                author="System"
            ).send()
            return
        
        history = cl.user_session.get("history", [])
        context_id = cl.user_session.get("context_id", "bedrock_kb")
        active_messages = cl.user_session.get("active_messages", {})
        
        active_messages.clear()
        cl.user_session.set("active_messages", active_messages)
        
        initial_state = {
            "messages": [HumanMessage(content=message_content)],
            "next": "",
            "current_task_instruction": "",
            "context_id": context_id,
            "agent_responses": [],
            "user_question": message_content
        }
        
        # Rest of the streaming logic...
        # (existing code continues)
```

---

## The Full UX Flow (Stage 1)

### User Experience

1. **User logs in** → Right Panel shows "Active Alerts" (empty)

2. **5 seconds later (Proactive)** → Red notification appears:
   ```
   🛡️ Guardian Alert
   Campaign 'Summer_2025' is under-pacing by 40%.
   Campaign: Summer_2025
   Click to investigate →
   ```

3. **User clicks notification** → Chat automatically sends:
   ```
   🔔 Proactive Alert Investigation
   
   Focus on Summer_2025. Context: under_pacing. Current spend: $12K of $20K budget. Expected: $16K by now.
   ```

4. **Orchestrator receives message** → Routes to Optimizer Agent (based on "under_pacing" context)

5. **Optimizer Agent responds** → With full context:
   ```
   I see that Summer_2025 is under-pacing by 40%. 
   Current spend is $12K of $20K budget, but expected spend is $16K by now.
   
   I recommend:
   - Increasing bid cap by 10%
   - Reviewing targeting parameters
   - Checking inventory availability
   ```

6. **User can ask follow-up questions** → Full conversation context maintained

---

## Evolution Through Stages

### Stage 2: Recommendation & Logging

**Panel Enhancement**: Shows recommended actions

```jsx
// Additional props in notification
{
  "recommended_action": "increase_bid_cap",
  "expected_outcome": "60-80% recovery",
  "historical_success": "8/8 similar fixes successful",
  "action_buttons": ["✅ Log Fix", "❌ False Alarm"]
}
```

**User clicks "✅ Log Fix"** → System logs action for learning

### Stage 3: Approval-Based Action

**Panel Enhancement**: Shows approval requests with success rates

```jsx
{
  "type": "approval_request",
  "recommended_action": "remove_supply_side_geo",
  "success_rate": "100% (8/8)",
  "expected_recovery": "60-80%",
  "action_buttons": ["✅ Approve", "❌ Reject"]
}
```

**User clicks "✅ Approve"** → Agent executes action autonomously

### Stage 4: Autonomous Action

**Panel Enhancement**: Shows executed actions (FYI only)

```jsx
{
  "type": "autonomous_action",
  "action_taken": "remove_supply_side_geo",
  "confidence": "95% (12/12 successful)",
  "status": "executed",
  "verify_in": "24 hours"
}
```

**User clicks** → See action details and outcome verification

---

## Prompt Injection Mechanism

### Context Injection Format

When a user clicks a notification, the system generates a **context-injected message** that gives the agent full context:

```
SYSTEM_TRIGGER: Focus on {entity_id}. Context: {issue_type}. {details}
```

### Example Injections

**Under-pacing Alert**:
```
SYSTEM_TRIGGER: Focus on Summer_2025. Context: under_pacing. Current spend: $12K of $20K budget. Expected: $16K by now. Days remaining: 5.
```

**Geo Conflict Alert**:
```
SYSTEM_TRIGGER: Focus on 67890. Context: geo_conflict. Both buyer and seller have geo-targeting. CTV deal with 68% delivery drop. Likely cause: Double geo-targeting.
```

**Bid Too Low Alert**:
```
SYSTEM_TRIGGER: Focus on 12345. Context: bid_too_low. Win rate: 2.1% (below 3% threshold). Consider increasing bid cap by 15-20%.
```

### Agent Context Understanding

The Orchestrator receives this message and:
1. **Extracts entity**: `Summer_2025` (campaign) or `67890` (deal)
2. **Identifies issue type**: `under_pacing`, `geo_conflict`, `bid_too_low`
3. **Routes to appropriate agent**: Optimizer for pacing, Specialist for conflicts
4. **Injects context**: Agent receives full details without needing to query

---

## Mock Data Strategy (Stage 1)

### Current Implementation

- **Mock alert generator**: `generate_mock_alert()` function
- **Random alert types**: 4 different alert patterns
- **Timing**: Alerts appear every 30 seconds (demo) or 5 minutes (production)

### Future: Real System Integration

**Stage 2+**: Replace mock generator with real system loops:

```python
# Future: Real Guardian monitoring
async def background_monitor():
    while True:
        # Real Guardian Agent checks
        issues = await guardian_agent.detect_issues()
        
        for issue in issues:
            alert = {
                "agent": "guardian",
                "issue_type": issue.type,
                "severity": issue.severity,
                "message": issue.message,
                "campaign_id": issue.campaign_id,
                "deal_id": issue.deal_id,
                "details": issue.details,
                "recommended_action": issue.recommended_action,  # Stage 2+
                "success_rate": issue.success_rate,  # Stage 3+
            }
            
            # Push to panel
            await update_notification_panel(alert)
        
        await asyncio.sleep(300)  # Check every 5 minutes
```

---

## Implementation Checklist

### Phase 1: Basic Panel (Stage 1)

- [x] Create `NotificationPanel.jsx` React component
- [ ] Mount panel in `start()` function
- [ ] Create `background_monitor()` async task
- [ ] Implement mock alert generator
- [ ] Add context injection handler
- [ ] Test click-to-investigate flow

### Phase 2: Enhanced Panel (Stage 2)

- [ ] Add action logging buttons
- [ ] Integrate with System of Record
- [ ] Add outcome verification display
- [ ] Show historical success rates

### Phase 3: Approval Workflow (Stage 3)

- [ ] Add approval request UI
- [ ] Implement approval handler
- [ ] Connect to agent execution
- [ ] Show approval history

### Phase 4: Autonomous Display (Stage 4)

- [ ] Show executed actions
- [ ] Display outcome verification
- [ ] Add rollback capability
- [ ] Show autonomous metrics

---

## Technical Notes

### Chainlit Custom Elements

- **Location**: `public/elements/NotificationPanel.jsx`
- **Mounting**: `cl.CustomElement(name="NotificationPanel", props={...}, display="side")`
- **Updates**: `await panel.update(props={...})`
- **Persistence**: Stored in `cl.user_session`

### Background Tasks

- **Pattern**: `asyncio.create_task(background_monitor())`
- **Error Handling**: Wrap in try/except with exponential backoff
- **Resource Management**: Use `asyncio.sleep()` for timing

### Context Injection

- **Format**: `SYSTEM_TRIGGER: Focus on {id}. Context: {type}. {details}`
- **Handler**: Detect in `main()` function, extract context, route appropriately
- **Agent Routing**: Use context to determine which agent handles the issue

---

## Benefits

### For Users

- ✅ **Proactive Awareness**: See issues before asking
- ✅ **One-Click Investigation**: Click alert → Full context → Agent responds
- ✅ **System Visibility**: Real-time view of portfolio health
- ✅ **Reduced Cognitive Load**: Alerts come with context, no need to explain

### For Agents

- ✅ **Full Context**: Receive complete issue details via prompt injection
- ✅ **Efficient Routing**: Orchestrator routes based on issue type
- ✅ **No Redundancy**: Don't need to query for information already provided
- ✅ **Progressive Autonomy**: Foundation for Stage 2-4 evolution

### For System

- ✅ **Autonomous Monitoring**: Background loops detect issues automatically
- ✅ **Learning Foundation**: Stage 1 sets up Stage 2-4 learning infrastructure
- ✅ **Scalability**: Can handle hundreds of alerts without user intervention
- ✅ **Trust Building**: Users see value before granting autonomy

---

## Related Documentation

- [Progressive Autonomy Model](../vision/PROGRESSIVE_AUTONOMY.md) - Four-stage evolution
- [Tool Instructions Architecture](../guides/TOOL_INSTRUCTIONS_ARCHITECTURE.md) - Agent context injection
- [Chainlit SQLite Persistence](../guides/CHAINLIT_SQLITE_PERSISTENCE.md) - UI persistence

---

**Last Updated**: December 1, 2025  
**Status**: 🎯 North Star Feature - Stage 1 Implementation

