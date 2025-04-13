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
        # Store chat services per user ID. Class variable for simplicity (consider better state management in production).
        if not hasattr(ContextService, '_chat_services'):
            ContextService._chat_services: Dict[int, ChatService] = {}
        self.context_limit = 10

    def _get_chat_service(self, user_id: int) -> ChatService:
        """Get or create a chat service instance for a user. Does NOT initialize the session."""
        if user_id not in ContextService._chat_services:
            logger.info(f"Creating NEW ChatService instance for user {user_id}")
            ContextService._chat_services[user_id] = ChatService()
        # else:
            # logger.debug(f"Reusing existing ChatService instance for user {user_id} (check initialization status)")
        return ContextService._chat_services[user_id]

    def _reset_chat_service(self, user_id: int):
        """Explicitly remove a user's chat service instance."""
        if user_id in ContextService._chat_services:
            logger.warning(f"Resetting (deleting) chat service instance for user {user_id}.")
            del ContextService._chat_services[user_id]

    def _get_context_entries(self, user_id: int, exclude_id: Optional[int] = None) -> List[models.JournalEntry]:
        """Fetches the 5 most recent journal entries for chat context."""
        try:
            return crud.get_journals(
                db=self.db,
                user_id=user_id,
                skip=0,
                limit=self.context_limit
            )
        except Exception as e:
            logger.error(f"Error fetching context entries for user {user_id}: {str(e)}", exc_info=True)
            return []

    def _get_consultation_context(self, user_id: int, target_entry_id: int) -> List[models.JournalEntry]:
        """Fetches the 5 journal entries immediately before the target entry for AI consultation."""
        try:
            entries = crud.get_recent_entries_before(
                db=self.db,
                user_id=user_id,
                target_entry_id=target_entry_id,
                limit=self.context_limit
            )
            if not entries:
                logger.warning(f"No entries found before target entry {target_entry_id} for user {user_id}")
                return []
            return entries
        except Exception as e:
            logger.error(f"Error fetching consultation context for user {user_id}: {str(e)}", exc_info=True)
            return []

    async def prepare_new_chat_session(self, user_id: int) -> List[models.JournalEntry]:
        """
        Resets the user's chat service and initializes a new session with the latest context.
        Called when the user enters the chat page (via /context endpoint).
        Returns the context entries used or empty list if no entries found.
        """
        logger.info(f"Preparing NEW chat session for user {user_id}.")

        try:
            # 1. Reset any existing service instance for the user first
            self._reset_chat_service(user_id)

            # 2. Fetch latest context
            context_entries = self._get_context_entries(user_id)

            # 3. Get a fresh ChatService instance
            chat_service = self._get_chat_service(user_id)

            # 4. Initialize the new session on the fresh instance
            try:
                await chat_service.start_chat(context_entries)
                logger.info(f"Successfully initialized new chat session for user {user_id} with {len(context_entries)} entries.")
                return context_entries # Return the entries used for context
            except (ValueError, AIConfigError, AIResponseError) as e:
                logger.error(f"Failed to initialize new chat session for user {user_id}: {e}", exc_info=True)
                # Ensure the failed service instance is cleaned up
                self._reset_chat_service(user_id)
                # Re-raise a user-friendly error or the original error
                raise ValueError(f"Failed to start chat session: {str(e)}") # Use ValueError to signal issue to router
            except Exception as e:
                logger.error(f"Unexpected error during chat session initialization for user {user_id}: {e}", exc_info=True)
                self._reset_chat_service(user_id)
                raise ValueError("An unexpected error occurred while preparing the chat session.")
        except Exception as e:
            logger.error(f"Critical error in prepare_new_chat_session for user {user_id}: {e}", exc_info=True)
            raise Exception(f"Failed to prepare chat session: {str(e)}")

    async def process_chat_message(self, message: str, user_id: int) -> str:
        """
        Process a chat message using the user's CURRENT chat session.
        Assumes the session was prepared by `prepare_new_chat_session` via the /context endpoint.
        Includes a fallback initialization check just in case.
        """
        chat_service = self._get_chat_service(user_id)

        # --- Fallback Initialization Check ---
        # Ideally, `prepare_new_chat_session` should have been called successfully via `/context`
        # before the user could send a message. This handles edge cases or direct API calls.
        if not chat_service.is_initialized:
            logger.warning(f"Chat session for user {user_id} was NOT initialized when process_chat_message was called. Attempting fallback initialization.")
            try:
                # Attempt to initialize here (less ideal as it might use slightly stale context if called directly)
                context_entries = self._get_context_entries(user_id)
                await chat_service.start_chat(context_entries)
                logger.info(f"Fallback chat session initialization successful for user {user_id}.")
            except (ValueError, AIConfigError, AIResponseError) as e:
                logger.error(f"Fallback chat initialization FAILED for user {user_id}: {e}")
                self._reset_chat_service(user_id) # Clean up failed instance
                raise AIResponseError(f"Failed to initialize chat during fallback: {e}") # Let router return 503

        # --- Send Message to Initialized Session ---
        try:
            response = await chat_service.send_message(message)
            return response
        except (AIResponseError, AIConfigError) as e: # Catch specific errors from send_message
            logger.error(f"Chat send/receive error for user {user_id}: {type(e).__name__} - {str(e)}")
            # Don't necessarily reset the service here unless the error indicates a fatal session issue
            # Re-raise the specific error for the router to handle
            raise
        except Exception as e:
             logger.error(f"Unexpected error processing chat for user {user_id}: {str(e)}", exc_info=True)
             # Consider resetting on truly unexpected errors
             # self._reset_chat_service(user_id)
             raise Exception("An unexpected error occurred while processing your message.")


    async def get_ai_consultation(self, entry_id: int, user_id: int) -> str:
        """
        Get AI consultation for a specific journal entry.
        Uses the separate `generate_ai_response` function, not the user's chat session.
        """
        logger.debug(f"Starting single AI consultation for entry {entry_id}, user {user_id}")
        try:
            target_entry = crud.get_journal(self.db, entry_id, user_id)
            if not target_entry:
                raise ValueError("Journal entry not found or does not belong to user.")

            # Get the 5 entries before the target entry
            context_entries = self._get_consultation_context(user_id, entry_id)

            # Use the global 'generate_ai_response' for single analysis
            response = await generate_ai_response(
                main_content=target_entry.content,
                context_entries=context_entries,
                prompt_instruction=(
                    f"Bạn là một chuyên gia tham vấn tâm lý đầy thấu cảm và ấm áp. Hãy lắng nghe và tham vấn cho người viết dựa trên đoạn nhật ký này.\n\n"
                    f"Đừng phân tích hay đánh giá. Thay vào đó, hãy:\n"
                    f"1. Thấu hiểu và phản ánh cảm xúc của họ\n"
                    f"2. Đồng cảm với trải nghiệm của họ\n"
                    f"3. Đưa ra những gợi ý nhẹ nhàng nếu phù hợp\n\n"
                    f"4. Hãy viết chat với phong thái nhẹ nhàng như một người bạn, thêm các biểu tượng cảm xúc đáng yêu thoải mái vào\n"
                    f"5. Nói chuyện tự nhiên vào, không chào hỏi, mình đã đọc được blah blah\n"
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
            raise AIServiceError(f"Failed to get AI consultation due to AI service issue: {str(e)}") # Use base AI error
        except Exception as e:
            logger.error(f"Unexpected error getting AI consultation for entry {entry_id}, user {user_id}: {str(e)}", exc_info=True)
            raise Exception("An unexpected error occurred while getting the AI consultation.")

    def get_chat_context_for_display(self, user_id: int) -> List[models.JournalEntry]:
        """
        DEPRECATED for triggering init. Use prepare_new_chat_session.
        This method *only* fetches entries for display/checking *without* resetting the session.
        Kept for potential future use cases or if frontend needs just the list without triggering reset.
        """
        logger.debug(f"Fetching chat context for DISPLAY ONLY for user {user_id}")
        entries = self._get_context_entries(user_id)
        if not entries:
             logger.warning(f"No journal entries found for context display for user {user_id}")
             raise ValueError("No journal entries found. Please write an entry to start chatting.")
        return entries

# --- END OF FILE backend/app/services/context_service.py ---