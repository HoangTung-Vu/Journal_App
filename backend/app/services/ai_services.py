# --- START OF FILE backend/app/services/ai_services.py ---
import time
import asyncio
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from typing import List, Optional
from ..core.config import settings
from ..db import models
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class AIServiceError(Exception):
    """Base exception for AI service errors"""
    pass

class AIConfigError(AIServiceError):
    """Raised when there are configuration issues"""
    pass

class AIResponseError(AIServiceError):
    """Raised when there are issues with AI response"""
    pass

class AIService:
    def __init__(self):
        self._init_ai_service()

    def _init_ai_service(self):
        """Initialize the AI service with proper error handling"""
        api_key = settings.GEMINI

        if not api_key or api_key == "Gemini":
            logger.error("GEMINI API key not properly configured")
            raise AIConfigError("GEMINI API key not properly configured")

        try:
            genai.configure(api_key=api_key)
            logger.info("Successfully configured Gemini API")

            self.model = genai.GenerativeModel('gemini-1.5-pro')
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
            }
            logger.info("Successfully initialized Gemini model")
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {str(e)}")
            raise AIConfigError(f"Failed to initialize AI service: {str(e)}")

    def format_entries_for_context(self, entries: List[models.JournalEntry]) -> str:
        """Format journal entries into a string for AI context"""
        if not entries:
            return "No recent journal entries available for context."

        context_str = "Recent Journal Entries Context:\n"
        context_str += "=============================\n"

        # Sort entries by date, newest first
        sorted_entries = sorted(entries, key=lambda x: x.created_at, reverse=True)

        for entry in sorted_entries:
            entry_date = entry.created_at.strftime('%Y-%m-%d %H:%M')
            context_str += f"\n--- Entry from {entry_date} ---\n"
            context_str += f"Title: {entry.title}\n"
            content_preview = (entry.content[:300] + '...') if len(entry.content) > 300 else entry.content
            context_str += f"Content:\n{content_preview}\n"
            context_str += "-----------------------------\n"

        return context_str

    async def generate_ai_response(
        self,
        main_content: str,
        context_entries: List[models.JournalEntry],
        prompt_instruction: str = "Analyze the following content based on the provided context:"
    ) -> str:
        """
        Generate an AI response using context from journal entries.
        
        Args:
            main_content: The primary content to analyze
            context_entries: List of journal entries for context
            prompt_instruction: Instruction for the AI
            
        Returns:
            str: The AI-generated response
            
        Raises:
            AIResponseError: If there's an error generating the response
        """
        try:
            start_time = time.time()
            logger.info(
                f"Generating AI response for content length: {len(main_content)}, "
                f"with {len(context_entries)} context entries"
            )

            # Format context, excluding the most recent entry
            if context_entries:
                context_entries = context_entries[1:]  # Exclude the most recent entry
            context_str = self.format_entries_for_context(context_entries)

            # Construct prompt
            full_prompt = f"""{context_str}
=============================

{prompt_instruction}

--- Main Content Start ---
{main_content}
--- Main Content End ---

Please provide your response:
"""
            # Generate response
            response = self.model.generate_content(
                full_prompt,
                safety_settings=self.safety_settings
            )

            if not response or not response.text:
                logger.warning("Received empty response from AI model")
                raise AIResponseError("AI model returned an empty response")

            # Log success and timing
            elapsed_time = time.time() - start_time
            logger.info(f"Successfully generated AI response in {elapsed_time:.2f} seconds")

            return response.text

        except Exception as e:
            logger.error(f"Failed to generate AI response: {str(e)}")
            
            if "quota" in str(e).lower():
                raise AIResponseError("AI service quota exceeded. Please try again later.")
            elif "API key" in str(e):
                raise AIResponseError("AI service configuration error. Please contact support.")
            else:
                raise AIResponseError(f"Failed to generate AI response: {str(e)}")

# Create a singleton instance
ai_service = AIService()

# Export the generate_ai_response function for backward compatibility
async def generate_ai_response(*args, **kwargs):
    return await ai_service.generate_ai_response(*args, **kwargs)

# --- END OF FILE backend/app/services/ai_services.py ---