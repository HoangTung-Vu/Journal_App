# backend/app/core/config.py
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env file from the backend directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret") # Provide a default for safety
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    GEMINI : str = os.getenv("GEMINI", "Gemini")

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        # case_sensitive = True # Uncomment if needed, default is case-insensitive

settings = Settings()

# Debug print to verify loading (remove in production)
# print(f"Loaded DATABASE_URL: {settings.DATABASE_URL}")
# print(f"Loaded SECRET_KEY: {'*' * len(settings.SECRET_KEY) if settings.SECRET_KEY else 'Not Set'}")