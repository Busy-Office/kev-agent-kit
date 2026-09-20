import json
from pathlib import Path

import pytest

import global_install as installer


def fake_runtime(root, source):
    return {"command": str(root / "test-python"), "args": ["server.py"], "env": {"KEV_BASE_URL": "http://127.0.0.1:8008"}}


def run(home, action="install", **kwargs):
    return installer.manage(action, home, runtime_builder=fake_runtime, **kwargs)


def test_install_update_uninstall_preserve_unrelated_settings(tmp_path):
    codex, _ = installer.locations(tmp_path, "codex")
    codex.parent.mkdir()
    codex.write_text('# Keep my comment\nmodel = "custom"\n[mcp_servers.other]\ncommand = "other-tool"\n')
    claude, _ = installer.locations(tmp_path, "claude")
    claude.write_text(json.dumps({"preferences": {"theme": "dark"}, "mcpServers": {"other": {"command": "other"}}}))
    state = run(tmp_path)
    assert set(state["clients"]) == set(installer.CLIENTS)
    assert "# Keep my comment" in codex.read_text()
    assert installer.read_config(codex)["model"] == "custom"
    for item in state["clients"].values():
        assert Path(item["skill"]).read_bytes() == (installer.SOURCE / "skills/kev-decision/SKILL.md").read_bytes()
    run(tmp_path, "update")
    # User adds an unrelated setting after installation. Uninstall must retain it.
    data = json.loads(claude.read_text())
    data["newSetting"] = 42
    claude.write_text(json.dumps(data))
    run(tmp_path, "uninstall")
    assert installer.entry(codex) is None
    assert installer.read_config(codex)["mcp_servers"]["other"]["command"] == "other-tool"
    assert json.loads(claude.read_text())["newSetting"] == 42
    assert json.loads(claude.read_text())["preferences"]["theme"] == "dark"
    for client in installer.CLIENTS:
        assert not installer.locations(tmp_path, client)[1].exists()


def test_conflict_preflight_does_not_partially_install(tmp_path):
    config, _ = installer.locations(tmp_path, "antigravity")
    config.parent.mkdir(parents=True)
    config.write_text('{"mcpServers":{"kev":{"command":"user-owned"}}}')
    with pytest.raises(RuntimeError, match="conflicts"):
        run(tmp_path)
    assert not installer.locations(tmp_path, "codex")[0].exists()
    assert installer.entry(config)["command"] == "user-owned"


def test_dry_run_has_no_writes(tmp_path):
    run(tmp_path, dry_run=True)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("target", ["config", "skill"])
def test_modified_owned_content_is_preserved(tmp_path, target):
    state = run(tmp_path, clients=["claude"])
    path = Path(state["clients"]["claude"][target])
    if target == "config":
        path.write_text('{"mcpServers":{"kev":{"command":"custom"}}}')
    else:
        path.write_text("My custom skill")
    before = path.read_bytes()
    for action in ("update", "uninstall"):
        with pytest.raises(RuntimeError, match="changed"):
            run(tmp_path, action)
        assert path.read_bytes() == before


def test_blank_json_config_is_supported(tmp_path):
    config, _ = installer.locations(tmp_path, "antigravity")
    config.parent.mkdir(parents=True)
    config.write_text("\n  ")
    run(tmp_path, clients=["antigravity"])
    assert installer.entry(config)["command"].endswith("test-python")


def test_transaction_rolls_back_on_write_error(tmp_path, monkeypatch):
    first, second = tmp_path / "first", tmp_path / "second"
    first.write_bytes(b"original")
    write = installer.atomic_write
    def fail(path, data):
        if path == second:
            raise OSError("simulated full disk")
        write(path, data)
    monkeypatch.setattr(installer, "atomic_write", fail)
    with pytest.raises(OSError):
        installer.transaction({first: b"modified", second: b"new"}, tmp_path / "installer")
    assert first.read_bytes() == b"original"
    assert not second.exists()


def test_concurrent_edit_during_runtime_preparation_is_preserved(tmp_path):
    config, _ = installer.locations(tmp_path, "claude")
    def changed_runtime(root, source):
        config.write_text('{"newPreference":"keep me"}')
        return fake_runtime(root, source)
    with pytest.raises(RuntimeError, match="Concurrent edit"):
        installer.manage("install", tmp_path, ["claude"], runtime_builder=changed_runtime)
    assert json.loads(config.read_text()) == {"newPreference": "keep me"}
    assert not installer.locations(tmp_path, "claude")[1].exists()
