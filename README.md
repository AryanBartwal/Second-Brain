# Second Brain

A personal knowledge system powered by retrieval-augmented generation (RAG).
Users can register, upload notes or PDFs, and ask grounded questions against their own private knowledge base.

## Why This Is Resume-Ready

- End-to-end full-stack app: FastAPI backend plus frontend dashboard.
- Secure multi-user architecture: JWT authentication with per-user data isolation.
- RAG pipeline: chunking, local embeddings, vector indexing, context-aware answer generation.
- Production-minded defaults: persistent vector storage, environment-based config, startup lifecycle, health endpoint.
- Practical UX: auth flow, PDF upload, note ingestion, and question-answer workflow.

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Pydantic
- Auth: JWT (python-jose), passlib password hashing
- RAG: sentence-transformers, Qdrant, Gemini API
- Parsing: PyPDF2
- Frontend: static HTML/CSS/JS served by FastAPI

## Features

- User registration and login
- Bearer-token protected note ingestion/query APIs
- Add plain text notes
- Upload PDFs and extract text content
- Chunk and embed note content
- Semantic retrieval from vector store
- LLM answer generation from retrieved context
- Live dashboard metrics (knowledge progress and usage rate)

## Project Structure

- `api/` API route modules
- `models/` SQLAlchemy models
- `db/` DB session and base configuration
- `services/` business logic (auth, chunking, embeddings, vector store, PDF, LLM)
- `main.py` FastAPI app entrypoint
- `index.html` frontend UI

## Quick Start

### 1) Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

### 3) Configure environment

```powershell
copy .env.example .env
```

Then update `.env` values, especially:

- `JWT_SECRET`
- `GEMINI_API_KEY`

### 4) Run the app

```powershell
python main.py
```

Open:

- App: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## API Overview

- `POST /auth/register`
- `POST /auth/login`
- `POST /notes/` (multipart; requires `Authorization: Bearer <token>`)
- `POST /notes/text` (JSON; requires bearer token)
- `POST /query/` (JSON; requires bearer token)
- `GET /stats/me` (live user analytics for dashboard widgets)

## Suggested Resume Bullet

Built a production-oriented RAG knowledge assistant using FastAPI, SQLAlchemy, JWT auth, Qdrant vector search, and Gemini-based answer synthesis, with secure per-user retrieval, PDF ingestion, and an interactive frontend dashboard.

## Notes

- Local Qdrant data persists under `data/qdrant` by default.
- SQLite database persists under `data/second_brain.db`.
- If `GEMINI_API_KEY` is not configured, retrieval still works and the API returns a clear LLM-unavailable message.
