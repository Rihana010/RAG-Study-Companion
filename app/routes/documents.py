import os
import uuid
from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename

from app.services.pdf_service import PDFService
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.utils.error_responses import internal_error

documents_bp = Blueprint('documents', __name__)

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@documents_bp.route('/', methods=['GET'])
def list_documents():
    """Returns all ingested documents stored in ChromaDB."""
    try:
        vector_store = VectorStore()
        sources = vector_store.list_sources()
        return jsonify({
            'status': 'success',
            'documents': sources
        })
    except Exception as e:
        return internal_error("loading your documents", e)

@documents_bp.route('/upload', methods=['POST'])
def upload_document():
    """Handles PDF file upload, text extraction, chunking, embedding, and vector database storage."""
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part in the request.'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected.'}), 400

    if not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': 'Invalid file format. Only PDF files are supported.'}), 400

    try:
        original_name = secure_filename(file.filename)
        unique_prefix = uuid.uuid4().hex[:8]
        safe_filename = f"{unique_prefix}_{original_name}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_filename)

        # Save file to disk
        file.save(save_path)

        # 1. Extract Text
        pages_data = PDFService.extract_text(save_path, original_name)
        
        if not pages_data or not any(p.get("text", "").strip() for p in pages_data):
            # No readable text extracted via PyMuPDF - might be scanned image PDF (Phase 2 will handle OCR)
            return jsonify({
                'status': 'warning',
                'message': 'PDF uploaded, but no text could be natively extracted. If this is a scanned document, OCR processing is required.',
                'filename': original_name,
                'pages': len(pages_data),
                'chunks': 0
            }), 200

        # 2. Chunk Text
        chunker = ChunkingService(
            chunk_size=current_app.config['CHUNK_SIZE'],
            chunk_overlap=current_app.config['CHUNK_OVERLAP']
        )
        chunks = chunker.chunk_pages(pages_data)

        # 3. Generate Embeddings
        embedder = EmbeddingService()
        texts = [chunk["text"] for chunk in chunks]
        embeddings = embedder.generate_embeddings(texts)

        # 4. Store in ChromaDB
        vector_store = VectorStore()
        vector_store.add_chunks(chunks, embeddings)

        return jsonify({
            'status': 'success',
            'message': f"Successfully ingested '{original_name}'",
            'filename': original_name,
            'pages': len(pages_data),
            'chunks': len(chunks)
        }), 200

    except Exception as e:
        return internal_error("processing your document", e)

@documents_bp.route('/<path:filename>', methods=['DELETE'])
def delete_document(filename: str):
    """Deletes document chunks from ChromaDB and local disk."""
    try:
        vector_store = VectorStore()
        deleted_count = vector_store.delete_source(filename)
        
        # Optionally remove physical file if matching name in uploads folder
        upload_folder = current_app.config['UPLOAD_FOLDER']
        for file_in_dir in os.listdir(upload_folder):
            if file_in_dir.endswith(filename):
                try:
                    os.remove(os.path.join(upload_folder, file_in_dir))
                except Exception:
                    pass

        return jsonify({
            'status': 'success',
            'message': f"Deleted {deleted_count} chunks for document '{filename}'."
        })
    except Exception as e:
        return internal_error("deleting your document", e)
