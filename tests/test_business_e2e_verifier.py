from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER = REPO_ROOT / "scripts" / "verify_business_e2e.py"
SPEC = importlib.util.spec_from_file_location("verify_business_e2e", VERIFIER)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EvidenceFixture:
    def __init__(self, root: Path, run_id: str = "20260718T000000Z") -> None:
        self.repo = root
        self.evidence_root = root / ".aris" / "business-e2e"
        self.run = self.evidence_root / run_id
        (self.run / "cn-data" / "receipts").mkdir(parents=True)
        self.manifest_rows: list[str] = []

    def add_codex_portal(self, site: str, *, recorded_rows: int | None = None) -> Path:
        raw = self.run / "cn-data" / "raw" / site / "2026-07-18"
        extracted = raw / "extracted"
        extracted.mkdir(parents=True, exist_ok=True)
        if site == "cnrds":
            artifact = extracted / "上市公司专利申请情况.csv"
            archive = raw / "cnrds-cird-000001-2020.zip"
            csv_text = (
                "Scode,Year,Ftyp,Aplctm,Invia,Umia,Desia,Invja,Umja,Desja\r\n"
                "股票代码,会计年度,公司类型,申请时间,当年独立申请的发明数量,当年独立申请的实用新型数量,当年独立申请的外观设计数量,当年联合申请的发明数量,当年联合申请的实用新型数量,当年联合申请的外观设计数量\r\n"
                "000001,2020,集团公司合计,上市后,272,1,39,0,0,0\r\n"
                "000001,2020,上市公司本身,上市后,272,1,39,0,0,0\r\n"
            )
            query = {
                "module": "创新专利研究 (CIRD)",
                "table": "上市公司专利申请情况",
                "security_code": "000001",
                "date_start": "2020-01-01",
                "date_end": "2020-12-31",
                "format": "csv",
                "selected_field_count": 10,
            }
            portal = {
                "preview_rows": 2,
                "preview_codes": ["000001"],
                "preview_years": [2020],
                "company_types": ["上市公司本身", "集团公司合计"],
                "queue_status": "压缩完成",
            }
            transport = {"ui_export_completed": True, "temporary_url_persisted": False}
            actual_rows, columns = 2, 10
        else:
            artifact = extracted / "FS_Combas.csv"
            archive = raw / "FS_Combas.zip"
            csv_text = (
                '"Stkcd","ShortName","Accper","Typrep","A001000000"\r\n'
                '"000001","平安银行","2020-12-31","A","4468514000000.00"\r\n'
            )
            query = {
                "module": "财务报表",
                "table": "资产负债表",
                "table_id": "FS_Combas",
                "security_code": "000001",
                "date_start": "2020-12-31",
                "date_end": "2020-12-31",
                "condition": "Typrep=A",
                "output_selection": "csv",
                "selected_fields": ["Stkcd", "ShortName", "Accper", "Typrep", "A001000000"],
            }
            portal = {
                "preview_rows": 1,
                "preview_code": "000001",
                "preview_date": "2020-12-31",
                "preview_report_type": "A",
                "preview_total_assets_nonempty": True,
                "export_summary_rows": 1,
                "export_summary_format": "CSV格式（*.csv）",
            }
            transport = {
                "ui_export_completed": True,
                "ui_local_save_clicked": True,
                "browser_download_event_observed": True,
                "temporary_url_persisted": False,
            }
            actual_rows, columns = 1, 5
        artifact.write_bytes(b"\xef\xbb\xbf" + csv_text.encode("utf-8"))
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr(artifact.name, artifact.read_bytes())
            bundle.writestr("README.txt", "vendor metadata")
        relative = artifact.relative_to(self.repo)
        archive_relative = archive.relative_to(self.repo)
        recorded_rows = actual_rows if recorded_rows is None else recorded_rows
        receipt = {
            "receipt_version": "1.0",
            "acceptance_id": f"p4-{site}-codex",
            "source": site,
            "adapter": "codex_native_chrome",
            "mcp_server": "native",
            "implementation": "codex_chrome",
            "profile_mode": "user_chrome",
            "started_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "status": "passed",
            "query": query,
            "portal_evidence": portal,
            "download_transport": transport,
            "artifacts": [
                {
                    "path": str(archive_relative),
                    "detected_format": "zip",
                    "size_bytes": archive.stat().st_size,
                    "sha256": sha256(archive),
                    "verified": True,
                },
                {
                    "path": str(relative),
                    "detected_format": "csv",
                    "encoding": "utf-8-bom",
                    "size_bytes": artifact.stat().st_size,
                    "sha256": sha256(artifact),
                    "data_rows": recorded_rows,
                    "columns": columns,
                    "code_filter_mismatches": 0,
                    "verified": True,
                }
            ],
            "secrets_or_session_material_persisted": False,
        }
        receipt_path = self.run / "cn-data" / "receipts" / f"p4-{site}-codex.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        self.manifest_rows.append(f"| {relative} | {sha256(artifact)} | codex_native_chrome |")
        self.flush_manifest()
        return artifact

    def flush_manifest(self) -> None:
        manifest = self.run / "cn-data" / "DATA_MANIFEST.md"
        manifest.write_text("# DATA_MANIFEST\n\n" + "\n".join(self.manifest_rows) + "\n", encoding="utf-8")


class BusinessE2EVerifierTests(unittest.TestCase):
    def make_p3_v2_receipt(self, repo: Path) -> tuple[verifier.Context, verifier.Receipt, Path, dict]:
        run = repo / ".aris" / "business-e2e" / "run"
        receipt_path = run / "receipts" / "p3-literature-synthesis.json"
        literature = run / "literature-v2"
        cards = literature / "cards"
        processing = literature / "pdf-processing"
        receipt_path.parent.mkdir(parents=True)
        cards.mkdir(parents=True)
        processing.mkdir(parents=True)

        pdf = run / "artifacts" / "fulltext" / "paper.pdf"
        pdf.parent.mkdir(parents=True)
        pdf.write_bytes(b"%PDF-1.7\nfixture\n%%EOF\n")
        relative_pdf = str(pdf.relative_to(repo))
        render_png = processing / "rendered" / "paper-p1.png"
        render_png.parent.mkdir()
        render_png.write_bytes(PNG_1X1)
        processing_path = processing / "paper_PDF_PROCESSING.json"
        artifact_identity = {
            "work_id": "paper",
            "artifact_id": "paper-fixture",
            "parent_artifact_id": "not_applicable",
            "artifact_role": "main_paper",
            "version_identity": "fixture PDF",
            "doi_or_source_id": "fixture:paper",
        }
        processing_payload = {
            "schema": verifier.P3_PDF_INSPECTION_SCHEMA,
            "ok": True,
            "ready_for_method_harvest": True,
            "source_pdf_preserved": True,
            "source_pdf": relative_pdf,
            "source_pdf_sha256": sha256(pdf),
            "size_bytes": pdf.stat().st_size,
            "page_count": 1,
            "identity": {"status": "pass"},
            "artifact_identity": artifact_identity,
            "text_layer": {"classification": "native_text"},
            "render_evidence": {
                "schema": verifier.P3_RENDER_EVIDENCE_SCHEMA,
                "page_number_basis": "1-based PDF viewer page",
                "count": 1,
                "pages": [
                    {
                        "source_pdf_sha256": sha256(pdf),
                        "viewer_page": 1,
                        "png_path": str(render_png.relative_to(repo)),
                        "png_sha256": sha256(render_png),
                        "png_bytes": render_png.stat().st_size,
                        "width_px": 1,
                        "height_px": 1,
                        "renderer_tool": "fixture-png-writer",
                        "renderer_version": "fixture-png-writer 1.0",
                    }
                ],
            },
        }
        processing_path.write_text(json.dumps(processing_payload), encoding="utf-8")
        relative_processing = str(processing_path.relative_to(repo))

        card_path = cards / "paper_METHOD_CARD.md"
        card_lines = ["# METHOD_CARD: paper"]
        card_lines.extend(verifier.P3_METHOD_CARD_TOKENS)
        field_values = {
            "fulltext_status": "open",
            "local_path": f"`{relative_pdf}`",
            "content_hash": f"`sha256:{sha256(pdf)}`",
            "size_bytes": str(pdf.stat().st_size),
            "pages": "1",
            "source_depth": "fulltext",
            "pdf_processing_receipt": f"`{relative_processing}`",
            "work_id": "paper",
            "artifact_id": "paper-fixture",
            "parent_artifact_id": "not_applicable",
            "artifact_role": "main_paper",
            "version_identity": "fixture PDF",
            "doi_or_source_id": "fixture:paper",
            "unit_of_observation": "firm",
            "response_n": "not_applicable",
            "unique_entity_n": "1",
            "estimand_unit": "firm",
            "cluster_unit": "none",
            "scale_provenance_status": "not_applicable",
            "numeric_audit_status": "pass",
            "safe_claim": "association only",
            "unsafe_claim": "causal effect",
        }
        card_lines.extend(f"- {name}: {field_values[name]}" for name in verifier.P3_METHOD_CARD_FIELDS)
        card_path.write_text("\n".join(card_lines) + "\n", encoding="utf-8")

        def artifact(path: Path) -> dict[str, object]:
            return {
                "path": str(path.relative_to(repo)),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }

        output_text = {
            "method_card_index": "\n".join(verifier.P3_OUTPUT_CONTRACTS["method_card_index"])
            + "\npaper paper_METHOD_CARD.md\n",
            "evidence_matrix": "\n".join(verifier.P3_OUTPUT_CONTRACTS["evidence_matrix"])
            + f"\npaper {sha256(pdf)} numeric_audit_status=pass\n",
            "literature_review": "\n".join(verifier.P3_OUTPUT_CONTRACTS["literature_review"])
            + "\npaper PDF p. 1\n",
            "acceptance_report": "\n".join(verifier.P3_OUTPUT_CONTRACTS["acceptance_report"])
            + f"\npaper {sha256(pdf)}\n| gate | status | evidence |\n| source | PASS | checked |\n",
            "pdf_visual_checks": "\n".join(verifier.P3_OUTPUT_CONTRACTS["pdf_visual_checks"])
            + "\npaper\n",
        }
        output_paths: dict[str, Path] = {}
        for role, text in output_text.items():
            path = processing / "PDF_VISUAL_CHECKS.md" if role == "pdf_visual_checks" else literature / f"{role}.md"
            path.write_text(text, encoding="utf-8")
            output_paths[role] = path

        manifest = run / "manifests" / "FULLTEXT_MANIFEST.md"
        manifest.parent.mkdir()
        manifest_row = {
            **artifact_identity,
            "title": "Fixture paper",
            "identity_evidence": "fixture",
            "channel": "fixture",
            "runtime": "codex",
            "adapter": "fixture",
            "local_path_or_gap": relative_pdf,
            "size_bytes": str(pdf.stat().st_size),
            "pages": "1",
            "sha256": sha256(pdf),
            "acquired_at": "2026-07-18T00:00:00Z",
            "provenance_receipt": "not_applicable",
            "browser_receipt": "not_applicable",
            "status": "verified",
            "blocker": "not_applicable",
            "notes": "fixture",
        }
        manifest.write_text(
            "# FULLTEXT_MANIFEST\n\n"
            + "| "
            + " | ".join(verifier.P3_FULLTEXT_MANIFEST_HEADER)
            + " |\n| "
            + " | ".join("---" for _ in verifier.P3_FULLTEXT_MANIFEST_HEADER)
            + " |\n| "
            + " | ".join(manifest_row[field] for field in verifier.P3_FULLTEXT_MANIFEST_HEADER)
            + " |\n",
            encoding="utf-8",
        )

        data = {
            "schema_version": verifier.P3_SYNTHESIS_SCHEMA,
            "status": "pass",
            "contract": {
                "name": "p3-fulltext-to-literature-review",
                "version": 2,
                "paper_count": 1,
                "required_nonempty_method_card_fields": list(verifier.P3_METHOD_CARD_FIELDS),
                "required_output_roles": list(verifier.P3_OUTPUT_CONTRACTS),
            },
            "inputs": [
                {
                    "paper_id": "paper",
                    "artifact_identity": artifact_identity,
                    "expected_render_pages": [1],
                    "pdf": {**artifact(pdf), "pages": 1, "detected_format": "pdf"},
                    "pdf_processing": artifact(processing_path),
                    "method_card": artifact(card_path),
                    "expected_fields": {
                        "source_depth": "fulltext",
                        "numeric_audit_status": "pass",
                    },
                }
            ],
            "outputs": {role: artifact(path) for role, path in output_paths.items()},
            "checks": {
                "identity_matched_fulltext_only": True,
                "artifact_identity_chain_joined": True,
                "all_paper_hashes_recorded": True,
                "pdf_processing_ready": True,
                "pdf_source_preserved": True,
                "exact_variable_construction_or_unknown": True,
                "main_null_and_mixed_results_preserved": True,
                "source_locations_present": True,
                "agreement_conflict_diagnosed": True,
                "claim_ceiling_preserved": True,
                "abstract_only_method_claims": False,
            },
        }
        receipt_path.write_text(json.dumps(data), encoding="utf-8")
        context = verifier.Context(repo_root=repo, run_dir=run)
        return context, verifier.Receipt(receipt_path, data), card_path, processing_payload

    def test_hash_corruption_and_row_mismatch_fail_existing_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = EvidenceFixture(Path(folder))
            cnrds = fixture.add_codex_portal("cnrds")
            fixture.add_codex_portal("csmar", recorded_rows=2)
            cnrds.write_text("security_code,value\n000001,changed\n", encoding="utf-8")

            report = verifier.verify_business_e2e(fixture.repo, fixture.evidence_root, fixture.run.name)
            browser = report.runtimes["codex"]["browser"]

        self.assertEqual(browser["P4_CNRDS"].status, "FAIL")
        self.assertIn("SHA-256 mismatch", browser["P4_CNRDS"].summary)
        self.assertEqual(browser["P4_CSMAR"].status, "FAIL")
        self.assertIn("rows 1 != 2", browser["P4_CSMAR"].summary)

    def test_p4_rejects_semantic_header_tamper_after_all_self_reported_hashes_are_refreshed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = EvidenceFixture(Path(folder))
            csv_path = fixture.add_codex_portal("csmar")
            receipt_path = fixture.run / "cn-data" / "receipts" / "p4-csmar-codex.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            archive_record, csv_record = receipt["artifacts"]
            archive_path = fixture.repo / archive_record["path"]
            old_hash = csv_record["sha256"]
            csv_path.write_bytes(csv_path.read_bytes().replace(b"A001000000", b"A001000001"))
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                bundle.writestr(csv_path.name, csv_path.read_bytes())
                bundle.writestr("README.txt", "vendor metadata")
            for record, path in ((archive_record, archive_path), (csv_record, csv_path)):
                record["sha256"] = sha256(path)
                record["size_bytes"] = path.stat().st_size
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            fixture.manifest_rows = [row.replace(old_hash, csv_record["sha256"]) for row in fixture.manifest_rows]
            fixture.flush_manifest()

            report = verifier.verify_business_e2e(fixture.repo, fixture.evidence_root, fixture.run.name)
            gate = report.runtimes["codex"]["browser"]["P4_CSMAR"]

        self.assertEqual(gate.status, "FAIL")
        self.assertIn("CSMAR exact header", gate.summary)

    def test_p4_rejects_stale_zip_and_missing_structured_portal_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = EvidenceFixture(Path(folder))
            fixture.add_codex_portal("cnrds")
            receipt_path = fixture.run / "cn-data" / "receipts" / "p4-cnrds-codex.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            archive_path = fixture.repo / receipt["artifacts"][0]["path"]
            stale = datetime.now(timezone.utc) - timedelta(days=2)
            os.utime(archive_path, (stale.timestamp(), stale.timestamp()))
            receipt["portal_evidence"].pop("queue_status")
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

            report = verifier.verify_business_e2e(fixture.repo, fixture.evidence_root, fixture.run.name)
            gate = report.runtimes["codex"]["browser"]["P4_CNRDS"]

        self.assertEqual(gate.status, "FAIL")
        self.assertIn("download freshness window", gate.summary)

    def test_recorded_pdf_pages_are_rechecked(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            run = repo / ".aris" / "business-e2e" / "run"
            receipt = run / "receipts" / "p3-cnki-codex.json"
            receipt.parent.mkdir(parents=True)
            artifact = run / "paper.pdf"
            artifact.write_bytes(b"%PDF-1.7\nfixture\n%%EOF\n")
            context = verifier.Context(repo_root=repo, run_dir=run)
            record = {
                "path": str(artifact.relative_to(repo)),
                "sha256": sha256(artifact),
                "size_bytes": artifact.stat().st_size,
                "pages": 2,
                "detected_format": "pdf",
            }
            with mock.patch.object(verifier, "_pdf_page_count", return_value=(3, None)):
                check = verifier._verify_artifact(record, receipt, context)

        self.assertEqual(check.status, "FAIL")
        self.assertIn("pages 3 != 2", check.summary)

    def test_p3_v2_recomputes_markdown_and_pdf_processing_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            context, receipt, card_path, _ = self.make_p3_v2_receipt(repo)
            with mock.patch.object(verifier, "_pdf_page_count", return_value=(1, None)):
                checks, manifest = verifier._p3_synthesis_checks(receipt, context)

            self.assertTrue(checks)
            self.assertTrue(all(check.status == "PASS" for check in checks), [check.summary for check in checks])
            self.assertEqual(len(manifest), 1)

            text = card_path.read_text(encoding="utf-8").replace(
                "- numeric_audit_status: pass", "- numeric_audit_status:"
            )
            card_path.write_text(text, encoding="utf-8")
            receipt.data["inputs"][0]["method_card"].update(
                {"sha256": sha256(card_path), "size_bytes": card_path.stat().st_size}
            )
            with mock.patch.object(verifier, "_pdf_page_count", return_value=(1, None)):
                checks, _ = verifier._p3_synthesis_checks(receipt, context)

        card_check = next(check for check in checks if check.name == "P3 method card contract:paper")
        self.assertEqual(card_check.status, "FAIL")
        self.assertIn("missing or blank fields: numeric_audit_status", card_check.summary)

    def test_p3_v2_rejects_weakened_processing_receipt_even_with_updated_hash(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            context, receipt, _, processing_payload = self.make_p3_v2_receipt(repo)
            record = receipt.data["inputs"][0]["pdf_processing"]
            processing_path = repo / record["path"]
            processing_payload["source_pdf_preserved"] = False
            processing_path.write_text(json.dumps(processing_payload), encoding="utf-8")
            record.update({"sha256": sha256(processing_path), "size_bytes": processing_path.stat().st_size})
            with mock.patch.object(verifier, "_pdf_page_count", return_value=(1, None)):
                checks, _ = verifier._p3_synthesis_checks(receipt, context)

        processing_check = next(check for check in checks if check.name == "P3 PDF processing:paper")
        self.assertEqual(processing_check.status, "FAIL")
        self.assertIn("source_pdf_preserved is not true", processing_check.summary)

    def test_p3_identity_chain_rejects_alternate_same_work_version_and_source(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            context, receipt, _, _ = self.make_p3_v2_receipt(repo)
            identity = receipt.data["inputs"][0]["artifact_identity"]
            identity.update(
                {
                    "artifact_id": "paper-alternate-version",
                    "version_identity": "alternate publisher version",
                    "doi_or_source_id": "fixture:alternate",
                }
            )
            with mock.patch.object(verifier, "_pdf_page_count", return_value=(1, None)):
                checks, _ = verifier._p3_synthesis_checks(receipt, context)

        identity_check = next(
            check for check in checks if check.name == "P3 artifact identity chain:paper"
        )
        self.assertEqual(identity_check.status, "FAIL")
        self.assertIn("PDF-processing artifact_identity differs", identity_check.summary)
        self.assertIn("method-card artifact identity differs", identity_check.summary)
        self.assertIn("matches=0", identity_check.summary)

    def test_p3_identity_chain_rejects_parent_artifact_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            context, receipt, _, _ = self.make_p3_v2_receipt(repo)
            receipt.data["inputs"][0]["artifact_identity"]["parent_artifact_id"] = "wrong-parent"
            with mock.patch.object(verifier, "_pdf_page_count", return_value=(1, None)):
                checks, _ = verifier._p3_synthesis_checks(receipt, context)

        identity_check = next(
            check for check in checks if check.name == "P3 artifact identity chain:paper"
        )
        self.assertEqual(identity_check.status, "FAIL")
        self.assertIn("PDF-processing artifact_identity differs", identity_check.summary)
        self.assertIn("method-card artifact identity differs", identity_check.summary)

    def test_p3_identity_chain_rejects_missing_and_duplicate_manifest_match(self) -> None:
        for expected_matches in (0, 2):
            with self.subTest(matches=expected_matches), tempfile.TemporaryDirectory() as folder:
                repo = Path(folder).resolve()
                context, receipt, _, _ = self.make_p3_v2_receipt(repo)
                manifest = context.run_dir / "manifests" / "FULLTEXT_MANIFEST.md"
                lines = manifest.read_text(encoding="utf-8").splitlines()
                if expected_matches == 0:
                    lines[-1] = lines[-1].replace("paper-fixture", "paper-other")
                else:
                    lines.append(lines[-1])
                manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
                with mock.patch.object(verifier, "_pdf_page_count", return_value=(1, None)):
                    checks, _ = verifier._p3_synthesis_checks(receipt, context)

                identity_check = next(
                    check for check in checks if check.name == "P3 artifact identity chain:paper"
                )
                self.assertEqual(identity_check.status, "FAIL")
                self.assertIn(f"matches={expected_matches}", identity_check.summary)

    def test_p3_identity_chain_rechecks_manifest_pdf_lineage_fields(self) -> None:
        mutations = {
            "local_path_or_gap": ("missing/paper.pdf", "local_path_or_gap differs"),
            "sha256": ("0" * 64, "SHA-256 differs"),
            "size_bytes": ("999", "size_bytes differs"),
            "pages": ("999", "pages differs"),
        }
        for field, (replacement, expected_message) in mutations.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                repo = Path(folder).resolve()
                context, receipt, _, _ = self.make_p3_v2_receipt(repo)
                manifest = context.run_dir / "manifests" / "FULLTEXT_MANIFEST.md"
                lines = manifest.read_text(encoding="utf-8").splitlines()
                cells = [cell.strip() for cell in lines[-1].strip()[1:-1].split("|")]
                cells[list(verifier.P3_FULLTEXT_MANIFEST_HEADER).index(field)] = replacement
                lines[-1] = "| " + " | ".join(cells) + " |"
                manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
                with mock.patch.object(verifier, "_pdf_page_count", return_value=(1, None)):
                    checks, _ = verifier._p3_synthesis_checks(receipt, context)
                identity_check = next(
                    check for check in checks if check.name == "P3 artifact identity chain:paper"
                )
                self.assertEqual(identity_check.status, "FAIL")
                self.assertIn(expected_message, identity_check.summary)

    def test_p3_identity_chain_receipt_flag_is_mandatory(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            context, receipt, _, _ = self.make_p3_v2_receipt(repo)
            receipt.data["checks"]["artifact_identity_chain_joined"] = False
            with mock.patch.object(verifier, "_pdf_page_count", return_value=(1, None)):
                checks, _ = verifier._p3_synthesis_checks(receipt, context)

        flag = next(
            check for check in checks if check.name == "P3 synthesis artifact_identity_chain_joined"
        )
        self.assertEqual(flag.status, "FAIL")

    def test_p3_v2_rejects_missing_render_png(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            context, receipt, _, processing_payload = self.make_p3_v2_receipt(repo)
            png_path = repo / processing_payload["render_evidence"]["pages"][0]["png_path"]
            png_path.unlink()
            with mock.patch.object(verifier, "_pdf_page_count", return_value=(1, None)):
                checks, _ = verifier._p3_synthesis_checks(receipt, context)

        processing_check = next(check for check in checks if check.name == "P3 PDF processing:paper")
        self.assertEqual(processing_check.status, "FAIL")
        self.assertIn("render PNG missing", processing_check.summary)

    def test_p3_v2_rejects_tampered_render_png(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            context, receipt, _, processing_payload = self.make_p3_v2_receipt(repo)
            png_path = repo / processing_payload["render_evidence"]["pages"][0]["png_path"]
            png_path.write_bytes(png_path.read_bytes() + b"tampered")
            with mock.patch.object(verifier, "_pdf_page_count", return_value=(1, None)):
                checks, _ = verifier._p3_synthesis_checks(receipt, context)

        processing_check = next(check for check in checks if check.name == "P3 PDF processing:paper")
        self.assertEqual(processing_check.status, "FAIL")
        self.assertIn("PNG SHA-256 mismatch", processing_check.summary)

    def test_p3_v2_rejects_false_render_dimensions_with_updated_receipt_hash(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            context, receipt, _, processing_payload = self.make_p3_v2_receipt(repo)
            processing_record = receipt.data["inputs"][0]["pdf_processing"]
            processing_path = repo / processing_record["path"]
            processing_payload["render_evidence"]["pages"][0]["width_px"] = 2
            processing_path.write_text(json.dumps(processing_payload), encoding="utf-8")
            processing_record.update(
                {"sha256": sha256(processing_path), "size_bytes": processing_path.stat().st_size}
            )
            with mock.patch.object(verifier, "_pdf_page_count", return_value=(1, None)):
                checks, _ = verifier._p3_synthesis_checks(receipt, context)

        processing_check = next(check for check in checks if check.name == "P3 PDF processing:paper")
        self.assertEqual(processing_check.status, "FAIL")
        self.assertIn("PNG dimensions 1x1 != 2x1", processing_check.summary)

    def test_p3_v2_rejects_render_page_beyond_current_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            context, receipt, _, processing_payload = self.make_p3_v2_receipt(repo)
            processing_record = receipt.data["inputs"][0]["pdf_processing"]
            processing_path = repo / processing_record["path"]
            page = processing_payload["render_evidence"]["pages"][0]
            old_png = repo / page["png_path"]
            new_png = old_png.with_name("paper-p2.png")
            old_png.rename(new_png)
            page["viewer_page"] = 2
            page["png_path"] = str(new_png.relative_to(repo))
            receipt.data["inputs"][0]["expected_render_pages"] = [2]
            processing_path.write_text(json.dumps(processing_payload), encoding="utf-8")
            processing_record.update(
                {"sha256": sha256(processing_path), "size_bytes": processing_path.stat().st_size}
            )
            with mock.patch.object(verifier, "_pdf_page_count", return_value=(1, None)):
                checks, _ = verifier._p3_synthesis_checks(receipt, context)

        processing_check = next(check for check in checks if check.name == "P3 PDF processing:paper")
        self.assertEqual(processing_check.status, "FAIL")
        self.assertIn("viewer_page 2 exceeds current PDF pages 1", processing_check.summary)

    def test_p3_legacy_synthesis_receipt_is_not_v2_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            run = repo / ".aris" / "business-e2e" / "run"
            receipt_path = run / "receipts" / "p3-literature-synthesis.json"
            receipt_path.parent.mkdir(parents=True)
            receipt = verifier.Receipt(receipt_path, {"schema_version": 1, "status": "pass"})

            checks, manifest = verifier._p3_synthesis_checks(
                receipt, verifier.Context(repo_root=repo, run_dir=run)
            )

        self.assertEqual(checks[0].status, "FAIL")
        self.assertIn("legacy synthesis receipt is not v2 evidence", checks[0].summary)
        self.assertEqual(manifest, [])

    def test_latest_json_mode_is_read_only_and_explicit_run_id_works(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            evidence = repo / ".aris" / "business-e2e"
            older = evidence / "20260717T000000Z"
            latest = evidence / "20260718T000000Z"
            older.mkdir(parents=True)
            latest.mkdir()
            marker = latest / "marker.txt"
            marker.write_text("unchanged", encoding="utf-8")
            before = {
                path.relative_to(repo): (path.stat().st_size, path.stat().st_mtime_ns)
                for path in repo.rglob("*")
                if path.is_file()
            }

            result = subprocess.run(
                [
                    sys.executable,
                    str(VERIFIER),
                    "--repo-root",
                    str(repo),
                    "--evidence-root",
                    str(evidence),
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            payload = json.loads(result.stdout)
            after = {
                path.relative_to(repo): (path.stat().st_size, path.stat().st_mtime_ns)
                for path in repo.rglob("*")
                if path.is_file()
            }
            explicit = verifier.select_run(evidence, older.name)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["run_id"], latest.name)
        self.assertEqual(payload["status"], "INCOMPLETE")
        self.assertEqual(before, after)
        self.assertEqual(explicit.name, older.name)

    def test_rejects_run_id_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            evidence = Path(folder)
            with self.assertRaises(verifier.VerificationInputError):
                verifier.select_run(evidence, "../outside")


if __name__ == "__main__":
    unittest.main()
