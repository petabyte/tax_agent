# Tax & Accounting Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a US federal tax & accounting Q&A agent using Claude Managed Agents, served via a FastAPI backend and an MCP server for Claude Desktop / claude.ai distribution.

**Architecture:** One Claude Managed Agent definition shared across all tenants; each user conversation gets its own Session. A FastAPI backend handles auth, session lifecycle, and SSE streaming. An MCP server wraps the backend via FastMCP for distribution through the Claude ecosystem. Tax reference data (2025 IRS figures) is embedded directly in the system prompt to avoid file-mounting complexity.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, sse-starlette, anthropic SDK (`AsyncAnthropic`), FastMCP (mcp package), httpx, python-dotenv, pytest, pytest-asyncio

**API Reference:** https://platform.claude.com/docs/en/managed-agents/sessions

---

## File Structure

```
managed_agents/
├── data/
│   └── tax_data.json          # Source-of-truth IRS figures (updated annually)
├── agent/
│   ├── setup.py               # One-time script: creates Agent + Environment via SDK
│   └── system_prompt.txt      # Agent system prompt with embedded 2025 tax data
├── backend/
│   ├── __init__.py
│   ├── main.py                # FastAPI app + all three routes
│   ├── sessions.py            # In-memory user_id → session_id store
│   └── auth.py                # X-Api-Key header validation
├── mcp/
│   ├── __init__.py
│   └── server.py              # FastMCP server exposing ask_tax_question tool
├── tests/
│   ├── conftest.py            # Shared fixtures and mock Anthropic client
│   ├── test_sessions.py       # Unit tests for sessions.py
│   ├── test_auth.py           # Unit tests for auth.py
│   ├── test_backend.py        # FastAPI route tests (mocked Anthropic)
│   └── test_golden.py         # Golden question set (real API, marked integration)
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `backend/__init__.py`, `mcp/__init__.py`

- [ ] **Step 1: Initialize git and create directory structure**

```bash
cd /home/geosan/PROJECTS/managed_agents
git init
mkdir -p data agent backend mcp tests
touch backend/__init__.py mcp/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write requirements.txt**

```
anthropic>=0.50.0
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
sse-starlette>=2.1.0
python-dotenv>=1.0.0
mcp>=1.6.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

- [ ] **Step 3: Write .env.example**

```
ANTHROPIC_API_KEY=sk-ant-...
AGENT_ID=
ENVIRONMENT_ID=
# Comma-separated list of valid API keys for the backend
API_KEYS=changeme
```

- [ ] **Step 4: Write .gitignore**

```
.env
__pycache__/
*.pyc
.pytest_cache/
.venv/
dist/
*.egg-info/
```

- [ ] **Step 5: Install dependencies**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example .gitignore backend/__init__.py mcp/__init__.py tests/__init__.py
git commit -m "chore: project scaffolding"
```

---

## Task 2: Tax Reference Data + System Prompt

**Files:**
- Create: `data/tax_data.json`
- Create: `agent/system_prompt.txt`

- [ ] **Step 1: Write data/tax_data.json**

This is the annual source of truth. Update every January when IRS releases new figures.

```json
{
  "tax_year": 2025,
  "brackets": {
    "single": [
      {"rate": 0.10, "min": 0, "max": 11925},
      {"rate": 0.12, "min": 11926, "max": 48475},
      {"rate": 0.22, "min": 48476, "max": 103350},
      {"rate": 0.24, "min": 103351, "max": 197300},
      {"rate": 0.32, "min": 197301, "max": 250525},
      {"rate": 0.35, "min": 250526, "max": 626350},
      {"rate": 0.37, "min": 626351, "max": null}
    ],
    "married_filing_jointly": [
      {"rate": 0.10, "min": 0, "max": 23850},
      {"rate": 0.12, "min": 23851, "max": 96950},
      {"rate": 0.22, "min": 96951, "max": 206700},
      {"rate": 0.24, "min": 206701, "max": 394600},
      {"rate": 0.32, "min": 394601, "max": 501050},
      {"rate": 0.35, "min": 501051, "max": 751600},
      {"rate": 0.37, "min": 751601, "max": null}
    ],
    "married_filing_separately": [
      {"rate": 0.10, "min": 0, "max": 11925},
      {"rate": 0.12, "min": 11926, "max": 48475},
      {"rate": 0.22, "min": 48476, "max": 103350},
      {"rate": 0.24, "min": 103351, "max": 197300},
      {"rate": 0.32, "min": 197301, "max": 250525},
      {"rate": 0.35, "min": 250526, "max": 375800},
      {"rate": 0.37, "min": 375801, "max": null}
    ],
    "head_of_household": [
      {"rate": 0.10, "min": 0, "max": 17000},
      {"rate": 0.12, "min": 17001, "max": 64850},
      {"rate": 0.22, "min": 64851, "max": 103350},
      {"rate": 0.24, "min": 103351, "max": 197300},
      {"rate": 0.32, "min": 197301, "max": 250500},
      {"rate": 0.35, "min": 250501, "max": 626350},
      {"rate": 0.37, "min": 626351, "max": null}
    ]
  },
  "standard_deductions": {
    "single": 15000,
    "married_filing_jointly": 30000,
    "married_filing_separately": 15000,
    "head_of_household": 22500,
    "additional_65_or_blind_single": 1600,
    "additional_65_or_blind_mfj_per_person": 1300
  },
  "contribution_limits": {
    "401k_employee": 23500,
    "401k_catchup_50_plus": 31000,
    "ira": 7000,
    "ira_catchup_50_plus": 8000,
    "roth_ira_phaseout_single_start": 150000,
    "roth_ira_phaseout_single_end": 165000,
    "roth_ira_phaseout_mfj_start": 236000,
    "roth_ira_phaseout_mfj_end": 246000,
    "hsa_self_only": 4300,
    "hsa_family": 8550,
    "hsa_catchup_55_plus": 1000,
    "sep_ira_max": 70000,
    "simple_ira": 16500,
    "simple_ira_catchup_50_plus": 20000,
    "fsa_healthcare": 3300
  },
  "self_employment_tax": {
    "rate_below_wage_base": 0.153,
    "rate_above_wage_base": 0.029,
    "ss_wage_base": 176100,
    "deductible_portion": 0.50
  },
  "deadlines_2026": {
    "q4_2025_estimated": "2026-01-15",
    "w2_1099_must_be_sent": "2026-01-31",
    "2025_return_and_q1_2026_estimated": "2026-04-15",
    "q2_2026_estimated": "2026-06-16",
    "q3_2026_estimated": "2026-09-15",
    "2025_extended_return": "2026-10-15"
  }
}
```

- [ ] **Step 2: Write agent/system_prompt.txt**

```
You are a US federal tax and accounting expert. Answer questions accurately and cite official sources in every response.

## 2025 TAX REFERENCE DATA

### Federal Income Tax Brackets (Tax Year 2025)

**Single Filers:**
10%: $0–$11,925 | 12%: $11,926–$48,475 | 22%: $48,476–$103,350
24%: $103,351–$197,300 | 32%: $197,301–$250,525 | 35%: $250,526–$626,350 | 37%: over $626,350

**Married Filing Jointly:**
10%: $0–$23,850 | 12%: $23,851–$96,950 | 22%: $96,951–$206,700
24%: $206,701–$394,600 | 32%: $394,601–$501,050 | 35%: $501,051–$751,600 | 37%: over $751,600

**Married Filing Separately:**
10%: $0–$11,925 | 12%: $11,926–$48,475 | 22%: $48,476–$103,350
24%: $103,351–$197,300 | 32%: $197,301–$250,525 | 35%: $250,526–$375,800 | 37%: over $375,800

**Head of Household:**
10%: $0–$17,000 | 12%: $17,001–$64,850 | 22%: $64,851–$103,350
24%: $103,351–$197,300 | 32%: $197,301–$250,500 | 35%: $250,501–$626,350 | 37%: over $626,350

### Standard Deductions (2025)
Single: $15,000 | MFJ: $30,000 | MFS: $15,000 | HoH: $22,500
Additional (age 65+/blind): $1,600 (single/HoH), $1,300 per qualifying person (MFJ/MFS)

### Contribution Limits (2025)
401(k) employee: $23,500 ($31,000 if 50+)
IRA: $7,000 ($8,000 if 50+) | Roth IRA phase-out: $150k–$165k (single), $236k–$246k (MFJ)
HSA: $4,300 self-only / $8,550 family (+$1,000 catch-up age 55+)
SEP-IRA: 25% of compensation, max $70,000
SIMPLE IRA: $16,500 ($20,000 if 50+) | Healthcare FSA: $3,300

### Self-Employment Tax (2025)
15.3% on net SE income up to $176,100 SS wage base; 2.9% above. Deduct 50% on Schedule 1.

### Key Deadlines
Jan 15, 2026: Q4 2025 estimated payment | Jan 31, 2026: W-2s/1099s due to recipients
Apr 15, 2026: 2025 return due + Q1 2026 estimated | Jun 16, 2026: Q2 2026 estimated
Sep 15, 2026: Q3 2026 estimated | Oct 15, 2026: Extended 2025 return due

---

## BEHAVIOR

**Search:** Always WebSearch before answering questions about rules, eligibility, credits, deductions, or anything not in the reference data above. Restrict searches to: irs.gov, treasury.gov, federalregister.gov, uscode.house.gov (26 USC). If results are incomplete, use WebFetch to retrieve the full IRS publication text.

**Tone:** Infer expertise from phrasing. Respond technically to technical questions (cite IRC sections, use tax terminology without defining basics). Respond in plain English to lay questions. Never condescend.

**Citations:** End every factual answer with "Source:" citing IRS publication number, IRC section, or URL.
Example: "Source: IRS Publication 505; IRC §3101"

**Scope:**
- US federal tax only. For state questions: "I cover US federal tax only. For state-specific rules, check your state's department of revenue website."
- No legal advice: "I can explain how the tax rules work, but I can't give legal advice for your specific situation. Consult a CPA or tax attorney."
- International tax beyond basic FBAR/FATCA: "International tax is outside my current scope. Consult a tax professional specializing in international tax."

**Accuracy:** If uncertain about a figure or rule, say so explicitly and direct the user to IRS.gov to verify. Never fabricate IRC sections, publication numbers, or dollar amounts.
```

- [ ] **Step 3: Commit**

```bash
git add data/tax_data.json agent/system_prompt.txt
git commit -m "feat: add IRS 2025 tax reference data and agent system prompt"
```

---

## Task 3: Agent + Environment Setup Script

**Files:**
- Create: `agent/setup.py`

This script runs once to create the Agent and Environment definitions in Managed Agents. It writes the resulting IDs to `.env`.

- [ ] **Step 1: Write agent/setup.py**

```python
import os
import re
from pathlib import Path
import anthropic
from dotenv import load_dotenv

load_dotenv()


def update_env(key: str, value: str) -> None:
    env_path = Path(".env")
    content = env_path.read_text() if env_path.exists() else ""
    pattern = rf"^{key}=.*$"
    replacement = f"{key}={value}"
    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        content += f"\n{replacement}"
    env_path.write_text(content)


def main() -> None:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    system_prompt = Path("agent/system_prompt.txt").read_text()

    print("Creating agent...")
    agent = client.beta.agents.create(
        name="Federal Tax & Accounting Agent",
        model="claude-sonnet-4-6",
        system=system_prompt,
        tools=[{"type": "agent_toolset_20260401"}],
    )
    print(f"Agent ID: {agent.id}")
    update_env("AGENT_ID", agent.id)

    print("Creating environment...")
    environment = client.beta.environments.create(
        name="tax-agent-env",
        config={
            "type": "cloud",
            "networking": {"type": "unrestricted"},
        },
    )
    print(f"Environment ID: {environment.id}")
    update_env("ENVIRONMENT_ID", environment.id)

    print("Done. IDs written to .env")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the setup script to verify it works**

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
python agent/setup.py
```

Expected output:
```
Creating agent...
Agent ID: agt_...
Creating environment...
Environment ID: env_...
Done. IDs written to .env
```

Verify `.env` now contains `AGENT_ID` and `ENVIRONMENT_ID` values.

- [ ] **Step 3: Commit**

```bash
git add agent/setup.py
git commit -m "feat: add agent and environment setup script"
```

---

## Task 4: Session Store

**Files:**
- Create: `backend/sessions.py`
- Create: `tests/conftest.py`
- Create: `tests/test_sessions.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_sessions.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_sessions.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.sessions'`

- [ ] **Step 3: Write backend/sessions.py**

```python
_store: dict[str, str] = {}


def get_session_id(user_id: str) -> str | None:
    return _store.get(user_id)


def set_session_id(user_id: str, session_id: str) -> None:
    _store[user_id] = session_id


def clear_session(user_id: str) -> None:
    _store.pop(user_id, None)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_sessions.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/sessions.py tests/test_sessions.py
git commit -m "feat: add in-memory session store"
```

---

## Task 5: Auth Middleware

**Files:**
- Create: `backend/auth.py`
- Create: `tests/test_auth.py`
- Update: `tests/conftest.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_auth.py`:

```python
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
```

- [ ] **Step 2: Run to verify tests fail**

```bash
pytest tests/test_auth.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.auth'`

- [ ] **Step 3: Write backend/auth.py**

```python
import os
from fastapi import Header, HTTPException


def require_api_key(x_api_key: str = Header(...)) -> str:
    valid_keys = {k.strip() for k in os.environ.get("API_KEYS", "").split(",") if k.strip()}
    if x_api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_auth.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/auth.py tests/test_auth.py
git commit -m "feat: add API key auth middleware"
```

---

## Task 6: FastAPI Backend

**Files:**
- Create: `backend/main.py`
- Create: `tests/conftest.py`
- Create: `tests/test_backend.py`

- [ ] **Step 1: Write tests/conftest.py with mock Anthropic client**

```python
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
    mock_client.beta.sessions.create.return_value = MagicMock(id="sess_mock")
    mock_client.beta.sessions.events.send = AsyncMock()
    mock_client.beta.sessions.events.list.return_value = []

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
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_backend.py`:

```python
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
```

- [ ] **Step 3: Run to verify tests fail**

```bash
pytest tests/test_backend.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.main'`

- [ ] **Step 4: Write backend/main.py**

```python
import os
import asyncio
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import anthropic
from dotenv import load_dotenv
from .auth import require_api_key
from .sessions import get_session_id, set_session_id

load_dotenv()

app = FastAPI(title="Tax & Accounting Agent API")
client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
AGENT_ID = os.environ["AGENT_ID"]
ENVIRONMENT_ID = os.environ["ENVIRONMENT_ID"]


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
        async with client.beta.sessions.events.stream(session_id) as stream:
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_backend.py -v
```

Expected: 5 passed

- [ ] **Step 6: Smoke-test the server locally**

```bash
uvicorn backend.main:app --reload --port 8000
```

In a second terminal:
```bash
curl -s -X POST "http://localhost:8000/session?user_id=test" \
  -H "x-api-key: changeme" | jq .
```

Expected: `{"session_id": "sess_..."}`

- [ ] **Step 7: Commit**

```bash
git add backend/main.py tests/conftest.py tests/test_backend.py
git commit -m "feat: add FastAPI backend with session and SSE streaming routes"
```

---

## Task 7: MCP Server

**Files:**
- Create: `mcp/server.py`
- Create: `tests/test_mcp.py`

The MCP server wraps the backend's `/session` + `/session/{id}/message` endpoints. It creates one session per MCP caller process (identified by `mcp-default` user ID) and streams the response back as a single string.

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp.py`:

```python
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

    with patch("mcp.server.httpx.AsyncClient", return_value=mock_http_client):
        from mcp.server import ask_tax_question
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

    with patch("mcp.server.httpx.AsyncClient", return_value=mock_http_client):
        from mcp.server import ask_tax_question
        result = await ask_tax_question("What is the 401k limit?")

    assert result == "The answer."
```

- [ ] **Step 2: Run to verify tests fail**

```bash
pytest tests/test_mcp.py -v
```

Expected: `ModuleNotFoundError: No module named 'mcp.server'` (or import conflicts — rename if needed)

Note: if `mcp` conflicts with the installed `mcp` package, rename the folder to `tax_mcp` and update imports.

- [ ] **Step 3: Write mcp/server.py**

```python
import os
import asyncio
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_mcp.py -v
```

Expected: 2 passed

- [ ] **Step 5: Smoke-test the MCP server** (requires backend running on :8000)

```bash
TAX_AGENT_API_URL=http://localhost:8000 python mcp/server.py
```

Expected: MCP server starts and waits for connections via stdio.

- [ ] **Step 6: Commit**

```bash
git add mcp/server.py tests/test_mcp.py
git commit -m "feat: add FastMCP server exposing ask_tax_question tool"
```

---

## Task 8: Golden Question Tests

**Files:**
- Create: `tests/test_golden.py`

These tests make real API calls. They are marked `integration` and skipped by default unless `--integration` is passed.

- [ ] **Step 1: Add pytest integration marker to conftest.py**

Append to `tests/conftest.py`:

```python
def pytest_addoption(parser):
    parser.addoption("--integration", action="store_true", default=False)


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--integration"):
        skip = pytest.mark.skip(reason="pass --integration to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)
```

- [ ] **Step 2: Write tests/test_golden.py**

```python
import os
import re
import pytest
import httpx

BASE_URL = os.environ.get("TAX_AGENT_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEYS", "changeme").split(",")[0].strip()
HEADERS = {"x-api-key": API_KEY}


def create_session(user_id: str) -> str:
    r = httpx.post(f"{BASE_URL}/session", params={"user_id": user_id}, headers=HEADERS)
    r.raise_for_status()
    return r.json()["session_id"]


def ask(session_id: str, question: str) -> str:
    parts = []
    with httpx.stream(
        "POST",
        f"{BASE_URL}/session/{session_id}/message",
        json={"content": question},
        headers={**HEADERS, "Accept": "text/event-stream"},
        timeout=120,
    ) as resp:
        for line in resp.iter_lines():
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            parts.append(data)
    return "".join(parts)


def has_citation(answer: str) -> bool:
    return bool(re.search(r"(Source:|IRS|IRC §|irs\.gov|Publication \d+)", answer, re.IGNORECASE))


QUESTIONS = [
    ("standard_deduction_single", "What is the standard deduction for a single filer in 2025?", ["15,000", "15000"]),
    ("standard_deduction_mfj", "What is the standard deduction for married filing jointly in 2025?", ["30,000", "30000"]),
    ("401k_limit", "What is the 401(k) employee contribution limit for 2025?", ["23,500", "23500"]),
    ("ira_limit", "What is the IRA contribution limit for 2025?", ["7,000", "7000"]),
    ("hsa_self", "What is the HSA contribution limit for self-only coverage in 2025?", ["4,300", "4300"]),
    ("se_tax_rate", "What is the self-employment tax rate in 2025?", ["15.3", "15.3%"]),
    ("home_office_w2", "Can a W-2 employee deduct a home office in 2025?", ["no", "suspended", "TCJA", "2017"]),
    ("quarterly_due", "When is the Q3 2025 estimated tax payment due?", ["september", "sep", "2025-09-15", "september 15"]),
    ("roth_phaseout_single", "At what income does the Roth IRA contribution phase out for a single filer in 2025?", ["150,000", "150000", "$150"]),
    ("scope_state", "What is the California income tax rate?", ["state", "federal only", "department of revenue"]),
]


@pytest.mark.integration
@pytest.mark.parametrize("name,question,expected_keywords", QUESTIONS)
def test_golden_question(name: str, question: str, expected_keywords: list[str]):
    session_id = create_session(f"golden-{name}")
    answer = ask(session_id, question)

    assert len(answer) > 50, f"Answer too short: {answer!r}"
    assert has_citation(answer), f"No citation found in: {answer!r}"

    answer_lower = answer.lower()
    assert any(kw.lower() in answer_lower for kw in expected_keywords), (
        f"None of {expected_keywords!r} found in answer:\n{answer}"
    )
```

- [ ] **Step 3: Run unit tests to verify nothing is broken**

```bash
pytest tests/ -v --ignore=tests/test_golden.py
```

Expected: all pass

- [ ] **Step 4: Run integration tests** (requires backend + real API key)

```bash
pytest tests/test_golden.py -v --integration
```

Expected: 10 passed. If any fail, inspect the answer text — most failures will be citation or keyword mismatches that need the system prompt tuned.

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/test_golden.py
git commit -m "test: add golden question integration test suite"
```

---

## Task 9: Final Wiring + README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --ignore=tests/test_golden.py
```

Expected: all pass with no warnings.

- [ ] **Step 2: Write README.md**

```markdown
# Federal Tax & Accounting Agent

A Q&A agent for US federal tax and accounting questions, built on Claude Managed Agents.

## Setup

1. `cp .env.example .env` — add your `ANTHROPIC_API_KEY`
2. `pip install -r requirements.txt`
3. `python agent/setup.py` — creates Agent + Environment, writes IDs to `.env`

## Run the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

## Run the MCP server

```bash
python mcp/server.py
```

Add to Claude Desktop `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "tax-agent": {
      "command": "python",
      "args": ["/path/to/managed_agents/mcp/server.py"],
      "env": {
        "TAX_AGENT_API_URL": "http://localhost:8000",
        "API_KEYS": "your-key"
      }
    }
  }
}
```

## Test

```bash
pytest tests/ -v                        # unit tests
pytest tests/ -v --integration          # unit + golden questions (real API)
```

## Annual update

Each January, update `data/tax_data.json` and `agent/system_prompt.txt` with new IRS figures,
then re-run `python agent/setup.py` to create a new Agent version.
```

- [ ] **Step 3: Final commit**

```bash
git add README.md
git commit -m "docs: add README with setup and usage instructions"
```
