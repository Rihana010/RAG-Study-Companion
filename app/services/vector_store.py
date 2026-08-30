import chromadb
from chromadb.config import Settings
import logging
from config import Config

logger = logging.getLogger(__name__)

class VectorStore:
    _instance = None
    _client = None
    _collection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorStore, cls).__new__(cls)
            cls._instance._init_chroma()
        return cls._instance

    def _init_chroma(self):
        persist_dir = Config.CHROMA_PERSIST_DIR
        logger.info(f"Initializing persistent ChromaDB client at: {persist_dir}")
        
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(allow_reset=True, anonymized_telemetry=False)
        )
        
        self._collection = self._client.get_or_create_collection(
            name="study_materials",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB collection 'study_materials' ready. Existing count: {self._collection.count()}")

    def add_chunks(self, chunks: list[dict], embeddings: list[list[float]]):
        """
        Adds text chunks with embeddings and metadata to ChromaDB.
        """
        if not chunks or not embeddings:
            return

        ids = [chunk["chunk_id"] for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = []

        for chunk in chunks:
            meta = {
                "source": str(chunk.get("source", "")),
                "page": int(chunk.get("page", 1)),
                "chunk_index": int(chunk.get("chunk_index", 0)),
                "content_type": str(chunk.get("content_type", "text")),
                "source_type": str(chunk.get("source_type", chunk.get("content_type", "text"))),
                "ocr": bool(chunk.get("ocr", False))
            }
            if "video_url" in chunk:
                meta["video_url"] = str(chunk["video_url"])
            if "video_title" in chunk:
                meta["video_title"] = str(chunk["video_title"])
            if "timestamp_start" in chunk:
                meta["timestamp_start"] = str(chunk["timestamp_start"])
                
            metadatas.append(meta)

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Added {len(chunks)} chunks to ChromaDB. Total count: {self._collection.count()}")

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        """
        Searches ChromaDB for the top_k most similar chunks to query_embedding.
        Returns list of dicts with document text, metadata, and distance.
        """
        if not query_embedding or self._collection.count() == 0:
            return []

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self._collection.count()),
            include=["documents", "metadatas", "distances"]
        )

        retrieved_chunks = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]
            
            for doc, meta, dist in zip(docs, metas, dists):
                retrieved_chunks.append({
                    "text": doc,
                    "metadata": meta,
                    "distance": dist,
                    "similarity": round(1.0 - dist, 4) if dist <= 1.0 else 0.0
                })

        return retrieved_chunks

    def list_sources(self) -> list[dict]:
        """
        Retrieves unique ingested document/video sources with chunk counts.
        """
        if self._collection.count() == 0:
            return []

        all_metas = self._collection.get(include=["metadatas"])["metadatas"]
        source_counts = {}

        for meta in all_metas:
            source = meta.get("source", "Unknown")
            source_type = meta.get("source_type") or meta.get("content_type", "text")
            
            if source not in source_counts:
                source_counts[source] = {
                    "source": source,
                    "source_type": source_type,
                    "content_type": source_type,
                    "chunks": 0,
                    "video_title": meta.get("video_title", None),
                    "video_url": meta.get("video_url", None)
                }
            source_counts[source]["chunks"] += 1

        return list(source_counts.values())

    def delete_source(self, source_name: str) -> int:
        """
        Deletes all chunks belonging to a specific source from ChromaDB.
        Returns count of deleted items.
        """
        if self._collection.count() == 0:
            return 0

        matching = self._collection.get(
            where={"source": source_name},
            include=["metadatas"]
        )
        
        ids_to_delete = matching.get("ids", [])
        if ids_to_delete:
            self._collection.delete(ids=ids_to_delete)
            logger.info(f"Deleted {len(ids_to_delete)} chunks for source: {source_name}")
            
        return len(ids_to_delete)
