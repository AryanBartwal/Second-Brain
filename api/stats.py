from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.session import get_db
from models.activity import ActivityEvent
from models.note import Note
from services.auth_service import get_current_user_id

router = APIRouter()

KNOWLEDGE_GOAL_NOTES = 20
USAGE_GOAL_QUERIES_7D = 14


class StatsResponse(BaseModel):
    notes_count: int
    queries_last_7d: int
    queries_total: int
    knowledge_base_percent: int
    usage_rate_percent: int


@router.get("/me", response_model=StatsResponse)
def get_my_stats(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    notes_count = db.query(func.count(Note.id)).filter(Note.user_id == current_user_id).scalar() or 0

    queries_total = (
        db.query(func.count(ActivityEvent.id))
        .filter(
            ActivityEvent.user_id == current_user_id,
            ActivityEvent.event_type == "query",
        )
        .scalar()
        or 0
    )

    since = datetime.now(timezone.utc) - timedelta(days=7)
    queries_last_7d = (
        db.query(func.count(ActivityEvent.id))
        .filter(
            ActivityEvent.user_id == current_user_id,
            ActivityEvent.event_type == "query",
            ActivityEvent.created_at >= since,
        )
        .scalar()
        or 0
    )

    knowledge_base_percent = min(100, int((notes_count / KNOWLEDGE_GOAL_NOTES) * 100))
    usage_rate_percent = min(100, int((queries_last_7d / USAGE_GOAL_QUERIES_7D) * 100))

    return {
        "notes_count": notes_count,
        "queries_last_7d": queries_last_7d,
        "queries_total": queries_total,
        "knowledge_base_percent": knowledge_base_percent,
        "usage_rate_percent": usage_rate_percent,
    }
