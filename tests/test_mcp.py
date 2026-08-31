from __future__ import annotations

from pathlib import Path

import pytest

from repocodex.mcp_server import tool_validate_diff, tool_get_context
from repocodex.commands.validate import validate


def test_mcp_validate_matches_cli(repo, monkeypatch):
    monkeypatch.chdir(repo.root)
    via_cli = validate(repo.root, all_concepts=True)
    via_mcp = tool_validate_diff()
    # MCP validate_diff uses all_concepts=False; compare engine_version and shape
    assert via_mcp["engine_version"] == via_cli["engine_version"]
    assert set(via_mcp.keys()) == set(via_cli.keys())


def test_plugin_packaging_exists():
    from pathlib import Path
    from repocodex.commands.install import _data_path

    assert _data_path("plugin", "plugin.json").exists()
    assert _data_path("plugin", "mcp.json").exists()
    assert _data_path("skills", "repocodex-coding", "SKILL.md").exists()
    assert _data_path("plugin", "hooks", "cursor-pre-commit").exists()
    assert _data_path("plugin", "hooks", "claude-pre-commit").exists()


def test_install_mcp_does_not_copy_when_extra_missing(tmp_path: Path, monkeypatch):
    from repocodex.commands.install import install

    monkeypatch.setattr("repocodex.commands.install.mcp_extra_available", lambda: False)
    payload = install(tmp_path, mcp=True)
    cursor_mcp = tmp_path / ".cursor" / "mcp.json"
    assert not cursor_mcp.exists()
    assert not any("mcp.json" in item for item in payload["installed"])
    assert payload.get("mcp") is not True
    assert payload["ok"] is not True or "mcp.json" not in "".join(payload["installed"])
    assert any("repocodex[mcp]" in item for item in payload.get("failed", []))


def test_install_mcp_writes_config_when_extra_present(tmp_path: Path, monkeypatch):
    from repocodex.commands.install import install

    monkeypatch.setattr("repocodex.commands.install.mcp_extra_available", lambda: True)
    payload = install(tmp_path, mcp=True)
    cursor_mcp = tmp_path / ".cursor" / "mcp.json"
    assert cursor_mcp.exists()
    text = cursor_mcp.read_text(encoding="utf-8")
    assert "repocodex" in text
    assert "-m" in text and "mcp" in text
    assert any("mcp.json" in item for item in payload["installed"])
    assert payload.get("mcp") is True
    assert payload["ok"] is True


def test_run_mcp_without_extra_exits_with_install_hint(monkeypatch):
    from repocodex.mcp_server import run_mcp

    monkeypatch.setattr("repocodex.mcp_server.mcp_extra_available", lambda: False)
    with pytest.raises(SystemExit) as exc:
        run_mcp()
    assert "repocodex[mcp]" in str(exc.value)
    assert "unavailable" not in str(exc.value).lower()


def test_mcp_server_registers_architecture_tool_names():
    from repocodex.mcp_server import register_mcp_tools

    class Recorder:
        def __init__(self) -> None:
            self.names: list[str] = []

        def tool(self, *args, **kwargs):
            def deco(fn):
                self.names.append(kwargs.get("name") or fn.__name__)
                return fn

            return deco

    rec = Recorder()
    register_mcp_tools(rec)
    assert rec.names == [
        "get_context",
        "get_impact",
        "read_concept",
        "write_memory",
        "validate_diff",
        "reconcile_memory",
    ]
    assert not any(name.endswith("_tool") for name in rec.names)
