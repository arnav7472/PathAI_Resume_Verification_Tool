from __future__ import annotations

import logging
import fitz  # PyMuPDF

try:
    from .ocr_parser import extract_text_with_ocr
except ImportError:
    extract_text_with_ocr = None

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using PyMuPDF first, with OCR fallback for scanned PDFs."""
    chunks: list[str] = []

    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as document:
            for page in document:
                page_text = page.get_text("text").strip()
                if page_text:
                    chunks.append(page_text)
    except Exception as exc:
        raise ValueError("Invalid or corrupted PDF file.") from exc

    text = "\n\n".join(chunks)
    
    OCR_THRESHOLD = 50
    # OCR fallback activates when native PDF text extraction is likely a scan/image.
    if len(text.strip()) < OCR_THRESHOLD and extract_text_with_ocr is not None:
        logger.info("Little text extracted (%d chars), triggering OCR fallback", len(text.strip()))
        ocr_text = extract_text_with_ocr(file_bytes)
        if ocr_text.strip():
            logger.info("OCR fallback successful, new text length: %d chars", len(ocr_text))
            text = ocr_text
        else:
            logger.warning("OCR fallback returned empty text")
    
    return text
