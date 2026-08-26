from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    argv: list[str]


def run_git(args: list[str], cwd: Path | str, check: bool = False) -> CommandResult:
    argv = ["git", *args]
    completed = subprocess.run(
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    result = CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        argv=argv,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result


def git_version(cwd: Path | str | None = None) -> str:
    result = run_git(["version"], cwd=cwd or Path.cwd())
    return result.stdout.strip() or result.stderr.strip()


def git_check_ignore(path: str, cwd: Path) -> bool:
    result = run_git(["check-ignore", "-q", path], cwd=cwd)
    return result.returncode == 0


def git_ls_files(cwd: Path) -> list[str]:
    result = run_git(["ls-files", "-z"], cwd=cwd)
    if result.returncode != 0:
        return []
    return [path for path in result.stdout.split("\0") if path]


def git_is_tracked(path: str, cwd: Path) -> bool:
    result = run_git(["ls-files", "--error-unmatch", "--", path], cwd=cwd)
    return result.returncode == 0


def git_show_index(path: str, cwd: Path) -> str | None:
    result = run_git(["show", f":{path}", "--"], cwd=cwd)
    if result.returncode != 0:
        return None
    return result.stdout
