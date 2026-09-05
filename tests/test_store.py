"""Pin store discovery, concept load, and reverse-index sync.

Discover ``.context`` roots while skipping venv and dependency trees. Writing
a concept updates the catalog, log, and merged reverse index.
"""

from __future__ import annotations

from pathlib import Path

from repocodex.schema import parse_concept
from repocodex.store.bundle import discover_context_roots, load_concepts, write_concept
from repocodex.store.reverse_index import expected_index, index_sync_errors, merged_index, parse_index_text, regenerate_all


def test_discover_skips_dependency_and_venv_trees(tmp_path: Path):
    root = tmp_path / "app"
    real = root / ".context"
    shard = root / "packages" / "billing" / ".context"
    decoys = [
        root / "node_modules" / "pkg" / ".context",
        root / ".venv" / "lib" / ".context",
        root / "venv" / "lib" / ".context",
        root / "env" / "lib" / ".context",
        root / "cdk.out" / "asset" / ".context",
        root / "infrastructure" / "cdk.out" / ".context",
        root / ".kiro" / "steering" / ".context",
    ]
    for path in [real, shard, *decoys]:
        path.mkdir(parents=True)

    found = {path.resolve() for path in discover_context_roots(root)}
    assert real.resolve() in found
    assert shard.resolve() in found
    assert found == {real.resolve(), shard.resolve()}


def test_bundle_loads_one_concept_per_file(repo):
    docs = load_concepts(repo.root)
    identities = {doc.identity for doc in docs}
    assert "invariants/enterprise-grace-period" in identities
    assert "decisions/custom-data-streamer" in identities
    assert "workflows/checkout-capture" in identities
    assert "decisions/layering-no-domain-to-infra" in identities
    workflow = next(d for d in docs if d.identity == "workflows/checkout-capture")
    assert len(workflow.anchors) == 3
    guard = next(d for d in docs if d.identity == "decisions/layering-no-domain-to-infra")
    assert guard.frontmatter.type == "GuardrailDecision"


def test_write_updates_catalog_log_and_reverse_index(repo):
    from tests.fixtures.repos import STREAMER_CONCEPT

    doc = parse_concept(STREAMER_CONCEPT.replace("custom-data-streamer", "copy"), "decisions/copy-streamer")
    doc.frontmatter.title = "Copy"
    write_concept(repo.root, doc)
    regenerate_all(repo.root)
    catalog = (repo.root / ".context" / "decisions" / "index.md").read_text(encoding="utf-8")
    assert "copy-streamer" in catalog
    log = (repo.root / ".context" / "log.md").read_text(encoding="utf-8")
    assert "copy-streamer" in log
    mapping = merged_index(repo.root)
    assert "src/core/streams/CustomDataStreamer.py" in mapping
    assert "decisions/copy-streamer" in mapping["src/core/streams/CustomDataStreamer.py"]


def test_index_sync_detects_drift(repo):
    from repocodex.store.reverse_index import reverse_index_path

    path = reverse_index_path(repo.root, repo.root / ".context")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# reverse-index\n", encoding="utf-8")
    errors = index_sync_errors(repo.root)
    assert errors


def test_parse_index_roundtrip():
    text = "## `src/a.py`\n- `decisions/x`\n"
    assert parse_index_text(text) == {"src/a.py": ["decisions/x"]}
