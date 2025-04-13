# --- START OF FILE backend/app/main.py ---
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
import os
from pathlib import Path
import sqlalchemy # Import sqlalchemy to use text

# Use relative imports for modules within the same package
from .db import database, models
from .routers import auth, journal, chat
from .core.config import settings
from .core.security import get_current_active_user # <--- THÊM DÒNG NÀY

# ... (phần còn lại của file giữ nguyên) ...

# Create database tables on startup if DB initialization is enabled
print("Initializing database...")
try:
    database.init_db()
    print("Database initialization check complete.")
except Exception as e:
     print(f"Database initialization failed: {e}")

app = FastAPI(
    title="AI Journal App API",
    version="0.4.0",
    description="API for an AI-powered journaling application with context-aware chat."
)

# ... (CORS config) ...

# --- API Routers ---
print("Including API routers...")
app.include_router(auth.router)
app.include_router(journal.router)
app.include_router(chat.router)
print("API routers included.")

# ... (Static files config) ...

# --- Root and HTML File Serving ---
print("Configuring static files and frontend serving...")
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
static_dir = frontend_dir / "static"

if not frontend_dir.is_dir(): print(f"ERROR: Frontend directory not found at calculated path: {frontend_dir}")
if not static_dir.is_dir(): print(f"WARNING: Static directory not found at calculated path: {static_dir}.")

if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    print(f"Mounted static directory: {static_dir}")
else:
     print("Static directory mounting skipped as it does not exist.")

@app.get("/", include_in_schema=False)
async def serve_index():
    index_path = frontend_dir / "index.html"
    if index_path.is_file(): return FileResponse(index_path, media_type='text/html')
    else: raise HTTPException(status_code=404, detail="index.html not found")

@app.get("/journal.html", include_in_schema=False)
async def serve_journal_page():
    journal_path = frontend_dir / "journal.html"
    if journal_path.is_file(): return FileResponse(journal_path, media_type='text/html')
    else: raise HTTPException(status_code=404, detail="journal.html not found")

@app.get("/chat.html", include_in_schema=False)
async def serve_chat_page():
    chat_path = frontend_dir / "chat.html"
    if chat_path.is_file(): return FileResponse(chat_path, media_type='text/html')
    else: raise HTTPException(status_code=404, detail="chat.html not found")

@app.get("/test-connection.html", include_in_schema=False)
async def serve_test_connection_page():
    test_path = frontend_dir / "test-connection.html"
    if test_path.is_file(): return FileResponse(test_path, media_type='text/html')
    else: raise HTTPException(status_code=404, detail="test-connection.html not found")

print("HTML file serving configured.")

# --- Health Check and Debug Endpoints ---
print("Configuring health check and debug endpoints...")
@app.get("/api/health", tags=["Health"])
async def health_check():
    db = None
    try:
        db = next(database.get_db())
        # Use sqlalchemy.text for executing raw SQL safely
        db.execute(sqlalchemy.text("SELECT 1"))
        db_status = "connected"
        status_code = status.HTTP_200_OK
        print("Health check: Database connection successful.")
    except Exception as e:
        print(f"Health check: Database connection failed: {e}")
        db_status = "disconnected"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(
             status_code=status_code,
             content={"status": "unhealthy", "database": db_status, "error": str(e)}
         )
    finally:
        if db: db.close()
    return JSONResponse(status_code=status_code, content={"status": "healthy", "database": db_status})

@app.get("/api/debug/ping", tags=["Debug"])
async def debug_ping():
    return {"message": "pong"}

# Endpoint này giờ đã có thể sử dụng get_current_active_user vì đã import
@app.get("/api/debug/config", tags=["Debug"])
async def debug_config(current_user: models.User = Depends(get_current_active_user)): # Protect endpoint
    return {
        "DATABASE_URL_Type": settings.DATABASE_URL.split("://")[0] if "://" in settings.DATABASE_URL else "Unknown",
        "ALGORITHM": settings.ALGORITHM,
        "ACCESS_TOKEN_EXPIRE_MINUTES": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        "GEMINI_API_KEY_SET": bool(settings.GEMINI and settings.GEMINI != "Gemini" and len(settings.GEMINI) > 10),
    }
print("Health check and debug endpoints configured.")

print("FastAPI application configured successfully.")
# --- END OF FILE backend/app/main.py ---