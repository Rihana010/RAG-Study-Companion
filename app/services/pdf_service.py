
import pymupdf as fitz  #pyMupdf
import os
import logging

from app.services.ocr_service import OCRService

logger = logging.getLogger(__name__)


class PDFService:
    @staticmethod
    def extract_text(
        file_path: str,
        filename: str,
        min_text_threshold: int = 40
    ) -> list[dict]:
        """
        Extract text page-by-page from a PDF.

        Normal text-based pages use PyMuPDF extraction.

        Image-based/scanned pages are sent through OCR. We detect these
        pages using both native text length and the presence of images,
        because scanned PDFs can contain small amounts of native text
        such as watermarks or footers.
        """

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        pages_data = []

        try:
            doc = fitz.open(file_path)

            if doc.is_encrypted:
                logger.warning(f"PDF {filename} is encrypted.")
                doc.close()
                return pages_data

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                # Extract whatever native text PyMuPDF can find.
                native_text = page.get_text("text").strip()

                content_type = "text"
                ocr_flag = False
                final_text = native_text

                # ---------------------------------------------------------
                # Detect scanned/image-based pages
                # ---------------------------------------------------------
                images = page.get_images(full=True)
                has_images = len(images) > 0

                should_ocr = (
                    len(native_text) < min_text_threshold
                    or has_images
                )

                if should_ocr:
                    logger.info(
                        f"Page {page_num + 1} of '{filename}' may be "
                        f"image-based "
                        f"(native text: {len(native_text)} chars, "
                        f"images: {len(images)}). Running OCR..."
                    )

                    try:
                        ocr_text = OCRService.ocr_pdf_page(page).strip()

                        # Use OCR when it produces more useful text than
                        # the native extraction.
                        if len(ocr_text) > len(native_text):
                            final_text = ocr_text
                            content_type = "ocr_text"
                            ocr_flag = True

                            logger.info(
                                f"Page {page_num + 1} of '{filename}' "
                                f"successfully extracted via OCR "
                                f"({len(ocr_text)} chars)."
                            )

                        else:
                            logger.info(
                                f"OCR did not produce more text for "
                                f"page {page_num + 1}; keeping native text."
                            )

                    except Exception as ocr_error:
                        # OCR failure should not destroy the entire PDF
                        # ingestion process.
                        logger.warning(
                            f"OCR failed for page {page_num + 1} "
                            f"of '{filename}': {ocr_error}"
                        )

                # ---------------------------------------------------------
                # Store page data
                # ---------------------------------------------------------
                pages_data.append(
                    {
                        "text": final_text,
                        "page": page_num + 1,
                        "source": filename,
                        "content_type": content_type,
                        "ocr": ocr_flag,
                    }
                )

            doc.close()

            logger.info(
                f"Successfully processed {len(pages_data)} pages "
                f"from {filename}"
            )

            return pages_data

        except Exception as e:
            logger.error(
                f"Error extracting text from PDF {filename}: {str(e)}"
            )

            raise ValueError(
                f"Could not read PDF file '{filename}': {str(e)}"
            )
