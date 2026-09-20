"""Install the shared skill and MCP runtime into user scope, preserving other settings."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import tomlkit

SOURCE = Path(__file__).resolve().parents[2]
CLIENTS = ("codex", "claude", "antigravity")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".kev-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        if path.exists():
            os.chmod(name, path.stat().st_mode & 0o777)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def locations(home, client):
    paths = {
        "codex": (home / ".codex/config.toml", home / ".agents/skills/kev-decision/SKILL.md"),
        "claude": (home / ".claude.json", home / ".claude/skills/kev-decision/SKILL.md"),
        "antigravity": (home / ".gemini/config/mcp_config.json", home / ".gemini/config/skills/kev-decision/SKILL.md"),
    }
    config, skill = paths[client]
    if home == Path.home():
        if client == "codex" and os.environ.get("CODEX_HOME"):
            config = Path(os.environ["CODEX_HOME"]) / "config.toml"
        if client == "claude" and os.environ.get("CLAUDE_CONFIG_DIR"):
            base = Path(os.environ["CLAUDE_CONFIG_DIR"])
            config, skill = base / ".claude.json", base / "skills/kev-decision/SKILL.md"
    return config, skill


def read_config(path):
    text = path.read_text() if path.exists() else ""
    return tomlkit.parse(text) if path.suffix == ".toml" else json.loads(text.strip() or "{}")


def entry(path):
    key = "mcp_servers" if path.suffix == ".toml" else "mcpServers"
    return read_config(path).get(key, {}).get("kev")


def config_bytes(path, value):
    doc = read_config(path)
    key = "mcp_servers" if path.suffix == ".toml" else "mcpServers"
    if key not in doc:
        doc[key] = {}
    if value is None:
        doc[key].pop("kev", None)
    else:
        doc[key]["kev"] = value
    text = tomlkit.dumps(doc) if path.suffix == ".toml" else json.dumps(doc, indent=2) + "\n"
    return text.encode()


def transaction(changes, root, expected=None):
    """Back up originals privately and roll back only our writes on an I/O error."""
    snapshot = {p: p.read_bytes() if p.exists() else None for p in changes}
    if expected is not None:
        for path in changes:
            if snapshot[path] != expected[path]:
                raise RuntimeError(f"Concurrent edit: {path}; no configuration changes applied")
    backup = root / "backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup.mkdir(parents=True, mode=0o700)
    os.chmod(backup.parent, 0o700)
    index = {}
    for number, (path, data) in enumerate(snapshot.items()):
        index[str(number)] = {"path": str(path), "existed": data is not None}
        if data is not None:
            atomic_write(backup / str(number), data)
    atomic_write(backup / "index.json", json.dumps(index, indent=2).encode())
    written = []
    try:
        for path, data in changes.items():
            # Stop if another process changed a configuration after it was read.
            current = path.read_bytes() if path.exists() else None
            if current != snapshot[path]:
                raise RuntimeError(f"Concurrent edit: {path}")
            if data is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, data)
            written.append(path)
    except Exception:
        for path in reversed(written):
            original = snapshot[path]
            if original is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, original)
        raise
    print(f"Backup: {backup}")


def prepare_runtime(root, source=SOURCE):
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required on PATH")
    release = root / "releases" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    files = ["kev/__init__.py", "kev/api.py", "integrations/kev-mcp/kev_mcp.py",
             "integrations/kev-mcp/pyproject.toml", "integrations/kev-mcp/uv.lock"]
    for name in files:
        atomic_write(release / name, (source / name).read_bytes())
    project = release / "integrations/kev-mcp"
    subprocess.run([uv, "sync", "--frozen", "--no-dev", "--directory", str(project)], check=True)
    python = project / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run([str(python), "-c", "import kev_mcp"], cwd=project, check=True)
    return {"command": str(python), "args": [str(project / "kev_mcp.py")],
            "env": {"KEV_BASE_URL": "http://127.0.0.1:8008", "KEV_TIMEOUT_SECONDS": "90"}}


def manage(action, home, clients=None, dry_run=False, source=SOURCE, runtime_builder=prepare_runtime):
    root = home / ".local/share/kev-agent-kit"
    manifest = root / "installation.json"
    manifest_data = manifest.read_bytes() if manifest.exists() else None
    state = json.loads(manifest_data) if manifest_data is not None else {"clients": {}}
    installed = state["clients"]
    if action == "status":
        for name, item in installed.items():
            config, skill = Path(item["config"]), Path(item["skill"])
            healthy = entry(config) == item["entry"] and skill.exists() and digest(skill.read_bytes()) == item["skill_sha256"]
            print(f"{name}: {'installed' if healthy else 'modified or missing'} ({config})")
        if not installed:
            print("Kev is not installed globally by this installer.")
        return state
    selected = clients or (list(installed) if installed else list(CLIENTS))
    if action in ("update", "uninstall") and not installed:
        raise RuntimeError("No managed installation. Run install first.")
    expected = {manifest: manifest_data}
    for name in selected:
        if name in installed:
            item = installed[name]
            config, skill = Path(item["config"]), Path(item["skill"])
            if entry(config) != item["entry"]:
                raise RuntimeError(f"{name}: Kev config changed outside installer; reconcile it before {action}.")
            if not skill.exists() or digest(skill.read_bytes()) != item["skill_sha256"]:
                raise RuntimeError(f"{name}: installed skill changed; preserve your edits before {action}.")
        else:
            config, skill = locations(home, name)
            if action == "uninstall":
                raise RuntimeError(f"{name} is not managed by this installer")
            if entry(config) is not None or skill.parent.exists():
                raise RuntimeError(f"{name}: an existing Kev config or skill conflicts; nothing overwritten.")
        if config.is_symlink() or skill.is_symlink():
            raise RuntimeError(f"{name}: refusing to replace a symlinked config or skill")
        for path in (config, skill):
            expected[path] = path.read_bytes() if path.exists() else None
        print(f"{action} {name}: {config}; {skill}")
    if dry_run:
        print("Dry run: no files or dependencies changed.")
        return state
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    changes = {}
    if action != "uninstall":
        runtime = runtime_builder(root, source)
        skill_data = (source / "skills/kev-decision/SKILL.md").read_bytes()
    for name in selected:
        previous = installed.get(name)
        config, skill = (Path(previous["config"]), Path(previous["skill"])) if previous else locations(home, name)
        if action == "uninstall":
            changes[config] = config_bytes(config, None)
            changes[skill] = None
            del installed[name]
        else:
            value = dict(runtime)
            if name == "codex":
                value.update(startup_timeout_sec=30, tool_timeout_sec=120, required=False,
                             enabled_tools=["kev_models", "kev_decide", "kev_check_permutations"])
            if name == "claude":
                value["type"] = "stdio"
            changes[config] = config_bytes(config, value)
            changes[skill] = skill_data
            installed[name] = {"config": str(config), "skill": str(skill), "entry": value,
                               "skill_sha256": digest(skill_data)}
    changes[manifest] = (json.dumps(state, indent=2) + "\n").encode()
    transaction(changes, root, expected)
    if action == "uninstall":
        # Remove only empty managed skill directories; retain other files.
        for path, data in changes.items():
            if data is None:
                try:
                    path.parent.rmdir()
                except OSError:
                    pass
        print("Removed selected registrations and skill files. Runtime releases, backups, and Docker weights retained.")
    else:
        print("Installed. Restart your agent clients to load their global MCP tools and skills.")
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "update", "uninstall", "status"])
    parser.add_argument("--clients", nargs="+", choices=CLIENTS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        manage(args.action, Path.home(), args.clients, args.dry_run)
    except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Kev installation stopped: {exc}\n")


if __name__ == "__main__":
    main()
