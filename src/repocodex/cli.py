from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from repocodex.commands.audit import audit as run_audit
from repocodex.commands.bootstrap import bootstrap as run_bootstrap
from repocodex.commands.context import context_for
from repocodex.commands.install import install as run_install
from repocodex.commands.reconcile import apply_anchor_patch, reconcile_memory
from repocodex.commands.repair import repair as run_repair
from repocodex.commands.validate import validate as run_validate
from repocodex.commands.write import write_memory
from repocodex.schema import envelope

app = typer.Typer(no_args_is_help=True, add_completion=False, help="RepoCodex executable memory CLI")


def _emit(payload: dict, exit_code: int = 0) -> None:
    typer.echo(json.dumps(payload, indent=2))
    raise typer.Exit(exit_code)


def _repo() -> Path:
    return Path.cwd()


@app.command("validate")
def validate_command(
    diff: bool = typer.Option(False, "--diff", help="Attest anchors intersecting the diff"),
    base: Optional[str] = typer.Option(None, "--base", help="Git diff base, e.g. origin/main...HEAD"),
    staged: bool = typer.Option(False, "--staged"),
    all_concepts: bool = typer.Option(False, "--all"),
    check: bool = typer.Option(False, "--check", help="Exit 1 on deterministic blocking outcomes"),
    hook: bool = typer.Option(False, "--hook"),
    memory_exempt: bool = typer.Option(False, "--memory-exempt"),
    review_ack: bool = typer.Option(False, "--review-ack"),
    apply_patches: bool = typer.Option(False, "--apply-patches"),
) -> None:
    """Attest anchors on the working tree or diff. JSON includes engine_version."""
    payload = run_validate(
        _repo(),
        base=base,
        staged=staged,
        all_concepts=all_concepts or not diff,
        memory_exempt=memory_exempt,
        review_ack=review_ack,
    )
    if apply_patches:
        for patch in payload.get("patches") or []:
            apply_anchor_patch(_repo(), patch)
            payload.setdefault("applied_patches", []).append(patch)
    code = 1 if (check or hook) and payload.get("blocking") else 0
    _emit(payload, code)


@app.command("write")
def write_command(
    concept: Optional[Path] = typer.Argument(None),
    identity: Optional[str] = typer.Option(None, "--identity"),
    stdin: bool = typer.Option(False, "--stdin"),
) -> None:
    """Write-gate a concept into .context/."""
    text = None
    if stdin:
        text = typer.get_text_stream("stdin").read()
    if concept is None and text is None:
        raise typer.BadParameter("provide a concept file or --stdin")
    payload = write_memory(_repo(), concept or Path("."), identity=identity, stdin_text=text)
    _emit(payload, 0 if payload.get("accepted") else 1)


@app.command("reconcile")
def reconcile_command(
    concept: Optional[Path] = typer.Argument(None),
    identity: Optional[str] = typer.Option(None, "--identity"),
    apply_patch: Optional[str] = typer.Option(None, "--apply-patch", help="JSON patch object"),
) -> None:
    """Repair DRIFT with gate-enforced new anchors, or apply a REANCHOR patch."""
    repo = _repo()
    if apply_patch:
        patch = json.loads(apply_patch)
        path = apply_anchor_patch(repo, patch)
        _emit(envelope({"applied": True, "path": str(path)}))
    if concept is None:
        raise typer.BadParameter("provide a concept file")
    payload = reconcile_memory(repo, concept, identity=identity)
    _emit(payload, 0 if payload.get("accepted") else 1)


@app.command("context")
def context_command(
    paths: list[Path] = typer.Argument(..., metavar="PATHS"),
    drafts: bool = typer.Option(False, "--drafts"),
) -> None:
    """Staged retrieval: reverse index → bodies + one link-hop of titles."""
    payload = context_for(_repo(), [str(p) for p in paths], include_drafts=drafts)
    _emit(payload)


@app.command("repair")
def repair_command() -> None:
    """Invoke the human repair flow against the current RECONCILE state."""
    _emit(run_repair(_repo()))


@app.command("install")
def install_command(
    mcp: bool = typer.Option(False, "--mcp", help="Register optional MCP wrapper"),
) -> None:
    """Install pre-commit hook, GitHub Action, skills, and optional MCP."""
    _emit(run_install(_repo(), mcp=mcp))


@app.command("bootstrap")
def bootstrap_command() -> None:
    """Mine history/comments/docs; keep only gate-passing drafts."""
    _emit(run_bootstrap(_repo()))


@app.command("audit")
def audit_command(
    sample_size: int = typer.Option(10, "--sample-size"),
    seed: int = typer.Option(0, "--seed"),
) -> None:
    """Sampling truth audit plus distinctiveness re-scoring."""
    _emit(run_audit(_repo(), sample_size=sample_size, seed=seed))


@app.command("mcp")
def mcp_command() -> None:
    """Run the optional MCP server wrapping the CLI."""
    from repocodex.mcp_server import run_mcp

    run_mcp()
