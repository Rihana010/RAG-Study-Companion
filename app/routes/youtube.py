from flask import Blueprint, jsonify, request
from app.services.youtube_service import YouTubeService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore

youtube_bp = Blueprint('youtube', __name__)

@youtube_bp.route('/ingest', methods=['POST'])
def ingest_youtube():
    """
    YouTube video transcript ingestion endpoint.
    Payload: { "url": "https://www.youtube.com/watch?v=..." }
    """
    data = request.get_json() or {}
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'status': 'error', 'message': 'YouTube URL is required.'}), 400

    try:
        # 1. Retrieve video transcript
        transcript_data = YouTubeService.get_transcript(url)

        # 2. Chunk transcript into timestamped blocks
        chunks = YouTubeService.chunk_transcript(transcript_data)
        if not chunks:
            return jsonify({'status': 'error', 'message': 'Transcript resulted in no usable text.'}), 400

        # 3. Generate embeddings
        embedder = EmbeddingService()
        texts = [c['text'] for c in chunks]
        embeddings = embedder.generate_embeddings(texts)

        # 4. Store in ChromaDB
        vector_store = VectorStore()
        vector_store.add_chunks(chunks, embeddings)

        return jsonify({
            'status': 'success',
            'message': f"Ingested video transcript: '{transcript_data['video_title']}'",
            'video_title': transcript_data['video_title'],
            'video_url': transcript_data['video_url'],
            'chunks': len(chunks)
        }), 200

    except ValueError as ve:
        return jsonify({'status': 'error', 'message': str(ve)}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': f"YouTube processing failed: {str(e)}"}), 500
