# --- START OF FILE backend/app/routers/journal.py ---
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

# Use relative imports
from .. import crud, schemas
from ..db import models
from ..core.security import get_current_active_user, DbSession, CurrentUser
from ..services.context_service import ContextService

router = APIRouter(
    prefix="/api/v1/journal",
    tags=["Journal"],
    dependencies=[Depends(get_current_active_user)],
    responses={
        404: {"description": "Journal entry not found"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden (Operation not allowed)"},
    },
)

@router.post("/", response_model=schemas.JournalEntry, status_code=status.HTTP_201_CREATED)
async def create_journal_entry(
    journal: schemas.JournalEntryCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Create a new journal entry for the current user.
    """
    return crud.create_journal(db=db, journal=journal, user_id=current_user.id)

@router.get("/", response_model=List[schemas.JournalEntry])
async def read_journal_entries(
    db: DbSession,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """
    Get a list of journal entries for the current user.
    """
    journals = crud.get_journals(db, user_id=current_user.id, skip=skip, limit=limit)
    return journals

@router.get("/{journal_id}", response_model=schemas.JournalEntry)
async def read_journal_entry(
    journal_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get a specific journal entry by ID, only if it belongs to the current user.
    """
    db_journal = crud.get_journal(db, journal_id=journal_id, user_id=current_user.id)
    if db_journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    return db_journal

@router.put("/{journal_id}", response_model=schemas.JournalEntry)
async def update_journal_entry(
    journal_id: int,
    journal_update: schemas.JournalEntryUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Update a journal entry by ID, only if it belongs to the current user.
    """
    updated_journal = crud.update_journal(db=db, journal_id=journal_id, journal_update=journal_update, user_id=current_user.id)
    if updated_journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    return updated_journal

@router.delete("/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry(
    journal_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Delete a journal entry by ID, only if it belongs to the current user.
    Returns 204 No Content on success.
    """
    deleted_journal = crud.delete_journal(db=db, journal_id=journal_id, user_id=current_user.id)
    if deleted_journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    return None

@router.post("/{journal_id}/consult", response_model=schemas.AIConsultationResponse)
async def get_ai_journal_consultation(
    journal_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get AI consultation/analysis for a specific journal entry,
    using 5 recent entries as context.
    """
    try:
        context_service = ContextService(db)
        consultation_text = await context_service.get_ai_consultation(
            entry_id=journal_id,
            user_id=current_user.id
        )
        return schemas.AIConsultationResponse(
            entry_id=journal_id,
            consultation=consultation_text
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to get AI consultation: {str(e)}"
            )
# --- END OF FILE backend/app/routers/journal.py ---