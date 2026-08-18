import re
import urllib.parse
import logging
import requests

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)

logger = logging.getLogger(__name__)


class YouTubeService:

    # ============================================================
    # VIDEO ID
    # ============================================================

    @staticmethod
    def extract_video_id(url: str) -> str:
        """
        Extract an 11-character YouTube video ID from a valid
        YouTube URL.
        """

        if not url:
            return ""

        url_str = url.strip()

        try:
            parsed = urllib.parse.urlparse(url_str)
        except Exception:
            return ""

        hostname = (
            parsed.hostname or ""
        ).lower()

        # Strict domain verification
        allowed_hosts = {
            "www.youtube.com",
            "youtube.com",
            "m.youtube.com",
            "youtu.be",
        }

        if hostname not in allowed_hosts:
            return ""

        # --------------------------------------------------------
        # youtu.be/<id>
        # --------------------------------------------------------

        if hostname == "youtu.be":

            video_id = parsed.path.strip("/")

            if len(video_id) == 11:
                return video_id

            return ""

        # --------------------------------------------------------
        # youtube.com/watch?v=<id>
        # --------------------------------------------------------

        if parsed.path == "/watch":

            query = urllib.parse.parse_qs(
                parsed.query
            )

            video_ids = query.get("v", [])

            if video_ids:

                video_id = video_ids[0]

                if len(video_id) == 11:
                    return video_id

            return ""

        # --------------------------------------------------------
        # youtube.com/embed/<id>
        # --------------------------------------------------------

        if parsed.path.startswith("/embed/"):

            parts = parsed.path.split("/")

            if (
                len(parts) > 2
                and len(parts[2]) == 11
            ):
                return parts[2]

            return ""

        # --------------------------------------------------------
        # youtube.com/shorts/<id>
        # --------------------------------------------------------

        if parsed.path.startswith("/shorts/"):

            parts = parsed.path.split("/")

            if (
                len(parts) > 2
                and len(parts[2]) == 11
            ):
                return parts[2]

            return ""

        # --------------------------------------------------------
        # Fallback
        # --------------------------------------------------------

        match = re.search(
            r"(?:v=|/)([0-9A-Za-z_-]{11})",
            url_str
        )

        if match:
            return match.group(1)

        return ""

    # ============================================================
    # VIDEO TITLE
    # ============================================================

    @staticmethod
    def fetch_video_title(video_id: str) -> str:
        """
        Fetch the YouTube video title using the public oEmbed
        endpoint.
        """

        try:

            oembed_url = (
                "https://www.youtube.com/oembed"
                f"?url=https://www.youtube.com/watch?v={video_id}"
                "&format=json"
            )

            response = requests.get(
                oembed_url,
                timeout=8
            )

            if response.status_code == 200:

                data = response.json()

                title = data.get(
                    "title"
                )

                if title:
                    return title

        except Exception as e:

            logger.warning(
                "Could not fetch video title for %s: %s",
                video_id,
                e
            )

        return f"YouTube Lecture ({video_id})"

    # ============================================================
    # TIMESTAMP
    # ============================================================

    @staticmethod
    def format_timestamp(
        seconds: float
    ) -> str:
        """
        Convert seconds to MM:SS or HH:MM:SS.
        """

        try:
            total_seconds = int(
                float(seconds)
            )
        except (
            TypeError,
            ValueError
        ):
            total_seconds = 0

        hours = total_seconds // 3600

        minutes = (
            total_seconds % 3600
        ) // 60

        secs = total_seconds % 60

        if hours > 0:

            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{secs:02d}"
            )

        return (
            f"{minutes:02d}:"
            f"{secs:02d}"
        )

    # ============================================================
    # TRANSCRIPT
    # ============================================================

    @classmethod
    def get_transcript(
        cls,
        url: str
    ) -> dict:
        """
        Validate a YouTube URL and retrieve its transcript.

        Compatible with youtube-transcript-api 1.2.x.
        """

        video_id = cls.extract_video_id(
            url
        )

        if not video_id:

            raise ValueError(
                "Invalid YouTube URL. "
                "Please provide a valid YouTube link."
            )

        logger.info(
            "Fetching transcript for YouTube video ID: %s",
            video_id
        )

        video_title = cls.fetch_video_title(
            video_id
        )

        video_url = (
            f"https://www.youtube.com/watch?v={video_id}"
        )

        try:

            # ----------------------------------------------------
            # Create API client
            # ----------------------------------------------------

            yt_api = YouTubeTranscriptApi()

            # ----------------------------------------------------
            # Get available transcripts
            # ----------------------------------------------------

            transcript_list = (
                yt_api.list(video_id)
            )

            transcript = None

            # ----------------------------------------------------
            # Prefer manually created English transcript
            # ----------------------------------------------------

            try:

                transcript = (
                    transcript_list
                    .find_manually_created_transcript(
                        ["en", "en-US", "en-GB"]
                    )
                )

                logger.info(
                    "Using manually created English transcript."
                )

            except Exception:

                transcript = None

            # ----------------------------------------------------
            # Fall back to generated English transcript
            # ----------------------------------------------------

            if transcript is None:

                try:

                    transcript = (
                        transcript_list
                        .find_generated_transcript(
                            ["en", "en-US", "en-GB"]
                        )
                    )

                    logger.info(
                        "Using automatically generated English transcript."
                    )

                except Exception:

                    transcript = None

            # ----------------------------------------------------
            # If English isn't available, try translatable
            # English transcripts.
            # ----------------------------------------------------

            if transcript is None:

                try:

                    for available in transcript_list:

                        if available.is_translatable:

                            transcript = (
                                available.translate("en")
                            )

                            logger.info(
                                "Using translated English transcript."
                            )

                            break

                except Exception as translation_error:

                    logger.warning(
                        "Could not find a translatable "
                        "transcript: %s",
                        translation_error
                    )

            # ----------------------------------------------------
            # Nothing found
            # ----------------------------------------------------

            if transcript is None:

                raise NoTranscriptFound(
                    video_id,
                    [],
                )

            # ----------------------------------------------------
            # Fetch transcript entries
            # ----------------------------------------------------

            fetched_transcript = (
                transcript.fetch()
            )

            if not fetched_transcript:

                raise ValueError(
                    "Transcript was empty."
                )

            entries = []

            for item in fetched_transcript:

                # youtube-transcript-api 1.x returns
                # FetchedTranscriptSnippet objects.
                text = getattr(
                    item,
                    "text",
                    ""
                )

                start_seconds = getattr(
                    item,
                    "start",
                    0.0
                )

                duration = getattr(
                    item,
                    "duration",
                    0.0
                )

                text = (
                    str(text)
                    .strip()
                )

                if not text:
                    continue

                entries.append(
                    {
                        "text": text,

                        "start_seconds": (
                            float(start_seconds)
                        ),

                        "duration": (
                            float(duration)
                        ),

                        "timestamp_start": (
                            cls.format_timestamp(
                                start_seconds
                            )
                        ),
                    }
                )

            if not entries:

                raise ValueError(
                    "Transcript contained no usable text."
                )

            logger.info(
                "Successfully fetched %d transcript "
                "entries for '%s'.",
                len(entries),
                video_title
            )

            return {
                "video_id": video_id,
                "video_title": video_title,
                "video_url": video_url,
                "entries": entries,
            }

        except TranscriptsDisabled:

            raise ValueError(
                f"Subtitles/transcripts are disabled "
                f"for video '{video_title}'."
            )

        except NoTranscriptFound:

            raise ValueError(
                f"No usable English transcript found "
                f"for video '{video_title}'."
            )

        except Exception as e:

            logger.exception(
                "Error fetching YouTube transcript "
                "for %s",
                video_id
            )

            raise ValueError(
                f"Could not retrieve transcript: {str(e)}"
            )

    # ============================================================
    # CHUNK TRANSCRIPT
    # ============================================================

    @classmethod
    def chunk_transcript(
        cls,
        transcript_data: dict,
        group_window_seconds: float = 60.0
    ) -> list[dict]:
        """
        Groups transcript entries into approximately
        60-second blocks while preserving timestamps.
        """

        entries = transcript_data.get(
            "entries",
            []
        )

        if not entries:
            return []

        title = transcript_data.get(
            "video_title",
            "YouTube Video"
        )

        url = transcript_data.get(
            "video_url",
            ""
        )

        video_id = transcript_data.get(
            "video_id",
            "unknown"
        )

        source_name = (
            f"YouTube: {title}"
        )

        chunks = []

        current_texts = []

        first_entry = entries[0]

        current_start_time = (
            first_entry.get(
                "timestamp_start",
                "00:00"
            )
        )

        window_start_sec = float(
            first_entry.get(
                "start_seconds",
                0.0
            )
        )

        # --------------------------------------------------------
        # Build timestamped chunks
        # --------------------------------------------------------

        for entry in entries:

            entry_start = float(
                entry.get(
                    "start_seconds",
                    0.0
                )
            )

            elapsed = (
                entry_start
                - window_start_sec
            )

            # Flush current block when window is reached.
            if (
                elapsed >= group_window_seconds
                and current_texts
            ):

                chunk_text = " ".join(
                    current_texts
                ).strip()

                if chunk_text:

                    chunks.append(
                        {
                            "chunk_id": (
                                f"yt_{video_id}_"
                                f"{len(chunks)}"
                            ),

                            "text": chunk_text,

                            "source": source_name,

                            "content_type": "youtube",

                            "video_url": url,

                            "video_title": title,

                            "timestamp_start": (
                                current_start_time
                            ),

                            "page": 1,

                            "chunk_index": (
                                len(chunks)
                            ),

                            "ocr": False,
                        }
                    )

                current_texts = []

                current_start_time = (
                    entry.get(
                        "timestamp_start",
                        cls.format_timestamp(
                            entry_start
                        )
                    )
                )

                window_start_sec = (
                    entry_start
                )

            text = entry.get(
                "text",
                ""
            ).strip()

            if text:
                current_texts.append(
                    text
                )

        # --------------------------------------------------------
        # Flush final block
        # --------------------------------------------------------

        if current_texts:

            chunk_text = " ".join(
                current_texts
            ).strip()

            if chunk_text:

                chunks.append(
                    {
                        "chunk_id": (
                            f"yt_{video_id}_"
                            f"{len(chunks)}"
                        ),

                        "text": chunk_text,

                        "source": source_name,

                        "content_type": "youtube",

                        "video_url": url,

                        "video_title": title,

                        "timestamp_start": (
                            current_start_time
                        ),

                        "page": 1,

                        "chunk_index": (
                            len(chunks)
                        ),

                        "ocr": False,
                    }
                )

        logger.info(
            "Grouped transcript into %d "
            "timestamped blocks.",
            len(chunks)
        )

        return chunks