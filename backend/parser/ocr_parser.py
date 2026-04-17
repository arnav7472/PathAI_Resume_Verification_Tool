from __future__ import annotations

import logging
from io import BytesIO
from typing import List

import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
import pytesseract


logger = logging.getLogger(__name__)


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Convert to grayscale and apply basic thresholding for better OCR.
    """
    # PIL to OpenCV
    open_cv_image = np.array(image)
    # Grayscale
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
    # Threshold
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Back to PIL
    return Image.fromarray(thresh)


def extract_text_with_ocr(pdf_bytes: bytes, max_pages: int = 10) -> str:
    """
    Extract text from PDF using OCR fallback.
    """
    chunks: List[str] = []
    
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            num_pages = min(len(document), max_pages)
            
            for page_num in range(num_pages):
                page = document[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Higher DPI for better OCR
                img_data = pix.tobytes("ppm")
                image = Image.open(BytesIO(img_data))
                
                # Preprocess
                processed_image = preprocess_image(image)
                
                # OCR
                text = pytesseract.image_to_string(processed_image, lang="eng")
                text = text.strip()
                if text:
                    chunks.append(text)
                    
    except Exception as e:
        logger.warning("OCR extraction failed: %s", str(e))
        return ""
    
    # Basic cleanup: join pages, normalize newlines/spaces
    full_text = "\n\n".join(chunks)
    full_text = "\n".join(line.strip() for line in full_text.splitlines() if line.strip())
    return full_text
