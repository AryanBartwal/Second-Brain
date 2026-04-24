import os
import uuid

COLLECTION_NAME = "second_brain"

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue
except ImportError:
    QdrantClient = None
    VectorParams = Distance = PointStruct = Filter = FieldCondition = MatchValue = None


_fallback_chunks: list[dict] = []


def _build_qdrant_client():
    if QdrantClient is None:
        return None

    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")

    if url:
        return QdrantClient(url=url, api_key=api_key)

    # Keep vectors across app restarts for local development.
    os.makedirs("data", exist_ok=True)
    return QdrantClient(path="data/qdrant")


client = _build_qdrant_client()

def init_qdrant():
    """Initialize Qdrant collection if it doesn't exist"""
    if client is None:
        return

    collections = client.get_collections().collections
    
    if not any(c.name == COLLECTION_NAME for c in collections):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=384,  # all-MiniLM-L6-v2 embedding size
                distance=Distance.COSINE
            )
        )
        print(f"Created Qdrant collection: {COLLECTION_NAME}")

def upsert_chunks(chunks: list[str], embeddings: list[list[float]], user_id: int, note_id: int):
    """
    Insert text chunks and their embeddings into Qdrant.
    
    Args:
        chunks: List of text chunks
        embeddings: List of embedding vectors
        user_id: ID of the user
        note_id: ID of the note
    """
    if client is None:
        for chunk in chunks:
            _fallback_chunks.append(
                {
                    "user_id": user_id,
                    "note_id": note_id,
                    "text": chunk,
                }
            )
        return

    points = []

    for chunk, embedding in zip(chunks, embeddings):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "user_id": user_id,
                    "note_id": note_id,
                    "text": chunk
                }
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )

def search_chunks(query_embedding: list[float], user_id: int, limit: int = 5) -> list[str]:
    """
    Search for similar chunks in Qdrant.
    
    Args:
        query_embedding: Query vector
        user_id: Filter by user ID
        limit: Number of results to return
        
    Returns:
        List of matching text chunks
    """
    if client is None:
        return [item["text"] for item in _fallback_chunks if item["user_id"] == user_id][:limit]

    try:
        # Try the modern API first
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=limit,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            )
        )
        return [hit.payload["text"] for hit in results]
    except Exception as e:
        print(f"Search error: {e}")
        return []


def delete_note_chunks(note_id: int, user_id: int):
    if client is None:
        global _fallback_chunks
        _fallback_chunks = [
            item for item in _fallback_chunks
            if not (item["note_id"] == note_id and item["user_id"] == user_id)
        ]
        return

    try:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(key="note_id", match=MatchValue(value=note_id)),
                    FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                ]
            ),
        )
    except Exception as e:
        print(f"Delete chunks error: {e}")