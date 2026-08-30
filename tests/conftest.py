import pytest
from app import create_app


class _DummyEncoded(list):
    def tolist(self):
        return list(self)


class _DummyEmbeddingModel:
    def encode(self, texts, show_progress_bar=False, convert_to_numpy=True):
        return _DummyEncoded([
            [float((len(text) % 10) + 1), 0.5, 0.25]
            for text in texts
        ])


class _DummyGroqCompletions:
    @staticmethod
    def create(*args, **kwargs):
        class _Message:
            content = "Stubbed response."

        class _Choice:
            message = _Message()

        class _Completion:
            choices = [_Choice()]

        return _Completion()


class _DummyGroqClient:
    def __init__(self):
        self.chat = type(
            "Chat",
            (),
            {"completions": _DummyGroqCompletions()}
        )()


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


@pytest.fixture(autouse=True)
def mock_external_dependencies(monkeypatch):
    monkeypatch.setattr("config.Config.GROQ_API_KEY", "test-key", raising=False)
    monkeypatch.setattr("app.services.embedding_service.SentenceTransformer", lambda *args, **kwargs: _DummyEmbeddingModel())
    monkeypatch.setattr("app.services.llm_service.Groq", lambda *args, **kwargs: _DummyGroqClient())
