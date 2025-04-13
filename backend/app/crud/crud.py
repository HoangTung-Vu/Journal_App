# --- START OF FILE backend/app/crud/crud.py ---
from sqlalchemy.orm import Session
from typing import List, Optional

# Use relative imports
from ..db import models
from ..schemas import schemas
from ..core.hashing import get_password_hash

# --- User CRUD ---
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    """Lấy user bằng ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Lấy user bằng email."""
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Tạo user mới."""
    hashed_password = get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Journal Entry CRUD ---

def get_journal(db: Session, journal_id: int, user_id: int) -> Optional[models.JournalEntry]:
    """Lấy một journal entry cụ thể theo ID, chỉ khi nó thuộc về user_id."""
    return db.query(models.JournalEntry).filter(
        models.JournalEntry.id == journal_id,
        models.JournalEntry.owner_id == user_id
    ).first()

def get_journals(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.JournalEntry]:
    """Lấy danh sách journal entries của một user cụ thể."""
    return db.query(models.JournalEntry)\
             .filter(models.JournalEntry.owner_id == user_id)\
             .order_by(models.JournalEntry.created_at.desc())\
             .offset(skip)\
             .limit(limit)\
             .all()

def create_journal(db: Session, journal: schemas.JournalEntryCreate, user_id: int) -> models.JournalEntry:
    """Tạo một journal entry mới cho user_id."""
    db_journal = models.JournalEntry(**journal.model_dump(), owner_id=user_id)
    db.add(db_journal)
    db.commit()
    db.refresh(db_journal)
    return db_journal

def update_journal(db: Session, journal_id: int, journal_update: schemas.JournalEntryUpdate, user_id: int) -> Optional[models.JournalEntry]:
    """Cập nhật một journal entry nếu nó tồn tại và thuộc về user_id."""
    db_journal = get_journal(db=db, journal_id=journal_id, user_id=user_id)
    if db_journal:
        update_data = journal_update.model_dump(exclude_unset=True) # Chỉ cập nhật các trường được cung cấp
        for key, value in update_data.items():
            setattr(db_journal, key, value)
        db.commit()
        db.refresh(db_journal)
    return db_journal


def delete_journal(db: Session, journal_id: int, user_id: int) -> Optional[models.JournalEntry]:
    """Xóa một journal entry nếu nó tồn tại và thuộc về user_id."""
    db_journal = get_journal(db=db, journal_id=journal_id, user_id=user_id)
    if db_journal:
        db.delete(db_journal)
        db.commit()
    return db_journal # Trả về object đã xóa (hoặc None nếu không tìm thấy)
# --- END OF FILE backend/app/crud/crud.py ---