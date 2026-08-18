import re
import uuid
import logging

logger = logging.getLogger(__name__)

class ChunkingService:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_pages(self, pages_data: list[dict]) -> list[dict]:
        """
        Takes page data dictionaries from PDF extraction:
        [{"text": "...", "page": 1, "source": "doc.pdf"}, ...]
        
        Returns chunk dictionaries:
        [
            {
                "chunk_id": "doc.pdf_p1_c0",
                "text": "...",
                "source": "doc.pdf",
                "page": 1,
                "chunk_index": 0,
                "content_type": "text"
            },
            ...
        ]
        """
        chunks = []
        
        for page_info in pages_data:
            text = page_info.get("text", "").strip()
            source = page_info.get("source", "unknown")
            page_num = page_info.get("page", 1)
            content_type = page_info.get("content_type", "text")
            ocr_flag = page_info.get("ocr", False)
            
            if not text:
                continue
                
            page_chunks = self._chunk_text(text)
            
            for idx, chunk_text in enumerate(page_chunks):
                chunk_id = f"{source}_p{page_num}_c{idx}_{uuid.uuid4().hex[:6]}"
                
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "source": source,
                    "page": page_num,
                    "chunk_index": idx,
                    "content_type": content_type,
                    "ocr": ocr_flag
                })
                
        logger.info(f"Generated {len(chunks)} chunks across {len(pages_data)} pages.")
        return chunks

    def _chunk_text(self, text: str) -> list[str]:
        """
        Splits text into chunks of roughly `chunk_size` characters with `chunk_overlap`.
        Tries to break at sentence or paragraph boundaries.
        """
        if len(text) <= self.chunk_size:
            return [text]
            
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + self.chunk_size
            
            if end >= text_len:
                chunks.append(text[start:].strip())
                break
                
            # Look for suitable boundary (period, newline, question mark, semicolon) near end
            search_window = text[max(start, end - 80):min(text_len, end + 40)]
            boundary_matches = [m.start() for m in re.finditer(r'[\.\?\!\n;]', search_window)]
            
            if boundary_matches:
                # Pick the boundary closest to end
                offset = max(start, end - 80)
                best_split = offset + boundary_matches[-1] + 1
                if best_split > start + 50: # Avoid tiny chunks
                    end = best_split

            chunk_content = text[start:end].strip()
            if chunk_content:
                chunks.append(chunk_content)
                
            # Move start forward by (end - overlap)
            start = max(start + 1, end - self.chunk_overlap)
            
        return chunks
