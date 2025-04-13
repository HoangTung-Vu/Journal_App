# --- START OF FILE backend/app/db/models.py ---
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # For server_default=func.now()

# Import Base from the database module using relative import
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    # is_active = Column(Boolean, default=True) # Optional: for disabling users
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to JournalEntry: one user has many entries
    # cascade="all, delete-orphan": if user is deleted, their entries are also deleted.
    entries = relationship("JournalEntry", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationship to User: many entries belong to one user
    owner = relationship("User", back_populates="entries")

    def __repr__(self):
        return f"<JournalEntry(id={self.id}, title='{self.title}', owner_id={self.owner_id})>"
# --- END OF FILE backend/app/db/models.py ---