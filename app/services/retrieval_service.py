import logging
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

class RetrievalService:
    def __init__(self, top_k: int = 4):
        self.top_k = top_k
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()

    def retrieve_context(self, query: str, top_k: int = None) -> list[dict]:
        """
        Embeds query and retrieves top_k relevant chunks from vector store.
        Returns formatted list of chunks with metadata and text.
        """
        k = top_k if top_k is not None else self.top_k
        if not query.strip():
            return []

        logger.info(f"Retrieving top {k} context chunks for query: '{query[:50]}...'")
        query_embedding = self.embedding_service.generate_query_embedding(query)
        
        results = self.vector_store.search(query_embedding, top_k=k)
        
        logger.info(f"Retrieved {len(results)} chunks.")
        return results
