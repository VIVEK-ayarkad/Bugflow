# BugFlow

A full-stack bug tracking app with JWT authentication, PostgreSQL persistence, CRUD issue management, and AI-assisted bug reporting.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, JWT (python-jose)
- **Frontend:** React, Vite
- **AI:** OpenAI API (optional — rule-based fallback when no key is set)

## Database Schema

```
Users ──< Projects ──< Issues
  │                      │
  └──────────────────────┘ (reporter)
```

| Table | Key Fields |
|-------|-----------|
| **users** | email, username, hashed_password |
| **projects** | name, description, owner_id → users |
| **issues** | title, description, status, priority, os, browser, steps_to_reproduce, expected/actual behavior, project_id, reporter_id |

## Quick Start

### 1. Backend

```bash
cd backend
python3.12 -m venv venv    # Python 3.12+ recommended (3.14 may fail on some deps)
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # optional: set SECRET_KEY and OPENAI_API_KEY
uvicorn app.main:app --reload
```

API runs at **http://127.0.0.1:8000** — docs at `/docs`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

UI runs at **http://localhost:5173**.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/login` | Login (returns JWT) |
| GET | `/api/auth/me` | Current user |
| GET/POST | `/api/projects` | List / create projects |
| GET/PUT/DELETE | `/api/projects/{id}` | Project CRUD |
| GET/POST | `/api/projects/{id}/issues` | List / create issues |
| GET/PUT/DELETE | `/api/projects/{id}/issues/{id}` | Issue CRUD |
| POST | `/api/ai/assist` | AI bug report assistant |

## AI-Assisted Bug Reporting

When reporting a bug, type a short description (e.g. "login broken") and click **Enhance with AI**:

- **With OpenAI key:** The LLM analyzes the text, asks follow-up questions for missing details (OS, browser, steps), and auto-formats a professional bug report.
- **Without API key:** A built-in rule-based fallback detects vague descriptions and prompts for the same details.

Set `OPENAI_API_KEY` in `backend/.env` to enable full LLM integration.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | dev key | JWT signing secret |
| `OPENAI_API_KEY` | (empty) | OpenAI API key for AI assist |
| `OPENAI_MODEL` | gpt-4o-mini | Model to use |
