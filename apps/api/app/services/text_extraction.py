from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader


class TextExtractionError(Exception):
    """Raised when text cannot be extracted from a supported document."""


def extract_text(content: bytes, content_type: str) -> str:
    if content_type == "text/plain":
        return _extract_plain_text(content)

    if content_type == "application/pdf":
        return _extract_pdf_text(content)

    raise TextExtractionError(f"unsupported content type: {content_type}")


def _extract_plain_text(content: bytes) -> str:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TextExtractionError("plain-text file is not valid UTF-8") from exc

    text = text.strip()
    if not text:
        raise TextExtractionError("document contains no extractable text")

    return text


def _extract_pdf_text(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
    except Exception as exc:
        raise TextExtractionError("failed to read PDF") from exc

    pages: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            pages.append(page_text.strip())

    text = "\n\n".join(pages).strip()

    if not text:
        raise TextExtractionError("PDF contains no extractable text")

    return text