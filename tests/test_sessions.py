import pytest
from backend.sessions import get_session_id, set_session_id, clear_session, _store


def setup_function():
    _store.clear()


def test_get_returns_none_for_unknown_user():
    assert get_session_id("user-1") is None


def test_set_then_get_returns_session_id():
    set_session_id("user-1", "sess_abc")
    assert get_session_id("user-1") == "sess_abc"


def test_clear_removes_session():
    set_session_id("user-1", "sess_abc")
    clear_session("user-1")
    assert get_session_id("user-1") is None


def test_clear_unknown_user_does_not_raise():
    clear_session("nonexistent")


def test_multiple_users_are_independent():
    set_session_id("user-1", "sess_aaa")
    set_session_id("user-2", "sess_bbb")
    assert get_session_id("user-1") == "sess_aaa"
    assert get_session_id("user-2") == "sess_bbb"
    clear_session("user-1")
    assert get_session_id("user-1") is None
    assert get_session_id("user-2") == "sess_bbb"
