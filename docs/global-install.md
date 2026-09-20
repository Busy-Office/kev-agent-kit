# Global Installation

Install once to use Kev from multiple projects in Codex, Claude Code, and Google
Antigravity. All clients share the Docker API on port 8008. Installation does not
start Docker, start the playground, grant blanket tool approval, or make Kev run
on every task.

## Install

Run from this checkout after installing uv:

```sh
uv sync --frozen --directory integrations/kev-mcp
uv run --frozen --directory integrations/kev-mcp python global_install.py install --dry-run
uv run --frozen --directory integrations/kev-mcp python global_install.py install
```

Default: configure all three clients. To select clients, add for example
`--clients codex claude`. The installer can provision settings before a client is
installed. It does not install the client applications themselves.

Restart your clients after installation. Invoke `$kev-decision` in Codex,
`/kev-decision` in Claude Code, or ask Antigravity to use `kev-decision`.

| Client | Global MCP config | Global skill directory |
| --- | --- | --- |
| Codex | `~/.codex/config.toml` | `~/.agents/skills/kev-decision` |
| Claude Code | `~/.claude.json` | `~/.claude/skills/kev-decision` |
| Antigravity | `~/.gemini/config/mcp_config.json` | `~/.gemini/config/skills/kev-decision` |

`CODEX_HOME` overrides the Codex configuration directory. `CLAUDE_CONFIG_DIR`
overrides Claude's configuration and skill directory. Update and uninstall use
the recorded installation paths, even if environment variables subsequently change.
Older Antigravity versions may use a different raw config location; inspect it
in the client before assuming the current documented path is loaded.

## What Changes

The installer adds only the `kev` server entry and its skill. It retains other
MCP servers and settings, including TOML comments. JSON formatting may change.
Preexisting unmanaged Kev entries or skill directories cause it to stop rather
than overwrite them.

Runtime copies and their locked Python environment live under
`~/.local/share/kev-agent-kit/releases/`. Client configs point directly to the
installed Python executable and adapter. There is no Git-root lookup and no need
for `uv` on the GUI client's PATH at runtime. Moving the source checkout does not
break an installed adapter. Docker still needs to be running.

Full configuration backups are stored privately under
`~/.local/share/kev-agent-kit/backups/`; they may contain your existing secrets, so
do not upload them. An installation manifest tracks the exact managed entries and
skill hashes. Failed configuration writes are rolled back; an unused runtime
release can remain after failure. No background updater is installed.

## Update And Check

After reviewing and pulling the latest repository changes:

```sh
uv run --frozen --directory integrations/kev-mcp python global_install.py update --dry-run
uv run --frozen --directory integrations/kev-mcp python global_install.py update
uv run --frozen --directory integrations/kev-mcp python global_install.py status
uv run --frozen --directory integrations/kev-mcp python smoke.py --client codex --installed
uv run --frozen --directory integrations/kev-mcp python smoke.py --client claude --installed
uv run --frozen --directory integrations/kev-mcp python smoke.py --client antigravity --installed
```

Update defaults to previously installed clients. It refreshes the copied adapter,
dependencies, and skills from this checkout; it does not fetch Git changes or
change Docker's model. Restart clients to use the new processes. Smoke checks run
the configured MCP processes from a temporary directory outside the checkout,
then discover and call all three tools against the live service. They are protocol
checks, not an interactive verification inside every client UI.

If you edited the installed Kev entry or skill, update and uninstall stop with a
conflict. Preserve your edits and reconcile them before retrying. Unrelated settings
can change freely and remain intact.

## Uninstall

```sh
uv run --frozen --directory integrations/kev-mcp python global_install.py uninstall --dry-run
uv run --frozen --directory integrations/kev-mcp python global_install.py uninstall
```

Use `--clients claude` to remove only one client. Uninstall removes the managed
server entries and unchanged skill files; it preserves unrelated settings, extra
skill-directory files, backups, copied runtimes, and Docker model weights. Retained
runtime releases can consume disk space; removal is deliberately separate from
unregistering tools. Restart clients afterward.

## Migration And Project-Only Use

The source skill now lives in `skills/kev-decision`. Client config templates live
in `integrations/config`. Neither location is automatically discovered, so simply
cloning this version does not create duplicate global/project tools or skills.

Updating this checkout removes its earlier tracked `.codex/config.toml`,
`.mcp.json`, `.agents/mcp_config.json`, and project skill entry points. If you copied
those into other projects, remove only their `kev` entries and project skill copies
when adopting global installation. Preserve other server definitions.

For project-only installation, skip the global installer and copy the relevant
template to `.codex/config.toml`, `.mcp.json`, or `.agents/mcp_config.json`. Copy the
self-contained source skill into `.agents/skills/kev-decision` for Codex/Antigravity
or `.claude/skills/kev-decision` for Claude Code. These templates assume the adapter
exists in that checkout. Choose one scope per client; do not install both.
