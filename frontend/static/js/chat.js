// Chat Interface Management
import { apiService } from './api.js';
import { showNotification } from './utils.js'; // Optional for general notifications
import { marked } from 'marked';

class ChatService {
    constructor() {
        this.chatContainer = document.getElementById('chat-container');
        this.messagesContainer = document.getElementById('chat-messages');
        this.inputArea = document.getElementById('chat-input-area');
        this.messageInput = document.getElementById('chat-input');
        this.sendButton = document.getElementById('send-chat-btn');
        this.loadingIndicator = document.getElementById('chat-loading');
        this.typingIndicator = null;
        this.debugMode = true; // Enable debug mode

        if (!this.chatContainer || !this.messagesContainer || !this.messageInput || !this.sendButton) {
            this.debugLog("Error: Chat UI elements not found:", {
                container: !!this.chatContainer,
                messages: !!this.messagesContainer,
                input: !!this.messageInput,
                button: !!this.sendButton
            });
            return;
        }

        // Configure marked options for markdown rendering
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: false,
            mangle: false
        });
    }

    debugLog(...args) {
        if (this.debugMode) {
            console.log('[ChatDebug]', new Date().toISOString(), ...args);
        }
    }

    init() {
        if (!this.messageInput || !this.sendButton) {
            this.debugLog("Error: Cannot initialize chat - missing required elements");
            return;
        }

        // Bind event listeners
        this.sendButton.addEventListener('click', () => this.handleSendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSendMessage();
            }
        });

        this.messageInput.addEventListener('input', () => this.autoResizeInput());
        
        this.autoResizeInput();
        this.scrollToBottom();
        this.debugLog("Chat service initialized successfully");
    }

    autoResizeInput() {
        if (!this.messageInput) return;
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 150) + 'px';
    }

    scrollToBottom() {
        if (this.messagesContainer) {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }
    }

    async handleSendMessage() {
        if (!this.messageInput) return;
        
        const messageText = this.messageInput.value.trim();
        if (!messageText) return;

        this.debugLog("=== New Chat Message ===");
        this.debugLog("User Message:", messageText);
        console.log("\n=== CHAT DEBUG ===");
        console.log("User:", messageText);

        this.setLoading(true);
        this.displayMessage(messageText, 'user');
        this.messageInput.value = '';
        this.autoResizeInput();
        this.scrollToBottom();

        try {
            this.debugLog("Sending request to API...");
            const response = await apiService.sendChatMessage(messageText);
            this.debugLog("Received API response:", response);
            console.log("AI:", response.reply);
            console.log("================\n");

            if (response && response.reply) {
                this.displayMessage(response.reply, 'ai');
                this.scrollToBottom();
            } else {
                throw new Error("Không nhận được phản hồi từ AI.");
            }
        } catch (error) {
            this.debugLog("Error in chat:", error);
            console.error("Chat error:", error);
            
            let errorMessage = "Lỗi khi gửi tin nhắn: ";
            if (error.message.includes("No journal entries found")) {
                errorMessage += "Không tìm thấy bài viết nào để làm ngữ cảnh. Vui lòng tạo ít nhất một bài viết trước khi chat.";
            } else if (error.message.includes("AI service")) {
                errorMessage += "Dịch vụ AI hiện không khả dụng. Vui lòng thử lại sau.";
            } else {
                errorMessage += error.message;
            }
            
            this.displayMessage(errorMessage, 'error');
            showNotification(errorMessage, true);
            console.log("Error:", errorMessage);
            console.log("================\n");
        } finally {
            this.setLoading(false);
            this.messageInput.focus();
        }
    }

    setLoading(isLoading) {
        if (this.messageInput) this.messageInput.disabled = isLoading;
        if (this.sendButton) this.sendButton.disabled = isLoading;
        if (this.loadingIndicator) {
            this.loadingIndicator.classList.toggle('hidden', !isLoading);
        }
        if (this.inputArea) {
            this.inputArea.style.opacity = isLoading ? 0.7 : 1;
        }
        this.debugLog("Loading state:", isLoading);
    }

    displayMessage(text, type = 'ai') {
        if (!this.messagesContainer) return;

        const messageElement = document.createElement('div');
        messageElement.classList.add('message', type);

        if (type === 'ai') {
            messageElement.innerHTML = marked.parse(text);
        } else {
            messageElement.textContent = text;
        }

        this.messagesContainer.appendChild(messageElement);
        this.scrollToBottom();
        this.debugLog(`Displayed ${type} message:`, text);
        return messageElement;
    }

    showTypingIndicator() {
        if (this.typingIndicator) return; // Already showing
        this.typingIndicator = this.displayMessage('AI is typing...', 'typing');
    }

    removeTypingIndicator() {
        if (this.typingIndicator) {
            this.typingIndicator.remove();
            this.typingIndicator = null;
        }
    }
}

export { ChatService };