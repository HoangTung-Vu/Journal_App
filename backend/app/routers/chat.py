# --- START OF FILE backend/app/routers/chat.py ---
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Use relative imports
from .. import schemas
from ..core.security import get_current_active_user, DbSession, CurrentUser
from ..services.context_service import ContextService
# Import specific exceptions if needed for handling
from ..services.ai_services import AIResponseError, AIConfigError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat"],
    dependencies=[Depends(get_current_active_user)], # Require login for all chat routes
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found (e.g., no context entries)"},
        500: {"description": "Internal Server Error"},
        503: {"description": "AI Service Unavailable or Error"},
    },
)

@router.post("/", response_model=schemas.ChatResponse)
async def handle_chat_message(
    chat_request: schemas.ChatRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Handle a chat message from the user. Initializes chat context
    from the user's 5 most recent journal entries if not already done
    in the current session for this user.
    """
    context_service = ContextService(db)
    try:
        logger.info(f"Received chat message from user {current_user.id}")
        ai_reply = await context_service.process_chat_message(
            message=chat_request.message,
            user_id=current_user.id
        )
        logger.info(f"Sending reply to user {current_user.id}")
        return schemas.ChatResponse(reply=ai_reply)

    except ValueError as e:
        # Handle cases like "Cannot start chat without journal entries."
        logger.warning(f"ValueError in chat for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AIConfigError as e:
         logger.error(f"AI Config Error in chat for user {current_user.id}: {str(e)}")
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service configuration error.")
    except AIResponseError as e:
         logger.error(f"AI Response Error in chat for user {current_user.id}: {str(e)}")
         # Pass specific AI error message if safe, otherwise generic
         detail_msg = f"AI service error: {str(e)}" if "safety" in str(e).lower() or "quota" in str(e).lower() else "AI service failed to respond."
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail_msg)
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Unexpected error in chat endpoint for user {current_user.id}", exc_info=True) # Log full traceback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred.")

@router.get("/context", response_model=List[schemas.JournalEntry])
async def get_chat_context_display(
    db: DbSession,
    current_user: CurrentUser,
):
    """
    (Optional) Get the current context (5 most recent journal entries)
    being used for the chat session. Useful for debugging or display.
    """
    context_service = ContextService(db)
    try:
        context_entries = context_service.get_chat_context_for_display(current_user.id)
        return context_entries
    except ValueError as e:
         # Raised by get_chat_context_for_display if no entries found
        logger.warning(f"No chat context found for user {current_user.id} on explicit request.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Error fetching chat context display for user {current_user.id}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch chat context.")

# --- END OF FILE backend/app/routers/chat.py ---