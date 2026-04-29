_store: dict[str, str] = {}


def get_session_id(user_id: str) -> str | None:
    return _store.get(user_id)


def set_session_id(user_id: str, session_id: str) -> None:
    _store[user_id] = session_id


def clear_session(user_id: str) -> None:
    _store.pop(user_id, None)
