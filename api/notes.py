from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from db.session import get_db
from models.note import Note
from services.chunker import chunk_text
from services.embedder import embed_texts
from services.vector_store import delete_note_chunks, upsert_chunks
from services.pdf_processor import extract_text_from_pdf
from services.auth_service import get_current_user_id

router = APIRouter()


class NoteCreateResponse(BaseModel):
    message: str
    note_id: int
    source: str


class NoteSummary(BaseModel):
    id: int
    source: str
    content_preview: str
    created_at: datetime | None


class NoteListResponse(BaseModel):
    notes: list[NoteSummary]
    total_count: int
    returned_count: int
    limit: int
    offset: int


class AddTextNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=20000)
    user_id: Optional[int] = None

@router.post("/", response_model=NoteCreateResponse)
async def add_note(
    user_id: int | None = Form(default=None),
    content: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Add a note from either text content or PDF file.
    - user_id: ID of the user
    - content: Text content (optional if file is provided)
    - file: PDF file (optional if content is provided)
    """
    
    # Validate that at least one input is provided
    if not content and not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either content or file must be provided"
        )

    if user_id is not None and user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add notes for your own account"
        )

    owner_id = current_user_id
    
    # Extract text from PDF if file is provided
    if file:
        filename = (file.filename or "").lower()
        if not filename.endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are supported"
            )
        
        # Read PDF content
        pdf_bytes = await file.read()
        try:
            extracted_text = extract_text_from_pdf(pdf_bytes)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        
        if not extracted_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Could not extract text from PDF. The document may be image-only "
                    "(scanned) or contain no selectable text."
                )
            )
        
        # Use extracted text as content
        final_content = extracted_text
    else:
        final_content = content
    
    # Create note in database
    note = Note(
        user_id=owner_id,
        content=final_content,
        source="pdf" if file else "text",
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    # Process text for RAG
    chunks = chunk_text(note.content)
    if chunks:
        embeddings = embed_texts(chunks)
        upsert_chunks(chunks, embeddings, owner_id, note.id)

    return {
        "message": "Note added successfully",
        "note_id": note.id,
        "source": note.source
    }


@router.post("/text", response_model=NoteCreateResponse)
def add_text_note(
    data: AddTextNoteRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Legacy endpoint for adding text notes via JSON.
    Kept for backward compatibility.
    """
    if data.user_id is not None and data.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add notes for your own account"
        )

    note = Note(user_id=current_user_id, content=data.content, source="text")
    db.add(note)
    db.commit()
    db.refresh(note)

    chunks = chunk_text(note.content)
    if chunks:
        embeddings = embed_texts(chunks)
        upsert_chunks(chunks, embeddings, current_user_id, note.id)

    return {
        "message": "Note added successfully",
        "note_id": note.id,
        "source": "text"
    }


@router.get("/", response_model=NoteListResponse)
def list_notes(
    source: str | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    query = db.query(Note).filter(Note.user_id == current_user_id)

    if source:
        query = query.filter(Note.source == source)
    if start_date:
        query = query.filter(Note.created_at >= start_date)
    if end_date:
        query = query.filter(Note.created_at <= end_date)

    total_count = query.count()
    notes = query.order_by(Note.id.desc()).offset(offset).limit(limit).all()
    return {
        "notes": [
            {
                "id": note.id,
                "source": note.source or "text",
                "content_preview": (note.content or "")[:160],
                "created_at": note.created_at,
            }
            for note in notes
        ],
        "total_count": total_count,
        "returned_count": len(notes),
        "limit": limit,
        "offset": offset,
    }


@router.delete("/{note_id}")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == current_user_id).first()
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    db.delete(note)
    db.commit()
    delete_note_chunks(note_id=note_id, user_id=current_user_id)

    return {"message": "Note deleted successfully", "note_id": note_id}