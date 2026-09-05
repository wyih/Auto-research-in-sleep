#!/usr/bin/env python3
"""Synchronize canonical business skills into the Codex package.

Shared authoring sources remain ``skills/<name>``. Codex-only files in
``overrides/codex-business`` are applied after copying those sources. The ARIS
installer consumes ``skills/skills-codex`` and installs that package into the
``.agents/skills`` discovery surface used by Codex.  The selected model inside
Codex does not create another package variant. Edit shared sources or overrides,
not generated package files. Kimi continues to consume the shared sources only.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
PACKAGE_ROOT = SKILLS_ROOT / "skills-codex"
OVERRIDES_ROOT = REPO_ROOT / "overrides" / "codex-business"

PORTABLE_SKILLS = (
    "browser-session-bridge",
    "business-author-style-profile",
    "business-claim-source-audit",
    "business-idea-creator",
    "business-lit-review",
    "business-number-audit",
    "business-novelty-check",
    "business-paper-plan",
    "business-paper-writing",
    "business-rebuttal",
    "business-research-pipeline",
    "business-research-suite",
    "business-run-passport",
    "business-prereview",
    "cn-data-bridge",
    "data-analysis-bridge",
    "empirical-design-plan",
    "evidence-to-claim",
    "fulltext-acquire",
    "method-harvest",
    "r-analysis-bridge",
    "results-to-docx",
    "stata-analysis-bridge",
    "wrds-query-bridge",
    "wrds-sas-cloud",
)

PORTABLE_REFERENCES = (
    "business-claim-source-audit.md",
    "business-confident-prose.md",
    "business-feasibility-gates.md",
    "business-handoff-schemas.md",
    "business-helper-resolution.md",
    "business-mode-registry.md",
    "business-method-routing.md",
    "business-repro-lock.md",
    "business-run-passport.md",
    "business-style-calibration.md",
    "business-wrds-policy.md",
)

IGNORED_NAMES = {".DS_Store", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def included_files(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if any(part in IGNORED_NAMES for part in path.relative_to(root).parts):
            continue
        if path.suffix in IGNORED_SUFFIXES or not path.is_file():
            continue
        files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def compare_tree(source: Path, target: Path, overrides: Path | None = None) -> list[str]:
    if not source.is_dir():
        return [f"missing canonical directory: {source.relative_to(REPO_ROOT)}"]
    if not target.is_dir():
        return [f"missing packaged directory: {target.relative_to(REPO_ROOT)}"]

    source_files = included_files(source)
    if overrides is not None:
        source_files.update(included_files(overrides))
    target_files = included_files(target)
    problems: list[str] = []
    for rel in sorted(source_files.keys() - target_files.keys()):
        problems.append(f"missing packaged file: {target.relative_to(REPO_ROOT)}/{rel}")
    for rel in sorted(target_files.keys() - source_files.keys()):
        problems.append(f"unexpected packaged file: {target.relative_to(REPO_ROOT)}/{rel}")
    for rel in sorted(source_files.keys() & target_files.keys()):
        if source_files[rel] != target_files[rel]:
            problems.append(f"content drift: {target.relative_to(REPO_ROOT)}/{rel}")
    return problems


def reference_source(name: str) -> Path:
    override = OVERRIDES_ROOT / "shared-references" / name
    return override if override.is_file() else SKILLS_ROOT / "shared-references" / name


def check() -> list[str]:
    problems: list[str] = []
    for name in PORTABLE_SKILLS:
        problems.extend(compare_tree(SKILLS_ROOT / name, PACKAGE_ROOT / name, OVERRIDES_ROOT / name))

    packaged_refs = PACKAGE_ROOT / "shared-references"
    for name in PORTABLE_REFERENCES:
        source = reference_source(name)
        target = packaged_refs / name
        if not source.is_file():
            problems.append(f"missing canonical reference: {source.relative_to(REPO_ROOT)}")
        elif not target.is_file():
            problems.append(f"missing packaged reference: {target.relative_to(REPO_ROOT)}")
        elif source.read_bytes() != target.read_bytes():
            problems.append(f"content drift: {target.relative_to(REPO_ROOT)}")
    return problems


def sync() -> None:
    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc", "*.pyo")
    for name in PORTABLE_SKILLS:
        source = SKILLS_ROOT / name
        target = PACKAGE_ROOT / name
        if not (source / "SKILL.md").is_file():
            raise FileNotFoundError(f"canonical skill missing SKILL.md: {source}")
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target, copy_function=shutil.copy2, ignore=ignore)
        override = OVERRIDES_ROOT / name
        if override.is_dir():
            shutil.copytree(override, target, dirs_exist_ok=True, ignore=ignore)

    packaged_refs = PACKAGE_ROOT / "shared-references"
    packaged_refs.mkdir(parents=True, exist_ok=True)
    for name in PORTABLE_REFERENCES:
        source = reference_source(name)
        if not source.is_file():
            raise FileNotFoundError(f"canonical shared reference missing: {source}")
        shutil.copy2(source, packaged_refs / name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift without writing",
    )
    args = parser.parse_args()

    if not args.check:
        sync()

    problems = check()
    if problems:
        print("Portable business mirror drift detected:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1

    action = "verified" if args.check else "synchronized"
    print(
        f"Portable business mirror {action}: "
        f"{len(PORTABLE_SKILLS)} skills, {len(PORTABLE_REFERENCES)} references"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
