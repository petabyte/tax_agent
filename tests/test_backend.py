import pytest
from backend.sessions import _store


def setup_function():
    _store.clear()


def test_create_session(api_client, mock_anthropic):
    response = api_client.post(
        "/session",
        params={"user_id": "user-1"},
        headers={"x-api-key": "test-api-key"},
    )
    assert response.status_code == 200
    assert response.json()["session_id"] == "sess_mock"
    mock_anthropic.beta.sessions.create.assert_called_once()


def test_create_session_invalid_key(api_client):
    response = api_client.post(
        "/session",
        params={"user_id": "user-1"},
        headers={"x-api-key": "bad-key"},
    )
    assert response.status_code == 401


def test_create_session_stores_mapping(api_client, mock_anthropic):
    api_client.post(
        "/session",
        params={"user_id": "user-1"},
        headers={"x-api-key": "test-api-key"},
    )
    from backend.sessions import get_session_id
    assert get_session_id("user-1") == "sess_mock"


def test_get_history(api_client, mock_anthropic):
    response = api_client.get(
        "/session/sess_mock/history",
        headers={"x-api-key": "test-api-key"},
    )
    assert response.status_code == 200
    assert "events" in response.json()


def test_get_history_invalid_key(api_client):
    response = api_client.get(
        "/session/sess_mock/history",
        headers={"x-api-key": "bad-key"},
    )
    assert response.status_code == 401
