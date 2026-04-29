import os
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import anthropic
from dotenv import load_dotenv
from .auth import require_api_key
from .sessions import set_session_id

UI_FILE = Path(__file__).parent.parent / "frontend" / "index.html"

load_dotenv()

app = FastAPI(title="Tax & Accounting Agent API")
client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
AGENT_ID = os.environ["AGENT_ID"]
ENVIRONMENT_ID = os.environ["ENVIRONMENT_ID"]


@app.get("/")
async def serve_ui():
    return FileResponse(UI_FILE)


class MessageRequest(BaseModel):
    content: str


@app.post("/session")
async def create_session(
    user_id: str,
    _: str = Depends(require_api_key),
):
    session = await client.beta.sessions.create(
        agent=AGENT_ID,
        environment_id=ENVIRONMENT_ID,
        title=f"session-{user_id}",
    )
    set_session_id(user_id, session.id)
    return {"session_id": session.id}


@app.post("/session/{session_id}/message")
async def send_message(
    session_id: str,
    body: MessageRequest,
    _: str = Depends(require_api_key),
):
    async def generate():
        stream = await client.beta.sessions.events.stream(session_id)
        await client.beta.sessions.events.send(
            session_id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": body.content}],
                }
            ],
        )
        async for event in stream:
            if event.type == "agent.message":
                for block in event.content:
                    yield {"data": block.text}
            elif event.type == "session.error":
                yield {"data": f"[ERROR] {event.error.message}"}
                yield {"data": "[DONE]"}
                break
            elif event.type == "session.status_idle":
                yield {"data": "[DONE]"}
                break

    return EventSourceResponse(generate())


@app.get("/session/{session_id}/history")
async def get_history(
    session_id: str,
    _: str = Depends(require_api_key),
):
    response = await client.beta.sessions.events.list(session_id)
    events = response.data if hasattr(response, "data") else list(response)
    return {"events": [e.model_dump() if hasattr(e, "model_dump") else e for e in events]}
