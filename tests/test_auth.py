import os
import pytest
from fastapi import HTTPException
from unittest.mock import patch


def test_valid_key_returns_key():
    from backend.auth import require_api_key
    with patch.dict(os.environ, {"API_KEYS": "key-a,key-b"}):
        result = require_api_key(x_api_key="key-a")
        assert result == "key-a"


def test_second_valid_key_accepted():
    from backend.auth import require_api_key
    with patch.dict(os.environ, {"API_KEYS": "key-a,key-b"}):
        result = require_api_key(x_api_key="key-b")
        assert result == "key-b"


def test_invalid_key_raises_401():
    from backend.auth import require_api_key
    with patch.dict(os.environ, {"API_KEYS": "key-a"}):
        with pytest.raises(HTTPException) as exc_info:
            require_api_key(x_api_key="wrong")
        assert exc_info.value.status_code == 401


def test_empty_key_raises_401():
    from backend.auth import require_api_key
    with patch.dict(os.environ, {"API_KEYS": "key-a"}):
        with pytest.raises(HTTPException):
            require_api_key(x_api_key="")
