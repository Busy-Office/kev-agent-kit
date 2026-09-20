"""Exercise the real STDIO transport and Docker-backed tools."""
import asyncio
import argparse
from datetime import timedelta
import json
from pathlib import Path
import sys
import tempfile
import tomllib

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", choices=["direct", "codex", "claude", "antigravity"], default="direct")
    parser.add_argument("--installed", action="store_true", help="Test the global installation from outside the checkout")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.installed:
        if args.client == "direct":
            parser.error("--installed requires --client codex, claude, or antigravity")
        state = json.loads((Path.home() / ".local/share/kev-agent-kit/installation.json").read_text())
        item = state["clients"][args.client]
        location = Path(item["config"])
        if args.client == "codex":
            config = tomllib.loads(location.read_text())["mcp_servers"]["kev"]
        else:
            config = json.loads(location.read_text())["mcpServers"]["kev"]
    elif args.client == "codex":
        config = tomllib.loads((root / "integrations/config/codex.toml").read_text())["mcp_servers"]["kev"]
    elif args.client == "claude":
        config = json.loads((root / "integrations/config/claude.json").read_text())["mcpServers"]["kev"]
    elif args.client == "antigravity":
        config = json.loads((root / "integrations/config/antigravity.json").read_text())["mcpServers"]["kev"]
    else:
        config = {"command": sys.executable, "args": [str(Path(__file__).with_name("kev_mcp.py"))]}
    params = StdioServerParameters(command=config["command"], args=config["args"], env=config.get("env"),
                                  cwd=tempfile.gettempdir() if args.installed else str(root))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=120)) as session:
            await session.initialize()
            listed = await session.list_tools()
            assert {t.name for t in listed.tools} == {"kev_models", "kev_decide", "kev_check_permutations"}
            for name, arguments in [
                ("kev_models", {}),
                ("kev_decide", {
                    "state": "I was charged twice for my shoes. Please refund the duplicate charge.",
                    "questions": {
                        "department": {"type": "choice", "instructions": "Which department should handle this?",
                                       "criteria": {"billing": "Charges and payments", "shipping": "Delivery and tracking", "other": "None of these"}},
                        "duplicate": {"type": "noul", "instructions": "Does the message report a duplicate charge?"},
                        "tone": {"type": "score", "instructions": "How angry is the customer?", "criteria": ["calm", "frustrated", "furious"]},
                    },
                }),
                ("kev_check_permutations", {
                    "state": "I was charged twice.",
                    "questions": {"topic": {"type": "choice", "instructions": "Which topic?", "criteria": {"billing": "Charges", "shipping": "Delivery"}}},
                    "question": "topic", "n_perm": 2,
                }),
            ]:
                result = await session.call_tool(name, arguments)
                assert not result.isError, result
                print(name, json.dumps(result.structuredContent or [c.model_dump() for c in result.content]))


if __name__ == "__main__":
    asyncio.run(main())
