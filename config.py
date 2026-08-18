import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-secret-key-12345')
    
    # LLM Settings
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'qwen/qwen3.6-27b')
    
    # Embedding & Vector Database
    EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')
    CHROMA_PERSIST_DIR = str(BASE_DIR / os.getenv('CHROMA_PERSIST_DIR', 'data/chroma'))
    
    # Upload Settings
    UPLOAD_FOLDER = str(BASE_DIR / os.getenv('UPLOAD_FOLDER', 'data/uploads'))
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 33554432)) # 32 MB
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Chunking Configuration
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 500))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 100))
    
    @staticmethod
    def init_app(app):
        # Ensure directories exist
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.CHROMA_PERSIST_DIR, exist_ok=True)
