from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any

from tests.test_accept_grok_browser_candidate import _pdf_bytes


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


acceptor = _load(
    "accept_grok_browser_candidate_promotion_tests",
    REPO_ROOT / "scripts" / "accept_grok_browser_candidate.py",
)
promoter = _load(
    "promote_grok_browser_candidate_tests",
    REPO_ROOT / "scripts" / "promote_grok_browser_candidate.py",
)
verifier = _load(
    "verify_business_e2e_promotion_tests",
    REPO_ROOT / "scripts" / "verify_business_e2e.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _manifest(header: tuple[str, ...], *, p4: bool) -> str:
    lines = [
        "# DATA_MANIFEST" if p4 else "# FULLTEXT_MANIFEST",
        "",
        "## Extracts" if p4 else "",
        "",
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    if p4:
        lines.extend(["", "## Definition Decisions", "", "No decisions. "])
    return "\n".join(lines) + "\n"


class PromotionFixture:
    def __init__(self, folder: str, stage: str) -> None:
        self.repo = Path(folder) / "repo"
        self.run = self.repo / ".aris" / "business-e2e" / "20260718T000000Z"
        self.stage = stage
        self.site = "sciencedirect" if stage == "P3" else "csmar"
        self.spec = self.run / "grok-workspace" / "acceptance-specs" / f"{stage.lower()}-{self.site}.json"
        self.candidate = self.run / "grok-workspace" / "receipts" / f"{stage.lower()}-{self.site}-grok-candidate.json"
        self.acceptance = self.run / "grok-workspace" / "receipts" / f"{stage.lower()}-{self.site}-external-acceptance.json"
        if stage == "P3":
            self.artifact = (
                self.run
                / "grok-workspace"
                / "artifacts"
                / "fulltext"
                / self.site
                / "accepted-paper.pdf"
            )
            self.output = self.run / "receipts" / "p3-sciencedirect-grok-devtools.json"
            self.manifest = self.run / "manifests" / "FULLTEXT_MANIFEST.md"
        else:
            self.artifact = (
                self.run
                / "cn-data"
                / "raw"
                / self.site
                / "2026-07-18_grok_v1"
                / "csmar-fs-combas-000001-2020.zip"
            )
            self.output = self.run / "cn-data" / "receipts" / "p4-csmar-grok-devtools.json"
            self.manifest = self.run / "cn-data" / "DATA_MANIFEST.md"

    def build(self) -> None:
        self.artifact.parent.mkdir(parents=True)
        self.output.parent.mkdir(parents=True)
        self.candidate.parent.mkdir(parents=True, exist_ok=True)
        verifier_source = (
            REPO_ROOT / "skills" / "browser-session-bridge" / "scripts" / "verify_download.py"
        )
        verifier_copy = (
            self.repo / "skills" / "browser-session-bridge" / "scripts" / "verify_download.py"
        )
        verifier_copy.parent.mkdir(parents=True)
        shutil.copyfile(verifier_source, verifier_copy)
        if self.stage == "P3":
            self.artifact.write_bytes(
                _pdf_bytes(
                    [
                        "Capital Structure Evidence",
                        "Ada Lovelace and Grace Hopper",
                        "DOI: 10.1234/example.2026.7",
                        "PII S0123456789012345",
                    ]
                )
            )
            spec_payload: dict[str, Any] = {
                "schema_version": acceptor.SPEC_SCHEMA,
                "stage": "P3",
                "site": self.site,
                "artifact": {
                    "path": self.artifact.relative_to(self.repo).as_posix(),
                    "format": "pdf",
                    "min_bytes": 1,
                },
                "p3": {
                    "expected_title": "Capital Structure Evidence",
                    "expected_authors": ["Ada Lovelace", "Grace Hopper"],
                    "expected_doi": "10.1234/example.2026.7",
                    "expected_pii": "S0123456789012345",
                },
            }
            self.manifest.parent.mkdir(parents=True, exist_ok=True)
            self.manifest.write_text(
                _manifest(promoter.P3_MANIFEST_HEADER, p4=False), encoding="utf-8"
            )
        else:
            csv_bytes = (
                '"Stkcd","ShortName","Accper","Typrep","A001000000"\r\n'
                '"000001","平安银行","2020-12-31","A","4468514000000.00"\r\n'
            ).encode("utf-8")
            with zipfile.ZipFile(self.artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("FS_Combas.csv", csv_bytes)
            spec_payload = {
                "schema_version": acceptor.SPEC_SCHEMA,
                "stage": "P4",
                "site": self.site,
                "artifact": {
                    "path": self.artifact.relative_to(self.repo).as_posix(),
                    "format": "zip",
                    "min_bytes": 1,
                },
                "p4": {
                    "expected_headers": [
                        "Stkcd",
                        "ShortName",
                        "Accper",
                        "Typrep",
                        "A001000000",
                    ],
                    "exact_rows": [
                        {
                            "Stkcd": "000001",
                            "ShortName": "平安银行",
                            "Accper": "2020-12-31",
                            "Typrep": "A",
                            "A001000000": "4468514000000.00",
                        }
                    ],
                    "min_rows": 1,
                    "archive_member": "FS_Combas.csv",
                    "member_format": "csv",
                },
            }
            self.manifest.parent.mkdir(parents=True, exist_ok=True)
            self.manifest.write_text(
                _manifest(promoter.P4_MANIFEST_HEADER, p4=True), encoding="utf-8"
            )
        _write_json(self.spec, spec_payload)
        status = self.artifact.stat()
        _write_json(
            self.candidate,
            {
                "schema_version": acceptor.CANDIDATE_SCHEMA,
                **acceptor.EXACT_BINDINGS,
                "stage": self.stage,
                "site": self.site,
                "acceptance_spec_sha256": _sha256(self.spec),
                "artifact": {
                    "path": self.artifact.relative_to(self.repo).as_posix(),
                    "format": "pdf" if self.stage == "P3" else "zip",
                    "size_bytes": status.st_size,
                    "mtime_ns": str(status.st_mtime_ns),
                    "sha256": _sha256(self.artifact),
                },
            },
        )
        acceptor.accept_candidate(
            workspace=self.repo,
            run_root=self.run,
            candidate=self.candidate,
            spec=self.spec,
            output=self.acceptance,
        )

    def promote(self) -> dict[str, Any]:
        return promoter.promote_candidate(
            workspace=self.repo,
            run_root=self.run,
            candidate=self.candidate,
            spec=self.spec,
            acceptance=self.acceptance,
            output=self.output,
        )

    def root_gate(self) -> verifier.Gate:
        return verifier._browser_gate(
            verifier.Context(repo_root=self.repo.resolve(), run_dir=self.run.resolve()),
            self.stage,
            self.site,
            "grok",
        )


class GrokBrowserCandidatePromotionTests(unittest.TestCase):
    def test_cli_promotes_with_six_explicit_paths(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = PromotionFixture(folder, "P4")
            fixture.build()
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "promote_grok_browser_candidate.py"),
                    "--candidate",
                    str(fixture.candidate),
                    "--spec",
                    str(fixture.spec),
                    "--acceptance",
                    str(fixture.acceptance),
                    "--output",
                    str(fixture.output),
                    "--workspace",
                    str(fixture.repo),
                    "--run-root",
                    str(fixture.run),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertTrue(summary["ok"])
            self.assertEqual(summary["schema_version"], promoter.RECEIPT_SCHEMA)
            self.assertTrue(fixture.output.is_file())

    def test_promotes_p4_zip_to_independent_receipt_csv_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = PromotionFixture(folder, "P4")
            fixture.build()

            payload = fixture.promote()

            self.assertEqual(payload["schema_version"], promoter.RECEIPT_SCHEMA)
            self.assertEqual(payload["status"], "passed")
            self.assertNotIn("portal_evidence", payload)
            self.assertNotIn("query", payload)
            self.assertFalse(payload["promotion"]["portal_observations_synthesized"])
            table = next(item for item in payload["artifacts"] if item["role"] == "accepted_table")
            table_path = fixture.repo / table["path"]
            self.assertTrue(table_path.is_file())
            self.assertEqual(_sha256(table_path), table["sha256"])
            manifest = fixture.manifest.read_text(encoding="utf-8")
            self.assertIn("## Definition Decisions\n\nNo decisions.", manifest)
            self.assertIn("| " + " | ".join(promoter.P4_MANIFEST_HEADER) + " |", manifest)
            self.assertLess(manifest.index(table["path"]), manifest.index("## Definition Decisions"))
            self.assertEqual(fixture.root_gate().status, "PASS")

    @unittest.skipUnless(shutil.which("pdfinfo") and shutil.which("pdftotext"), "Poppler required")
    def test_promotes_p3_pdf_and_root_rechecks_identity_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = PromotionFixture(folder, "P3")
            fixture.build()

            payload = fixture.promote()

            self.assertEqual(payload["artifact"]["pages"], 1)
            self.assertIn(payload["artifact"]["path"], fixture.manifest.read_text(encoding="utf-8"))
            self.assertEqual(fixture.root_gate().status, "PASS")

    def test_rejects_tampered_acceptance_without_touching_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = PromotionFixture(folder, "P4")
            fixture.build()
            original_manifest = fixture.manifest.read_bytes()
            acceptance = json.loads(fixture.acceptance.read_text(encoding="utf-8"))
            acceptance["verifier_report"]["stage_content"]["row_count"] = 999
            _write_json(fixture.acceptance, acceptance)

            with self.assertRaisesRegex(promoter.PromotionError, "verifier_report"):
                fixture.promote()

            self.assertEqual(fixture.manifest.read_bytes(), original_manifest)
            self.assertFalse(fixture.output.exists())
            self.assertFalse((fixture.artifact.parent / "extracted" / "FS_Combas.csv").exists())

    def test_root_rejects_receipt_or_extracted_table_tampering(self) -> None:
        for target in ("receipt", "table"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as folder:
                fixture = PromotionFixture(folder, "P4")
                fixture.build()
                payload = fixture.promote()
                if target == "receipt":
                    stored = json.loads(fixture.output.read_text(encoding="utf-8"))
                    stored["portal_evidence"] = {"preview_rows": 1}
                    _write_json(fixture.output, stored)
                else:
                    table = next(
                        item for item in payload["artifacts"] if item["role"] == "accepted_table"
                    )
                    (fixture.repo / table["path"]).write_text("tampered\n", encoding="utf-8")

                gate = fixture.root_gate()
                self.assertEqual(gate.status, "FAIL")

    def test_rejects_non_runtime_owned_artifact_even_after_external_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = PromotionFixture(folder, "P4")
            fixture.artifact = fixture.run / "cn-data" / "raw" / "csmar" / "codex-copy.zip"
            fixture.build()

            with self.assertRaisesRegex(promoter.PromotionError, "version directory"):
                fixture.promote()


if __name__ == "__main__":
    unittest.main()
