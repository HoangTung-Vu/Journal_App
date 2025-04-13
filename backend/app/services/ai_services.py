# --- START OF FILE backend/app/services/ai_services.py ---
import time
import asyncio
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, ContentDict, PartDict
from typing import List, Optional, Dict, Union
from ..core.config import settings
from ..db import models # Keep this if needed by format_entries_for_context
import logging
from datetime import datetime
# Removed Session import as it's not directly used here

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

# --- AIService Class (Mostly Unchanged) ---
class AIService:
    def __init__(self):
        self._init_ai_service()

    def _init_ai_service(self):
        """Initialize the AI service with proper error handling"""
        api_key = settings.GEMINI
        if not api_key or api_key == "Gemini" or len(api_key) < 10:
            logger.error("GEMINI API key not properly configured or is placeholder")
            raise AIConfigError("GEMINI API key not configured. Please set it in .env")
        try:
            genai.configure(api_key=api_key)
            logger.info("Successfully configured Gemini API")
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            self.model = genai.GenerativeModel(
                'gemini-1.5-flash', # Using flash as requested implicitly
                safety_settings=self.safety_settings
                 # Add system instruction during model init if supported and desired globally
                 # system_instruction="General assistant instruction if needed"
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
        sorted_entries = sorted(entries, key=lambda x: x.created_at, reverse=True)

        for entry in sorted_entries:
            entry_date = entry.created_at.strftime('%Y-%m-%d %H:%M')
            context_str += f"\n--- Entry from {entry_date} (ID: {entry.id}) ---\n" # Added ID for clarity
            context_str += f"Title: {entry.title}\n"
            content_preview = (entry.content[:500] + '...') if len(entry.content) > 500 else entry.content
            context_str += f"Content:\n{content_preview}\n"
            context_str += "-----------------------------\n"

        return context_str

    # --- generate_ai_response for single analysis (Unchanged) ---
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
            response = await self.model.generate_content_async(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=1500,
                    temperature=0.7
                )
            )

            # Check for blocked response *before* accessing text
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                reason = response.prompt_feedback.block_reason.name
                logger.warning(f"Single analysis prompt blocked due to: {reason}")
                raise AIResponseError(f"Request blocked by safety settings: {reason}")
            # Check candidates after checking prompt feedback
            if not response.candidates or not response.candidates[0].content.parts:
                 # Check if finished due to safety
                 finish_reason = response.candidates[0].finish_reason.name if response.candidates else 'UNKNOWN'
                 if finish_reason == 'SAFETY':
                      logger.warning("Single analysis response blocked by safety settings.")
                      raise AIResponseError("Response blocked by safety settings.")
                 else:
                      logger.warning("Received empty or incomplete response from AI model for single analysis. Finish reason: %s", finish_reason)
                      raise AIResponseError(f"AI model returned an incomplete response (Reason: {finish_reason}).")

            # If checks pass, access text
            response_text = response.text # .text usually concatenates parts

            elapsed_time = time.time() - start_time
            logger.info(f"Successfully generated single AI analysis in {elapsed_time:.2f} seconds")
            return response_text

        except Exception as e:
             # Catch specific exceptions if possible, otherwise re-raise generic
            logger.error(f"Failed to generate single AI analysis: {str(e)}", exc_info=True)
            if isinstance(e, AIResponseError): # Re-raise specific AI errors
                 raise
            elif "quota" in str(e).lower():
                raise AIResponseError("AI service quota exceeded. Please try again later.")
            elif "API key" in str(e):
                raise AIResponseError("AI service configuration error. Please contact support.")
            else:
                raise AIResponseError(f"Failed to generate AI analysis: {str(e)}")


# --- ChatService Class ---
class ChatService:
    """Service for handling continuous chat conversations with AI"""
    def __init__(self):
        # Get the already initialized AI service (model, config)
        self.ai_service = AIService() # Instantiate AIService to get configured model
        self.chat_history: List[ContentDict] = []
        self.is_initialized = False
        self._chat_session: Optional[genai.ChatSession] = None # Store the actual chat session
        self.system_instruction = """Bạn là một trợ lý AI tâm lý, thấu hiểu và đồng cảm.
Nhiệm vụ của bạn là trò chuyện với người dùng về những bài viết nhật ký gần đây của họ.
Sử dụng ngữ cảnh được cung cấp từ nhật ký để hiểu rõ hơn về tâm trạng và suy nghĩ của người dùng.
Hãy trả lời một cách nhẹ nhàng thoải mái, sử dụng những biểu tưởng cảm xúc cho sinh động, gợi mở và khuyến khích người dùng chia sẻ thêm nếu họ muốn.
Nếu người dùng hỏi về những điều không liên quan đến nhật ký hoặc cảm xúc, hãy trả lời một cách tự nhiên nhưng cố gắng hướng cuộc trò chuyện quay lại chủ đề chính nếu phù hợp.
Luôn giữ thái độ tích cực và hỗ trợ."""

    def _format_history_for_api(self, entries: List[models.JournalEntry]) -> List[ContentDict]:
        """Formats entries and initial prompt into the history structure for genai.ChatSession."""
        context_str = self.ai_service.format_entries_for_context(entries)
        # Combine system instruction and context into the first user message for simplicity
        initial_user_message = f"""{self.system_instruction}

Đây là ngữ cảnh từ các bài viết nhật ký gần đây của tôi để bạn tham khảo:
--- START CONTEXT ---
{context_str}
--- END CONTEXT ---

Bây giờ, hãy bắt đầu trò chuyện. Tôi sẽ là người bắt đầu."""

        # Initial history for the ChatSession object
        history: List[ContentDict] = [
            {'role': 'user', 'parts': [PartDict(text=initial_user_message)]},
            # The model's first reply sets the tone
            {'role': 'model', 'parts': [PartDict(text="Chào bạn, tôi đã đọc qua ngữ cảnh bạn cung cấp từ nhật ký. Tôi rất sẵn lòng lắng nghe và trò chuyện về bất cứ điều gì bạn đang suy nghĩ hoặc cảm thấy. Bạn muốn bắt đầu như thế nào?")]}
        ]
        return history

    async def start_chat(self, context_entries: List[models.JournalEntry]):
        """Initialize the genai.ChatSession with context."""
        if self.is_initialized:
            logger.warning("ChatService.start_chat called but already initialized.")
            return

        if not context_entries:
             logger.error("Attempted to start chat with no context entries.")
             # This should ideally be caught before calling start_chat
             raise ValueError("Cannot start chat without context entries.")

        logger.info(f"Initializing ChatService session with {len(context_entries)} context entries.")
        try:
            initial_history = self._format_history_for_api(context_entries)
            self.chat_history = initial_history.copy() # Store local copy

            # Start the actual chat session with the correctly formatted history
            self._chat_session = self.ai_service.model.start_chat(
                history=self.chat_history # Pass the prepared history
            )

            self.is_initialized = True
            logger.info("ChatService session successfully initialized.")

        except Exception as e:
            logger.error(f"Error initializing chat session in ChatService: {str(e)}", exc_info=True)
            self.is_initialized = False
            self._chat_session = None
            self.chat_history = [] # Clear history on failure
            # Raise a more specific error if possible
            if "API key" in str(e):
                 raise AIConfigError("Failed to initialize chat session due to API key issue.")
            else:
                 raise AIResponseError(f"Failed to initialize chat session: {str(e)}")

    async def send_message(self, message: str) -> str:
        """Send a message to the ongoing chat session and get the AI response."""
        if not self.is_initialized or not self._chat_session:
            logger.error("ChatService.send_message called but session not initialized.")
            # ContextService should ideally reset the service state if this happens unexpectedly
            raise AIResponseError("Chat session is not active. Please try again.")

        logger.debug(f"Sending message to chat session: '{message[:50]}...'")
        try:
            start_time = time.time()
            # Use the existing ChatSession object to send the message
            response = await self._chat_session.send_message_async(
                message,
                 generation_config=genai.types.GenerationConfig(
                    # candidate_count=1, # Often default
                    max_output_tokens=1000, # Optional: Limit response length
                    temperature=1.5 # Adjust temperature for conversational tone
                )
            )

            # IMPORTANT: Check for blocked responses *before* accessing response.text
            # Check prompt feedback first
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                reason = response.prompt_feedback.block_reason.name
                logger.warning(f"Chat prompt blocked due to: {reason}. Message: '{message[:50]}...'")
                raise AIResponseError(f"Your message was blocked by safety settings: {reason}")

            # Check candidate feedback if prompt was okay
            # Accessing _chat_session.history might be needed if internal state isn't immediately reflected
            # For simplicity, let's rely on the response object first
            if not response.candidates or not response.candidates[0].content.parts:
                 finish_reason = response.candidates[0].finish_reason.name if response.candidates else 'UNKNOWN'
                 if finish_reason == 'SAFETY':
                      logger.warning("Chat response blocked by safety settings.")
                      raise AIResponseError("The AI's response was blocked by safety settings.")
                 else:
                      logger.warning("Received empty or incomplete response from AI chat model. Finish reason: %s", finish_reason)
                      raise AIResponseError(f"AI model returned an incomplete response (Reason: {finish_reason}).")

            # If checks pass, get the text
            response_text = response.text # .text should combine parts

            # Update local history *after* successful response
            # Note: _chat_session.history updates internally. This is a backup/local view.
            self.chat_history.append({'role': 'user', 'parts': [PartDict(text=message)]})
            self.chat_history.append({'role': 'model', 'parts': [PartDict(text=response_text)]})

            elapsed_time = time.time() - start_time
            logger.info(f"Successfully received chat response in {elapsed_time:.2f} seconds")
            return response_text

        except Exception as e:
            logger.error(f"Error sending/receiving chat message: {str(e)}", exc_info=True)
            # Re-raise specific errors if caught, otherwise wrap general exceptions
            if isinstance(e, AIResponseError):
                 raise
            elif "quota" in str(e).lower():
                raise AIResponseError("AI service quota exceeded. Please try again later.")
            elif "API key" in str(e):
                raise AIConfigError("AI service configuration error.") # Config error more likely here
            else:
                # General failure during send/receive
                raise AIResponseError(f"Failed to process chat message: {str(e)}")

    def get_current_history(self) -> List[ContentDict]:
         """Returns the current chat history maintained locally."""
         # Consider returning self._chat_session.history if available and reliable
         return self.chat_history


# --- Global instance for single analysis (Backward Compatibility) ---
# It's better practice to inject dependencies, but keeping this for now
try:
    ai_service = AIService()
    # Export the generate_ai_response function linked to this instance
    async def generate_ai_response(*args, **kwargs):
        return await ai_service.generate_ai_response(*args, **kwargs)
except AIConfigError as e:
     logger.critical(f"CRITICAL: Failed to initialize global AIService: {e}. Single analysis will fail.")
     # Define a dummy function to avoid NameError later, but it will raise
     async def generate_ai_response(*args, **kwargs):
          raise AIConfigError("Global AIService failed to initialize.")


# ChatService is NOT a singleton; it's created per user session by ContextService

# --- END OF FILE backend/app/services/ai_services.py ---