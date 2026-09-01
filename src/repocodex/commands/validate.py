from __future__ import annotations

import os
from pathlib import Path

from repocodex import ENGINE_VERSION
from repocodex.config import RepoConfig, load_config
from repocodex.engine.blocking import REQUIRED_CHECK_REASONS
from repocodex.engine.contradiction import contradiction_flags
from repocodex.engine.dilution import dilution_warnings
from repocodex.engine.impact import intent_impact
from repocodex.engine.liveness import CLAIM_BROKEN, DRIFT, LIVE, REANCHOR, WEAK, classify_anchor, evaluate_claims
from repocodex.engine.ratchet import skipped_memory
from repocodex.metrics import Timer, false_drift_rate, record_metric
from repocodex.schema import ConceptStatus, envelope
from repocodex.store.bundle import load_concepts
from repocodex.store.reverse_index import index_sync_errors, merged_index
from repocodex.tools.git import git_is_tracked, run_git


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
    order = [LIVE, WEAK, REANCHOR, CLAIM_BROKEN, "CONTRADICTION", "RECONCILE"]
    mapped = []
    for item in outcomes:
        mapped.append("RECONCILE" if item == DRIFT else item)
    rank = {name: i for i, name in enumerate(order)}
    worst = LIVE
    for item in mapped:
        if rank.get(item, 0) > rank.get(worst, 0):
            worst = item
    return worst


def _in_ci() -> bool:
    return os.environ.get("CI", "").lower() in {"1", "true", "yes"} or os.environ.get(
        "GITHUB_ACTIONS", ""
    ).lower() in {"1", "true", "yes"}


def _ack_evidence(root: Path, ack_file: str | None) -> dict | None:
    env_evidence = os.environ.get("REPOCODEX_REVIEW_ACK_EVIDENCE")
    if env_evidence and _in_ci():
        return {"via": "ci_context", "evidence": env_evidence[:500]}
    path_str = ack_file or os.environ.get("REPOCODEX_ACK_FILE")
    if not path_str:
        default = root / ".repocodex" / "acknowledgments" / "memory-exempt.json"
        if default.is_file() and git_is_tracked(str(default.relative_to(root)), root):
            path_str = str(default.relative_to(root))
        else:
            return None
    rel = path_str
    candidate = Path(path_str)
    if candidate.is_absolute():
        try:
            rel = str(candidate.relative_to(root))
        except ValueError:
            return None
    if not git_is_tracked(rel, root):
        return None
    target = root / rel
    if not target.is_file():
        return None
    text = target.read_text(encoding="utf-8")
    if "memory-exempt" not in text and "repocodex-ack" not in text.lower():
        return None
    return {"via": "committed_record", "path": rel}


def validate(
    root: Path,
    *,
    base: str | None = None,
    staged: bool = False,
    all_concepts: bool = False,
    memory_exempt: bool = False,
    review_ack: bool = False,
    ack_file: str | None = None,
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
                if not any(anchor.path == path or path.endswith(Path(anchor.path).name) for path in files):
                    continue
            outcomes.append(classify_anchor(doc, i, anchor, config, staged=staged, base=base))

    claim_findings = []
    by_concept_class: dict[str, str] = {}
    for outcome in outcomes:
        prev = by_concept_class.get(outcome.concept)
        by_concept_class[outcome.concept] = outcome.classification if not prev else prev
    seen_concepts = {o.concept for o in outcomes}
    for doc in intersecting:
        if doc.identity not in seen_concepts and not all_concepts:
            continue
        anchor_class = by_concept_class.get(doc.identity)
        claim_findings.extend(
            finding.to_json()
            for finding in evaluate_claims(doc, config, anchor_class=anchor_class)
        )

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
    sync_errors = index_sync_errors(root, staged=staged)
    ratchet = skipped_memory(
        files,
        concepts,
        index,
        config,
        posture=config.posture,
        staged=staged,
        base=base,
    )
    dilutions = dilution_warnings(concepts, files, config, base=base, staged=staged)

    classifications = [o.classification for o in outcomes]
    if contradictions:
        classifications.append("CONTRADICTION")
    if claim_findings:
        classifications.append(CLAIM_BROKEN)
    result = _worst(classifications) if classifications else LIVE
    if lost:
        result = "RECONCILE"
    if ratchet and result in {LIVE, WEAK}:
        result = "WRITE"

    blocking_reasons: list[str] = []
    if lost:
        blocking_reasons.append("drift")
    if claim_findings:
        blocking_reasons.append("claim_broken")
    if sync_errors:
        blocking_reasons.append("index_sync")
    if ratchet:
        blocking_reasons.append("skipped_memory")
    if contradictions:
        blocking_reasons.append("contradiction")
    blocking_reasons = [reason for reason in blocking_reasons if reason in REQUIRED_CHECK_REASONS]
    blocking_reasons = list(dict.fromkeys(blocking_reasons))

    labels = os.environ.get("GITHUB_PR_LABELS", "")
    if "memory-exempt" in labels:
        memory_exempt = True

    audit_entries: list[str] = []
    repair_tasks: list[dict] = []
    exempt_applied = False
    exemption_refused = None
    if memory_exempt and blocking_reasons:
        evidence = _ack_evidence(root, ack_file)
        if evidence:
            exempt_applied = True
            blocking_reasons = []
            audit_entries.append("memory-exempt override acknowledged by review agent")
            repair_tasks.append(
                {
                    "path": ".context/repair-tasks/exempt.md",
                    "body": "Follow-up: repair skipped memory / drift after memory-exempt merge.\n",
                }
            )
        else:
            exemption_refused = "missing_acknowledgment"

    if config.posture == "shadow":
        blocking = "skipped_memory" in blocking_reasons
    else:
        blocking = bool(blocking_reasons)

    for outcome in outcomes:
        if outcome.classification == DRIFT:
            record_metric(
                root,
                "drift",
                {"concept": outcome.concept, "path": outcome.path, "reason": outcome.reason},
            )
    derived_false_drift = false_drift_rate(root)

    payload = envelope(
        {
            "result": result,
            "posture": config.posture,
            "blocking": blocking,
            "blocking_reasons": blocking_reasons,
            "outcomes": [o.to_json() for o in outcomes],
            "lost": lost,
            "weak": weak,
            "claim_findings": claim_findings,
            "patches": patches,
            "candidates": candidates,
            "impacted_scenarios": impacted,
            "dilution_warnings": dilutions,
            "contradictions": contradictions,
            "index_sync": sync_errors,
            "skipped_memory": ratchet,
            "changed_files": files,
            "memory_exempt": exempt_applied,
            "exemption_refused": exemption_refused,
            "audit_entries": audit_entries,
            "repair_tasks": repair_tasks,
            "false_drift_rate": derived_false_drift,
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
            "reconcile_retries": len(lost),
            "false_drift_rate": derived_false_drift,
        },
    )
    return payload
