from typing import List, Optional
from sqlalchemy.orm import Session
from ..db import models
from ..crud import crud
from .ai_services import generate_ai_response
import logging

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, db: Session):
        self.db = db

    async def process_chat_message(self, message: str, user_id: int) -> str:
        """
        Process a chat message from a user and return AI's response.
        
        Args:
            message: The user's message
            user_id: The ID of the user sending the message
            
        Returns:
            str: The AI's response
            
        Raises:
            Exception: If there's an error processing the message
        """
        try:
            # Get the 5 most recent journal entries for context
            context_entries = crud.get_journals(
                db=self.db,
                user_id=user_id,
                skip=0,
                limit=5
            )
            
            # Log the context being used
            logger.info(
                f"Processing chat message for user {user_id} with {len(context_entries)} context entries"
            )

            if not context_entries:
                logger.warning(f"No journal entries found for user {user_id}")
                raise Exception("No journal entries found for context")

            # Generate AI response using the context
            try:
                response = await generate_ai_response(
                    main_content=message,
                    context_entries=context_entries,
                    prompt_instruction=(
                        "Based on the context from recent journal entries, "
                        "respond to the following user message in a helpful and conversational manner:"
                    )
                )
                return response
            except Exception as ai_error:
                logger.error(f"AI service error: {str(ai_error)}")
                raise Exception(f"AI service error: {str(ai_error)}")

        except Exception as e:
            logger.error(f"Error processing chat message for user {user_id}: {str(e)}")
            raise Exception(f"Failed to process chat message: {str(e)}")

    def get_chat_context(self, user_id: int) -> List[models.JournalEntry]:
        """
        Get the most recent journal entries to use as context for the chat.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List[models.JournalEntry]: List of recent journal entries
        """
        try:
            return crud.get_journals(
                db=self.db,
                user_id=user_id,
                skip=0,
                limit=5
            )
        except Exception as e:
            logger.error(f"Error fetching chat context for user {user_id}: {str(e)}")
            raise Exception(f"Failed to fetch chat context: {str(e)}") 