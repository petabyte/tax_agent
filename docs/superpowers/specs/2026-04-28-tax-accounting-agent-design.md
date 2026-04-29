# Tax & Accounting Agent — Design Spec
**Date:** 2026-04-28
**Status:** Approved

---

## Overview

A conversational AI agent that answers US federal tax and accounting questions for any user — individuals, freelancers, small business owners, and accounting professionals alike. Distributed as an MCP server and a SaaS web app. No document processing, no PII handling.

---

## Goals

- Answer complex US federal tax and accounting questions accurately, citing official sources
- Serve all user types: lay users get plain-English answers, professionals get terse, cite-the-code answers — tone is inferred automatically from how the user writes
- Distribute via MCP server (Claude Desktop / claude.ai ecosystem) and a web app (SaaS, listed on Product Hunt / AppSumo / G2)
- No state tax scope for MVP — federal only; state taxes are a v2 expansion

---

## Non-Goals

- Document processing (W-2s, 1099s, receipts) — no PII handling
- State or international tax
- Legal advice (agent declines and redirects appropriately)
- Storing user financial data of any kind

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Distribution Layer                 │
│                                                      │
│   MCP Server (Claude Desktop / claude.ai)            │
│   REST API  (your web app + third-party devs)        │
│   Web App   (Next.js, direct SaaS users)             │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│              Your Backend (Node/Python)              │
│                                                      │
│   • Auth + API key management (per tenant)           │
│   • Session lifecycle (create / resume / list)       │
│   • Billing hooks                                    │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│           Claude Managed Agents (Anthropic)          │
│                                                      │
│   Agent:  system prompt + tools config               │
│   Env:    container with tax_data.json mounted       │
│   Session: one per user conversation                 │
│                                                      │
│   Tools available to Claude:                         │
│   • WebSearch  → IRS.gov, tax code, official only    │
│   • WebFetch   → retrieve full IRS publication text  │
│   • Bash       → read tax_data.json                  │
└─────────────────────────────────────────────────────┘
```

One Managed Agent definition is shared across all tenants. Sessions are the per-user isolation boundary. No user data is persisted — stateless Q&A only.

---

## Components

### 1. Managed Agent Definition
Created once, referenced by all sessions.

- **Model:** `claude-sonnet-4-6`
- **Tools:** WebSearch, WebFetch, Bash
- **System prompt responsibilities:**
  - Identity: "You are a US federal tax and accounting expert"
  - Source scoping: web searches restricted to IRS.gov, 26 USC, treasury.gov, irs.gov/pub — prohibits citing tax blogs or non-authoritative sources
  - Tone adaptation: infer expertise level from user phrasing; match tone automatically
  - Citation requirement: every factual claim must end with a source (IRS pub number, IRC section, or URL)
  - Scope boundary: decline state/international/legal questions gracefully, explain limitation, suggest where to look
  - No memory reliance: all tax figures must come from WebSearch or tax_data.json, never from training memory alone

### 2. Environment
Container template, created once and reused.

- Minimal container (no heavy packages)
- Mounted file: `tax_data.json` — IRS tax brackets, standard deduction amounts, contribution limits (IRA, 401k, HSA), key filing deadlines (~50KB, updated each January)
- Open network access (WebSearch requires it)

### 3. Session
One session per user conversation.

- Created when a user starts a new chat
- Persists across reconnects (Managed Agents stores event history server-side)
- Archived after 24h inactivity
- Backend maps `user_id → session_id`

### 4. Backend (thin layer)
REST API you build and host.

| Endpoint | Purpose |
|---|---|
| `POST /session` | Create a Managed Agent session, return `session_id` |
| `POST /session/:id/message` | Send user message, stream response via SSE |
| `GET /session/:id/history` | Retrieve full conversation history |

- Auth middleware validates API keys per tenant
- Billing hooks fire on session creation and per-message token counts

### 5. MCP Server
Wraps the backend, published to npm and Anthropic's MCP directory.

- Exposes one tool: `ask_tax_question(question: string) → answer: string`
- Uses the REST API under the hood
- MCP users get the same agent as web app users

### 6. Web App
Thin Next.js front-end for direct SaaS customers.

- Chat UI, sign-up/login, subscription management
- Calls the REST API
- Listed on Product Hunt, AppSumo, G2

---

## Data Flow

```
User question
    │
    ▼
Backend: validate API key, resolve session_id
    │
    ▼
POST event to Managed Agents session
    │
    ▼
Claude: read system prompt + conversation history
decides which tools to call
    │
    ├── WebSearch → IRS.gov / 26 USC
    └── Bash → read tax_data.json
    │
    ▼
Claude synthesizes answer with source citation
    │
    ▼
Streamed via SSE → backend → client
```

Claude always searches before answering — never relies on training data alone for tax specifics. If IRS.gov returns ambiguous results, Claude fetches the full publication via WebFetch.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Web search returns no results | Fall back to `tax_data.json`, state uncertainty explicitly, recommend IRS.gov directly |
| IRS.gov unreachable | Answer from training knowledge, flag clearly: "I couldn't verify this in real-time — please confirm at IRS.gov" |
| Out-of-scope question (state, international, legal) | Decline gracefully, explain federal-only scope, suggest where to look |
| Ambiguous question | Ask one clarifying question before searching |
| Session expires mid-conversation | Backend auto-creates new session, replays last user message |

---

## Testing

- **Golden question set:** 50 curated questions with known correct answers (brackets, deduction limits, common scenarios) — run after any system prompt change
- **Source citation check:** automated test verifies every response contains at least one IRS.gov URL or publication reference
- **Scope boundary test:** state tax and international questions must always trigger a graceful decline
- **Annual regression:** re-run golden set + update `tax_data.json` each January when IRS publishes new-year figures

---

## Distribution & Monetization

- **MCP server:** published to npm + Anthropic MCP directory — free discovery channel
- **Web app SaaS:** $30–150/month per user, listed on Product Hunt / AppSumo / G2
- **API access tier:** for developers and accounting firms building on top

---

## Future Scope (v2+)

- US state tax support (50 jurisdictions)
- Document Q&A (non-PII: tax forms with numbers redacted client-side before upload)
- Accounting firm white-label tier
- Multi-agent specialist routing for complex cross-domain questions
