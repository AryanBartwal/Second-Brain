import hashlib

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


_model = None


def _get_model():
    global _model
    if _model is None and SentenceTransformer is not None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _fallback_embedding(text: str, dimension: int = 384) -> list[float]:
    values = [0.0] * dimension
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % dimension
        values[index] += 1.0
    return values


def embed_texts(texts):
    """
    Convert list of texts into vectors locally.

    Falls back to a deterministic hashing-based embedding when
    sentence-transformers is not available.
    """
    model = _get_model()
    if model is not None:
        return model.encode(texts).tolist()

    return [_fallback_embedding(text) for text in texts]
