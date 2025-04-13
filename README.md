# Journal App with AI Assistant

A modern journal application that combines personal journaling with AI-powered assistance. Built with FastAPI for the backend and vanilla JavaScript for the frontend.

## Project Structure

The project consists of two main components:

### Frontend (`frontend/`)
- Vanilla JavaScript-based web application
  - `js/`: JavaScript source files
  - `static/`: Static assets (CSS, images, etc.)
  - HTML files: `index.html`, `journal.html`, `chat.html`, `test-connection.html`

### Backend (`backend/`)
FastAPI-based REST API server with the following structure:
- `app/`: Main application package
  - `main.py`: Application entry point and FastAPI app configuration
  - `db/`: Database related code
    - `database.py`: Database connection and session management
    - `models.py`: SQLAlchemy models
  - `routers/`: API route handlers
    - `auth.py`: Authentication endpoints
    - `journal.py`: Journal entry endpoints
    - `chat.py`: AI chat endpoints
  - `schemas/`: Pydantic models for request/response validation
    - `schemas.py`: Base schemas
    - `chat.py`: Chat-related schemas
  - `services/`: Business logic and external service integration
    - `ai_services.py`: Gemini AI integration
    - `context_service.py`: Context management for AI interactions
  - `core/`: Core application configuration
  - `crud/`: Database CRUD operations
  - `schemas.sql`: Database schema definitions
- `requirements.txt`: Python dependencies
- `.env`: Environment configuration
- `run.sh`: Shell script for running the application
- `run.py`: Application entry point

## Prerequisites

- Python 3.8+
- PostgreSQL
- Node.js (for development tools)
- Google Gemini API key (for AI features)

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   Create a `.env` file with the following variables:
   ```
   DATABASE_URL=postgresql://username:password@localhost/dbname
   SECRET_KEY=your_secret_key
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   GEMINI=your_gemini_api_key
   ```

5. Initialize the database:
   ```bash
   # Create the database schema
   psql -U your_username -d your_database -f app/schemas.sql
   ```

6. Run the application:
   ```bash
   # Using the shell script
   ./run.sh
   
   # Or directly with uvicorn
   uvicorn run:app --reload
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. The frontend is built with vanilla JavaScript and can be served using any static file server. For development, you can use:
   ```bash
   python -m http.server 8000
   ```

## Features

- User authentication and authorization
- Journal entry management (CRUD operations)
- AI-powered chat assistance using Google's Gemini API
- Real-time connection testing
- Responsive design
- Secure API endpoints with JWT authentication

## API Documentation

The backend API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Security Considerations

- JWT-based authentication
- Environment variables for sensitive data
- Password hashing with bcrypt
- Secure session management

## Development

### Backend Development
- FastAPI for API development
- SQLAlchemy for database ORM
- PostgreSQL as the database
- Uvicorn as the ASGI server
- Pydantic for data validation
- JWT for authentication

### Frontend Development
- Vanilla JavaScript
- HTML5 and CSS3
- No external frameworks required

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 