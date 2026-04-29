import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("AGENT_ID", "agt_test")
os.environ.setdefault("ENVIRONMENT_ID", "env_test")
os.environ.setdefault("API_KEYS", "test-api-key")


def make_mock_event(event_type: str, text: str = "") -> MagicMock:
    event = MagicMock()
    event.type = event_type
    if event_type == "agent.message":
        block = MagicMock()
        block.text = text
        event.content = [block]
    return event


class MockStream:
    def __init__(self, events):
        self._events = events

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for event in self._events:
            yield event


@pytest.fixture
def mock_anthropic(monkeypatch):
    mock_client = MagicMock()
    mock_client.beta.sessions.create = AsyncMock(return_value=MagicMock(id="sess_mock"))
    mock_client.beta.sessions.events.send = AsyncMock()
    mock_client.beta.sessions.events.list = AsyncMock(return_value=[])

    events = [
        make_mock_event("agent.message", "Your federal tax answer here."),
        make_mock_event("session.status_idle"),
    ]
    mock_client.beta.sessions.events.stream.return_value = MockStream(events)

    with patch("backend.main.client", mock_client):
        yield mock_client


@pytest.fixture
def api_client(mock_anthropic):
    from backend.main import app
    return TestClient(app)
