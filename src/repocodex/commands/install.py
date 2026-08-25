from __future__ import annotations

import json
from pathlib import Path
import shutil
import stat

from repocodex.schema import envelope


def _data_path(*parts: str) -> Path:
    base = Path(__file__).resolve().parents[1] / "data"
    return base.joinpath(*parts)


def _copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)


def install(
    repo: Path,
    *,
    mcp: bool = False,
    skills: bool = True,
) -> dict:
    installed: list[str] = []
    hook_src = _data_path("hooks", "pre-commit")
    hook_dest = repo / ".git" / "hooks" / "pre-commit"
    if (repo / ".git").exists():
        _copy(hook_src, hook_dest)
        hook_dest.chmod(hook_dest.stat().st_mode | stat.S_IEXEC)
        installed.append(str(hook_dest.relative_to(repo)))

    action_src = _data_path("action", "repocodex.yml")
    action_dest = repo / ".github" / "workflows" / "repocodex.yml"
    _copy(action_src, action_dest)
    installed.append(str(action_dest.relative_to(repo)))

    if skills:
        for name in ("repocodex-coding", "repocodex-review"):
            src = _data_path("skills", name, "SKILL.md")
            for dest_root in (repo / ".cursor" / "skills" / name, repo / ".claude" / "skills" / name):
                dest = dest_root / "SKILL.md"
                _copy(src, dest)
                installed.append(str(dest.relative_to(repo)))
        plugin_src = _data_path("plugin")
        plugin_dest = repo / ".repocodex" / "plugin"
        if plugin_src.exists():
            shutil.copytree(plugin_src, plugin_dest, dirs_exist_ok=True)
            installed.append(str(plugin_dest.relative_to(repo)))

    if mcp:
        mcp_src = _data_path("plugin", "mcp.json")
        cursor_mcp = repo / ".cursor" / "mcp.json"
        if mcp_src.exists():
            if cursor_mcp.exists():
                existing = json.loads(cursor_mcp.read_text(encoding="utf-8"))
            else:
                existing = {}
            incoming = json.loads(mcp_src.read_text(encoding="utf-8"))
            servers = existing.setdefault("mcpServers", {})
            servers.update(incoming.get("mcpServers", incoming))
            cursor_mcp.parent.mkdir(parents=True, exist_ok=True)
            cursor_mcp.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
            installed.append(str(cursor_mcp.relative_to(repo)))

    config = repo / ".repocodex.toml"
    if not config.exists():
        config.write_text(
            'engine_version = "1.0.0"\nposture = "shadow"\nscope_lines = 40\n',
            encoding="utf-8",
        )
        installed.append(".repocodex.toml")

    return envelope({"installed": installed, "mcp": mcp})
