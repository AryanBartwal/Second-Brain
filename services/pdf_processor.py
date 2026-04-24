import PyPDF2
from io import BytesIO

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text content from a PDF file.
    
    Args:
        pdf_bytes: PDF file content as bytes
        
    Returns:
        Extracted text as a string
    """
    text_content = []

    try:
        if not pdf_bytes:
            raise RuntimeError("Empty PDF file")

        pdf_file = BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        if pdf_reader.is_encrypted:
            decrypt_result = pdf_reader.decrypt("")
            if decrypt_result == 0:
                raise RuntimeError("PDF is encrypted and cannot be read without a password")

        for page_num, page in enumerate(pdf_reader.pages):
            try:
                text = page.extract_text() or ""
                cleaned = text.strip()
                if cleaned:
                    text_content.append(cleaned)
            except Exception:
                # Continue parsing other pages when a single page fails extraction.
                continue

        return "\n\n".join(text_content)

    except Exception as e:
        raise RuntimeError(f"Error extracting text from PDF: {str(e)}")