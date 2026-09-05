"""Pin monorepo shard discovery and isolated reverse indexes.

A nested ``packages/*/ .context`` tree must get its own generated reverse
index under ``.repocodex/reverse-index``, not a leftover file in the shard.
"""

from __future__ import annotations

from tests.fixtures.repos import GRACE_CONCEPT, init_git_repo, write_architecture_fixtures
from repocodex.commands.validate import validate
from repocodex.store.bundle import discover_context_roots
from repocodex.store.reverse_index import regenerate_all


def test_monorepo_shards_have_local_indexes(tmp_path):
    root = tmp_path / "mono"
    root.mkdir()
    write_architecture_fixtures(root)
    shard = root / "packages" / "billing" / ".context" / "invariants"
    shard.mkdir(parents=True)
    (shard / "local.md").write_text(
        GRACE_CONCEPT.replace("invariants/enterprise-grace-period", "invariants/local"),
        encoding="utf-8",
    )
    (shard.parent / "index.md").write_text("---\nokf_version: '0.2'\n---\n\n# shard\n", encoding="utf-8")
    init_git_repo(root)
    regenerate_all(root)
    roots = discover_context_roots(root)
    assert len(roots) >= 2
    assert not (root / "packages" / "billing" / ".context" / "reverse-index.md").exists()
    assert (root / ".repocodex" / "reverse-index" / "packages-billing.md").exists()
    payload = validate(root, all_concepts=True)
    assert payload["engine_version"]
