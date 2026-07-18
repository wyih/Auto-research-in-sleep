#!/usr/bin/env python3
"""Externally accept one already-frozen Grok P3 blind candidate.

This runner is deliberately separate from candidate generation.  It re-hashes
the frozen bundle, invokes the root candidate verifier and the real bundle
tests, checks immutability again, and only then emits an external-acceptance
receipt plus a Grok runtime wrapper.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree as ET


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact(path: Path, repo_root: Path) -> dict[str, object]:
    resolved = path.resolve(strict=True)
    return {
        "path": resolved.relative_to(repo_root).as_posix(),
        "sha256": _sha256(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return payload


def _load_verifier(repo_root: Path) -> Any:
    path = repo_root / "scripts" / "verify_business_e2e.py"
    spec = importlib.util.spec_from_file_location("verify_business_e2e_external", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load verifier: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as destination:
        json.dump(payload, destination, ensure_ascii=False, indent=2, sort_keys=True)
        destination.write("\n")


def _junit_counts(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("unexpected JUnit root")

    def integer(name: str) -> int:
        raw = root.attrib.get(name)
        if raw is not None:
            return int(raw)
        return sum(int(suite.attrib.get(name, "0")) for suite in root.findall("testsuite"))

    return {
        "tests": integer("tests"),
        "failures": integer("failures"),
        "errors": integer("errors"),
        "skipped": integer("skipped"),
        "xfailed": 0,
    }


def _run_candidate_verifier(
    repo_root: Path,
    candidate: Path,
    report_path: Path,
) -> tuple[subprocess.CompletedProcess[str], Mapping[str, Any]]:
    command = [
        sys.executable,
        str(repo_root / "scripts" / "verify_business_e2e.py"),
        "--repo-root",
        str(repo_root),
        "--p3-candidate",
        str(candidate),
        "--json",
    ]
    result = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=300,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"candidate verifier did not emit JSON: {error}") from error
    if not isinstance(payload, dict):
        raise RuntimeError("candidate verifier JSON root is not an object")
    _write_new_json(report_path, payload)
    return result, payload


def _run_bundle_tests(
    repo_root: Path,
    candidate_root: Path,
    candidate_sha256: str,
    bundle_digest: str,
    evidence_root: Path,
    verifier: Any,
) -> tuple[Mapping[str, Any], Path]:
    junit_path = evidence_root / "bundle-tests.junit.xml"
    output_path = evidence_root / "bundle-tests.output.txt"
    if importlib.util.find_spec("pytest") is not None:
        pytest_prefix = [sys.executable, "-m", "pytest"]
    else:
        uv = shutil.which("uv")
        if uv is None:
            raise RuntimeError("pytest is unavailable and uv was not found")
        pytest_prefix = [
            uv,
            "run",
            "--offline",
            "--with",
            "pytest",
            "python",
            "-m",
            "pytest",
        ]
    command = [
        *pytest_prefix,
        "-q",
        "tests/test_business_literature_pipeline_e2e.py",
        f"--junitxml={junit_path}",
    ]
    environment = dict(os.environ)
    environment.update(
        {
            "ARIS_BUSINESS_LITERATURE_RUN_ROOT": str(candidate_root),
            "ARIS_P3_BLIND_CANDIDATE": "1",
        }
    )
    started_at = _now()
    result = subprocess.run(
        command,
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=900,
    )
    completed_at = _now()
    with output_path.open("x", encoding="utf-8") as destination:
        destination.write(result.stdout)
        if result.stderr:
            destination.write("\n[stderr]\n")
            destination.write(result.stderr)
    counts = _junit_counts(junit_path) if junit_path.is_file() else {
        "tests": 0,
        "failures": 0,
        "errors": 1,
        "skipped": 0,
        "xfailed": 0,
    }
    clean = (
        result.returncode == 0
        and counts["tests"] > 0
        and counts["failures"] == 0
        and counts["errors"] == 0
        and counts["skipped"] == 0
        and counts["xfailed"] == 0
    )
    report = {
        "schema_version": verifier.P3_BUNDLE_TEST_SCHEMA,
        "status": "PASS" if clean else "FAIL",
        "candidate_root": candidate_root.relative_to(repo_root).as_posix(),
        "candidate_sha256": candidate_sha256,
        "bundle_digest": bundle_digest,
        "test_file": "tests/test_business_literature_pipeline_e2e.py",
        "command": command,
        "environment": {
            "ARIS_BUSINESS_LITERATURE_RUN_ROOT": candidate_root.relative_to(repo_root).as_posix(),
            "ARIS_P3_BLIND_CANDIDATE": "1",
        },
        "started_at": started_at,
        "completed_at": completed_at,
        "returncode": result.returncode,
        "counts": counts,
        "junit_report": _artifact(junit_path, repo_root) if junit_path.is_file() else None,
        "command_output": _artifact(output_path, repo_root),
    }
    return report, output_path


def accept_candidate(repo_root: Path, candidate_path: Path) -> tuple[int, Path | None]:
    repo = repo_root.resolve(strict=True)
    candidate = candidate_path.resolve(strict=True)
    verifier = _load_verifier(repo)
    initial = verifier.verify_p3_candidate(repo, candidate)
    if initial.get("status") != "PASS":
        print(json.dumps(initial, ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)
        return 1, None

    relative = candidate.relative_to(repo)
    run_dir = repo.joinpath(*relative.parts[:3])
    candidate_data = _load_json(candidate)
    candidate_root = (repo / str(candidate_data["candidate_root"])).resolve(strict=True)
    tag = str(candidate_data["grok_run_tag"])
    evidence_root = run_dir / "receipts" / "p3-grok-external" / tag
    if evidence_root.exists():
        raise FileExistsError(f"external acceptance evidence already exists: {evidence_root}")
    evidence_root.mkdir(parents=True)

    acceptance_started_at = _now()
    candidate_sha_before = _sha256(candidate)
    digest_before = str(initial["bundle_digest"])
    verifier_report_path = evidence_root / "candidate-verifier.json"
    verifier_result, verifier_report = _run_candidate_verifier(
        repo, candidate, verifier_report_path
    )
    bundle_report, _ = _run_bundle_tests(
        repo,
        candidate_root,
        candidate_sha_before,
        digest_before,
        evidence_root,
        verifier,
    )
    bundle_report_path = evidence_root / "bundle-tests.json"
    _write_new_json(bundle_report_path, bundle_report)

    final = verifier.verify_p3_candidate(repo, candidate)
    candidate_sha_after = _sha256(candidate)
    digest_after = str(final.get("bundle_digest") or "")
    verifier_pass = verifier_result.returncode == 0 and verifier_report.get("status") == "PASS"
    tests_pass = bundle_report.get("status") == "PASS"
    immutable = (
        final.get("status") == "PASS"
        and candidate_sha_before == candidate_sha_after
        and digest_before == digest_after
    )
    passed = verifier_pass and tests_pass and immutable
    acceptance_completed_at = _now()
    candidate_record = _artifact(candidate, repo)
    generation_record = dict(candidate_data["generation_record"])
    external_payload = {
        "schema_version": verifier.P3_EXTERNAL_ACCEPTANCE_SCHEMA,
        "runtime": "grok",
        "stage": "P3",
        "status": "pass" if passed else "fail",
        "grok_run_tag": tag,
        "acceptance_started_at": acceptance_started_at,
        "acceptance_completed_at": acceptance_completed_at,
        "candidate_receipt": candidate_record,
        "generation_record": generation_record,
        "candidate_verifier_report": _artifact(verifier_report_path, repo),
        "bundle_test_report": _artifact(bundle_report_path, repo),
        "candidate_sha256_before": candidate_sha_before,
        "candidate_sha256_after": candidate_sha_after,
        "bundle_digest_before": digest_before,
        "bundle_digest_after": digest_after,
        "candidate_hash_unchanged": candidate_sha_before == candidate_sha_after,
        "bundle_digest_unchanged": digest_before == digest_after,
        "repository_tests_run_externally": True,
        "general_verifier_run_externally": True,
        "candidate_remained_immutable": immutable,
    }
    external_path = evidence_root / "external-acceptance.json"
    _write_new_json(external_path, external_payload)
    if not passed:
        print(f"P3 candidate external acceptance failed: {external_path}", file=sys.stderr)
        return 1, None

    wrapper_created_at = _now()
    wrapper_payload = {
        "schema_version": verifier.RUNTIME_INVOCATION_SCHEMA,
        "runtime": "grok",
        "stage": "P3",
        "status": "passed",
        "skill": ["method-harvest", "business-lit-review"],
        "wrapper_created_at": wrapper_created_at,
        "completed_at": wrapper_created_at,
        "candidate_receipt": candidate_record,
        "generation_record": generation_record,
        "external_acceptance_receipt": _artifact(external_path, repo),
        "candidate_verifier_report": _artifact(verifier_report_path, repo),
        "bundle_test_report": _artifact(bundle_report_path, repo),
        "evidence": [
            candidate_record,
            generation_record,
            _artifact(external_path, repo),
            _artifact(verifier_report_path, repo),
            _artifact(bundle_report_path, repo),
        ],
    }
    wrapper_path = run_dir / "receipts" / f"p3-grok-runtime-invocation-{tag}.json"
    _write_new_json(wrapper_path, wrapper_payload)
    return 0, wrapper_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root",
    )
    parser.add_argument("--candidate", type=Path, required=True, help="frozen candidate receipt")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        status, wrapper = accept_candidate(args.repo_root, args.candidate)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"accept_p3_grok_candidate: {error}", file=sys.stderr)
        return 2
    if wrapper is not None:
        print(wrapper)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
