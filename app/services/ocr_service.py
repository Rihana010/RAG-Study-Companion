import os
import io
import logging
from PIL import Image
import pytesseract
import pymupdf as fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Check standard Windows installation paths for Tesseract
TESSERACT_COMMON_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
]

for t_path in TESSERACT_COMMON_PATHS:
    if os.path.exists(t_path):
        pytesseract.pytesseract.tesseract_cmd = t_path
        logger.info(f"Tesseract executable found at: {t_path}")
        break

class OCRService:
    @staticmethod
    def is_ocr_available() -> bool:
        """Checks if Tesseract OCR binary is installed and executable."""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    @staticmethod
    def ocr_pdf_page(page: fitz.Page, dpi: int = 150) -> str:
        """
        Renders a PyMuPDF PDF page to an image and performs OCR text extraction.
        Returns extracted text string.
        """
        try:
            # Render page to image pixmap
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))

            if not OCRService.is_ocr_available():
                logger.warning("OCR requested but Tesseract binary is not installed/configured.")
                return ""

            # Perform PyTesseract OCR
            extracted_text = pytesseract.image_to_string(image).strip()
            logger.info(f"OCR extracted {len(extracted_text)} characters from page {page.number + 1}.")
            return extracted_text

        except Exception as e:
            logger.error(f"OCR processing failed for page {page.number + 1}: {e}")
            return ""
