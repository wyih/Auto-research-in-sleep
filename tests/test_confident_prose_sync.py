"""Keep the business line's anti-defensive-writing contract in sync with upstream.

Upstream ARIS maintains the canonical CONFIDENT PROSE, HONEST LIMITS block
inline in ``skills/paper-write/SKILL.md`` (#423/#424). The business release
does not install ``paper-write`` — its writing skill is the portable
``business-paper-writing`` — so the contract lives in the portable shared
reference ``skills/shared-references/business-confident-prose.md``, which all
three skill trees ship byte-identically.

These tests make the relationship structural instead of manual:

- when a future upstream merge changes the paper-write block, the hash test
  fails and tells the maintainer to re-sync the shared reference (one file),
  instead of the business line silently going stale;
- the pointer test guards against the binding reference being dropped from
  ``business-paper-writing``;
- the content test guards against the shared reference being gutted.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PAPER_WRITE = REPO_ROOT / "skills" / "paper-write" / "SKILL.md"
BUSINESS_WRITING = REPO_ROOT / "skills" / "business-paper-writing" / "SKILL.md"
SHARED_REF = REPO_ROOT / "skills" / "shared-references" / "business-confident-prose.md"

# sha256 of the upstream block as last synced. Bump this constant together
# with a content refresh of business-confident-prose.md.
UPSTREAM_BLOCK_SHA256 = "ca17bd19079f3f1f750648f6d6717bdd059c6941affbde8a50bf8aa8bd930ebb"


def upstream_confident_prose_block() -> str:
    lines = PAPER_WRITE.read_text(encoding="utf-8").splitlines()
    start = next(
        i for i, line in enumerate(lines) if line.startswith("=== CONFIDENT PROSE")
    )
    end = next(
        i for i in range(start + 1, len(lines)) if lines[i].startswith("- **")
    )
    return "\n".join(lines[start:end]).rstrip() + "\n"


def test_shared_reference_tracks_upstream_block() -> None:
    digest = hashlib.sha256(upstream_confident_prose_block().encode()).hexdigest()
    assert digest == UPSTREAM_BLOCK_SHA256, (
        "skills/paper-write/SKILL.md's CONFIDENT PROSE, HONEST LIMITS block "
        "changed (likely via an upstream merge). Re-sync "
        "skills/shared-references/business-confident-prose.md with the new "
        "content, then update UPSTREAM_BLOCK_SHA256 in "
        "tests/test_confident_prose_sync.py."
    )


def test_business_writing_binds_the_shared_reference() -> None:
    text = BUSINESS_WRITING.read_text(encoding="utf-8")
    assert "../shared-references/business-confident-prose.md" in text
    assert "binding, not advisory" in text


def test_shared_reference_keeps_the_core_rules() -> None:
    text = SHARED_REF.read_text(encoding="utf-8")
    for marker in (
        "stacked hedges",
        "self-defence",
        "further research is needed",
        "never upgrade claims",
        "null or",
    ):
        assert marker in text, marker
