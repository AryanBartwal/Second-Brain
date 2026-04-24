import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Configure test-safe environment before importing the app.
os.environ["DATABASE_URL"] = "sqlite:///./data/test_second_brain.db"
os.environ["JWT_SECRET"] = "test-jwt-secret"
os.environ.setdefault("RELOAD", "false")

db_path = Path("data/test_second_brain.db")
if db_path.exists():
    db_path.unlink()

from main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
