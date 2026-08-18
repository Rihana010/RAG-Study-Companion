import os
import pymupdf as fitz
import pytest
from app.services.pdf_service import PDFService
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService

@pytest.fixture
def sample_pdf(tmp_path):
    pdf_path = os.path.join(tmp_path, "sample_physics.pdf")
    doc = fitz.open()
    
    # Page 1
    page1 = doc.new_page()
    page1.insert_text((50, 50), "Module 1: Quantum Physics fundamentals.\nQuantum tunneling allows particles to pass through potential barriers.")
    
    # Page 2
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Module 2: Superconductivity.\nSuperconductors exhibit zero electrical resistance below critical temperature.")
    
    doc.save(pdf_path)
    doc.close()
    return pdf_path

def test_pdf_service(sample_pdf):
    filename = os.path.basename(sample_pdf)
    extracted = PDFService.extract_text(sample_pdf, filename)
    assert len(extracted) == 2
    assert extracted[0]["page"] == 1
    assert "Quantum tunneling" in extracted[0]["text"]
    assert extracted[1]["page"] == 2
    assert "Superconductors" in extracted[1]["text"]

def test_chunking_service():
    chunker = ChunkingService(chunk_size=100, chunk_overlap=20)
    pages_data = [
        {
            "text": "This is a long sentence explaining quantum mechanics and wave-particle duality. " * 3,
            "page": 1,
            "source": "test.pdf"
        }
    ]
    chunks = chunker.chunk_pages(pages_data)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk["source"] == "test.pdf"
        assert chunk["page"] == 1
        assert "chunk_id" in chunk
        assert len(chunk["text"]) <= 120

def test_embedding_service():
    embedder = EmbeddingService()
    embeddings = embedder.generate_embeddings(["What is quantum mechanics?", "Superconductivity principles"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) > 0  # e.g., 384 dimensions for all-MiniLM-L6-v2

def test_vector_store(tmp_path, monkeypatch):
    monkeypatch.setattr("config.Config.CHROMA_PERSIST_DIR", str(tmp_path / "chroma_test"))
    VectorStore._instance = None
    vector_store = VectorStore()
    
    chunks = [
        {
            "chunk_id": "c1",
            "text": "Quantum tunneling occurs in subatomic particles.",
            "source": "physics_test.pdf",
            "page": 1,
            "chunk_index": 0,
            "content_type": "text",
            "ocr": False
        }
    ]
    embedder = EmbeddingService()
    embeddings = embedder.generate_embeddings([c["text"] for c in chunks])
    
    vector_store.add_chunks(chunks, embeddings)
    sources = vector_store.list_sources()
    assert len(sources) == 1
    assert sources[0]["source"] == "physics_test.pdf"
    
    query_emb = embedder.generate_query_embedding("quantum tunneling")
    results = vector_store.search(query_emb, top_k=1)
    assert len(results) == 1
    assert "subatomic" in results[0]["text"]
    
    deleted = vector_store.delete_source("physics_test.pdf")
    assert deleted == 1
    assert len(vector_store.list_sources()) == 0

def test_retrieval_and_llm_service():
    retriever = RetrievalService(top_k=2)
    results = retriever.retrieve_context("What is physics?")
    assert isinstance(results, list)
    
    llm = LLMService()
    response = llm.generate_grounded_response("Explain quantum tunneling", results)
    assert "reply" in response
    assert "sources" in response
