import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['app'] == 'RAG Study Companion'

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Study Companion' in response.data

def test_chat_placeholder(client):
    response = client.post('/api/chat/', json={'message': 'Hello world'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'reply' in data

