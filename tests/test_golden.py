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
