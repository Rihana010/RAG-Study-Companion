from flask import Blueprint, jsonify, request
from app.services.agent_service import AgentService

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/', methods=['POST'])
def send_message():
    """
    RAG Chat endpoint with Agent Tool Router.
    Payload:
    {
        "message": "Give me 5 MCQs on Module 3",
        "history": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
    }
    """
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    history = data.get('history', [])

    if not message:
        return jsonify({'status': 'error', 'message': 'Message text is required.'}), 400

    try:
        agent = AgentService()
        result = agent.process_request(user_query=message, history=history)

        return jsonify({
            'status': 'success',
            'reply': result.get('reply', ''),
            'sources': result.get('sources', []),
            'tool_used': result.get('tool_used', 'answer_question'),
            'quiz_data': result.get('quiz_data', None),
            'flashcards_data': result.get('flashcards_data', None),
            'summary_data': result.get('summary_data', None)
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f"An error occurred while processing your request: {str(e)}"
        }), 500
