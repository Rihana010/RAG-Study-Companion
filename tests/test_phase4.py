import pytest
from app.services.study_service import StudyService

def test_json_extractor():
    raw_json = '{"title": "Test Quiz", "questions": []}'
    extracted = StudyService._extract_json(raw_json)
    assert extracted.get("title") == "Test Quiz"

    raw_markdown = 'Here is your json output:\n```json\n{"title": "Markdown Quiz"}\n```\nHope this helps!'
    extracted_md = StudyService._extract_json(raw_markdown)
    assert extracted_md.get("title") == "Markdown Quiz"

def test_quiz_endpoint(client):
    response = client.post('/api/study/quiz', json={'topic': 'E-Waste Management', 'count': 5})
    assert response.status_code in (200, 400)
    data = response.get_json()
    assert 'status' in data

def test_flashcards_endpoint(client):
    response = client.post('/api/study/flashcards', json={'topic': 'E-Waste Management', 'count': 5})
    assert response.status_code in (200, 400)
    data = response.get_json()
    assert 'status' in data

def test_summary_endpoint(client):
    response = client.post('/api/study/summary', json={'topic': 'E-Waste Management'})
    assert response.status_code in (200, 400)
    data = response.get_json()
    assert 'status' in data
