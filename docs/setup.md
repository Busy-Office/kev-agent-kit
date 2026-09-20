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
docker compose logs --tail 30 kev
uv sync --frozen --directory integrations/kev-mcp
uv run --frozen --directory integrations/kev-mcp python global_install.py install
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

Run the [global installer](global-install.md), then restart Codex. It registers
`kev_models`, `kev_decide`, and `kev_check_permutations` in your user configuration.
The installed runtime uses an absolute Python path and works outside this checkout.

Try: “Use $kev-decision to classify this message: I was charged twice for my shoes.”
The source skill is in `skills/kev-decision/SKILL.md`; the installed Codex copy
is in `~/.agents/skills/kev-decision/SKILL.md`.

## Connect Claude Code

After global installation, launch `claude` in any project. The installer adds the
same adapter to the user-scoped `mcpServers` object in `~/.claude.json`. Check
the connection with `/mcp`, then try `/kev-decision I was charged twice for my shoes`.
The self-contained skill is installed in `~/.claude/skills/kev-decision/SKILL.md`.
No credentials or permission bypass are installed. Approve tools when prompted.

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
uv run --frozen --directory integrations/kev-mcp python smoke.py --client codex --installed
uv run --frozen --directory integrations/kev-mcp python smoke.py --client claude --installed
uv run --frozen --directory integrations/kev-mcp python smoke.py --client antigravity --installed
uv run --frozen --directory integrations/kev-mcp python -m pytest -q
```

The adapter reuses `kev/api.py` for validation without importing torch. Requests
are capped at 64 KB and 16 questions, permutation checks at eight passes. HTTP
timeouts are 90 seconds, below Codex's 120-second tool timeout. The server serializes
inference; avoid parallel large calls. These transport limits do not guarantee
content fits Kev's token limits; keep state concise.

## Connect Google Antigravity

The global installer adds `kev` to `~/.gemini/config/mcp_config.json` and installs
the skill in `~/.gemini/config/skills/kev-decision/SKILL.md`. Restart Antigravity
and open any workspace.

In the IDE, open the agent panel's **… → MCP Servers → Manage MCP Servers** and
refresh the server list. **View raw config** lets you inspect the configuration.
In Antigravity CLI, use `/mcp` to inspect or reload servers. Ask:
“Use the kev-decision skill to classify: I was charged twice for my shoes.”
Approve tool use if prompted. These locations follow the current
[Antigravity MCP documentation](https://antigravity.google/docs/mcp) and
[skill documentation](https://antigravity.google/docs/skills).

For older versions whose **View raw config** opens a different location, merge
only the installed `kev` entry into that file, preserving other servers. The
installer targets the current documented global location; do not assume an older
IDE reads it. Do not add the same server twice in one client.

The optional project templates in `integrations/config` use macOS/Linux shell
launchers (or WSL). The global runtime uses an absolute Python executable. This
installer has been verified on macOS; native Windows has not been tested. The API remains
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
