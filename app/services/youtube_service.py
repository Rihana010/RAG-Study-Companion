import re
import urllib.parse
import logging
import requests
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

logger = logging.getLogger(__name__)

class YouTubeService:
    @staticmethod
    def extract_video_id(url: str) -> str:
        """Extracts 11-character video ID from valid YouTube URLs only."""
        if not url:
            return ""

        url_str = url.strip()
        parsed = urllib.parse.urlparse(url_str)
        hostname = (parsed.hostname or '').lower()

        # Strict domain verification
        if hostname not in ('www.youtube.com', 'youtube.com', 'm.youtube.com', 'youtu.be'):
            return ""

        if hostname == 'youtu.be':
            vid_id = parsed.path.strip('/')
            return vid_id if len(vid_id) == 11 else ""

        if parsed.path == '/watch':
            query = urllib.parse.parse_qs(parsed.query)
            vid_ids = query.get('v', [])
            return vid_ids[0] if vid_ids and len(vid_ids[0]) == 11 else ""

        if parsed.path.startswith('/embed/'):
            parts = parsed.path.split('/')
            return parts[2] if len(parts) > 2 and len(parts[2]) == 11 else ""

        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url_str)
        return match.group(1) if match else ""

    @staticmethod
    def fetch_video_title(video_id: str) -> str:
        """Fetches video title using no-embed oEmbed endpoint."""
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            resp = requests.get(oembed_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("title", f"YouTube Video ({video_id})")
        except Exception as e:
            logger.warning(f"Could not fetch video title for {video_id}: {e}")
        return f"YouTube Lecture ({video_id})"

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """Converts floating seconds to MM:SS or HH:MM:SS string format."""
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @classmethod
    def get_transcript(cls, url: str) -> dict:
        """Validates URL and retrieves public YouTube transcript."""
        video_id = cls.extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL. Please provide a valid YouTube link.")

        logger.info(f"Fetching transcript for YouTube video ID: {video_id}")
        video_title = cls.fetch_video_title(video_id)
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            yt_api = YouTubeTranscriptApi()
            fetched_transcript = yt_api.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])
            
            entries = []
            for item in fetched_transcript:
                start_sec = item.get('start', 0.0)
                entries.append({
                    'text': item.get('text', '').strip(),
                    'start_seconds': start_sec,
                    'duration': item.get('duration', 0.0),
                    'timestamp_start': cls.format_timestamp(start_sec)
                })

            if not entries:
                raise ValueError("Transcript was empty.")

            return {
                "video_id": video_id,
                "video_title": video_title,
                "video_url": video_url,
                "entries": entries
            }

        except TranscriptsDisabled:
            raise ValueError(f"Subtitles/transcripts are disabled for video '{video_title}'.")
        except NoTranscriptFound:
            raise ValueError(f"No English transcript found for video '{video_title}'.")
        except Exception as e:
            logger.error(f"Error fetching YouTube transcript for {video_id}: {e}")
            raise ValueError(f"Could not retrieve transcript: {str(e)}")

    @classmethod
    def chunk_transcript(cls, transcript_data: dict, group_window_seconds: float = 60.0) -> list[dict]:
        """Groups transcript entries into ~60-second semantic blocks with timestamps preserved."""
        entries = transcript_data.get("entries", [])
        if not entries:
            return []

        title = transcript_data.get("video_title", "YouTube Video")
        url = transcript_data.get("video_url", "")
        source_name = f"YouTube: {title}"

        chunks = []
        current_texts = []
        current_start_time = entries[0]["timestamp_start"]
        window_start_sec = entries[0]["start_seconds"]

        for idx, entry in enumerate(entries):
            elapsed = entry["start_seconds"] - window_start_sec
            
            # If adding this entry exceeds window and we already have text, flush current block
            if elapsed >= group_window_seconds and current_texts:
                chunk_text = " ".join(current_texts).strip()
                if chunk_text:
                    chunks.append({
                        "chunk_id": f"yt_{transcript_data['video_id']}_{len(chunks)}",
                        "text": chunk_text,
                        "source": source_name,
                        "content_type": "youtube",
                        "video_url": url,
                        "video_title": title,
                        "timestamp_start": current_start_time,
                        "page": 1,
                        "chunk_index": len(chunks),
                        "ocr": False
                    })
                current_texts = []
                current_start_time = entry["timestamp_start"]
                window_start_sec = entry["start_seconds"]

            current_texts.append(entry["text"])

        # Flush any remaining text at the end
        if current_texts:
            chunk_text = " ".join(current_texts).strip()
            if chunk_text:
                chunks.append({
                    "chunk_id": f"yt_{transcript_data['video_id']}_{len(chunks)}",
                    "text": chunk_text,
                    "source": source_name,
                    "content_type": "youtube",
                    "video_url": url,
                    "video_title": title,
                    "timestamp_start": current_start_time,
                    "page": 1,
                    "chunk_index": len(chunks),
                    "ocr": False
                })

        logger.info(f"Grouped transcript into {len(chunks)} timestamped blocks.")
        return chunks
