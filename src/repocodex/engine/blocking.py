from __future__ import annotations

REQUIRED_CHECK_REASONS = frozenset(
    {
        "drift",
        "claim_broken",
        "skipped_memory",
        "index_sync",
        "contradiction",
    }
)
