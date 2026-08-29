"""
Text extraction from uploaded files.

Handles: PDF (text-layer + fallback OCR), DOCX, plain text, images.
Install deps: pip install pdfplumber python-docx pillow pytesseract
System dep:   sudo apt-get install tesseract-ocr
"""

import os
import io
from pathlib import Path


def extract_text(file_path: str) -> str:
    """
    Route to the correct extractor based on file extension.
    Returns extracted text as a single string.
    Raises ValueError for unsupported types.
    """
    path = Path(file_path)
    ext  = path.suffix.lower()

    if ext == ".pdf":
        return _extract_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return _extract_docx(file_path)
    elif ext in (".txt", ".md", ".csv"):
        return path.read_text(encoding="utf-8", errors="replace")
    elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
        return _extract_image(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _extract_pdf(file_path: str) -> str:
    """
    Try text-layer extraction first (pdfplumber).
    If the result is too short (scanned PDF), fall back to OCR via Tesseract.
    """
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n\n".join(pages).strip()

        if len(text) > 100:
            return text

        # Scanned PDF: render pages as images and OCR
        return _ocr_pdf(file_path)

    except ImportError:
        return _ocr_pdf(file_path)


def _ocr_pdf(file_path: str) -> str:
    """Render PDF pages as PIL images, then run Tesseract OCR."""
    try:
        import fitz         # PyMuPDF
        import pytesseract
        from PIL import Image

        doc    = fitz.open(file_path)
        pages  = []
        for page in doc:
            pix  = page.get_pixmap(dpi=200)
            img  = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img)
            pages.append(text)
        return "\n\n".join(pages).strip()

    except ImportError:
        return "[OCR unavailable: install pymupdf + pytesseract]"


def _extract_docx(file_path: str) -> str:
    try:
        from docx import Document
        doc   = Document(file_path)
        paras = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(paras)
    except ImportError:
        return "[DOCX extraction unavailable: install python-docx]"


def _extract_image(file_path: str) -> str:
    try:
        import pytesseract
        from PIL import Image
        img  = Image.open(file_path)
        return pytesseract.image_to_string(img)
    except ImportError:
        return "[Image OCR unavailable: install pytesseract + pillow]"
