import logging
from flask import jsonify

logger = logging.getLogger(__name__)


def error_response(message: str, status_code: int):
    return jsonify({
        "status": "error",
        "message": message
    }), status_code


def bad_request(message: str):
    return error_response(message, 400)


def internal_error(action: str, exc: Exception):
    logger.exception("Error while %s", action, exc_info=exc)
    return error_response(
        f"An unexpected error occurred while {action}. Please try again.",
        500
    )


def parse_positive_int(
    value,
    field_name: str,
    default: int,
    *,
    min_value: int = 1,
    max_value: int | None = None
) -> int:
    if value in (None, ""):
        parsed = default
    else:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"'{field_name}' must be a valid integer.") from exc

    if parsed < min_value:
        raise ValueError(f"'{field_name}' must be at least {min_value}.")

    if max_value is not None and parsed > max_value:
        raise ValueError(f"'{field_name}' must be at most {max_value}.")

    return parsed


def safe_value_error_message(raw_message: str, fallback: str) -> str:
    normalized = (raw_message or "").strip()

    if normalized.startswith("Invalid YouTube URL"):
        return "Invalid YouTube URL. Please provide a valid YouTube link."
    if normalized.startswith("Subtitles/transcripts are disabled"):
        return "Transcripts are disabled for this YouTube video."
    if normalized.startswith("No usable English transcript found"):
        return "No usable English transcript is available for this video."
    if normalized.startswith("Transcript was empty"):
        return "The transcript was empty for this video."
    if normalized.startswith("Transcript contained no usable text"):
        return "The transcript contained no usable text."
    if normalized.startswith("Transcript resulted in no usable text"):
        return "Transcript resulted in no usable text."

    return fallback
