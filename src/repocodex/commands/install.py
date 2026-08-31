from __future__ import annotations

from pathlib import Path
import shutil
import stat

from repocodex import ENGINE_VERSION
from repocodex.schema import envelope


def _data_path(*parts: str) -> Path:
    base = Path(__file__).resolve().parents[1] / "data"
    return base.joinpath(*parts)


def _copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)


def _resolvable(path: Path) -> bool:
    return path.exists()


def install(
    repo: Path,
    *,
    mcp: bool = False,
    skills: bool = True,
) -> dict:
    installed: list[str] = []
    failed: list[str] = []
    skipped: list[str] = []

    hook_src = _data_path("hooks", "pre-commit")
    hook_dest = repo / ".git" / "hooks" / "pre-commit"
    if (repo / ".git").exists():
        if not hook_src.exists():
            failed.append("hooks/pre-commit (missing from distribution)")
        else:
            _copy(hook_src, hook_dest)
            hook_dest.chmod(hook_dest.stat().st_mode | stat.S_IEXEC)
            if _resolvable(hook_dest):
                installed.append(str(hook_dest.relative_to(repo)))
            else:
                failed.append("hooks/pre-commit")

    action_src = _data_path("action", "repocodex.yml")
    action_dest = repo / ".github" / "workflows" / "repocodex.yml"
    if not action_src.exists():
        failed.append("action/repocodex.yml (missing from distribution)")
    else:
        _copy(action_src, action_dest)
        if _resolvable(action_dest):
            installed.append(str(action_dest.relative_to(repo)))
        else:
            failed.append("action/repocodex.yml")

    if skills:
        for name in ("repocodex-coding", "repocodex-review"):
            src = _data_path("skills", name, "SKILL.md")
            if not src.exists():
                failed.append(f"skills/{name}/SKILL.md (missing from distribution)")
                continue
            for dest_root in (repo / ".cursor" / "skills" / name, repo / ".claude" / "skills" / name):
                dest = dest_root / "SKILL.md"
                _copy(src, dest)
                if _resolvable(dest):
                    installed.append(str(dest.relative_to(repo)))
                else:
                    failed.append(str(dest.relative_to(repo)))
        plugin_src = _data_path("plugin")
        plugin_dest = repo / ".repocodex" / "plugin"
        if plugin_src.exists():
            shutil.copytree(plugin_src, plugin_dest, dirs_exist_ok=True)
            for hook in (plugin_dest / "hooks").glob("*"):
                if hook.is_file():
                    hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
            adapter = plugin_dest / "hooks" / "claude-pre-commit"
            portable = plugin_dest / "hooks" / "pre-commit"
            if adapter.exists() and not portable.exists():
                failed.append("plugin/hooks/pre-commit (adapter would not resolve)")
            elif _resolvable(plugin_dest):
                installed.append(str(plugin_dest.relative_to(repo)))
            else:
                failed.append(".repocodex/plugin")
        else:
            failed.append("plugin (missing from distribution)")

    if mcp:
        # run_mcp cannot start in this release; do not copy mcp.json or claim a working surface.
        skipped.append("mcp (not available in this release)")

    config = repo / ".repocodex.toml"
    if not config.exists():
        config.write_text(
            f'engine_version = "{ENGINE_VERSION}"\nposture = "shadow"\nscope_lines = 40\n',
            encoding="utf-8",
        )
        installed.append(".repocodex.toml")

    gitignore = repo / ".gitignore"
    ignore_line = ".repocodex/metrics.jsonl"
    if gitignore.exists():
        text = gitignore.read_text(encoding="utf-8")
        if ignore_line not in text and ".repocodex/" not in text:
            gitignore.write_text(text.rstrip() + f"\n{ignore_line}\n", encoding="utf-8")
    else:
        gitignore.write_text(f"{ignore_line}\n", encoding="utf-8")

    return envelope(
        {
            "installed": installed,
            "failed": failed,
            "skipped": skipped,
            "ok": not failed,
            "mcp": False,
        }
    )
