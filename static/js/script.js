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
    fetch('/api/new_chat', {
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
        fetch('/api/chat', {
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
    // Use smooth scrolling for better user experience
    chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: 'smooth'
    });
}

// Add MutationObserver to handle dynamic content updates
function setupScrollObserver() {
    const chatContainer = document.getElementById('chat-container');
    const observer = new MutationObserver(() => {
        scrollToBottom();
    });

    observer.observe(chatContainer, {
        childList: true,
        subtree: true,
        characterData: true
    });
}

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

async function initVoiceRecognition() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async() => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const reader = new FileReader();

            reader.onloadend = async() => {
                try {
                    const response = await fetch('/api/transcribe', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            audio: reader.result
                        })
                    });

                    const data = await response.json();
                    if (data.error) {
                        console.error('Transcription error:', data.error);
                        return;
                    }

                    const messageInput = document.getElementById('message-input');
                    messageInput.value = data.transcription;
                    messageInput.focus();
                    messageInput.setSelectionRange(data.transcription.length, data.transcription.length);
                } catch (error) {
                    console.error('Error sending audio for transcription:', error);
                }
            };

            reader.readAsDataURL(audioBlob);
            audioChunks = [];
        };
    } catch (error) {
        console.error('Error initializing voice recognition:', error);
        document.getElementById('voice-button').style.display = 'none';
    }
}

function toggleVoiceInput() {
    if (!mediaRecorder) {
        initVoiceRecognition();
        return;
    }

    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

function startRecording() {
    if (mediaRecorder && mediaRecorder.state === 'inactive') {
        audioChunks = [];
        mediaRecorder.start();
        isRecording = true;
        document.getElementById('voice-button').classList.add('listening');
        document.getElementById('voice-status').classList.add('active');
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        isRecording = false;
        document.getElementById('voice-button').classList.remove('listening');
        document.getElementById('voice-status').classList.remove('active');
    }
}

// Chat history functionality
let currentPage = 1;

function showHistoryModal() {
    const modal = document.getElementById('history-modal');
    modal.classList.add('active');
    loadChatHistory();
}

function hideHistoryModal() {
    const modal = document.getElementById('history-modal');
    modal.classList.remove('active');
}

function loadChatHistory() {
    fetch(`/api/chat-history?page=${currentPage}`)
        .then(response => response.json())
        .then(data => {
            const historyList = document.getElementById('history-list');
            historyList.innerHTML = '';

            data.chats.forEach(chat => {
                const historyItem = document.createElement('div');
                historyItem.className = 'history-item';

                // Format the message and response using the existing formatMessage function
                const formattedMessage = formatMessage(chat.message);
                const formattedResponse = formatMessage(chat.response);

                historyItem.innerHTML = `
                    <div class="timestamp">${chat.timestamp}</div>
                    <div class="message user">
                        <div class="message-content">
                            ${formattedMessage}
                        </div>
                    </div>
                    <div class="message assistant">
                        <div class="message-content">
                            ${formattedResponse}
                        </div>
                    </div>
                `;
                historyList.appendChild(historyItem);
            });

            // Update pagination
            document.getElementById('page-info').textContent = `Page ${data.current_page} of ${data.total_pages}`;
            document.getElementById('prev-page').disabled = !data.has_prev;
            document.getElementById('next-page').disabled = !data.has_next;
        })
        .catch(error => {
            console.error('Error loading chat history:', error);
        });
}

// Event listeners for history functionality
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

    // Initialize voice recognition
    initVoiceRecognition();

    // Setup scroll observer
    setupScrollObserver();

    // Initialize with welcome message
    startNewChat();

    // History button
    const historyButton = document.getElementById('history-button');
    historyButton.addEventListener('click', showHistoryModal);

    // Close modal button
    const closeButton = document.querySelector('.close-button');
    closeButton.addEventListener('click', hideHistoryModal);

    // Close modal when clicking outside
    const modal = document.getElementById('history-modal');
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            hideHistoryModal();
        }
    });

    // Pagination buttons
    document.getElementById('prev-page').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadChatHistory();
        }
    });

    document.getElementById('next-page').addEventListener('click', () => {
        currentPage++;
        loadChatHistory();
    });
});

// Hamburger menu for mobile nav
const menuToggle = document.getElementById('menu-toggle');
const navLinks = document.getElementById('nav-links');
const navOverlay = document.getElementById('mobile-nav-overlay');

if (menuToggle && navLinks && navOverlay) {
    menuToggle.addEventListener('click', function() {
        const isOpen = navLinks.classList.toggle('open');
        navOverlay.classList.toggle('active', isOpen);
        menuToggle.setAttribute('aria-expanded', isOpen);
    });
    navOverlay.addEventListener('click', function() {
        navLinks.classList.remove('open');
        navOverlay.classList.remove('active');
        menuToggle.setAttribute('aria-expanded', 'false');
    });
    // Optional: close menu on ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            navLinks.classList.remove('open');
            navOverlay.classList.remove('active');
            menuToggle.setAttribute('aria-expanded', 'false');
        }
    });
}

// Medicine Identifier Functions
function identifyMedicine(method) {
    clearResults();
    showLoading();

    const formData = new FormData();

    if (method === 'text') {
        const medicineName = document.getElementById('medicine-name').value.trim();
        if (!medicineName) {
            showError('Please enter a medicine name');
            hideLoading();
            return;
        }
        formData.append('medicine_name', medicineName);
    } else if (method === 'image') {
        const file = document.getElementById('medicine-image').files[0];
        if (!file) {
            showError('Please select an image');
            hideLoading();
            return;
        }
        formData.append('image', file);
    }

    fetch('/api/medicine-helper', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.status === 'success') {
                showResults(data.medicine_name, data.use_cases);
            } else {
                showError(data.error || 'An error occurred');
            }
        })
        .catch(error => {
            hideLoading();
            showError('Network error. Please try again.');
            console.error('Error:', error);
        });
}

function handleFile(file) {
    const allowedTypes = ['image/png', 'image/jpg', 'image/jpeg', 'image/gif', 'image/bmp'];

    if (!allowedTypes.includes(file.type)) {
        showError('Please select a valid image file (PNG, JPG, JPEG, GIF, BMP)');
        return;
    }

    const reader = new FileReader();
    reader.onload = function(e) {
        const previewImg = document.getElementById('preview-img');
        const imagePreview = document.getElementById('image-preview');
        const uploadArea = document.getElementById('upload-area');
        const imageSubmitBtn = document.getElementById('image-submit-btn');

        previewImg.src = e.target.result;
        imagePreview.style.display = 'block';
        uploadArea.style.display = 'none';
        imageSubmitBtn.disabled = false;
    };
    reader.readAsDataURL(file);
}

function removeImage() {
    const imagePreview = document.getElementById('image-preview');
    const uploadArea = document.getElementById('upload-area');
    const imageInput = document.getElementById('medicine-image');
    const imageSubmitBtn = document.getElementById('image-submit-btn');

    imagePreview.style.display = 'none';
    uploadArea.style.display = 'block';
    imageInput.value = '';
    imageSubmitBtn.disabled = true;
}

function showLoading() {
    document.getElementById('loading-state').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-state').style.display = 'none';
}

function showResults(medicineName, useCases) {
    document.getElementById('result-medicine-name').textContent = medicineName;
    document.getElementById('use-cases-content').innerHTML = useCases.replace(/\n/g, '<br>');
    document.getElementById('results-section').style.display = 'block';
}

function showError(message) {
    document.getElementById('error-message').textContent = message;
    document.getElementById('error-section').style.display = 'block';
}

function clearResults() {
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('error-section').style.display = 'none';
}

// Initialize medicine helper page functionality
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the medicine helper page
    if (document.querySelector('.medicine-helper-container')) {
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const method = btn.dataset.method;
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.querySelectorAll('.input-section').forEach(section => section.classList.remove('active'));
                document.getElementById(`${method}-input`).classList.add('active');
                clearResults();
            });
        });

        // File upload functionality
        const uploadArea = document.getElementById('upload-area');
        const imageInput = document.getElementById('medicine-image');

        if (uploadArea && imageInput) {
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });

            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) handleFile(files[0]);
            });

            uploadArea.addEventListener('click', () => {
                imageInput.click();
            });

            imageInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) handleFile(e.target.files[0]);
            });
        }
    }
});