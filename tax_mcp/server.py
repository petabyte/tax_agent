import os
import httpx
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.responses import PlainTextResponse
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("tax-agent")

BASE_URL = os.environ.get("TAX_AGENT_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEYS", "changeme").split(",")[0].strip()
MCP_API_KEY = os.environ.get("MCP_API_KEY", "")
_session_id: str | None = None


class _AuthMiddleware:
    """ASGI middleware that checks x-api-key header or ?api_key= query param."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if MCP_API_KEY and scope["type"] in ("http", "websocket"):
            headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
            key = headers.get("x-api-key", "")
            if not key:
                qs = scope.get("query_string", b"").decode()
                params = dict(p.split("=", 1) for p in qs.split("&") if "=" in p)
                key = params.get("api_key", "")
            if key != MCP_API_KEY:
                response = PlainTextResponse("Unauthorized", status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


async def _get_or_create_session() -> str:
    global _session_id
    if _session_id:
        return _session_id
    async with httpx.AsyncClient() as http:
        r = await http.post(
            f"{BASE_URL}/session",
            params={"user_id": "mcp-default"},
            headers={"x-api-key": API_KEY},
        )
        r.raise_for_status()
        _session_id = r.json()["session_id"]
    return _session_id


@mcp.tool()
async def ask_tax_question(question: str) -> str:
    """Ask a US tax or accounting question (federal, state, local, municipal, or city) and get a cited answer."""
    session_id = await _get_or_create_session()
    answer_parts: list[str] = []

    async with httpx.AsyncClient(timeout=120) as http:
        async with http.stream(
            "POST",
            f"{BASE_URL}/session/{session_id}/message",
            json={"content": question},
            headers={"x-api-key": API_KEY, "Accept": "text/event-stream"},
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                answer_parts.append(data)

    return "".join(answer_parts)


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        # Disable DNS rebinding protection — safe for a public server with its own auth
        mcp.settings.transport_security.enable_dns_rebinding_protection = False
        port = int(os.environ.get("PORT", 8001))
        app = _AuthMiddleware(mcp.sse_app())
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        mcp.run()
