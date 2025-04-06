// Global variables
let statusCheckInterval = null;
let conversationUpdateInterval = null;
const statusUpdateFrequency = 1000; // 1 second
const conversationUpdateFrequency = 5000; // 5 seconds
let lastEventTimestamp = 0;

// DOM Elements
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const refreshConversationBtn = document.getElementById('refreshConversationBtn');
const clearEventsBtn = document.getElementById('clearEventsBtn');
const autoScrollSwitch = document.getElementById('autoScrollSwitch');
const assistantStatus = document.getElementById('assistantStatus');
const serverStatus = document.getElementById('serverStatus');
const vadStatus = document.getElementById('vadStatus');
const lastUpdated = document.getElementById('lastUpdated');
const conversationHistory = document.getElementById('conversationHistory');
const eventsContainer = document.getElementById('eventsContainer');
const vadConfig = document.getElementById('vadConfig');
const serverConfig = document.getElementById('serverConfig');

// Helper function to format timestamps
function formatTimestamp(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString();
}

// Helper function to format relative time
function formatRelativeTime(timestamp) {
    const now = Date.now();
    const diff = now - timestamp * 1000;
    
    if (diff < 1000) {
        return 'just now';
    } else if (diff < 60000) {
        const seconds = Math.floor(diff / 1000);
        return `${seconds} second${seconds !== 1 ? 's' : ''} ago`;
    } else if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
    } else if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
    } else {
        return formatTimestamp(timestamp);
    }
}

// Update status indicators
function updateStatus() {
    fetch('/get_status')
        .then(response => response.json())
        .then(data => {
            // Update last updated time
            lastUpdated.textContent = new Date().toLocaleTimeString();
            
            // Update assistant status
            if (data.status === 'running') {
                assistantStatus.textContent = 'Running';
                assistantStatus.className = 'badge bg-success';
                startBtn.disabled = true;
                stopBtn.disabled = false;
                
                // Update server connection status
                if (data.server_connected) {
                    serverStatus.textContent = 'Connected';
                    serverStatus.className = 'badge bg-success';
                } else {
                    serverStatus.textContent = 'Disconnected';
                    serverStatus.className = 'badge bg-danger';
                }
                
                // Update VAD status
                if (data.vad_state === 'speaking') {
                    vadStatus.textContent = 'Speaking';
                    vadStatus.className = 'badge bg-warning';
                } else {
                    vadStatus.textContent = 'Listening';
                    vadStatus.className = 'badge bg-info';
                }
                
                // Update events if there are new ones
                updateEvents(data.recent_events);
                
            } else {
                assistantStatus.textContent = 'Stopped';
                assistantStatus.className = 'badge bg-secondary';
                serverStatus.textContent = 'Disconnected';
                serverStatus.className = 'badge bg-secondary';
                vadStatus.textContent = 'Idle';
                vadStatus.className = 'badge bg-secondary';
                startBtn.disabled = false;
                stopBtn.disabled = true;
            }
        })
        .catch(error => {
            console.error('Error getting status:', error);
            assistantStatus.textContent = 'Error';
            assistantStatus.className = 'badge bg-danger';
        });
}

// Update conversation history
function updateConversation() {
    fetch('/get_conversation')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayConversation(data.conversation);
            }
        })
        .catch(error => {
            console.error('Error getting conversation:', error);
        });
}

// Display conversation history
function displayConversation(conversation) {
    if (!conversation || conversation.length === 0) {
        conversationHistory.innerHTML = `
            <div class="text-center text-muted p-4">
                No conversation history yet
            </div>
        `;
        return;
    }
    
    let html = '';
    conversation.forEach(item => {
        const timestamp = formatRelativeTime(item.timestamp);
        
        html += `
            <div class="conversation-item mb-3">
                <div class="conversation-time text-muted small mb-1">${timestamp}</div>
                <div class="conversation-user mb-2">
                    <i class="fas fa-user-circle me-2"></i>
                    <div class="conversation-bubble user-bubble">${item.user_input}</div>
                </div>
                <div class="conversation-system">
                    <i class="fas fa-robot me-2"></i>
                    <div class="conversation-bubble system-bubble">${item.system_response}</div>
                </div>
            </div>
        `;
    });
    
    conversationHistory.innerHTML = html;
    
    // Scroll to bottom if container is scrollable
    conversationHistory.scrollTop = conversationHistory.scrollHeight;
}

// Update events list
function updateEvents(events) {
    if (!events || events.length === 0) {
        eventsContainer.innerHTML = `
            <div class="text-center text-muted p-4">
                No events yet
            </div>
        `;
        return;
    }
    
    // Filter only new events based on timestamp
    const newEvents = events.filter(event => event.timestamp > lastEventTimestamp);
    
    if (newEvents.length === 0) {
        return; // No new events
    }
    
    // Update last event timestamp
    lastEventTimestamp = Math.max(...events.map(event => event.timestamp));
    
    // Clear "No events yet" message if it's there
    if (eventsContainer.querySelector('.text-center.text-muted')) {
        eventsContainer.innerHTML = '';
    }
    
    let html = '';
    newEvents.forEach(event => {
        const timestamp = formatTimestamp(event.timestamp);
        const iconClass = event.is_error ? 'fa-exclamation-triangle text-danger' : 'fa-info-circle text-info';
        
        html += `
            <div class="event-item ${event.is_error ? 'event-error' : ''}">
                <span class="event-time">${timestamp}</span>
                <i class="fas ${iconClass} me-2"></i>
                <span class="event-message">${event.message}</span>
            </div>
        `;
    });
    
    // Append new events
    eventsContainer.innerHTML += html;
    
    // Auto-scroll if enabled
    if (autoScrollSwitch.checked) {
        eventsContainer.scrollTop = eventsContainer.scrollHeight;
    }
}

// Start the voice assistant
function startAssistant() {
    fetch('/start_assistant', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            startStatusChecks();
            startBtn.disabled = true;
            stopBtn.disabled = false;
        } else {
            alert(`Failed to start: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error starting assistant:', error);
        alert('Error starting assistant. Check console for details.');
    });
}

// Stop the voice assistant
function stopAssistant() {
    fetch('/stop_assistant', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            stopStatusChecks();
            startBtn.disabled = false;
            stopBtn.disabled = true;
            assistantStatus.textContent = 'Stopped';
            assistantStatus.className = 'badge bg-secondary';
            serverStatus.textContent = 'Disconnected';
            serverStatus.className = 'badge bg-secondary';
            vadStatus.textContent = 'Idle';
            vadStatus.className = 'badge bg-secondary';
        } else {
            alert(`Failed to stop: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error stopping assistant:', error);
        alert('Error stopping assistant. Check console for details.');
    });
}

// Start regular status checks
function startStatusChecks() {
    // Clear any existing intervals
    stopStatusChecks();
    
    // Start status check interval
    statusCheckInterval = setInterval(updateStatus, statusUpdateFrequency);
    
    // Start conversation update interval
    conversationUpdateInterval = setInterval(updateConversation, conversationUpdateFrequency);
    
    // Perform initial updates
    updateStatus();
    updateConversation();
}

// Stop regular status checks
function stopStatusChecks() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
    
    if (conversationUpdateInterval) {
        clearInterval(conversationUpdateInterval);
        conversationUpdateInterval = null;
    }
}

// Clear events container
function clearEvents() {
    eventsContainer.innerHTML = `
        <div class="text-center text-muted p-4">
            No events yet
        </div>
    `;
    lastEventTimestamp = 0;
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Initial check for assistant status
    updateStatus();
    
    // Button event listeners
    startBtn.addEventListener('click', startAssistant);
    stopBtn.addEventListener('click', stopAssistant);
    refreshConversationBtn.addEventListener('click', updateConversation);
    clearEventsBtn.addEventListener('click', clearEvents);
    
    // Debug information
    vadConfig.textContent = `Threshold: 0.3
Frame Duration: 30ms
Speech Timeout: 1.0s
Silence Timeout: 1.5s`;

    serverConfig.textContent = `URL: [from environment]
Retry Limit: 5
Retry Delay: 2.0s
Timeout: 10.0s`;
});

// Handle page visibility changes to conserve resources
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
        // Page is hidden, stop frequent updates
        stopStatusChecks();
    } else if (assistantStatus.textContent === 'Running') {
        // Page is visible again and assistant is running, resume updates
        startStatusChecks();
    }
});
