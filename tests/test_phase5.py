import pytest
from app.services.agent_service import AgentService, ALLOWED_TOOLS

def test_tool_whitelist():
    assert "answer_question" in ALLOWED_TOOLS
    assert "generate_quiz" in ALLOWED_TOOLS
    assert "generate_flashcards" in ALLOWED_TOOLS
    assert "summarize_material" in ALLOWED_TOOLS
    assert "search_documents" in ALLOWED_TOOLS
    assert "search_youtube" in ALLOWED_TOOLS

    # Arbitrary dangerous calls MUST NOT be in whitelist
    assert "system_exec" not in ALLOWED_TOOLS
    assert "os_system" not in ALLOWED_TOOLS
    assert "eval" not in ALLOWED_TOOLS

def test_agent_service_fallback_to_grounded():
    agent = AgentService()
    # Query when library is empty should return grounded response / notice
    result = agent.process_request("What is superconductivity?")
    assert result["status"] == "success"
    assert "reply" in result
    assert "tool_used" in result

def test_agent_quiz_routing_empty_lib():
    agent = AgentService()
    result = agent.process_request("Give me 5 MCQs on Module 3")
    # Even if intent router selects quiz, empty library returns clear error message
    assert "status" in result
    assert "reply" in result

def test_chat_endpoint_agent_integration(client):
    response = client.post('/api/chat/', json={'message': 'Explain quantum physics'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'tool_used' in data
