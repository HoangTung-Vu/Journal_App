# --- START OF FILE backend/app/services/ai_services.py ---
import time
import random
import asyncio # Import asyncio for async sleep
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from ..core.config import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)

api_key = settings.GEMINI

# Validate API key
if not api_key or api_key == "Gemini":
    logger.error("GEMINI API key not properly configured. Please set GEMINI environment variable.")
    raise ValueError("GEMINI API key not properly configured")

try:
    genai.configure(api_key=api_key)
    logger.info("Successfully configured Gemini API")
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {str(e)}")
    raise

safety_settings={
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT : HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT :  HarmBlockThreshold.BLOCK_NONE
}

try:
    model = genai.GenerativeModel('gemini-1.5-pro')
    logger.info("Successfully initialized Gemini model")
except Exception as e:
    logger.error(f"Failed to initialize Gemini model: {str(e)}")
    raise

async def get_ai_consultation(entry_content: str) -> str:
    """
    Get AI consultation for a journal entry using Gemini model.

    Args:
        entry_content: The text content of the journal entry.

    Returns:
        A string containing the AI-generated consultation/analysis.

    Raises:
        Exception: If the AI service fails to generate a response.
    """
    try:
        logger.info(f"AI Service: Received content for analysis (length: {len(entry_content)})")
        
        # Generate response from Gemini
        response = model.generate_content(
            entry_content,
            safety_settings=safety_settings
        )
        
        if not response or not response.text:
            raise ValueError("Empty response from Gemini model")
            
        # Add timestamp to response
        result = f"{response.text}\n\n(Phân tích bởi AI lúc: {time.strftime('%H:%M:%S')})"
        logger.info("AI Service: Analysis complete successfully")
        return result
        
    except Exception as e:
        logger.error(f"AI Service failed: {str(e)}")
        raise Exception(f"AI consultation failed: {str(e)}")
# --- END OF FILE backend/app/services/ai_services.py ---