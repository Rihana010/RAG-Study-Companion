import os
import pymupdf as fitz
import pytest
from app.services.pdf_service import PDFService
from app.services.ocr_service import OCRService

@pytest.fixture
def mixed_pdf(tmp_path):
    pdf_path = os.path.join(tmp_path, "mixed_study_notes.pdf")
    doc = fitz.open()
    
    # Page 1: Native Text (High density)
    page1 = doc.new_page()
    page1.insert_text((50, 50), "High density native text explaining thermodynamics and entropy principles in physics.")
    
    # Page 2: Low Text / Scanned simulation
    page2 = doc.new_page()
    page2.insert_text((50, 50), "X") # Very low text density < 40 chars
    
    doc.save(pdf_path)
    doc.close()
    return pdf_path

def test_ocr_availability():
    is_avail = OCRService.is_ocr_available()
    assert isinstance(is_avail, bool)

def test_pdf_ocr_pipeline(mixed_pdf):
    filename = os.path.basename(mixed_pdf)
    pages = PDFService.extract_text(mixed_pdf, filename, min_text_threshold=40)
    
    assert len(pages) == 2
    # Page 1 should be native text
    assert pages[0]["content_type"] == "text"
    assert pages[0]["ocr"] is False
    assert "thermodynamics" in pages[0]["text"]
    
    # Page 2 should have triggered OCR decision check
    assert pages[1]["page"] == 2
    assert "ocr" in pages[1]
