from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from db.session import get_db
from models.activity import ActivityEvent
from services.embedder import embed_texts
from services.vector_store import search_chunks
from services.llm import generate_answer
from services.auth_service import get_current_user_id

router = APIRouter()

class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2000)
    user_id: Optional[int] = None

class QueryResponse(BaseModel):
    answer: str
    sources_count: int

@router.post("/", response_model=QueryResponse)
def query_memory(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )

    if request.user_id is not None and request.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only query your own notes"
        )

    db.add(ActivityEvent(user_id=current_user_id, event_type="query"))
    db.commit()
    
    query_vector = embed_texts([request.question])[0]
    results = search_chunks(query_vector, current_user_id)
    
    if results:
        context = "\n\n".join(results)
        answer = generate_answer(context, request.question)
    else:
        answer = generate_answer(
            "No personal notes were found for this user yet.",
            request.question,
        )

    return {
        "answer": answer,
        "sources_count": len(results)
    }