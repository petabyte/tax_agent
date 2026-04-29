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
        content = content.rstrip("\n") + ("\n" if content else "") + f"{replacement}\n"
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
