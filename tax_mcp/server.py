import os
import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("tax-agent")

BASE_URL = os.environ.get("TAX_AGENT_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEYS", "changeme").split(",")[0].strip()
_session_id: str | None = None


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
    """Ask a US federal tax or accounting question and get a cited answer."""
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
    mcp.run()
