import os

_client = None
_client_mode = None


def _get_client():
    global _client, _client_mode
    if _client is not None:
        return _client

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    # Try modern google-genai client first.
    try:
        from google import genai  # type: ignore

        _client = genai.Client(api_key=api_key)
        _client_mode = "google_genai"
        return _client
    except Exception:
        pass

    # Fallback for older SDK package: google-generativeai
    try:
        import google.generativeai as legacy_genai  # type: ignore

        legacy_genai.configure(api_key=api_key)
        _client = legacy_genai.GenerativeModel("gemini-2.5-flash")
        _client_mode = "google_generativeai"
        return _client
    except Exception:
        return None

def generate_answer(context: str, question: str) -> str:
    """
    Generate an answer using Gemini LLM based on retrieved context.
    
    Args:
        context: Retrieved text chunks as context
        question: User's question
        
    Returns:
        Generated answer
    """
    prompt = f"""You are a helpful AI assistant. Use the context below to answer the question accurately.
If the context doesn't contain enough information, say so clearly.

Context:
{context}

Question:
{question}

Answer:"""

    client = _get_client()
    if client is None:
        return "LLM service is unavailable. Set GEMINI_API_KEY and install google-genai to enable generated answers."

    try:
        if _client_mode == "google_genai":
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return getattr(response, "text", "") or "No answer returned by the model."

        if _client_mode == "google_generativeai":
            response = client.generate_content(prompt)
            return getattr(response, "text", "") or "No answer returned by the model."

        return "LLM client is not properly configured."
    except Exception as e:
        return f"Error generating answer: {str(e)}"