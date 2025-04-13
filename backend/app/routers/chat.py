# --- START OF FILE backend/app/routers/chat.py ---
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import schemas
from ..core.security import get_current_active_user, DbSession, CurrentUser
from ..services.chat_service import ChatService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat"],
    dependencies=[Depends(get_current_active_user)],
    responses={
        401: {"description": "Unauthorized"},
        503: {"description": "AI Service Unavailable"},
    },
)

@router.post("/", response_model=schemas.ChatResponse)
async def handle_chat_message(
    chat_request: schemas.ChatRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Handle a chat message from the user and return AI's response.
    Uses context from the user's 5 most recent journal entries.
    """
    try:
        chat_service = ChatService(db)
        
        # Log the incoming request
        logger.info(f"Received chat message from user {current_user.id}")
        
        # Process the message and get response
        response = await chat_service.process_chat_message(
            message=chat_request.message,
            user_id=current_user.id
        )
        
        return schemas.ChatResponse(reply=response)

    except Exception as e:
        if "context" in str(e).lower():
            raise HTTPException(status_code=404, detail="No journal entries found for context")
        elif "ai" in str(e).lower():
            raise HTTPException(status_code=503, detail="AI service is currently unavailable")
        else:
            logger.error(f"Error in chat endpoint for user {current_user.id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/context", response_model=list[schemas.JournalEntry])
async def get_chat_context(
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get the current context being used for chat (5 most recent journal entries).
    This endpoint is useful for debugging and showing users what context is being used.
    """
    try:
        chat_service = ChatService(db)
        context_entries = chat_service.get_chat_context(current_user.id)
        return context_entries
    except Exception as e:
        if "context" in str(e).lower():
            raise HTTPException(status_code=404, detail="No journal entries found for context")
        else:
            logger.error(f"Error fetching chat context for user {current_user.id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
# --- END OF FILE backend/app/routers/chat.py ---