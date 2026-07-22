#!/usr/bin/env python3
"""Build an auditable standalone academic results DOCX from a JSON spec."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from author_identity import OFFICE_AUTHOR_ENV, OfficeAuthorError, resolve_office_author
from results_docx import BuildRequest, ResultsDocxError, build_results_pack


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path, help="JSON build specification")
    parser.add_argument("--out", required=True, type=Path, help="Output .docx under a results_docx directory")
    parser.add_argument("--manifest", type=Path, help="Markdown manifest path (default: beside DOCX)")
    parser.add_argument("--receipt", type=Path, help="JSON audit receipt path (default: beside DOCX)")
    parser.add_argument(
        "--author",
        help=(
            "Office author identity (otherwise read "
            f"{OFFICE_AUTHOR_ENV} or the installer-created user configuration)"
        ),
    )
    parser.add_argument("--force", action="store_true", help="Replace existing output/manifest/receipt")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        author = resolve_office_author(args.author)
        result = build_results_pack(
            BuildRequest(
                spec_path=args.spec,
                output_path=args.out,
                manifest_path=args.manifest,
                receipt_path=args.receipt,
                author=author,
                force=args.force,
            )
        )
    except (OfficeAuthorError, ResultsDocxError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "docx": str(result.output_path),
                "sha256": result.output_sha256,
                "bytes": result.output_bytes,
                "manifest": str(result.manifest_path),
                "receipt": str(result.receipt_path),
                "tables": result.table_count,
                "figures": result.figure_count,
                "narrative_claims": result.narrative_claim_count,
                "narrative_mode": result.narrative_mode,
                "metadata_passed": result.metadata_audit["passed"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
