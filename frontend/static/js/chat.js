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
        this.inputArea = document.getElementById('chat-input-area'); // Used? Maybe just container
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
            // Optionally display a persistent error message on the page
            if (this.messagesContainer) {
                 this.messagesContainer.innerHTML = '<div class="message error-message"><div class="message-content"><p>Lỗi giao diện người dùng. Không thể tải Chat.</p></div></div>';
            }
            return; // Stop initialization
        }

        // Configure marked options if not already done globally
        if (window.marked) {
             marked.setOptions({
                 breaks: true, // Convert single line breaks to <br>
                 gfm: true, // Use GitHub Flavored Markdown
                 headerIds: false, // Don't generate header IDs
                 mangle: false // Don't obfuscate email addresses
             });
             console.log("Marked library configured.");
        } else {
             console.warn("Marked library not found. Markdown rendering will be disabled.");
        }


        this.initializeEventListeners();
        this.performInitialCheck(); // Check for entries and display welcome
    }

    initializeEventListeners() {
        this.sendButton.addEventListener('click', () => this.handleSendMessage());

        this.messageInput.addEventListener('keypress', (e) => {
            // Send on Enter, unless Shift+Enter is pressed
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault(); // Prevent new line in textarea
                this.handleSendMessage();
            }
        });

        // Auto-resize textarea (optional but nice)
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto'; // Reset height
            this.messageInput.style.height = `${this.messageInput.scrollHeight}px`; // Set to scroll height
        });
    }

    async performInitialCheck() {
         if (this.initialCheckDone) return;
         this.initialCheckDone = true;
         this.setLoadingState(true, true); // Show loading initially

        try {
             // Use the /context endpoint to check for entries
            const entries = await apiService.getChatContext(); // Assuming this returns entries or throws 404
            this.hasEntries = entries && entries.length > 0;
            console.log("Initial entry check successful. Has entries:", this.hasEntries);
            this.displayWelcomeMessage();
        } catch (error) {
            console.error('Error checking for entries:', error);
            this.hasEntries = false; // Assume no entries on error
            if (error.message && error.message.includes("No journal entries found")) {
                 console.log("No entries found via context endpoint.");
                 this.displayWelcomeMessage(); // Display specific welcome message
            } else if (error.message && error.message.includes("401")) {
                // This should ideally be caught by ApiService redirecting, but handle defensively
                this.displayErrorMessage("Bạn cần đăng nhập để sử dụng tính năng Chat.");
                this.messageInput.disabled = true;
                this.sendButton.disabled = true;
            }
             else {
                // Generic error during initial check
                this.displayErrorMessage("Không thể kiểm tra trạng thái nhật ký. Vui lòng thử lại.");
                 this.messageInput.disabled = true;
                 this.sendButton.disabled = true;
            }
        } finally {
             this.setLoadingState(false, true); // Hide initial loading
        }
    }

    displayWelcomeMessage() {
        let welcomeText;
        if (this.hasEntries) {
            welcomeText = "Chào bạn! Tôi đã đọc qua các bài viết nhật ký gần đây của bạn. Bạn muốn trò chuyện về điều gì hôm nay?";
        } else {
            welcomeText = "Chào bạn! Dường như bạn chưa có bài viết nhật ký nào gần đây. Hãy viết ít nhất một bài để chúng ta có thể bắt đầu trò chuyện nhé.";
             // Disable input if no entries
             this.messageInput.disabled = true;
             this.sendButton.disabled = true;
             this.messageInput.placeholder = "Vui lòng tạo bài viết nhật ký trước...";
        }

        this.displayMessage({
            role: 'ai', // Display as AI message
            content: welcomeText
        });
    }

    async handleSendMessage() {
        const userMessage = this.messageInput.value.trim();

        if (!userMessage || this.isProcessing) {
            return; // Ignore empty messages or if already processing
        }

        if (!this.hasEntries) {
            showNotification("Vui lòng tạo ít nhất một bài viết nhật ký trước khi bắt đầu chat.", true);
            return;
        }

        this.isProcessing = true;
        this.setLoadingState(true); // Show typing indicator, disable button

        // Display user message immediately
        this.displayMessage({
            role: 'user',
            content: userMessage
        });

        // Clear input and reset height
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        this.messageInput.focus(); // Keep focus on input

        try {
            const response = await apiService.sendChatMessage(userMessage);

            if (response && typeof response.reply === 'string') {
                this.displayMessage({
                    role: 'ai',
                    content: response.reply
                });
            } else {
                 console.error('Invalid response format from server:', response);
                throw new Error('Phản hồi không hợp lệ từ máy chủ.');
            }
        } catch (error) {
            console.error('Chat send/receive error:', error);
            let errorMessage = 'Đã xảy ra lỗi khi xử lý tin nhắn của bạn.';

            // Check for specific error messages passed from ApiService/Backend
             if (error.message) {
                 if (error.message.includes("Please write at least one journal entry")) {
                    errorMessage = error.message;
                    this.hasEntries = false; // Update state
                     this.messageInput.disabled = true;
                     this.sendButton.disabled = true;
                } else if (error.message.includes("AI service error:") || error.message.includes("AI Error:")) {
                     errorMessage = error.message; // Display specific AI error
                 } else if (error.message.includes("401") || error.message.includes("Authentication required")) {
                     errorMessage = "Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.";
                     // Optionally trigger redirect via auth service
                 } else if (error.message.includes("503") || error.message.includes("AI service unavailable") || error.message.includes("AI service failed to respond")) {
                      errorMessage = "Dịch vụ AI hiện không khả dụng. Vui lòng thử lại sau.";
                 } else if (error.message.includes("safety settings")) {
                      errorMessage = "Nội dung bị chặn bởi cài đặt an toàn.";
                 }
             }
            this.displayErrorMessage(errorMessage);
        } finally {
            this.isProcessing = false;
            this.setLoadingState(false); // Hide indicator, enable button
        }
    }

    displayMessage(messageData) { // messageData = { role: 'user'/'ai', content: '...' }
        const messageDiv = document.createElement('div');
        // Use role to determine class
        messageDiv.className = `message ${messageData.role}-message`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        try {
            // Use marked to render AI messages, treat user messages as plain text
            if (messageData.role === 'ai' && window.marked) {
                contentDiv.innerHTML = marked.parse(messageData.content);
            } else {
                 // For user messages or if marked fails, use textContent for safety
                 const p = document.createElement('p');
                 p.textContent = messageData.content;
                 contentDiv.appendChild(p);
                 // contentDiv.textContent = messageData.content; // Simpler, but doesn't create <p>
            }
        } catch (error) {
            console.error('Error parsing markdown:', error);
             // Fallback to plain text on error
            const p = document.createElement('p');
            p.textContent = messageData.content;
            contentDiv.appendChild(p);
            // contentDiv.textContent = messageData.content;
        }

        messageDiv.appendChild(contentDiv);
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    displayErrorMessage(messageText) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message error-message'; // Specific class for errors

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = `<p><i class="fas fa-exclamation-triangle"></i> ${messageText}</p>`; // Add icon

        errorDiv.appendChild(contentDiv);
        this.messagesContainer.appendChild(errorDiv);
        this.scrollToBottom();
    }

    setLoadingState(isLoading, isInitial = false) {
         if (isInitial) {
             // Handle initial page loading state differently if needed
              // e.g., show a full page spinner instead of typing indicator
              // For now, we use the same indicator but maybe hide input
              if (isLoading) {
                   this.messageInput.disabled = true;
                   this.sendButton.disabled = true;
                   // Maybe show a different loading message initially
                   // this.loadingIndicator.innerHTML = "<p>Đang khởi tạo chat...</p>";
                   this.loadingIndicator.style.display = 'flex'; // Use flex if styled that way
              } else {
                   // Enable input only if user has entries
                   this.messageInput.disabled = !this.hasEntries;
                   this.sendButton.disabled = !this.hasEntries;
                   this.loadingIndicator.style.display = 'none';
              }

         } else {
             // Handle loading state during message exchange
             if (isLoading) {
                 this.sendButton.disabled = true;
                 this.messageInput.disabled = true; // Disable input while AI replies
                 this.loadingIndicator.style.display = 'flex'; // Show typing indicator
             } else {
                 this.sendButton.disabled = false;
                 this.messageInput.disabled = false; // Re-enable input
                 this.loadingIndicator.style.display = 'none'; // Hide indicator
                 this.messageInput.focus(); // Refocus input after reply
             }
         }

    }

    scrollToBottom() {
        // Use smooth scroll for better UX
        this.messagesContainer.scrollTo({
            top: this.messagesContainer.scrollHeight,
            behavior: 'smooth'
        });
    }
}

// Export the class (though it's instantiated in chat.html's script tag)
export { ChatService };
// --- END OF FILE frontend/static/js/chat.js ---