# --- START OF FILE backend/app/schemas/schemas.py ---
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class User(UserBase):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}

# --- Journal Entry Schemas ---
class JournalEntryBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)

class JournalEntryCreate(JournalEntryBase):
    pass

class JournalEntryUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)

class JournalEntry(JournalEntryBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

# --- AI Consultation Schemas ---
class AIConsultationResponse(BaseModel):
    entry_id: int
    consultation: str

# --- Chat Schemas ---
# Defined here for consistency, can be in schemas/chat.py and imported via __init__.py
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's message to the chat AI")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="AI's reply to the user's message")

# --- END OF FILE backend/app/schemas/schemas.py ---