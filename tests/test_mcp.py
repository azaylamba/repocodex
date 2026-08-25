from __future__ import annotations

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
