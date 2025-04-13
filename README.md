# Journal AI 📔✨ - Your Reflective Companion

**Journal AI** is more than just a digital diary; it's your personal space for self-reflection, enhanced by an intelligent and empathetic AI assistant. Securely capture your daily thoughts, feelings, and experiences, and then explore them further through insightful conversations or focused analysis powered by Google's Gemini AI.

Whether you're looking to understand your emotions better, track personal growth, or simply need a non-judgmental space to process your day, Journal AI provides the tools you need.

**(Optional: Consider adding a screenshot or GIF of the app interface here)**
<!-- ![Journal AI Screenshot](link/to/your/screenshot.png) -->

## What Journal AI Offers

*   **✍️ Secure & Private Journaling:** Effortlessly write, edit, view, and organize your journal entries in a clean, intuitive interface. Your thoughts are protected with secure user authentication.
*   **💬 Context-Aware AI Chat:** Engage in meaningful conversations with an AI assistant that understands the context of your **most recent journal entries**. Ask questions, explore feelings, or simply chat – the AI listens and responds based on your recent writings, creating a uniquely personal experience. *Each chat session starts fresh, focusing on your current context.*
*   **💡 AI-Powered Entry Consultation:** Select any specific journal entry and request an AI consultation. The AI analyzes the entry, considering its surrounding context (other recent entries), to provide focused reflections, empathetic feedback, and gentle prompts for deeper understanding.
*   **🔒 Privacy Focused:** Your journal entries are stored securely in your own database instance, and authentication ensures only you can access your thoughts.
*   **📱 Responsive Design:** Access and use your journal seamlessly across different devices (basic responsiveness assumed).

## Why Choose Journal AI?

*   **Deeper Self-Reflection:** Go beyond simple recording. Use the AI chat and consultation features to explore patterns, understand triggers, and gain new perspectives on your own experiences.
*   **Empathetic Listening:** Sometimes you just need to talk. The AI assistant is designed to be an empathetic, non-judgmental listener, available whenever you need it.
*   **Track Your Journey:** Look back on your entries and AI interactions to see how you've grown and navigated life's ups and downs.
*   **Secure Personal Space:** Keep your most private thoughts safe with user accounts and password protection.

## Technology Stack

*   **Backend:** FastAPI (Python), PostgreSQL, SQLAlchemy, Pydantic, JWT Authentication
*   **AI:** Google Gemini API
*   **Frontend:** Vanilla JavaScript, HTML5, CSS3 (No frameworks)

## Getting Started (For Local Setup/Development)

These instructions are for developers who want to run the application locally.

### Prerequisites

*   Python 3.8+ & Pip
*   PostgreSQL Server (Running)
*   Google Gemini API key

### Backend Setup

1.  **Clone & Navigate:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>/backend
    ```
2.  **Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate # Linux/macOS
    # venv\Scripts\activate # Windows
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Environment (`.env`):**
    Create a `.env` file in the `backend` directory with your specific settings:
    ```dotenv
    # Example .env content
    DATABASE_URL=postgresql://your_db_user:your_db_password@localhost:5432/journal_ai_db
    SECRET_KEY=a_very_strong_and_secret_key_please_change_me
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=60
    GEMINI=YOUR_GOOGLE_GEMINI_API_KEY_HERE
    # SKIP_DB_INIT=false # Set to true if you manage migrations separately
    ```
    *   **Important:** Replace placeholders with your actual database credentials, a strong secret key, and your Gemini API key. Ensure your PostgreSQL server is running and the specified database exists.
5.  **Initialize Database Schema:**
    *   The application attempts to create tables on startup (`init_db()` in `database.py`). Ensure the database user has permission to create tables.
    *   *Alternatively, if you prefer manual setup or have `SKIP_DB_INIT=true`*:
        ```bash
        # Connect to your PostgreSQL instance (e.g., using psql)
        psql -U your_db_user -d journal_ai_db
        # Manually create tables based on backend/app/db/models.py if needed
        # (Or use a migration tool like Alembic in a real-world scenario)
        ```
6.  **Run the Backend Server:**
    ```bash
    # Using the provided script (if executable)
    # ./run.sh

    # Or directly with uvicorn (recommended for development)
    uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    The backend API will be available at `http://localhost:8000`.

### Frontend Setup

1.  **Navigate:**
    ```bash
    cd ../frontend # Assuming you are in the backend directory
    ```
2.  **Serve Files:**
    The frontend consists of static HTML, CSS, and JS files. You can serve them using a simple HTTP server.
    ```bash
    python -m http.server 7000 # Or any other available port
    ```
    *   **Note:** Ensure the `API_BASE_URL` constant in `frontend/static/js/api.js` points to your running backend (e.g., `http://127.0.0.1:8000`).

## Usage

1.  Ensure both the backend and frontend servers are running.
2.  Open your web browser and navigate to the address where the frontend is being served (e.g., `http://localhost:7000`).
3.  Register a new account or log in if you already have one.
4.  Start journaling, chatting with the AI, or exploring past entries!

## API Documentation

Interactive API documentation is automatically generated by FastAPI:

*   **Swagger UI:** `http://localhost:8000/docs`
*   **ReDoc:** `http://localhost:8000/redoc`

## Contributing

Contributions are welcome! Please follow these steps:

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/your-feature-name`).
3.  Commit your changes (`git commit -m 'Add some amazing feature'`).
4.  Push to the branch (`git push origin feature/your-feature-name`).
5.  Open a Pull Request.

