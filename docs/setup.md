# Kev Agent Kit Setup and Operations

This is the installation and operations reference. For a plain-language overview,
start with the [user guide](user-guide.md). For prompts and a real observed result,
see [practical use cases](use-cases.md). [All documentation](README.md).

Claude Code, Codex, or Antigravity calls a lightweight STDIO MCP process on the host. It sends typed
requests to Kev in Docker at `http://127.0.0.1:8008`. Only the container loads the
model. It has no repository mount and no Docker socket. Weights persist in the
`kev-local_kev-models` volume (the original cache name is retained across the
project rename). First startup needs network access to Hugging Face.

## Start

```sh
docker compose up -d --build
docker compose logs -f kev
uv sync --frozen --directory integrations/kev-mcp
curl --fail http://127.0.0.1:8008/v1/models
```

Default: `jaredpalmer/kev-0.5b`, fp32 CPU, four inference threads. Ordinary Linux
containers on this Mac do not use PyTorch MPS. A native macOS Kev server can replace
Docker at the same URL. Do not use MPS latency figures as CPU performance estimates.

The image uses upstream dependency pins except torch and its exclusive dependencies,
which come from PyTorch's 2.8.0 CPU wheel. Base images have version tags; model Hub
downloads use upstream's current revision. This is a local development setup,
not a fully digest-pinned release artifact.

## Playground

From the repository root, run `npm --prefix playground run dev` to open the
playground at http://127.0.0.1:8009. Both `dev` and production `start` explicitly
use port 8009; if occupied, startup fails instead of choosing another port.
The API proxy defaults to http://127.0.0.1:8008, so no environment variable is needed.
Production `start` requires `npm --prefix playground run build` first.

## Connect Codex

Open this repository as a trusted project and restart the Codex session to load
`.codex/config.toml`. It registers `kev_models`, `kev_decide`, and
`kev_check_permutations`. The launcher resolves the Git repository root, so it
works from any directory in a renamed or newly cloned checkout. `sh`, `git`, and
`uv` must be on the client's PATH.

Try: “Use $kev-decision to classify this message: I was charged twice for my shoes.”
The repo skill is in `.agents/skills/kev-decision/SKILL.md`.

## Connect Claude Code

Launch `claude` inside this checkout. The repository's `.mcp.json` registers the
same STDIO adapter; approve the project server when Claude Code prompts. Check
the connection with `/mcp`, then try `/kev-decision I was charged twice for my shoes`.
The skill in `.claude/skills/kev-decision/SKILL.md` loads the shared guidance from
`.agents/skills/kev-decision/SKILL.md`. `CLAUDE.md` imports the repository development
instructions. No global configuration, credentials, or permission bypass is installed.

## Verify The Integration

The smoke checks launch the exact configuration for each client using an MCP test
client. They verify protocol initialization, tool discovery, and all three tools;
they do not replace first-run approval or an interactive test inside each product.

Verify the actual STDIO protocol and a live decision independently of Codex:

```sh
uv run --frozen --directory integrations/kev-mcp python smoke.py
uv run --frozen --directory integrations/kev-mcp python smoke.py --client codex
uv run --frozen --directory integrations/kev-mcp python smoke.py --client claude
uv run --frozen --directory integrations/kev-mcp python smoke.py --client antigravity
uv run --frozen --directory integrations/kev-mcp python -m pytest -q
```

The adapter reuses `kev/api.py` for validation without importing torch. Requests
are capped at 64 KB and 16 questions, permutation checks at eight passes. HTTP
timeouts are 90 seconds, below Codex's 120-second tool timeout. The server serializes
inference; avoid parallel large calls. These transport limits do not guarantee
content fits Kev's token limits; keep state concise.

## Connect Google Antigravity

Open this checkout as your Antigravity workspace. The repository includes
`.agents/mcp_config.json` for the local `kev` server and the shared skill at
`.agents/skills/kev-decision/SKILL.md`.

In the IDE, open the agent panel's **… → MCP Servers → Manage MCP Servers** and
refresh the server list. **View raw config** lets you inspect the configuration.
In Antigravity CLI, use `/mcp` to inspect or reload servers. Ask:
“Use the kev-decision skill to classify: I was charged twice for my shoes.”
Approve tool use if prompted. These locations follow the current
[Antigravity MCP documentation](https://antigravity.google/docs/mcp) and
[skill documentation](https://antigravity.google/docs/skills).

If your installed version only exposes a global raw configuration, merge the
`kev` entry from `.agents/mcp_config.json` into its `mcpServers` object, preserving
other servers. For global configuration, replace the command and arguments with
`"command": "uv"` and
`"args": ["run", "--frozen", "--directory", "/absolute/path/to/kev-agent-kit/integrations/kev-mcp", "python", "kev_mcp.py"]`.
This avoids depending on which workspace the IDE starts the process from. If a
GUI client cannot find `uv`, use its absolute executable path from `command -v uv`.

The included shell launchers target macOS/Linux (or WSL). For native Windows,
configure `uv` directly with an absolute directory as above. The API remains
localhost:8008 and the playground localhost:8009 for every client.

## Operation

```sh
docker compose ps
docker compose logs --tail 50 kev
docker compose stop
docker compose up -d
```

`docker compose down` removes the container but preserves downloaded weights.
Do not add `--volumes` unless intentionally deleting the model cache.
For another model: `KEV_MODEL=jaredpalmer/kev-0.6b docker compose up -d`.
Larger models require more RAM and CPU time; benchmark before switching.
Use `KEV_CPU_THREADS` to change the default four CPU threads.

Kev has no authentication, so the published port binds only to localhost. Requests
and results are not logged by the adapter. Tool results still enter the agent
conversation and may be processed by its configured provider; local inference
does not make the full agent workflow offline.

## Interpretation

Kev probabilities are advisory. Coding-task calibration is unverified; risk/CI
questions are experiments, not validated gates. Choice confidence is not a
probability of correctness. Use code inspection and tests to decide what to change.

References: [Kev](https://github.com/jaredpalmer/kev),
[upstream Docker proposal](https://github.com/jaredpalmer/kev/pull/4),
[Codex MCP](https://developers.openai.com/codex/mcp/),
[Claude Code MCP](https://code.claude.com/docs/en/mcp).
