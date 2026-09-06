"""Copy RepoCodex hooks, skills, rules, and optional MCP config into a repository."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import sys

from repocodex import ENGINE_VERSION, render_engine_version
from repocodex.mcp_server import MCP_EXTRA_HINT, mcp_extra_available
from repocodex.schema import envelope

_HOOK_CLI_TOKEN = "'__REPOCODEX_HOOK_CLI__'"
_HOOK_PYTHON_TOKEN = "'__REPOCODEX_HOOK_PYTHON__'"


def _data_path(*parts: str) -> Path:
    """Resolve a path under the packaged ``repocodex/data`` tree."""
    base = Path(__file__).resolve().parents[1] / "data"
    return base.joinpath(*parts)


def _copy(src: Path, dest: Path) -> None:
    """Copy ``src`` to ``dest``, creating parent directories as needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)


def _copy_substituted(src: Path, dest: Path) -> None:
    """Copy ``src`` to ``dest``, filling the engine-version token."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render_engine_version(src.read_text(encoding="utf-8")), encoding="utf-8")


def resolve_install_binding() -> tuple[str, str]:
    """Return console-script and interpreter paths for the running install.

    Prefers a ``repocodex`` executable next to ``sys.executable`` (venv or
    system Scripts/bin). Always returns the current interpreter so the hook
    can fall back to ``python -m repocodex`` from the same environment.

    Returns:
        A pair of ``(cli_script, python_executable)``. ``cli_script`` is
        empty when no executable sits next to the interpreter.
    """
    # Keep the venv console stub. Path.resolve() follows it to the
    # framework interpreter, which does not have the package.
    python = sys.executable
    script = Path(python).parent / "repocodex"
    cli = str(script) if script.is_file() and os.access(script, os.X_OK) else ""
    return cli, python


def _sh_single_quote(value: str) -> str:
    """Return ``value`` wrapped in POSIX single quotes."""
    return "'" + value.replace("'", "'\\''") + "'"


def render_pre_commit_hook(template: str, *, cli: str = "", python: str = "") -> str:
    """Fill install-time CLI bind placeholders in a pre-commit hook template.

    Args:
        template: Hook script text containing ``__REPOCODEX_HOOK_CLI__`` tokens.
        cli: Absolute path to a ``repocodex`` console script, if any.
        python: Absolute path to the interpreter that has the package.

    Returns:
        Hook text with quoted bind paths substituted.
    """
    return template.replace(_HOOK_CLI_TOKEN, _sh_single_quote(cli)).replace(
        _HOOK_PYTHON_TOKEN, _sh_single_quote(python)
    )


def _resolvable(path: Path) -> bool:
    """Return True when ``path`` exists after an install copy."""
    return path.exists()


def install(
    repo: Path,
    *,
    mcp: bool = False,
    skills: bool = True,
) -> dict:
    """Install distribution artefacts into ``repo`` and report what landed.

    Always attempts the git pre-commit hook (when ``.git`` exists) and the
    GitHub Actions workflow. When ``skills`` is true, also copies Cursor and
    Claude skills, the Cursor rule, a CLAUDE.md pointer (create or append),
    and the plugin tree. When ``mcp`` is true, merges ``mcpServers`` into
    ``.cursor/mcp.json`` if the MCP extra is installed. Creates
    ``.repocodex.toml`` when missing and ignores ``.repocodex/metrics.jsonl``.

    Returns:
        Envelope with ``installed``, ``failed``, ``skipped`` path lists,
        ``ok`` (true when ``failed`` is empty), and ``mcp`` (true only when
        MCP config was written).

    """
    installed: list[str] = []
    failed: list[str] = []
    skipped: list[str] = []
    mcp_ok = False

    hook_src = _data_path("hooks", "pre-commit")
    hook_dest = repo / ".git" / "hooks" / "pre-commit"
    if (repo / ".git").exists():
        if not hook_src.exists():
            failed.append("hooks/pre-commit (missing from distribution)")
        else:
            cli, python = resolve_install_binding()
            text = render_pre_commit_hook(
                hook_src.read_text(encoding="utf-8"),
                cli=cli,
                python=python,
            )
            hook_dest.parent.mkdir(parents=True, exist_ok=True)
            hook_dest.write_text(text, encoding="utf-8")
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
        _copy_substituted(action_src, action_dest)
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

        # Cursor rule — alwaysApply points at the skill; the skill owns the loop.
        cursor_rule_src = _data_path("rules", "cursor", "repocodex.mdc")
        cursor_rule_dest = repo / ".cursor" / "rules" / "repocodex.mdc"
        if cursor_rule_src.exists():
            _copy(cursor_rule_src, cursor_rule_dest)
            if _resolvable(cursor_rule_dest):
                installed.append(str(cursor_rule_dest.relative_to(repo)))
            else:
                failed.append(".cursor/rules/repocodex.mdc")
        else:
            failed.append(".cursor/rules/repocodex.mdc (missing from distribution)")

        # CLAUDE.md — Claude Code auto-reads this at session start; pointer only.
        claude_md_src = _data_path("rules", "claude", "CLAUDE.md")
        claude_md_dest = repo / "CLAUDE.md"
        if claude_md_src.exists():
            if not claude_md_dest.exists():
                _copy(claude_md_src, claude_md_dest)
                if _resolvable(claude_md_dest):
                    installed.append("CLAUDE.md")
                else:
                    failed.append("CLAUDE.md")
            else:
                # CLAUDE.md already exists — append a pointer if not present.
                existing = claude_md_dest.read_text(encoding="utf-8")
                marker = ".claude/skills/repocodex-coding/SKILL.md"
                if marker not in existing:
                    addition = "\n" + claude_md_src.read_text(encoding="utf-8")
                    claude_md_dest.write_text(existing.rstrip() + addition, encoding="utf-8")
                    installed.append("CLAUDE.md (updated)")
                else:
                    skipped.append("CLAUDE.md (repocodex section already present)")
        else:
            failed.append("CLAUDE.md (missing from distribution)")
        plugin_src = _data_path("plugin")
        plugin_dest = repo / ".repocodex" / "plugin"
        if plugin_src.exists():
            shutil.copytree(plugin_src, plugin_dest, dirs_exist_ok=True)
            plugin_json = plugin_dest / "plugin.json"
            if plugin_json.is_file():
                plugin_json.write_text(
                    render_engine_version(plugin_json.read_text(encoding="utf-8")),
                    encoding="utf-8",
                )
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
        if not mcp_extra_available():
            failed.append(MCP_EXTRA_HINT)
        else:
            mcp_src = _data_path("plugin", "mcp.json")
            cursor_mcp = repo / ".cursor" / "mcp.json"
            if not mcp_src.exists():
                failed.append("plugin/mcp.json (missing from distribution)")
            else:
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
                mcp_ok = True

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
            "mcp": mcp_ok,
        }
    )
