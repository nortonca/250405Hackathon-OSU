document.addEventListener('DOMContentLoaded', () => {
    // Connect to Socket.IO server
    const socket = io();
    const messageContainer = document.getElementById('message-container');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');

    // Display connection status
    socket.on('connect', () => {
        addMessageToContainer('System', 'Connected to server', 'text-green-500');
    });

    socket.on('disconnect', () => {
        addMessageToContainer('System', 'Disconnected from server', 'text-red-500');
    });

    // Handle incoming messages
    socket.on('response', (data) => {
        addMessageToContainer('Server', data.data, 'message message-received');
    });

    // Send message when button is clicked
    sendButton.addEventListener('click', sendMessage);

    // Send message when Enter key is pressed
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    function sendMessage() {
        const message = messageInput.value.trim();
        if (message) {
            // Send message to server
            socket.emit('message', message);
            
            // Display sent message
            addMessageToContainer('You', message, 'message message-sent');
            
            // Clear input
            messageInput.value = '';
        }
    }

    function addMessageToContainer(sender, text, className) {
        // Create message element
        const messageDiv = document.createElement('div');
        messageDiv.className = 'flex flex-col ' + className;
        
        // Add sender name if provided
        if (sender) {
            const senderSpan = document.createElement('span');
            senderSpan.className = 'text-xs text-gray-500 mb-1';
            senderSpan.textContent = sender;
            messageDiv.appendChild(senderSpan);
        }
        
        // Add message text
        const textSpan = document.createElement('span');
        textSpan.textContent = text;
        messageDiv.appendChild(textSpan);
        
        // Add timestamp
        const timestamp = document.createElement('span');
        timestamp.className = 'text-xs text-gray-400 self-end mt-1';
        timestamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        messageDiv.appendChild(timestamp);
        
        // Add to container
        messageContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        messageContainer.scrollTop = messageContainer.scrollHeight;
    }
}); 