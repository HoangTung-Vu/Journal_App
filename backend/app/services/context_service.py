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
        self._chat_services: Dict[int, ChatService] = {}
        self.context_limit = 5 # Number of recent entries for context

    def _get_chat_service(self, user_id: int) -> ChatService:
        """Get or create a chat service instance for a user."""
        if user_id not in self._chat_services:
            logger.info(f"Creating new ChatService instance for user {user_id}")
            self._chat_services[user_id] = ChatService()
        return self._chat_services[user_id]

    def _get_context_entries(self, user_id: int, exclude_id: Optional[int] = None) -> List[models.JournalEntry]:
        """Fetches the most recent journal entries for context."""
        try:
            entries = crud.get_journals(
                db=self.db,
                user_id=user_id,
                skip=0,
                limit=self.context_limit
            )
            if exclude_id:
                entries = [e for e in entries if e.id != exclude_id]
            return entries
        except Exception as e:
            logger.error(f"Error fetching context entries for user {user_id}: {str(e)}", exc_info=True)
            # Don't raise here, let the caller handle lack of entries if critical
            return []

    async def process_chat_message(self, message: str, user_id: int) -> str:
        """
        Process a chat message from a user, initializing chat if necessary,
        and return AI's response.
        """
        chat_service = self._get_chat_service(user_id)

        try:
            # Initialize chat service if not already initialized for this session
            if not chat_service.is_initialized:
                logger.info(f"Chat session not initialized for user {user_id}. Initializing...")
                context_entries = self._get_context_entries(user_id)

                if not context_entries:
                    logger.warning(f"No journal entries found for context for user {user_id}")
                    # Option 1: Deny chat
                    raise ValueError("Cannot start chat without journal entries.")
                    # Option 2: Start chat without context (might require ChatService adjustment)
                    # await chat_service.start_chat([])
                    # raise ValueError("Started chat without context, functionality may be limited.")

                # Attempt to initialize the chat session with context
                await chat_service.start_chat(context_entries)
                logger.info(f"Chat session initialized successfully for user {user_id}.")

            # Send the user's message to the initialized chat session
            response = await chat_service.send_message(message)
            return response

        except (ValueError, AIResponseError, AIConfigError) as e: # Catch specific errors
            logger.error(f"Chat processing error for user {user_id}: {type(e).__name__} - {str(e)}")
            # Reset chat service on specific errors to force re-initialization next time?
            if isinstance(e, (AIConfigError, ValueError)) or "session is not active" in str(e).lower():
                 logger.warning(f"Resetting chat service for user {user_id} due to error.")
                 if user_id in self._chat_services:
                    del self._chat_services[user_id] # Remove instance to force recreation

            # Re-raise the error with a user-friendly message potentially
            if "Cannot start chat without journal entries" in str(e):
                 raise Exception("Please write at least one journal entry to start chatting.") # More specific
            elif isinstance(e, AIConfigError):
                 raise Exception("AI service configuration error. Please contact administrator.")
            elif isinstance(e, AIResponseError):
                 raise Exception(f"AI Error: {str(e)}") # Pass AI error message through
            else:
                 raise Exception(f"Failed to process chat message: {str(e)}") # Generic fallback
        except Exception as e:
             logger.error(f"Unexpected error processing chat for user {user_id}: {str(e)}", exc_info=True)
             # Reset chat service on unexpected errors too?
             if user_id in self._chat_services:
                 del self._chat_services[user_id]
             raise Exception("An unexpected error occurred while processing your message.")

    async def get_ai_consultation(self, entry_id: int, user_id: int) -> str:
        """
        Get AI consultation for a specific journal entry (Existing Functionality).
        """
        try:
            # Get the target entry
            target_entry = crud.get_journal(self.db, entry_id, user_id)
            if not target_entry:
                raise ValueError("Journal entry not found or does not belong to user.")

            # Get context entries (excluding the target entry)
            context_entries = self._get_context_entries(user_id, exclude_id=entry_id)

            # Use the global ai_service instance for single analysis
            # (Doesn't use the per-user ChatService)
            response = await generate_ai_response(
                main_content=target_entry.content,
                context_entries=context_entries,
                prompt_instruction=(
                    f"Based on the context from recent entries (if any), please analyze the following "
                    f"specific journal entry (ID: {target_entry.id}, Title: '{target_entry.title}'). "
                    f"Focus your analysis primarily on this specific entry, using the context for background understanding:"
                )
            )
            return response

        except ValueError as e:
             logger.warning(f"Value error getting AI consultation for entry {entry_id}, user {user_id}: {str(e)}")
             raise # Re-raise specific error
        except (AIResponseError, AIConfigError) as e:
            logger.error(f"AI service error during consultation for entry {entry_id}, user {user_id}: {str(e)}")
            raise Exception(f"Failed to get AI consultation due to AI service issue: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting AI consultation for entry {entry_id}, user {user_id}: {str(e)}", exc_info=True)
            raise Exception("An unexpected error occurred while getting the AI consultation.")

    def get_chat_context_for_display(self, user_id: int) -> List[models.JournalEntry]:
        """
        Get the most recent journal entries used as context (for display/debug).
        """
        entries = self._get_context_entries(user_id)
        if not entries:
             # Raise an error if the intention is that context *must* exist for this call
             raise ValueError("No journal entries found for context.")
        return entries

# --- END OF FILE backend/app/services/context_service.py ---