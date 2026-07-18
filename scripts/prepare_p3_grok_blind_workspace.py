#!/usr/bin/env python3
"""Prepare a strict-sandbox input workspace for blind Grok P3 generation.

The resulting directory contains only the two skill snapshots, three immutable
PDF inputs, a minimal manifest, the local download verifier, and the prompt.
It does not launch Grok.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence


CORPUS: Mapping[str, tuple[str, str, int]] = {
    "graham_harvey_popadak_rajgopal_2017": (
        "artifacts/fulltext/open/corporate-culture-field-w23255.pdf",
        "f69be9aa4373ff67db8a98b9bcb27ff3576067ae82a1337a88e1aaed998847a2",
        79,
    ),
    "zhao_teng_wu_2018": (
        "artifacts/fulltext/sciencedirect/S1755309118300030-corporate-culture-firm-performance-china.pdf",
        "459e22da3a37ad6bd4823271ddfc4d6c8d027e054a43057b89c6cd0090d9770b",
        19,
    ),
    "duan_2018": (
        "artifacts/fulltext/cnki/duan-2018-quality-culture-performance.pdf",
        "79b6a8b9f2c6f075343f1322c38ff4c6c79abedba8ed963cee5f8a6094a28117",
        67,
    ),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pdf_pages(path: Path) -> int:
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo is None:
        raise RuntimeError("pdfinfo is required for blind workspace preparation")
    result = subprocess.run(
        [pdfinfo, str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=60,
    )
    match = re.search(r"^Pages:\s*(\d+)\s*$", result.stdout, flags=re.MULTILINE)
    if result.returncode != 0 or match is None:
        raise RuntimeError(f"pdfinfo failed for {path}")
    return int(match.group(1))


def _artifact(path: Path, repo_root: Path) -> dict[str, object]:
    resolved = path.resolve(strict=True)
    return {
        "path": resolved.relative_to(repo_root).as_posix(),
        "sha256": _sha256(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def _copy_verified_pdf(source: Path, destination: Path, digest: str, pages: int) -> None:
    if _sha256(source) != digest or _pdf_pages(source) != pages:
        raise ValueError(f"source PDF identity failed: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing)
    if _sha256(destination) != digest or _pdf_pages(destination) != pages:
        raise RuntimeError(f"snapshot PDF identity failed: {destination}")


def _minimal_manifest(
    source_manifest: Path,
    source_to_snapshot: Mapping[str, str],
) -> str:
    lines = source_manifest.read_text(encoding="utf-8").splitlines()
    table_indices = [index for index, line in enumerate(lines) if line.strip().startswith("|")]
    if len(table_indices) < 2:
        raise ValueError("canonical manifest table is absent")
    header_index, separator_index = table_indices[:2]
    selected: list[str] = []
    for line in lines[separator_index + 1 :]:
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip()[1:-1].split("|")]
        if len(cells) != 21:
            raise ValueError("canonical manifest has a non-21-column row")
        source_path = cells[11].strip("`").strip()
        snapshot_path = source_to_snapshot.get(source_path)
        if snapshot_path is None:
            continue
        cells[8] = "isolated_snapshot"
        cells[9] = "grok"
        cells[10] = "strict_sandbox_snapshot"
        cells[11] = f"`{snapshot_path}`"
        cells[16] = "`inputs/isolation-preparation.json`"
        cells[17] = "not_applicable"
        cells[20] = cells[20] + " Isolated byte-identical blind-generation snapshot."
        selected.append("| " + " | ".join(cells) + " |")
    if len(selected) != len(source_to_snapshot):
        raise ValueError("canonical manifest does not contain each fixed verified source exactly once")
    if any("| verified |" not in line for line in selected):
        raise ValueError("one or more fixed manifest rows are not verified")
    return "\n".join(lines[: separator_index + 1] + selected) + "\n"


def prepare(repo_root: Path, run_dir: Path, tag: str) -> Path:
    repo = repo_root.resolve(strict=True)
    run = run_dir.resolve(strict=True)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", tag):
        raise ValueError("tag must be a safe directory name")
    try:
        relative_run = run.relative_to(repo)
    except ValueError as error:
        raise ValueError("run directory must be inside the repository") from error
    if relative_run.parts[:2] != (".aris", "business-e2e") or len(relative_run.parts) != 3:
        raise ValueError("run directory must be .aris/business-e2e/<run-id>")
    root = run / "grok-workspace" / "p3-synthesis-v2" / tag
    root.mkdir(parents=True, exist_ok=False)

    source_manifest = run / "manifests" / "FULLTEXT_MANIFEST.md"
    source_to_snapshot = {
        str(run.relative_to(repo) / values[0]): str(root.relative_to(repo) / values[0])
        for values in CORPUS.values()
    }
    manifest_path = root / "inputs" / "FULLTEXT_MANIFEST_MINIMAL.md"
    manifest_path.parent.mkdir()
    manifest_path.write_text(
        _minimal_manifest(source_manifest, source_to_snapshot),
        encoding="utf-8",
    )

    pdf_lineage = []
    for paper_id, (relative_source, digest, pages) in CORPUS.items():
        source = run / relative_source
        destination = root / relative_source
        _copy_verified_pdf(source, destination, digest, pages)
        pdf_lineage.append(
            {
                "paper_id": paper_id,
                "source": _artifact(source, repo),
                "snapshot": _artifact(destination, repo),
                "pages": pages,
                "byte_identical": True,
            }
        )

    for skill_name in ("method-harvest", "business-lit-review"):
        shutil.copytree(
            repo / "skills" / skill_name,
            root / "skills" / skill_name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
    verifier_source = repo / "skills" / "browser-session-bridge" / "scripts" / "verify_download.py"
    verifier_destination = root / "tools" / "verify_download.py"
    verifier_destination.parent.mkdir()
    shutil.copy2(verifier_source, verifier_destination)
    prompt_source = (
        run / "grok-workspace" / "prompts" / "p3-synthesis-runtime.md"
    )
    prompt_path = root / "PROMPT.md"
    prompt_path.write_text(
        prompt_source.read_text(encoding="utf-8")
        .replace("<p3_root>", ".")
        .replace("<repo_candidate_root>", root.relative_to(repo).as_posix())
        .replace("<outer_repo_root>", str(repo)),
        encoding="utf-8",
    )

    skill_inventory = [
        _artifact(path, repo)
        for path in sorted((root / "skills").rglob("*"))
        if path.is_file()
    ]
    launch_command = [
        "env",
        "PYTHONDONTWRITEBYTECODE=1",
        "grok",
        "--sandbox",
        "strict",
        "--permission-mode",
        "bypassPermissions",
        "--cwd",
        str(root),
        "--disable-web-search",
        "--disallowed-tools",
        "web_search,web_fetch,search_tool,use_tool,Agent",
        "--no-memory",
        "--no-subagents",
        "--prompt-file",
        str(prompt_path),
    ]
    receipt = {
        "schema_version": "aris.business-e2e.p3-isolation-preparation.v1",
        "runtime": "grok",
        "stage": "P3",
        "grok_run_tag": tag,
        "candidate_root": root.relative_to(repo).as_posix(),
        "prepared_at": _now(),
        "sandbox_profile": "strict",
        "network_tools_disabled": True,
        "mcp_meta_tools_disabled": True,
        "memory_disabled": True,
        "subagents_disabled": True,
        "repository_tests_copied": False,
        "root_verifier_copied": False,
        "prior_synthesis_outputs_copied": False,
        "minimal_manifest": _artifact(manifest_path, repo),
        "prompt": _artifact(prompt_path, repo),
        "local_pdf_verifier": _artifact(verifier_destination, repo),
        "pdf_lineage": pdf_lineage,
        "skill_snapshot": skill_inventory,
        "launch_command": launch_command,
    }
    receipt_path = root / "inputs" / "isolation-preparation.json"
    with receipt_path.open("x", encoding="utf-8") as destination:
        json.dump(receipt, destination, ensure_ascii=False, indent=2, sort_keys=True)
        destination.write("\n")
    return root


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = prepare(args.repo_root, args.run_dir, args.tag)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"prepare_p3_grok_blind_workspace: {error}", file=sys.stderr)
        return 2
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
