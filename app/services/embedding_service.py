import logging
from sentence_transformers import SentenceTransformer
from config import Config

logger = logging.getLogger(__name__)

class EmbeddingService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._initialize_model()
        return cls._instance

    def _initialize_model(self):
        model_name = Config.EMBEDDING_MODEL_NAME
        logger.info(f"Loading SentenceTransformer model: {model_name}...")
        try:
            self._model = SentenceTransformer(model_name)
            logger.info("SentenceTransformer model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model '{model_name}': {e}")
            raise e

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generates vector embeddings for a list of text strings.
        Returns a list of float vectors.
        """
        if not texts:
            return []
            
        if self._model is None:
            self._initialize_model()
            
        logger.debug(f"Generating embeddings for {len(texts)} items.")
        embeddings = self._model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return embeddings.tolist()

    def generate_query_embedding(self, query: str) -> list[float]:
        """
        Generates vector embedding for a single query string.
        """
        embeddings = self.generate_embeddings([query])
        return embeddings[0] if embeddings else []
