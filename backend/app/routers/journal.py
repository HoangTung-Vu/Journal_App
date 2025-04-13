# --- START OF FILE backend/app/routers/journal.py ---
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

# Use relative imports
from .. import crud, schemas
from ..db import models
from ..core.security import get_current_active_user, DbSession, CurrentUser # Import dependency and types
from ..services import ai_services # Import the AI service

router = APIRouter(
    prefix="/api/v1/journal", # Consistent prefix
    tags=["Journal"],
    dependencies=[Depends(get_current_active_user)], # Require authentication for all journal routes
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
    Tạo một journal entry mới cho người dùng hiện tại.
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
    Lấy danh sách các journal entries của người dùng hiện tại.
    """
    # Fetch journals sorted descending by creation date (crud handles this)
    journals = crud.get_journals(db, user_id=current_user.id, skip=skip, limit=limit)
    return journals

@router.get("/{journal_id}", response_model=schemas.JournalEntry)
async def read_journal_entry(
    journal_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Lấy chi tiết một journal entry cụ thể theo ID, chỉ khi nó thuộc về người dùng hiện tại.
    """
    db_journal = crud.get_journal(db, journal_id=journal_id, user_id=current_user.id)
    if db_journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    return db_journal

@router.put("/{journal_id}", response_model=schemas.JournalEntry)
async def update_journal_entry(
    journal_id: int,
    journal_update: schemas.JournalEntryUpdate, # Use dedicated update schema
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Cập nhật một journal entry theo ID, chỉ khi nó thuộc về người dùng hiện tại.
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
    Xóa một journal entry theo ID, chỉ khi nó thuộc về người dùng hiện tại.
    Trả về 204 No Content nếu thành công.
    """
    deleted_journal = crud.delete_journal(db=db, journal_id=journal_id, user_id=current_user.id)
    if deleted_journal is None:
        # Even if not found, deleting a non-existent resource is often idempotent,
        # but we can choose to return 404 if preferred.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    # No response body needed for 204
    return None # Or: return Response(status_code=status.HTTP_204_NO_CONTENT)


# Endpoint for AI Consultation - Now uses context
@router.post("/{journal_id}/consult", response_model=schemas.AIConsultationResponse)
async def get_ai_journal_consultation(
    journal_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Nhận tư vấn/phân tích từ AI cho một journal entry cụ thể,
    sử dụng 5 entry gần nhất làm context.
    """
    db_journal = crud.get_journal(db, journal_id=journal_id, user_id=current_user.id)
    if db_journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")

    try:
        # Fetch recent entries for context (limit=5 gets the 5 most recent due to ordering in crud)
        # Exclude the current entry being analyzed from the context itself? Optional.
        # context_entries = crud.get_journals(db, user_id=current_user.id, skip=0, limit=6) # Fetch 6
        # context_entries = [e for e in context_entries if e.id != journal_id][:5] # Exclude current, take 5
        # Simpler: just fetch the 5 most recent, including the current one if it's recent.
        context_entries = crud.get_journals(db, user_id=current_user.id, skip=0, limit=5)

        # Call AI service with context
        consultation_text = await ai_services.generate_ai_response(
            main_content=db_journal.content,
            context_entries=context_entries,
            prompt_instruction=f"Based on the context from recent entries, please analyze the following journal entry (ID: {db_journal.id}, Title: '{db_journal.title}'):"
        )
        return schemas.AIConsultationResponse(
            entry_id=journal_id,
            consultation=consultation_text
        )
    except Exception as e:
        # Log the error here if needed
        print(f"Error getting AI consultation for entry {journal_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, # Use 503 for service failure
            detail=f"Failed to get AI consultation: {str(e)}"
        )
# --- END OF FILE backend/app/routers/journal.py ---