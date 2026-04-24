from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/second_brain.db")

os.makedirs("data", exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def run_startup_migrations():
    if "sqlite" not in DATABASE_URL:
        return

    with engine.begin() as conn:
        inspector = inspect(conn)
        if not inspector.has_table("notes"):
            return

        columns = {col["name"] for col in inspector.get_columns("notes")}

        if "source" not in columns:
            conn.execute(text("ALTER TABLE notes ADD COLUMN source VARCHAR(20) DEFAULT 'text'"))

        if "created_at" not in columns:
            conn.execute(text("ALTER TABLE notes ADD COLUMN created_at DATETIME"))
            conn.execute(text("UPDATE notes SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()