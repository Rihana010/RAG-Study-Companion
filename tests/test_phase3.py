import pytest
from app.services.youtube_service import YouTubeService

def test_youtube_video_id_extraction():
    url1 = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    url2 = "https://youtu.be/dQw4w9WgXcQ"
    url3 = "https://www.youtube.com/embed/dQw4w9WgXcQ"
    invalid_url = "https://example.com/not_youtube"
    
    assert YouTubeService.extract_video_id(url1) == "dQw4w9WgXcQ"
    assert YouTubeService.extract_video_id(url2) == "dQw4w9WgXcQ"
    assert YouTubeService.extract_video_id(url3) == "dQw4w9WgXcQ"
    assert YouTubeService.extract_video_id(invalid_url) == ""

def test_timestamp_formatting():
    assert YouTubeService.format_timestamp(0) == "00:00"
    assert YouTubeService.format_timestamp(65) == "01:05"
    assert YouTubeService.format_timestamp(3665) == "01:01:05"

def test_transcript_chunking():
    transcript_data = {
        "video_id": "test_id_123",
        "video_title": "Quantum Mechanics Intro",
        "video_url": "https://www.youtube.com/watch?v=test_id_123",
        "entries": [
            {"text": "Welcome to quantum mechanics lecture.", "start_seconds": 0.0, "duration": 5.0, "timestamp_start": "00:00"},
            {"text": "Today we cover wave-particle duality.", "start_seconds": 30.0, "duration": 4.0, "timestamp_start": "00:30"},
            {"text": "Subatomic particles behave like waves.", "start_seconds": 70.0, "duration": 5.0, "timestamp_start": "01:10"}
        ]
    }
    
    chunks = YouTubeService.chunk_transcript(transcript_data, group_window_seconds=60.0)
    assert len(chunks) == 2
    assert chunks[0]["content_type"] == "youtube"
    assert chunks[0]["timestamp_start"] == "00:00"
    assert "quantum mechanics" in chunks[0]["text"]
    assert chunks[1]["timestamp_start"] == "01:10"

def test_invalid_youtube_ingest(client):
    response = client.post('/api/youtube/ingest', json={'url': 'invalid-link'})
    assert response.status_code == 400
    data = response.get_json()
    assert data['status'] == 'error'
    assert 'Invalid YouTube URL' in data['message']
