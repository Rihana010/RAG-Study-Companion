from app.services.vector_store import VectorStore


def test_chat_route_accepts_conversation_history_alias(client, monkeypatch):
    captured = {}

    def fake_process_request(self, user_query, history=None):
        captured["history"] = history
        return {
            "status": "success",
            "reply": "ok",
            "sources": [],
            "tool_used": "answer_question"
        }

    monkeypatch.setattr(
        "app.services.agent_service.AgentService.process_request",
        fake_process_request
    )

    history = [{"role": "user", "content": "earlier"}]
    response = client.post(
        "/api/chat/",
        json={"message": "next", "conversation_history": history}
    )

    assert response.status_code == 200
    assert captured["history"] == history


def test_study_quiz_invalid_count_returns_400(client):
    response = client.post(
        "/api/study/quiz",
        json={"topic": "physics", "count": "abc"}
    )
    data = response.get_json()
    assert response.status_code == 400
    assert data["status"] == "error"
    assert "count" in data["message"]


def test_study_flashcards_count_below_min_returns_400(client):
    response = client.post(
        "/api/study/flashcards",
        json={"topic": "physics", "count": 0}
    )
    data = response.get_json()
    assert response.status_code == 400
    assert data["status"] == "error"
    assert data["message"] == "'count' must be an integer between 1 and 30."


def test_documents_list_errors_are_sanitized(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.vector_store.VectorStore.list_sources",
        lambda self: (_ for _ in ()).throw(RuntimeError("internal path leak"))
    )
    response = client.get("/api/documents/")
    data = response.get_json()
    assert response.status_code == 500
    assert data["status"] == "error"
    assert data["message"] == "An unexpected error occurred while loading your documents. Please try again."


def test_youtube_value_error_message_is_sanitized(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.youtube_service.YouTubeService.get_transcript",
        lambda _url: (_ for _ in ()).throw(ValueError("Could not retrieve transcript: token=secret"))
    )
    response = client.post("/api/youtube/ingest", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    data = response.get_json()
    assert response.status_code == 400
    assert data["status"] == "error"
    assert data["message"] == "Could not retrieve transcript for this YouTube video."


def test_list_sources_maps_content_type_to_source_type():
    class FakeCollection:
        @staticmethod
        def count():
            return 1

        @staticmethod
        def get(include=None):
            return {
                "metadatas": [
                    {
                        "source": "video-1",
                        "content_type": "youtube"
                    }
                ]
            }

    store = object.__new__(VectorStore)
    store._collection = FakeCollection()

    sources = store.list_sources()
    assert sources[0]["source_type"] == "youtube"
    assert sources[0]["content_type"] == "youtube"
