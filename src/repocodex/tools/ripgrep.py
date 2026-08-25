from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    argv: list[str]


def rg_binary() -> str:
    found = shutil.which("rg")
    if not found:
        raise FileNotFoundError("ripgrep (rg) is required")
    return found


def run_rg(args: list[str], cwd: Path | str) -> CommandResult:
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
    result = run_rg(["--version"], cwd=Path.cwd())
    first = (result.stdout or result.stderr).splitlines()
    return first[0].strip() if first else ""


def _glob_args(exclusions: list[str] | None) -> list[str]:
    args: list[str] = ["--glob", "!.git/**"]
    for glob in exclusions or []:
        pattern = glob if glob.startswith("!") else f"!{glob}"
        args.extend(["--glob", pattern])
    return args


def rg_count(pattern: str, root: Path, *, fixed: bool = True, exclusions: list[str] | None = None) -> int:
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
    args = ["--color", "never", "--line-number"]
    if fixed:
        args.append("-F")
    args.extend(["--", pattern, str(path)])
    result = run_rg(args, cwd=path.parent)
    return [line for line in result.stdout.splitlines() if line]


def rg_files(pattern: str, root: Path, *, fixed: bool = True, exclusions: list[str] | None = None) -> list[str]:
    args = ["--files-with-matches", "--color", "never", *_glob_args(exclusions)]
    if fixed:
        args.append("-F")
    args.extend(["--", pattern, str(root)])
    result = run_rg(args, cwd=root)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]
