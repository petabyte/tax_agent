import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_ask_tax_question_returns_answer():
    answer_chunks = ["Your federal ", "tax answer here.", "[DONE]"]

    async def mock_stream_lines():
        for chunk in answer_chunks:
            yield f"data: {chunk}"

    mock_response = MagicMock()
    mock_response.aiter_lines = mock_stream_lines
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_post = AsyncMock(return_value=MagicMock(
        json=lambda: {"session_id": "sess_test"},
        raise_for_status=lambda: None,
    ))

    mock_http_client = MagicMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)
    mock_http_client.post = mock_post
    mock_http_client.stream = MagicMock(return_value=mock_response)

    with patch("tax_mcp.server.httpx.AsyncClient", return_value=mock_http_client):
        # Reset the module-level _session_id before each test
        import tax_mcp.server as srv
        srv._session_id = None
        from tax_mcp.server import ask_tax_question
        result = await ask_tax_question("What is the standard deduction for 2025?")

    assert "Your federal tax answer here." in result
    assert "[DONE]" not in result


@pytest.mark.asyncio
async def test_ask_tax_question_strips_done_marker():
    async def mock_stream_lines():
        yield "data: The answer."
        yield "data: [DONE]"

    mock_response = MagicMock()
    mock_response.aiter_lines = mock_stream_lines
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_http_client = MagicMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)
    mock_http_client.post = AsyncMock(return_value=MagicMock(
        json=lambda: {"session_id": "sess_x"},
        raise_for_status=lambda: None,
    ))
    mock_http_client.stream = MagicMock(return_value=mock_response)

    with patch("tax_mcp.server.httpx.AsyncClient", return_value=mock_http_client):
        import tax_mcp.server as srv
        srv._session_id = None
        from tax_mcp.server import ask_tax_question
        result = await ask_tax_question("What is the 401k limit?")

    assert result == "The answer."
