"""Thin wrappers around the ripgrep binary used by matching and impact."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


@dataclass
class CommandResult:
    """Captured stdout, stderr, and argv from a subprocess."""

    returncode: int
    stdout: str
    stderr: str
    argv: list[str]


def rg_binary() -> str:
    """Return the path to ``rg``.

    Raises:
        FileNotFoundError: If ripgrep is not on PATH.
    """
    found = shutil.which("rg")
    if not found:
        raise FileNotFoundError("ripgrep (rg) is required")
    return found


def run_rg(args: list[str], cwd: Path | str) -> CommandResult:
    """Run ripgrep with ``args`` in ``cwd`` and return the captured result."""
    argv = [rg_binary(), *args]
    completed = subprocess.run(
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        argv=argv,
    )


def rg_version() -> str:
    """Return the first line of ``rg --version``, or an empty string."""
    result = run_rg(["--version"], cwd=Path.cwd())
    first = (result.stdout or result.stderr).splitlines()
    return first[0].strip() if first else ""


def _glob_args(exclusions: list[str] | None) -> list[str]:
    """Return ripgrep --glob arguments that exclude .git and ``exclusions``."""
    args: list[str] = ["--glob", "!.git/**"]
    for glob in exclusions or []:
        pattern = glob if glob.startswith("!") else f"!{glob}"
        args.extend(["--glob", pattern])
    return args


def rg_count(pattern: str, root: Path, *, fixed: bool = True, exclusions: list[str] | None = None) -> int:
    """Return the total number of matches for ``pattern`` under ``root``."""
    args = ["--count-matches", "--no-heading", "--color", "never", *_glob_args(exclusions)]
    if fixed:
        args.append("-F")
    args.extend(["--", pattern, str(root)])
    result = run_rg(args, cwd=root)
    total = 0
    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        try:
            total += int(line.rsplit(":", 1)[1])
        except ValueError:
            continue
    return total


def search_file(pattern: str, path: Path, *, fixed: bool = True) -> list[str]:
    """Return matching lines from ``path``, including ripgrep line numbers."""
    args = ["--color", "never", "--line-number"]
    if fixed:
        args.append("-F")
    args.extend(["--", pattern, str(path)])
    result = run_rg(args, cwd=path.parent)
    return [line for line in result.stdout.splitlines() if line]


def rg_files(pattern: str, root: Path, *, fixed: bool = True, exclusions: list[str] | None = None) -> list[str]:
    """Return paths under ``root`` that contain ``pattern``."""
    args = ["--files-with-matches", "--color", "never", *_glob_args(exclusions)]
    if fixed:
        args.append("-F")
    args.extend(["--", pattern, str(root)])
    result = run_rg(args, cwd=root)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]
