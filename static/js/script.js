function formatMessage(message) {
    // Convert URLs to clickable links
    message = message.replace(
        /(https?:\/\/[^\s]+)/g,
        '<a href="$1" target="_blank" style="color: var(--primary-color); text-decoration: underline;">$1</a>'
    );

    // Format lists
    message = message.replace(
        /^\s*[-*]\s+(.+)$/gm,
        '<li>$1</li>'
    );

    // Format numbered lists
    message = message.replace(
        /^\s*\d+\.\s+(.+)$/gm,
        '<li>$1</li>'
    );

    // Wrap lists in appropriate tags
    if (message.includes('<li>')) {
        message = message.replace(
            /((?:<li>.*<\/li>\n?)+)/g,
            '<ul>$1</ul>'
        );
    }

    // Format paragraphs
    message = message.replace(
        /^(?!<[a-z])(.+)$/gm,
        '<p>$1</p>'
    );

    // Format bold text
    message = message.replace(
        /\*\*(.*?)\*\*/g,
        '<strong>$1</strong>'
    );

    // Format code blocks
    message = message.replace(
        /`(.*?)`/g,
        '<code>$1</code>'
    );

    // Format warning messages
    message = message.replace(/warning-message:(.*?)(?=\n|$)/g,
        '<div class="warning-message"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>$1</div>');

    // Format emergency messages
    message = message.replace(/emergency-message:(.*?)(?=\n|$)/g,
        '<div class="emergency-message"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>$1</div>');

    // Format health tips
    message = message.replace(/health-tip:(.*?)(?=\n|$)/g,
        '<div class="health-tip"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>$1</div>');

    return message;
}

function detectMessageType(message) {
    const lowerMessage = message.toLowerCase();

    if (lowerMessage.includes('emergency') ||
        lowerMessage.includes('urgent') ||
        lowerMessage.includes('immediately') ||
        lowerMessage.includes('severe')) {
        return 'emergency';
    }

    if (lowerMessage.includes('warning') ||
        lowerMessage.includes('caution') ||
        lowerMessage.includes('be careful')) {
        return 'warning';
    }

    if (lowerMessage.includes('tip') ||
        lowerMessage.includes('recommendation') ||
        lowerMessage.includes('suggestion')) {
        return 'health-tip';
    }

    return 'normal';
}

function createDisclaimer() {
    return `
        <div class="disclaimer-banner">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <p>I am an AI assistant and cannot provide medical diagnoses. Please consult with healthcare professionals for medical advice. In case of emergency, call emergency services immediately.</p>
    </div>
    `;
}

function startNewChat() {
    const chatContainer = document.getElementById('chat-container');
    const messageInput = document.getElementById('message-input');

    // Clear the chat container
    chatContainer.innerHTML = '';

    // Clear the input field
    messageInput.value = '';

    // Focus on the input field
    messageInput.focus();

    // Add a welcome message
    const welcomeMessage = document.createElement('div');
    welcomeMessage.className = 'message assistant';
    welcomeMessage.innerHTML = `
        <p>Hello! I'm Dr.Wise, your AI health assistant. I'll help you with your health concerns, but first, I need to gather some important information to provide you with the best possible guidance.</p>
        <p>Could you please tell me your age and gender?</p>
        <p>Or you can ask me anything about health.</p>
        ${createDisclaimer()}
    `;
    chatContainer.appendChild(welcomeMessage);

    // Clear conversation history on the server
    fetch('/new_chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    });
}

function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();

    if (message) {
        // Add user message to chat
        addMessageToChat('user', message);

        // Clear input
        messageInput.value = '';

        // Show loading indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message assistant loading';
        loadingDiv.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
        document.getElementById('chat-container').appendChild(loadingDiv);

        // Scroll to bottom
        scrollToBottom();

        // Send message to server
        fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `message=${encodeURIComponent(message)}`
            })
            .then(response => response.json())
            .then(data => {
                // Remove loading indicator
                document.querySelector('.loading').remove();

                if (data.error) {
                    addMessageToChat('assistant', `Error: ${data.error}`);
                } else {
                    addMessageToChat('assistant', data.message);
                }
                scrollToBottom();
            })
            .catch(error => {
                // Remove loading indicator
                document.querySelector('.loading').remove();
                addMessageToChat('assistant', 'Sorry, there was an error processing your request. Please try again.');
                scrollToBottom();
            });
    }
}

function addMessageToChat(role, message) {
    const chatContainer = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    // Format the message with proper styling
    const formattedMessage = formatMessage(message);
    messageDiv.innerHTML = formattedMessage;

    chatContainer.appendChild(messageDiv);
}

function scrollToBottom() {
    const chatContainer = document.getElementById('chat-container');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Add event listener for Enter key
document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Add placeholder text that changes periodically
    const placeholders = [
        "How can I help with your health today?",
        "Describe your symptoms...",
        "Tell me about your medical history...",
        "What medications are you currently taking?",
        "How long have you been experiencing these symptoms?"
    ];

    let currentPlaceholder = 0;
    setInterval(() => {
        messageInput.placeholder = placeholders[currentPlaceholder];
        currentPlaceholder = (currentPlaceholder + 1) % placeholders.length;
    }, 3000);

    // Initialize with welcome message
    startNewChat();
});