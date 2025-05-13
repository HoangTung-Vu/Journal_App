from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Use relative import for settings
from ..core.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Add explicit debug print to see what URL is being used
print(f"DEBUG: Attempting to connect with DATABASE_URL: {SQLALCHEMY_DATABASE_URL}")

# Check if DATABASE_URL is set
if not SQLALCHEMY_DATABASE_URL:
    print("Warning: DATABASE_URL not set. Using default SQLite database 'journal_app.db'.")
    SQLALCHEMY_DATABASE_URL = "sqlite:///./journal_app.db" # Default fallback

# Add connect_args for SQLite only if using SQLite
connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    print(f"Using SQLite database at: {SQLALCHEMY_DATABASE_URL}")
elif SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
     print(f"Connecting to PostgreSQL database...")
else:
     print(f"Connecting to database: {SQLALCHEMY_DATABASE_URL.split('@')[1] if '@' in SQLALCHEMY_DATABASE_URL else SQLALCHEMY_DATABASE_URL}") # Hide credentials


try:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args=connect_args # Pass connect_args here
        # echo=True # Uncomment for debugging SQL queries
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    print("Database engine created successfully.")
except Exception as e:
    print(f"Error creating database engine: {e}")
    print("Please check your DATABASE_URL in the .env file or environment variables.")
    raise

# Dependency to get DB session
def get_db():
    """Dependency function that yields a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create tables (call this once at startup if needed)
def init_db():
    """Initializes the database by creating tables."""
    try:
        # Check environment variable to optionally skip creation
        skip_table_creation = os.getenv("SKIP_DB_INIT", "false").lower() == "true"

        if skip_table_creation:
            print("Skipping database table creation (SKIP_DB_INIT=true).")
            return

        print("Attempting to create database tables...")
        # Import models here to ensure Base is populated before create_all
        from . import models # noqa
        Base.metadata.create_all(bind=engine)
        print("Database tables checked/created successfully.")
    except Exception as e:
        print(f"Error during database table creation: {e}")
        print("Ensure the database server is running and accessible.")
        print("For permissions issues, grant necessary privileges to the database user.")
        print("Or set SKIP_DB_INIT=true in your environment variables if tables already exist.")
        # Consider whether to raise the error or just log it
        # raise # Uncomment if startup should fail on DB error