# --- START OF FILE backend/app/services/context_service.py ---

from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from ..db import models
from ..crud import crud
# Import ChatService specifically from ai_services
from .ai_services import ChatService, generate_ai_response, AIServiceError, AIConfigError, AIResponseError
import logging

logger = logging.getLogger(__name__)

class ContextService:
    def __init__(self, db: Session):
        self.db = db
        # Store chat services per user ID. Key: user_id (int), Value: ChatService instance
        # !!! This dictionary needs to be managed at a higher level (e.g., application state)
        # !!! or passed around carefully if ContextService is instantiated per request.
        # !!! For simplicity in this example, let's assume it's managed correctly,
        # !!! but in a real app, use FastAPI dependencies or a shared state mechanism.
        # !!! A simple global dict is often problematic in production.
        # <<< TEMPORARY SOLUTION: Using a class variable (less ideal but works for demo) >>>
        if not hasattr(ContextService, '_chat_services'):
             ContextService._chat_services: Dict[int, ChatService] = {}

        self.context_limit = 5 # Number of recent entries for context

    def _get_chat_service(self, user_id: int) -> ChatService:
        """Get or create a chat service instance for a user."""
        # Access the class variable
        if user_id not in ContextService._chat_services:
            logger.info(f"Creating new ChatService instance for user {user_id}")
            ContextService._chat_services[user_id] = ChatService()
        else:
            logger.debug(f"Reusing existing ChatService instance for user {user_id}")
        return ContextService._chat_services[user_id]

    def _reset_chat_service(self, user_id: int):
        """Explicitly remove a user's chat service instance."""
        if user_id in ContextService._chat_services:
            logger.warning(f"Resetting chat service for user {user_id}.")
            del ContextService._chat_services[user_id]

    def _get_context_entries(self, user_id: int, exclude_id: Optional[int] = None) -> List[models.JournalEntry]:
        """Fetches the most recent journal entries for context."""
        try:
            # Use limit from self.context_limit
            entries = crud.get_journals(
                db=self.db,
                user_id=user_id,
                skip=0,
                limit=self.context_limit
            )
            if exclude_id:
                entries = [e for e in entries if e.id != exclude_id]
            logger.debug(f"Fetched {len(entries)} context entries for user {user_id}.")
            return entries
        except Exception as e:
            logger.error(f"Error fetching context entries for user {user_id}: {str(e)}", exc_info=True)
            return []

    async def process_chat_message(self, message: str, user_id: int) -> str:
        """
        Process a chat message from a user, initializing chat if necessary,
        and return AI's response using the persistent chat session.
        """
        chat_service = self._get_chat_service(user_id)

        try:
            # Initialize chat service ONLY if not already initialized for this user's service instance
            if not chat_service.is_initialized:
                logger.info(f"Chat session not initialized for user {user_id}. Attempting initialization...")
                context_entries = self._get_context_entries(user_id)

                if not context_entries:
                    logger.warning(f"No journal entries found for context for user {user_id}. Cannot start chat.")
                    # Deny chat explicitly
                    raise ValueError("Please write at least one journal entry to start chatting.")

                # Attempt to initialize the chat session with context
                await chat_service.start_chat(context_entries)
                logger.info(f"Chat session initialized successfully for user {user_id}.")
            else:
                 logger.debug(f"Chat session already initialized for user {user_id}.")

            # Send the user's message to the initialized chat session
            response = await chat_service.send_message(message)
            return response

        except (ValueError, AIResponseError, AIConfigError) as e: # Catch specific errors
            logger.error(f"Chat processing error for user {user_id}: {type(e).__name__} - {str(e)}")
            # Reset chat service on specific errors to force re-initialization next time
            # Especially if the session is invalid or configuration is wrong.
            # ValueError("Please write...") doesn't require reset, others might.
            if not isinstance(e, ValueError) or "journal entry" not in str(e):
                 self._reset_chat_service(user_id)

            # Re-raise the error with a user-friendly message potentially
            if "Please write at least one journal entry" in str(e):
                 raise Exception("Please write at least one journal entry to start chatting.")
            elif isinstance(e, AIConfigError):
                 raise Exception("AI service configuration error. Please contact administrator.")
            elif isinstance(e, AIResponseError):
                 # Pass specific AI error message if safe (like safety or quota)
                 if "safety setting" in str(e).lower() or "quota" in str(e).lower():
                      raise Exception(f"AI Error: {str(e)}")
                 else:
                      raise Exception(f"AI service failed to respond properly.")
            else:
                 # Other ValueErrors from within ChatService
                 raise Exception(f"Failed to process chat message: {str(e)}")
        except Exception as e:
             logger.error(f"Unexpected error processing chat for user {user_id}: {str(e)}", exc_info=True)
             # Reset chat service on unexpected errors too
             self._reset_chat_service(user_id)
             raise Exception("An unexpected error occurred while processing your message.")

    async def get_ai_consultation(self, entry_id: int, user_id: int) -> str:
        """
        Get AI consultation for a specific journal entry (Existing Functionality - unchanged).
        This uses the separate `generate_ai_response` function, not the user's chat session.
        """
        logger.debug(f"Starting single AI consultation for entry {entry_id}, user {user_id}")
        try:
            target_entry = crud.get_journal(self.db, entry_id, user_id)
            if not target_entry:
                raise ValueError("Journal entry not found or does not belong to user.")

            context_entries = self._get_context_entries(user_id, exclude_id=entry_id)

            # Use the global 'generate_ai_response' for single analysis
            response = await generate_ai_response(
                main_content=target_entry.content,
                context_entries=context_entries,
                prompt_instruction=(
                    f"Bạn là một chuyên gia tham vấn tâm lý đầy thấu cảm và ấm áp. Hãy lắng nghe và tham vấn cho người viết dựa trên đoạn nhật ký này.\n\n"
                    f"Đừng phân tích hay đánh giá. Thay vào đó, hãy:\n"
                    f"1. Thấu hiểu và phản ánh cảm xúc của họ\n"
                    f"2. Đồng cảm với trải nghiệm của họ\n"
                    f"3. Đặt câu hỏi gợi mở để giúp họ tự khám phá bản thân\n"
                    f"4. Đưa ra những gợi ý nhẹ nhàng nếu phù hợp\n\n"
                    f"Dưới đây là đoạn nhật ký cần tham vấn (ID: {target_entry.id}, Tiêu đề: '{target_entry.title}').\n"
                    f"Bạn có thể tham khảo các entries gần đây để hiểu rõ hơn về bối cảnh của họ:"
                )
            )
            logger.debug(f"Finished single AI consultation for entry {entry_id}, user {user_id}")
            return response

        except ValueError as e:
             logger.warning(f"Value error getting AI consultation for entry {entry_id}, user {user_id}: {str(e)}")
             raise # Re-raise specific error like "not found"
        except (AIResponseError, AIConfigError) as e:
            logger.error(f"AI service error during consultation for entry {entry_id}, user {user_id}: {str(e)}")
            raise Exception(f"Failed to get AI consultation due to AI service issue: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting AI consultation for entry {entry_id}, user {user_id}: {str(e)}", exc_info=True)
            raise Exception("An unexpected error occurred while getting the AI consultation.")

    def get_chat_context_for_display(self, user_id: int) -> List[models.JournalEntry]:
        """
        Get the most recent journal entries potentially used as context (for display/check).
        """
        logger.debug(f"Fetching chat context for display for user {user_id}")
        entries = self._get_context_entries(user_id)
        if not entries:
             # Raise an error that the frontend can interpret as "no entries found"
             logger.warning(f"No journal entries found for context display for user {user_id}")
             raise ValueError("No journal entries found. Please write an entry to start chatting.")
        return entries

# --- END OF FILE backend/app/services/context_service.py ---