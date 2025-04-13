// --- START OF FILE frontend/static/js/chat.js ---
// Chat Interface Management
import { apiService } from './api.js'; // Correct import using the instance
import { showNotification } from './utils.js';
// Ensure Marked library is loaded (globally via script tag in HTML)

class ChatService {
    constructor() {
        console.log("Initializing ChatService...");
        this.chatContainer = document.getElementById('chat-container');
        this.messagesContainer = document.getElementById('chat-messages');
        this.inputArea = document.getElementById('chat-input-area'); // Container for input/button
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.loadingIndicator = document.getElementById('loading-indicator');
        // this.typingIndicator = null; // Keep if separate typing indicator is used

        this.hasEntries = false; // Flag to check if user has journal entries
        this.isProcessing = false; // Flag to prevent multiple submissions
        this.initialCheckDone = false; // Flag to ensure initial check runs once

        // Log initialization status
        console.log("Chat elements found:", {
            container: !!this.chatContainer,
            messages: !!this.messagesContainer,
            input: !!this.messageInput,
            button: !!this.sendButton,
            loading: !!this.loadingIndicator
        });

        if (!this.messagesContainer || !this.messageInput || !this.sendButton || !this.loadingIndicator) {
            console.error("Error: Required chat UI elements not found! Chat cannot function.");
            if (this.messagesContainer) {
                 this.messagesContainer.innerHTML = '<div class="message error-message"><div class="message-content"><p>Lỗi giao diện người dùng. Không thể tải Chat.</p></div></div>';
            }
            return; // Stop initialization
        }

        // Configure marked
        if (window.marked) {
             marked.setOptions({ breaks: true, gfm: true, headerIds: false, mangle: false });
             console.log("Marked library configured.");
        } else {
             console.warn("Marked library not found. Markdown rendering will be disabled.");
        }

        this.initializeEventListeners();
        // Initial check is triggered by auth successful setup or page load
        // this.performInitialCheck(); // Moved to be called after auth check
    }

    initializeEventListeners() {
        if (!this.sendButton || !this.messageInput) return; // Guard

        this.sendButton.addEventListener('click', () => this.handleSendMessage());

        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSendMessage();
            }
        });

        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = `${this.messageInput.scrollHeight}px`;
        });
    }

    async performInitialCheck() {
        if (!apiService.token) return; // Don't run if not logged in
        console.log("Performing initial chat context check...");
        this.initialCheckDone = true;
        this.setLoadingState(true, true); // Show initial loading

        try {
            // Always get fresh context from server
            const entries = await apiService.getChatContext(); // This will now prepare a new chat session
            this.hasEntries = true; // If successful, user has entries
            console.log("Initial entry check successful. User has entries.");
            this.displayWelcomeMessage(); // Display standard welcome message

        } catch (error) {
            console.error('Error checking for entries:', error);
            this.hasEntries = false; // Assume no entries on error

            // Check if error indicates "no entries found" (e.g., 404 or specific message)
            if (error.message && (error.message.includes("404") || error.message.toLowerCase().includes("no journal entries found"))) {
                console.log("No entries found via context endpoint.");
                this.displayWelcomeMessage(); // Display the specific welcome message for no entries
            } else if (error.message && error.message.includes("401")) {
                // Should be handled by Auth service redirect, but handle defensively
                this.displayErrorMessage("Bạn cần đăng nhập để sử dụng tính năng Chat.");
                this.disableInput("Authentication required.");
            } else {
                // Generic error during initial check
                this.displayErrorMessage("Không thể kiểm tra trạng thái nhật ký. Vui lòng thử làm mới trang.");
                this.disableInput("Error loading context.");
            }
        } finally {
            this.setLoadingState(false, true); // Hide initial loading, enable/disable input based on hasEntries
        }
    }

    displayWelcomeMessage() {
        // Clear previous messages maybe? Or just add to them.
        // this.messagesContainer.innerHTML = ''; // Uncomment to clear history on load

        let welcomeText;
        if (this.hasEntries) {
            welcomeText = "Chào bạn! Tôi đã đọc qua các bài viết nhật ký gần đây của bạn. Bạn muốn trò chuyện về điều gì hôm nay?";
            this.enableInput();
        } else {
            welcomeText = "Chào bạn! Dường như bạn chưa có bài viết nhật ký nào. Hãy viết ít nhất một bài trong tab 'Xem Nhật ký' để chúng ta có thể bắt đầu trò chuyện nhé.";
            this.disableInput("Vui lòng tạo bài viết nhật ký trước...");
        }

        this.displayMessage({ role: 'ai', content: welcomeText });
    }

    async handleSendMessage() {
        if (!this.messageInput || !this.sendButton) return; // Guard
        const userMessage = this.messageInput.value.trim();

        if (!userMessage || this.isProcessing || !this.hasEntries) {
             if(!this.hasEntries) {
                  showNotification("Vui lòng tạo ít nhất một bài viết nhật ký trước khi bắt đầu chat.", true);
             }
            return; // Ignore empty, processing, or no-entry state
        }

        this.isProcessing = true;
        this.setLoadingState(true); // Show typing indicator, disable input/button

        // Display user message
        this.displayMessage({ role: 'user', content: userMessage });

        // Clear input & reset height
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        // Don't refocus immediately, wait for AI response

        try {
            const response = await apiService.sendChatMessage(userMessage);

            if (response && typeof response.reply === 'string') {
                this.displayMessage({ role: 'ai', content: response.reply });
            } else {
                 console.error('Invalid response format from server:', response);
                throw new Error('Phản hồi không hợp lệ từ máy chủ.');
            }
        } catch (error) {
            console.error('Chat send/receive error:', error);
            let errorMessage = 'Đã xảy ra lỗi khi xử lý tin nhắn của bạn.';

             // Check for specific error messages from ApiService/Backend
             if (error.message) {
                 // Check for "write entry" message specifically
                 if (error.message.toLowerCase().includes("please write at least one journal entry")) {
                    errorMessage = "Vui lòng tạo ít nhất một bài viết nhật ký trước khi bắt đầu chat.";
                    this.hasEntries = false; // Update state
                    this.disableInput("Vui lòng tạo bài viết nhật ký trước...");
                 } else if (error.message.includes("AI service error:") || error.message.includes("AI Error:")) {
                      errorMessage = error.message; // Display specific AI error (e.g., safety, quota)
                 } else if (error.message.includes("401") || error.message.includes("Authentication required")) {
                      errorMessage = "Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.";
                      // Consider triggering authService.redirectToLogin() after a delay
                 } else if (error.message.includes("503") || error.message.includes("AI service unavailable") || error.message.includes("AI service failed to respond")) {
                      errorMessage = "Dịch vụ AI hiện không khả dụng hoặc không phản hồi. Vui lòng thử lại sau.";
                 } else if (error.message.includes("400") && error.message.includes("Bad Request")) {
                      // General bad request, could be various issues.
                      errorMessage = "Yêu cầu không hợp lệ. Vui lòng thử lại.";
                 } else {
                      // Use the error message if it seems informative, otherwise generic
                      errorMessage = `Lỗi: ${error.message}`;
                 }
             }
            this.displayErrorMessage(errorMessage);
        } finally {
            this.isProcessing = false;
            // Enable/disable based on hasEntries, hide loading
            this.setLoadingState(false);
        }
    }

    displayMessage(messageData) { // { role: 'user'/'ai', content: '...' }
        if (!this.messagesContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${messageData.role}-message`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        try {
            if (messageData.role === 'ai' && window.marked) {
                // Sanitize potentially harmful HTML before parsing markdown
                // Basic sanitization (more robust needed for production)
                // const sanitizedHtml = messageData.content.replace(/<script.*?>.*?<\/script>/gi, '');
                contentDiv.innerHTML = marked.parse(messageData.content); // Use parse for block elements
            } else {
                 const p = document.createElement('p');
                 p.textContent = messageData.content;
                 contentDiv.appendChild(p);
            }
        } catch (error) {
            console.error('Error parsing markdown:', error);
            const p = document.createElement('p');
            p.textContent = messageData.content; // Fallback to plain text
            contentDiv.appendChild(p);
        }

        messageDiv.appendChild(contentDiv);
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    displayErrorMessage(messageText) {
        this.displayMessage({ role: 'error', content: messageText }); // Use displayMessage with error role/style
    }

    setLoadingState(isLoading, isInitial = false) {
        if (!this.loadingIndicator || !this.sendButton || !this.messageInput) return; // Guard

        if (isLoading) {
             this.loadingIndicator.style.display = 'flex';
             if(!isInitial) { // Only disable input/button during message exchange loading
                this.sendButton.disabled = true;
                this.messageInput.disabled = true;
             }
        } else {
            this.loadingIndicator.style.display = 'none';
             // Enable/disable based on whether the user *can* chat (has entries)
             if (this.hasEntries) {
                 this.enableInput();
             } else {
                 // Keep disabled if no entries, even after loading finishes
                 this.disableInput(this.messageInput.placeholder || "Vui lòng tạo bài viết nhật ký trước...");
             }
             // Refocus input only if it's enabled
            if (!this.messageInput.disabled) {
                 this.messageInput.focus();
            }
        }
    }

    // Helper methods to enable/disable input area
    enableInput() {
        if (!this.messageInput || !this.sendButton) return;
         this.messageInput.disabled = false;
         this.sendButton.disabled = false;
         this.messageInput.placeholder = "Nhập tin nhắn của bạn ở đây...";
    }

    disableInput(placeholderText = "Chat không khả dụng.") {
        if (!this.messageInput || !this.sendButton) return;
        this.messageInput.disabled = true;
        this.sendButton.disabled = true;
        this.messageInput.placeholder = placeholderText;
    }


    scrollToBottom() {
        if (!this.messagesContainer) return;
        this.messagesContainer.scrollTo({
            top: this.messagesContainer.scrollHeight,
            behavior: 'smooth'
        });
    }
}

// Export the class
export { ChatService };
// --- END OF FILE frontend/static/js/chat.js ---