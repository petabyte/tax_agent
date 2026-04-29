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
python tax_mcp/server.py
```

Add to Claude Desktop `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "tax-agent": {
      "command": "python",
      "args": ["/path/to/managed_agents/tax_mcp/server.py"],
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
