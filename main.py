from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
from pathlib import Path
from contextlib import asynccontextmanager
import uvicorn

load_dotenv()

from db.base import Base
from db.session import engine, run_startup_migrations
from api import auth, notes, query, stats
from models import activity  # noqa: F401
from services.vector_store import init_qdrant


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_startup_migrations()
    init_qdrant()
    yield


app = FastAPI(
    title="Second Brain API",
    description="RAG-based knowledge management system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(notes.router, prefix="/notes", tags=["Notes"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(stats.router, prefix="/stats", tags=["Stats"])

@app.get("/")
def root():
    index_path = Path(__file__).with_name("index.html")
    if index_path.exists():
        return FileResponse(index_path)

    return {
        "message": "Welcome to Second Brain API",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").strip().lower() == "true"
    uvicorn.run("main:app", host=host, port=port, reload=reload)