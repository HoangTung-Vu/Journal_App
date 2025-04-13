# --- START OF FILE backend/app/main.py ---
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
from pathlib import Path

# Use relative imports for modules within the same package
from .db import database, models
from .routers import auth, journal, chat # Import the new chat router
from .core.config import settings # Import settings

# Create database tables on startup if DB initialization is enabled
# Consider doing this offline via Alembic migrations in a real application
print("Initializing database...")
database.init_db()
print("Database initialization complete.")


app = FastAPI(
    title="AI Journal App API",
    version="0.3.0", # Version bump
    description="API for a simple AI-powered journaling application with chat."
)

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:5500",  # Default port for Python's http.server or Live Server extension
    "http://localhost:3000",  # Common React/Vue port
    "http://127.0.0.1:5500",
    "http://127.0.0.1:3000",
    # Add the origin of your deployed frontend if applicable
    # "https://your-frontend-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all standard methods
    allow_headers=["*"], # Allows all headers
)

# --- API Routers ---
app.include_router(auth.router) # Includes prefix /api/v1/auth from auth.py
app.include_router(journal.router) # Includes prefix /api/v1/journal from journal.py
app.include_router(chat.router) # Includes prefix /api/v1/chat from chat.py

# --- Static Files and Frontend Serving ---

# Get the absolute path to the 'frontend' directory relative to this file's location
# backend/app/main.py -> backend/ -> frontend/
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
static_dir = frontend_dir / "static"

# Check if directories exist (for debugging)
if not frontend_dir.is_dir():
    print(f"Warning: Frontend directory not found at {frontend_dir}")
if not static_dir.is_dir():
     print(f"Warning: Static directory not found at {static_dir}")

# Mount static files (CSS, JS) under /static path
# This means files in frontend/static/css/style.css will be available at http://.../static/css/style.css
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
     print("Static directory mounting skipped as it does not exist.")


# --- Root and HTML File Serving ---

@app.get("/", include_in_schema=False)
async def serve_index():
    """Serves the main login/register page."""
    index_path = frontend_dir / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)
    else:
        raise HTTPException(status_code=404, detail="index.html not found")

@app.get("/journal.html", include_in_schema=False)
async def serve_journal_page():
    """Serves the main journal application page."""
    journal_path = frontend_dir / "journal.html"
    if journal_path.is_file():
        return FileResponse(journal_path)
    else:
        raise HTTPException(status_code=404, detail="journal.html not found")

@app.get("/chat.html", include_in_schema=False)
async def serve_chat_page():
    """Serves the chat application page."""
    chat_path = frontend_dir / "chat.html"
    if chat_path.is_file():
        return FileResponse(chat_path)
    else:
        raise HTTPException(status_code=404, detail="chat.html not found")

@app.get("/test-connection.html", include_in_schema=False)
async def serve_test_connection_page():
    """Serves the API test connection page."""
    test_path = frontend_dir / "test-connection.html"
    if test_path.is_file():
        return FileResponse(test_path)
    else:
         raise HTTPException(status_code=404, detail="test-connection.html not found")


# --- Health Check and Debug Endpoints ---

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    # Add database connection check if needed
    try:
        # Try getting a db session to check connection
        db = next(database.get_db())
        # You could perform a simple query like db.execute(text("SELECT 1"))
        print("Database connection successful for health check.")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        print(f"Database connection failed during health check: {e}")
        return JSONResponse(
             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
             content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
         )

# Optional Debug Endpoints (consider removing in production)
@app.get("/api/debug/ping", tags=["Debug"])
async def debug_ping():
    """Simple ping endpoint for connection testing."""
    return {"message": "pong"}

@app.get("/api/debug/config", tags=["Debug"])
async def debug_config():
    """Returns sensitive configuration - USE WITH CAUTION, ideally remove in production."""
    # Be very careful about exposing sensitive settings
    # Only expose non-sensitive or necessary config for debugging
    return {
        "DATABASE_URL_Type": settings.DATABASE_URL.split("://")[0] if "://" in settings.DATABASE_URL else "Unknown",
        "ALGORITHM": settings.ALGORITHM,
        "ACCESS_TOKEN_EXPIRE_MINUTES": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        # "SECRET_KEY": "HIDDEN", # Never expose the secret key
        # "DATABASE_URL": "HIDDEN", # Never expose the full DB URL if it contains passwords
    }

# Example of handling 404 for API routes explicitly if needed
# (FastAPI does this by default, but you can customize)
# @app.exception_handler(404)
# async def custom_404_handler(request: Request, exc: HTTPException):
#     if request.url.path.startswith("/api/"):
#         return JSONResponse(
#             status_code=status.HTTP_404_NOT_FOUND,
#             content={"detail": f"API endpoint not found: {request.url.path}"},
#         )
#     # For non-API paths, you might want to serve index.html for SPAs
#     # or return the default FastAPI 404 HTML response
#     return PlainTextResponse(f"Not Found: {request.url.path}", status_code=404)

print("FastAPI application configured.")
# --- END OF FILE backend/app/main.py ---