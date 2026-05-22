from __future__ import annotations

import logging
import fitz  # PyMuPDF

try:
    from .ocr_parser import extract_text_with_ocr, extract_text_with_ocr_detailed
except ImportError:
    extract_text_with_ocr = None
    extract_text_with_ocr_detailed = None

try:
    from .extraction_quality import estimate_text_quality
except ImportError:
    estimate_text_quality = None

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using PyMuPDF first, with OCR fallback for scanned PDFs."""
    text, _ = extract_text_from_pdf_detailed(file_bytes)
    return text


def extract_text_from_pdf_detailed(file_bytes: bytes) -> tuple[str, dict]:
    """Like extract_text_from_pdf but returns extraction warnings and quality metadata."""
    chunks: list[str] = []
    ocr_used = False
    native_chars = 0

    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as document:
            for page in document:
                page_text = page.get_text("text").strip()
                if page_text:
                    chunks.append(page_text)
    except Exception as exc:
        raise ValueError("Invalid or corrupted PDF file.") from exc

    text = "\n\n".join(chunks)
    native_chars = len(text.strip())
    meta: dict = {"native_chars": native_chars, "ocr_used": False, "warnings": []}
    
    OCR_THRESHOLD = 50
    # OCR fallback activates when native PDF text extraction is likely a scan/image.
    if native_chars < OCR_THRESHOLD and extract_text_with_ocr is not None:
        logger.info("Little text extracted (%d chars), triggering OCR fallback", native_chars)
        if extract_text_with_ocr_detailed is not None:
            ocr_text, ocr_meta = extract_text_with_ocr_detailed(file_bytes)
        else:
            ocr_text = extract_text_with_ocr(file_bytes)
            ocr_meta = {"ocr_attempted": True}
        
        if ocr_text.strip():
            logger.info("OCR fallback successful, new text length: %d chars", len(ocr_text))
            text = ocr_text
            ocr_used = True
            meta["ocr_used"] = True
            meta["ocr_meta"] = ocr_meta
        else:
            logger.warning("OCR fallback returned empty text")
            meta["warnings"].append("OCR fallback returned no text — file may be unreadable.")
    
    # Estimate overall extraction quality
    if estimate_text_quality is not None:
        quality = estimate_text_quality(text)
        meta["quality"] = quality
        if quality.get("is_low_quality"):
            meta["warnings"].append(quality["detail"])
    
    meta["warnings"] = meta["warnings"][:4]  # cap warnings
    return text, meta
