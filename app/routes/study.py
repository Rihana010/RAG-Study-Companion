from flask import Blueprint, jsonify, request
from app.services.study_service import StudyService
from app.utils.error_responses import bad_request, parse_positive_int

study_bp = Blueprint('study', __name__)

@study_bp.route('/quiz', methods=['POST'])
def generate_quiz():
    """Generates an interactive study quiz."""
    data = request.get_json() or {}
    topic = data.get('topic', '').strip()
    try:
        count = parse_positive_int(
            data.get('count', 5),
            'count',
            5,
            min_value=1,
            max_value=20
        )
    except ValueError as exc:
        return bad_request(str(exc))
    
    study_service = StudyService()
    result = study_service.generate_quiz(topic=topic, count=count)
    
    status_code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), status_code

@study_bp.route('/flashcards', methods=['POST'])
def generate_flashcards():
    """Generates study flashcards."""
    data = request.get_json() or {}
    topic = data.get('topic', '').strip()
    try:
        count = parse_positive_int(
            data.get('count', 10),
            'count',
            10,
            min_value=1,
            max_value=30
        )
    except ValueError as exc:
        return bad_request(str(exc))

    study_service = StudyService()
    result = study_service.generate_flashcards(topic=topic, count=count)

    status_code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), status_code

@study_bp.route('/summary', methods=['POST'])
def summarize():
    """Generates a structured study summary."""
    data = request.get_json() or {}
    topic = data.get('topic', '').strip()

    study_service = StudyService()
    result = study_service.summarize_material(topic=topic)

    status_code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), status_code
