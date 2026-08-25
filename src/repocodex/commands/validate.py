from __future__ import annotations

import os
from pathlib import Path

from repocodex import ENGINE_VERSION
from repocodex.config import RepoConfig, load_config
from repocodex.engine.contradiction import contradiction_flags
from repocodex.engine.dilution import dilution_warnings
from repocodex.engine.impact import intent_impact
from repocodex.engine.liveness import DRIFT, LIVE, REANCHOR, WEAK, classify_anchor
from repocodex.engine.ratchet import skipped_memory
from repocodex.metrics import Timer, record_metric
from repocodex.schema import ConceptStatus, envelope, utc_now
from repocodex.store.bundle import append_log, discover_context_roots, load_concepts
from repocodex.store.reverse_index import index_sync_errors, merged_index
from repocodex.tools.git import run_git


def _paths_from_name_status(output: str) -> list[str]:
    files: list[str] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if not parts or not parts[0]:
            continue
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            files.extend([parts[1], parts[2]])
        elif len(parts) >= 2:
            files.append(parts[1])
    return files


def changed_files(root: Path, *, base: str | None, staged: bool) -> list[str]:
    args = ["diff", "-M", "--name-status"]
    if staged:
        args.append("--cached")
    elif base:
        args.append(base)
    result = run_git(args, cwd=root)
    files = _paths_from_name_status(result.stdout)
    if not files and not staged and not base:
        unstaged = run_git(["diff", "-M", "--name-status"], cwd=root)
        staged_files = run_git(["diff", "-M", "--name-status", "--cached"], cwd=root)
        untracked = run_git(["ls-files", "--others", "--exclude-standard"], cwd=root)
        files = sorted(
            {
                *_paths_from_name_status(unstaged.stdout),
                *_paths_from_name_status(staged_files.stdout),
                *[line.strip() for line in untracked.stdout.splitlines() if line.strip()],
            }
        )
    return [path for path in dict.fromkeys(files) if path]


def _worst(outcomes: list[str]) -> str:
    order = [LIVE, WEAK, REANCHOR, "CONTRADICTION", "RECONCILE"]
    mapped = []
    for item in outcomes:
        mapped.append("RECONCILE" if item == DRIFT else item)
    rank = {name: i for i, name in enumerate(order)}
    worst = LIVE
    for item in mapped:
        if rank.get(item, 0) > rank.get(worst, 0):
            worst = item
    return worst


def validate(
    root: Path,
    *,
    base: str | None = None,
    staged: bool = False,
    all_concepts: bool = False,
    memory_exempt: bool = False,
    review_ack: bool = False,
    config: RepoConfig | None = None,
) -> dict:
    timer = Timer()
    config = config or load_config(root)
    files = changed_files(root, base=base, staged=staged)
    concepts = load_concepts(root)
    index = merged_index(root)
    intersecting: list = []
    file_set = set(files)
    for doc in concepts:
        if doc.status != ConceptStatus.stable:
            continue
        if all_concepts or any(path in file_set for path in doc.pinned_paths):
            intersecting.append(doc)

    outcomes = []
    for doc in intersecting:
        for i, anchor in enumerate(doc.anchors):
            if not all_concepts and files and anchor.path not in file_set:
                # still attest anchors whose files moved off the diff via rename
                if not any(anchor.path == path or path.endswith(Path(anchor.path).name) for path in files):
                    continue
            outcomes.append(classify_anchor(doc, i, anchor, config, diff_files=files))

    lost = [o.to_json() for o in outcomes if o.classification == DRIFT]
    weak = [o.to_json() for o in outcomes if o.classification == WEAK]
    patches = [o.patch for o in outcomes if o.patch]
    candidates = []
    for outcome in outcomes:
        for item in outcome.candidates or []:
            if item not in candidates:
                candidates.append(item)

    impacted = intent_impact(files, concepts, index)
    contradictions = contradiction_flags(concepts, root)
    sync_errors = index_sync_errors(root)
    context_files = {path for path in files if ".context/" in path.replace("\\", "/")}
    ratchet = skipped_memory(
        files,
        concepts,
        index,
        config,
        context_touched=bool(context_files),
        posture=config.posture,
    )
    dilutions = dilution_warnings(concepts, files, config, base=base, staged=staged)

    classifications = [o.classification for o in outcomes]
    if contradictions:
        classifications.append("CONTRADICTION")
    result = _worst(classifications) if classifications else LIVE
    if lost:
        result = "RECONCILE"

    blocking_reasons: list[str] = []
    if config.posture != "shadow":
        if lost:
            blocking_reasons.append("drift")
        if sync_errors:
            blocking_reasons.append("index_sync")
        if ratchet:
            blocking_reasons.append("skipped_memory")
        if contradictions:
            blocking_reasons.append("contradiction")

    labels = os.environ.get("GITHUB_PR_LABELS", "")
    if "memory-exempt" in labels:
        memory_exempt = True

    exempt_applied = False
    if memory_exempt and blocking_reasons:
        if review_ack:
            exempt_applied = True
            blocking_reasons = []
            roots = discover_context_roots(root)
            ctx = roots[0] if roots else root / ".context"
            ctx.mkdir(parents=True, exist_ok=True)
            append_log(ctx, "memory-exempt override acknowledged by review agent")
            task_dir = ctx / "repair-tasks"
            task_dir.mkdir(exist_ok=True)
            (task_dir / f"exempt-{utc_now().replace(':', '')}.md").write_text(
                "Follow-up: repair skipped memory / drift after memory-exempt merge.\n",
                encoding="utf-8",
            )
        else:
            blocking_reasons.append("exempt_requires_review_ack")

    payload = envelope(
        {
            "result": result,
            "posture": config.posture,
            "blocking": bool(blocking_reasons),
            "blocking_reasons": blocking_reasons,
            "outcomes": [o.to_json() for o in outcomes],
            "lost": lost,
            "weak": weak,
            "patches": patches,
            "candidates": candidates,
            "impacted_scenarios": impacted,
            "dilution_warnings": dilutions,
            "contradictions": contradictions,
            "index_sync": sync_errors,
            "skipped_memory": ratchet,
            "changed_files": files,
            "memory_exempt": exempt_applied,
            "latency_ms": timer.ms(),
        },
        engine_version=ENGINE_VERSION,
    )
    record_metric(
        root,
        "validate",
        {
            "result": result,
            "latency_ms": payload["latency_ms"],
            "posture": config.posture,
            "rejection_reasons": blocking_reasons,
            "reconcile_retries": 1 if lost else 0,
            "false_drift_rate": None,
            "tokens_per_turn": None,
        },
    )
    return payload
