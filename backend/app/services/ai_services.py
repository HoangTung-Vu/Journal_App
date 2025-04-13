# --- START OF FILE backend/app/services/ai_services.py ---
import time
import asyncio
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, ContentDict, PartDict
from typing import List, Optional, Dict, Union
from ..core.config import settings
from ..db import models
import logging
from datetime import datetime
from sqlalchemy.orm import Session

# Set up logging
logger = logging.getLogger(__name__)

class AIServiceError(Exception):
    """Base exception for AI service errors"""
    pass

class AIConfigError(AIServiceError):
    """Raised when there are configuration issues"""
    pass

class AIResponseError(AIServiceError):
    """Raised when there are issues with AI response"""
    pass

class AIService:
    def __init__(self):
        self._init_ai_service()

    def _init_ai_service(self):
        """Initialize the AI service with proper error handling"""
        api_key = settings.GEMINI

        # Simple check if key looks like the placeholder
        if not api_key or api_key == "Gemini" or len(api_key) < 10:
            logger.error("GEMINI API key not properly configured or is placeholder")
            raise AIConfigError("GEMINI API key not configured. Please set it in .env")

        try:
            genai.configure(api_key=api_key)
            logger.info("Successfully configured Gemini API")

            # Define safety settings - BLOCK_NONE can be risky, consider stricter settings
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            # Choose the model - 1.5 Flash is faster and cheaper, Pro is more powerful
            self.model = genai.GenerativeModel(
                'gemini-1.5-flash',
                safety_settings=self.safety_settings
            )
            logger.info(f"Successfully initialized Gemini model: {self.model.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {str(e)}", exc_info=True)
            raise AIConfigError(f"Failed to initialize AI service: {str(e)}")

    def format_entries_for_context(self, entries: List[models.JournalEntry]) -> str:
        """Format journal entries into a string for AI context"""
        if not entries:
            return "No recent journal entries available for context."

        context_str = "Recent Journal Entries Context:\n"
        context_str += "=============================\n"

        # Sort entries by date, newest first (API should already do this, but good practice)
        sorted_entries = sorted(entries, key=lambda x: x.created_at, reverse=True)

        for entry in sorted_entries:
            entry_date = entry.created_at.strftime('%Y-%m-%d %H:%M')
            context_str += f"\n--- Entry from {entry_date} ---\n"
            context_str += f"Title: {entry.title}\n"
            # Limit context length per entry if needed
            content_preview = (entry.content[:500] + '...') if len(entry.content) > 500 else entry.content
            context_str += f"Content:\n{content_preview}\n"
            context_str += "-----------------------------\n"

        return context_str

    async def generate_ai_response(
        self,
        main_content: str,
        context_entries: List[models.JournalEntry],
        prompt_instruction: str = "Analyze the following content based on the provided context:"
    ) -> str:
        """
        Generate an AI response for a single journal entry analysis (existing functionality).
        """
        try:
            start_time = time.time()
            logger.info(
                f"Generating single AI analysis response for content length: {len(main_content)}, "
                f"with {len(context_entries)} context entries"
            )
            context_str = self.format_entries_for_context(context_entries)

            full_prompt = f"""{context_str}
=============================

{prompt_instruction}

--- Main Content Start ---
{main_content}
--- Main Content End ---

Please provide your analysis based *only* on the main content and the context provided:
"""
            # Use generate_content for single turn
            response = await self.model.generate_content_async(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=1500, # Adjust token limit as needed
                    temperature=0.7 # Lower temperature for more focused analysis
                )
                # Safety settings are applied at model level
            )

            if not response or not response.text:
                logger.warning("Received empty response from AI model for single analysis")
                raise AIResponseError("AI model returned an empty response")

            elapsed_time = time.time() - start_time
            logger.info(f"Successfully generated single AI analysis in {elapsed_time:.2f} seconds")
            return response.text

        except Exception as e:
            logger.error(f"Failed to generate single AI analysis: {str(e)}", exc_info=True)
            if "quota" in str(e).lower():
                raise AIResponseError("AI service quota exceeded. Please try again later.")
            elif "API key" in str(e):
                raise AIResponseError("AI service configuration error. Please contact support.")
            else:
                raise AIResponseError(f"Failed to generate AI analysis: {str(e)}")

class ChatService:
    """Service for handling continuous chat conversations with AI"""
    def __init__(self):
        self.ai_service = AIService()
        self.chat_history: List[ContentDict] = []
        self.is_initialized = False
        self._chat_session: Optional[genai.ChatSession] = None # Store the chat session
        self.system_instruction = """Bạn là một trợ lý AI tâm lý, thấu hiểu và đồng cảm.
Nhiệm vụ của bạn là trò chuyện với người dùng về những bài viết nhật ký gần đây của họ.
Sử dụng ngữ cảnh được cung cấp từ nhật ký để hiểu rõ hơn về tâm trạng và suy nghĩ của người dùng.
Hãy trả lời một cách nhẹ nhàng, gợi mở và khuyến khích người dùng chia sẻ thêm nếu họ muốn.
Nếu người dùng hỏi về những điều không liên quan đến nhật ký hoặc cảm xúc, hãy trả lời một cách tự nhiên nhưng cố gắng hướng cuộc trò chuyện quay lại chủ đề chính nếu phù hợp.
Luôn giữ thái độ tích cực và hỗ trợ."""

    def _format_history_for_api(self, entries: List[models.JournalEntry]) -> List[ContentDict]:
        """Formats entries into the initial history structure for the API."""
        context_str = self.ai_service.format_entries_for_context(entries)
        # Gemini API structure: list of {'role': 'user'/'model', 'parts': [{'text': '...'}]}
        history: List[ContentDict] = [
            {'role': 'user', 'parts': [{'text': f"Đây là ngữ cảnh từ các bài viết nhật ký gần đây của tôi:\n\n{context_str}\n\nHãy ghi nhớ ngữ cảnh này khi chúng ta trò chuyện nhé."}]},
            {'role': 'model', 'parts': [{'text': "Chào bạn, tôi đã đọc qua các bài viết gần đây của bạn. Tôi ở đây để lắng nghe và trò chuyện cùng bạn. Bạn muốn bắt đầu từ đâu?"}]}
        ]
        return history

    async def start_chat(self, context_entries: List[models.JournalEntry]):
        """Initialize the chat session with context."""
        if self.is_initialized:
            logger.info("Chat already initialized, skipping.")
            return

        if not context_entries:
             logger.warning("Attempted to start chat with no context entries.")
             raise ValueError("Cannot start chat without context entries.")

        logger.info(f"Starting new chat session with {len(context_entries)} context entries.")
        try:
            # Format context as the initial part of the history
            initial_history = self._format_history_for_api(context_entries)

            # Create the chat session using the model and initial history
            self._chat_session = self.ai_service.model.start_chat(
                history=initial_history,
                 # Add system instruction if the model/API version supports it well
                 # system_instruction=self.system_instruction # Check documentation for best practice
            )
            # Store the initial history we constructed
            self.chat_history = initial_history.copy() # Store the history locally too

            # Prepend system instruction to the first *user* message implicitly if not supported directly
            # (Handled within the structure now)

            self.is_initialized = True
            logger.info("Chat session successfully initialized.")

        except Exception as e:
            logger.error(f"Error initializing chat session: {str(e)}", exc_info=True)
            self.is_initialized = False
            self._chat_session = None
            self.chat_history = []
            raise AIResponseError(f"Failed to initialize chat session: {str(e)}")

    async def send_message(self, message: str) -> str:
        """Send a message to the ongoing chat session and get the AI response."""
        if not self.is_initialized or not self._chat_session:
            logger.error("Chat session not initialized before sending message.")
            raise AIResponseError("Chat session is not active. Please start a new session.")

        logger.info(f"Sending message to chat: '{message[:50]}...'")
        try:
            start_time = time.time()
            # Send message using the chat session
            # The session automatically manages history internally based on start_chat
            response = await self._chat_session.send_message_async(message)

            if not response or not response.text:
                logger.warning("Received empty response from AI chat model")
                # Don't add empty response to history? Or add a placeholder?
                # For now, raise error.
                raise AIResponseError("AI chat model returned an empty response")

            # Manually update local history *after* successful response
            # Gemini's ChatSession history updates internally, but we keep a local copy too
            self.chat_history.append({'role': 'user', 'parts': [{'text': message}]})
            self.chat_history.append({'role': 'model', 'parts': [{'text': response.text}]})

            elapsed_time = time.time() - start_time
            logger.info(f"Successfully received chat response in {elapsed_time:.2f} seconds")
            return response.text

        except Exception as e:
            logger.error(f"Error sending/receiving chat message: {str(e)}", exc_info=True)
            # Should we reset the session on error? Maybe not immediately.
            # Let the calling service decide if re-initialization is needed.
            if "quota" in str(e).lower():
                raise AIResponseError("AI service quota exceeded. Please try again later.")
            elif "API key" in str(e):
                raise AIResponseError("AI service configuration error. Please contact support.")
            elif "stopped due to safety" in str(e).lower():
                 logger.warning(f"Chat message blocked by safety settings: {e}")
                 raise AIResponseError("Your message or the AI's intended response was blocked due to safety settings.")
            else:
                raise AIResponseError(f"Failed to process chat message: {str(e)}")

    def get_current_history(self) -> List[ContentDict]:
         """Returns the current chat history."""
         # Return the history managed by the ChatSession if available and accurate,
         # otherwise return our local copy.
         # Note: Accessing _chat_session.history might be needed if local copy drifts.
         return self.chat_history


# Create singleton instance for single entry analysis (backward compatibility)
ai_service = AIService()

# Export the generate_ai_response function for backward compatibility
async def generate_ai_response(*args, **kwargs):
    # Ensure AIService is initialized before calling
    if not hasattr(ai_service, 'model'):
        raise AIConfigError("AIService not properly initialized for single analysis.")
    return await ai_service.generate_ai_response(*args, **kwargs)

# ChatService is NOT a singleton; it's created per user session by ContextService

# --- END OF FILE backend/app/services/ai_services.py ---