/**
 * Notification Panel - DOM Bridge Architecture
 * Observes DOM for hidden messages, parses JSON, renders cards in sidebar overlay
 * ALSO: Loads notifications directly from JSON on page load for immediate display
 */

// 0. Load notifications directly from JSON file (for starter screen display)
async function loadNotificationsFromJSON() {
    try {
        // Try public/ path first (Chainlit serves from public/)
        const response = await fetch('/public/mock_alerts.json');
        if (!response.ok) {
            console.warn('Could not load notifications JSON from /public/, will rely on DOM bridge');
            return;
        }
        const data = await response.json();
        const alerts = data.alerts || [];
        
        console.log(`📋 Loaded ${alerts.length} notification(s) from JSON - rendering on starter screen`);
        
        // Render each alert as a card immediately
        alerts.forEach(alert => {
            const agentLower = (alert.agent || 'System').toLowerCase();
            const agentCapitalized = agentLower.charAt(0).toUpperCase() + agentLower.slice(1);
            const cardData = {
                id: alert.id || `alert_${Date.now()}_${Math.random()}`,
                agent: agentCapitalized, // Capitalized: Guardian, Optimizer, etc.
                icon: {
                    'guardian': '🛡️',
                    'specialist': '🔧',
                    'optimizer': '🎯',
                    'pathfinder': '🧭'
                }[agentLower] || '🔔',
                severity: alert.severity || 'info',
                message: alert.message || 'Notification',
                context: alert.details || alert.message || ''
            };
            renderCard(cardData);
        });
    } catch (e) {
        console.warn('Failed to load notifications from JSON:', e);
        // Fall back to DOM bridge method
    }
}

// Load notifications immediately on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(loadNotificationsFromJSON, 1000);
    });
} else {
    setTimeout(loadNotificationsFromJSON, 1000);
}

// 1. Inject the Panel Container - MULTIPLE ATTEMPTS
function injectPanel() {
    if (!document.getElementById('custom-notification-panel')) {
        const panel = document.createElement('div');
        panel.id = 'custom-notification-panel';
        document.body.appendChild(panel);
        console.log('🔔 Notification HUD Mounted');
        return true;
    }
    return false;
}

// Try multiple times to ensure panel is created
document.addEventListener('DOMContentLoaded', injectPanel);
setTimeout(injectPanel, 100);
setTimeout(injectPanel, 500);
setTimeout(injectPanel, 1000);
setTimeout(injectPanel, 2000);

// Also try immediately if DOM is already loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectPanel);
} else {
    injectPanel();
}

// 2. The "Action Trigger" - Simulates user input
window.triggerAgent = (agent, context) => {
    const prompt = `SYSTEM_TRIGGER: @${agent} ${context}`;
    
    // Find the Chat Input
    const textarea = document.querySelector('textarea#chat-input') || 
                     document.querySelector('textarea[placeholder*="message"]') ||
                     document.querySelector('textarea');
    const sendButton = document.querySelector('button[aria-label="Send"]') ||
                       document.querySelector('button[type="submit"]') ||
                       document.querySelector('button:has(svg[aria-label="Send"])');
    
    if (textarea && sendButton) {
        // React-friendly value setter
        const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, "value"
        ).set;
        nativeTextAreaValueSetter.call(textarea, prompt);
        
        // Dispatch input event so React knows it changed
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        textarea.dispatchEvent(new Event('change', { bubbles: true }));
        
        // Simulate Click
        setTimeout(() => {
            sendButton.click();
            console.log(`✅ Triggered agent investigation: ${agent}`);
        }, 100);
    } else {
        console.error("Could not find chat input to trigger agent.", {
            textarea: !!textarea,
            sendButton: !!sendButton
        });
    }
};

// Extract processing logic into separate function
// CRITICAL: Only hide THIS message, don't touch parent/siblings (breaks Chainlit)
function processNotificationMessage(messageRow) {
    if (messageRow.hasAttribute('data-notification-processed')) return;
    
    messageRow.setAttribute('data-notification-processed', 'true');
    
    // Hide immediately - AGGRESSIVE
    messageRow.setAttribute('data-hidden', 'true');
    messageRow.style.display = 'none';
    messageRow.style.visibility = 'hidden';
    messageRow.style.opacity = '0';
    messageRow.style.height = '0';
    messageRow.style.width = '0';
    messageRow.style.overflow = 'hidden';
    messageRow.style.margin = '0';
    messageRow.style.padding = '0';
    messageRow.style.position = 'absolute';
    messageRow.style.left = '-9999px';
    messageRow.style.pointerEvents = 'none';
    
    // Extract JSON
    try {
        let codeBlock = messageRow.querySelector('code') || 
                       messageRow.querySelector('pre code') ||
                       messageRow.querySelector('[class*="markdown"] code') ||
                       messageRow.querySelector('[class*="code"]');
        
        if (!codeBlock) {
            // Try to find JSON in any text content
            const textContent = messageRow.innerText || messageRow.textContent || '';
            const jsonMatch = textContent.match(/\{[\s\S]*"agent"[\s\S]*\}/);
            if (jsonMatch) {
                const jsonText = jsonMatch[0].replace(/^```json\s*/i, '').replace(/\s*```$/i, '').trim();
                const data = JSON.parse(jsonText);
                renderCard(data);
                return;
            }
        }
        
        if (codeBlock) {
            let jsonText = codeBlock.innerText || codeBlock.textContent;
            jsonText = jsonText.replace(/^```json\s*/i, '').replace(/\s*```$/i, '').trim();
            const data = JSON.parse(jsonText);
            renderCard(data);
        } else {
            console.warn('Could not find code block in notification message');
        }
    } catch (e) {
        console.error('Failed to parse notification JSON', e);
    }
}

// 3. The "DOM Bridge" (MutationObserver) - SIMPLE AND FOCUSED
// Watch for messages containing our JSON signature, hide them, render cards
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
            if (node.nodeType !== 1) return; // Only elements
            
            // Look for message elements
            let messageRow = node;
            
            // If node is not a message, look for one inside
            if (!node.classList?.contains('cl-message') && 
                !node.classList?.contains('message-row') &&
                !node.querySelector?.('.cl-message')) {
                // Try to find a message element
                messageRow = node.querySelector?.('.cl-message') ||
                           node.querySelector?.('[class*="message"]') ||
                           null;
            }
            
            if (!messageRow) return;
            
            // Check if already processed
            if (messageRow.hasAttribute('data-notification-processed')) return;
            
            // Check if it contains our JSON signature
            const textContent = messageRow.innerText || messageRow.textContent || '';
            const innerHTML = messageRow.innerHTML || '';
            
            // Look for our signature: JSON with "agent" field
            if (textContent.includes('{"agent":') || 
                textContent.includes('"__NOTIFY__"') ||
                innerHTML.includes('{"agent":')) {
                
                console.log('🔍 Found notification message, processing...');
                processNotificationMessage(messageRow);
            }
        });
    });
});

// Check for existing messages that might have been added before observer started
// Only check once, not repeatedly (to avoid performance issues)
let hasCheckedExisting = false;
function checkExistingMessages() {
    if (hasCheckedExisting) return; // Only check once
    hasCheckedExisting = true;
    
    // Check message-like elements
    const selectors = [
        '.cl-message',
        '[class*="message"]',
        'div[class*="Message"]'
    ];
    
    let allMessages = [];
    selectors.forEach(selector => {
        try {
            const found = document.querySelectorAll(selector);
            allMessages.push(...Array.from(found));
        } catch (e) {
            // Ignore invalid selectors
        }
    });
    
    console.log(`🔍 Checking ${allMessages.length} existing messages for notifications`);
    
    allMessages.forEach((messageRow) => {
        if (!messageRow.hasAttribute('data-notification-processed')) {
            const textContent = messageRow.innerText || messageRow.textContent || '';
            if (textContent.includes('"__NOTIFY__"') || textContent.includes('{"agent":')) {
                console.log('🔍 Found existing notification message, processing...');
                processNotificationMessage(messageRow);
            }
        }
    });
}

// Start observing after DOM is ready - ONLY ONCE
let observerStarted = false;
function startObserver() {
    if (observerStarted) return;
    
    // Find the chat messages container
    const chatContainer = document.querySelector('[class*="chat"]') ||
                         document.querySelector('[class*="messages"]') ||
                         document.querySelector('main') ||
                         document.body;
    
    if (chatContainer) {
        // Watch for new messages - use subtree to catch nested messages
        observer.observe(chatContainer, { 
            childList: true,
            subtree: true  // Need subtree to catch messages nested in containers
        });
        observerStarted = true;
        console.log('🔔 DOM Observer started');
        
        // Check existing messages immediately
        setTimeout(checkExistingMessages, 1000);
    } else {
        console.warn('Could not find chat container, retrying...');
        setTimeout(startObserver, 1000);
    }
}

// Start observer after page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(startObserver, 2000));
} else {
    setTimeout(startObserver, 2000);
}

// 4. Render Card Function
function renderCard(data) {
    // Ensure panel exists - create if missing
    let panel = document.getElementById('custom-notification-panel');
    if (!panel) {
        console.warn('Panel not found, creating it now...');
        panel = document.createElement('div');
        panel.id = 'custom-notification-panel';
        document.body.appendChild(panel);
        console.log('✅ Panel created on-demand');
    }
    
    // Force panel visibility - BUT DON'T BLOCK CHAT
    panel.style.display = 'flex';
    panel.style.visibility = 'visible';
    panel.style.opacity = '1';
    panel.style.position = 'fixed';
    panel.style.top = '80px';
    panel.style.right = '20px';
    panel.style.width = '320px';
    panel.style.zIndex = '0'; // ZERO z-index so chat can be on top
    panel.style.left = 'auto'; // Ensure it stays on right
    panel.style.touchAction = 'none'; // Don't interfere with touch events
    panel.style.isolation = 'isolate'; // Isolate stacking context
    panel.style.flexDirection = 'column';
    panel.style.gap = '12px';
    panel.style.pointerEvents = 'none'; // CRITICAL: Container doesn't block clicks
    panel.style.overflowY = 'auto';
    panel.style.height = 'calc(100vh - 100px)';
    panel.style.paddingBottom = '20px';
    panel.style.background = 'transparent';
    panel.style.maxHeight = 'calc(100vh - 100px)';

    const card = document.createElement('div');
    const agent = (data.agent || 'System').toLowerCase();
    // Use agent-based class for distinct colors
    card.className = `notification-card ${agent} ${data.severity || 'info'}`;
    card.setAttribute('data-agent', agent);
    
    // DEBUG: Log the classes being applied
    console.log(`🎨 Rendering card for agent: ${agent}, classes: ${card.className}, data-agent: ${agent}`);
    
    // Build card HTML
    const icon = data.icon || '🔔';
    // Capitalize agent name (Guardian, Optimizer, etc.)
    const agentName = (data.agent || 'System').charAt(0).toUpperCase() + (data.agent || 'System').slice(1).toLowerCase();
    const message = data.message || 'Notification';
    const severity = data.severity || 'info';
    
    card.innerHTML = `
        <div class="card-header">
            <span class="card-icon">${icon}</span>
            <span>${agentName}</span>
        </div>
        <div class="card-message">${message}</div>
        <div class="card-hint">Click to Investigate →</div>
    `;
    
    // Click handler - ONLY trigger on explicit user click
    card.onclick = (e) => {
        e.stopPropagation();
        e.preventDefault();
        
        // Only trigger if user explicitly clicked (not programmatic)
        if (e.isTrusted) {
            const context = data.context || data.message || '';
            console.log(`🔔 User clicked notification card: ${agentName}`);
            window.triggerAgent(agentName, context);
        }
        
        // Animate removal
        card.style.transform = 'translateX(120%)';
        card.style.opacity = '0';
        setTimeout(() => {
            card.remove();
            console.log(`✅ Removed notification card: ${agent}`);
        }, 300);
    };
    
    // Check if this alert already exists (prevent duplicates)
    const existingCards = panel.querySelectorAll('.notification-card');
    const cardId = data.id || `${agent}-${message.substring(0, 20)}`;
    let duplicate = false;
    existingCards.forEach(existingCard => {
        const existingText = existingCard.innerText || '';
        if (existingText.includes(agent) && existingText.includes(message.substring(0, 20))) {
            duplicate = true;
        }
    });
    
    if (duplicate) {
        console.log(`⚠️ Duplicate notification skipped: ${agent} - ${message.substring(0, 30)}`);
        return;
    }
    
    // Add to panel
    panel.appendChild(card);
    
    // Limit to max 10 cards (remove oldest if needed)
    const cards = panel.querySelectorAll('.notification-card');
    if (cards.length > 10) {
        cards[0].remove();
    }
    
    console.log(`✅ Rendered notification card: ${agentName} - ${severity}`);
}
