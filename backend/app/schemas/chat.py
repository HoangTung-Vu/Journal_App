from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message to the chat AI")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="AI's reply to the user's message") 