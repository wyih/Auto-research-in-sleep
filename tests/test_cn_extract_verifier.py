from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import struct
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER = REPO_ROOT / "skills" / "cn-data-bridge" / "scripts" / "verify_cn_extract.py"
SPEC = importlib.util.spec_from_file_location("verify_cn_extract", VERIFIER)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ExtractFixture:
    def __init__(self, root: Path, site: str) -> None:
        self.repo = root.resolve()
        started = datetime.now(timezone.utc) - timedelta(minutes=2)
        self.run = self.repo / ".aris" / "business-e2e" / started.strftime("%Y%m%dT%H%M%SZ")
        self.site = site
        self.runtime = "codex"
        raw = self.run / "cn-data" / "raw" / site / "2026-07-18"
        receipts = self.run / "cn-data" / "receipts"
        extracted = raw / "extracted"
        extracted.mkdir(parents=True)
        receipts.mkdir(parents=True)
        if site == "cnrds":
            self.csv_path = extracted / "上市公司专利申请情况.csv"
            self.zip_path = raw / "cnrds-cird-000001-2020.zip"
            csv_text = (
                "Scode,Year,Ftyp,Aplctm,Invia,Umia,Desia,Invja,Umja,Desja\r\n"
                "股票代码,会计年度,公司类型,申请时间,当年独立申请的发明数量,"
                "当年独立申请的实用新型数量,当年独立申请的外观设计数量,"
                "当年联合申请的发明数量,当年联合申请的实用新型数量,"
                "当年联合申请的外观设计数量\r\n"
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
        else:
            self.csv_path = extracted / "FS_Combas.csv"
            self.zip_path = raw / "FS_Combas.zip"
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
                "selected_fields": list(verifier.CSMAR_HEADER),
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
        self.csv_path.write_bytes(b"\xef\xbb\xbf" + csv_text.encode("utf-8"))
        self._write_zip(self.csv_path.read_bytes())
        completed = datetime.now(timezone.utc)
        receipt: dict[str, object] = {
            "receipt_version": "1.0",
            "acceptance_id": f"p4-{site}-codex",
            "runtime": "codex",
            "source": site,
            "adapter": verifier.CODEX_ADAPTER,
            **verifier.CODEX_BINDINGS,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "status": "passed",
            "query": query,
            "portal_evidence": portal,
            "download_transport": transport,
            "artifacts": [self._artifact(self.zip_path, "zip"), self._artifact(self.csv_path, "csv")],
            "secrets_or_session_material_persisted": False,
        }
        self.receipt_path = receipts / f"p4-{site}-codex.json"
        self.receipt_path.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")

    def _artifact(self, path: Path, detected_format: str) -> dict[str, object]:
        record: dict[str, object] = {
            "path": str(path.relative_to(self.repo)),
            "detected_format": detected_format,
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
            "verified": True,
        }
        if detected_format == "csv":
            record.update(
                {
                    "encoding": "utf-8-bom",
                    "data_rows": 2 if self.site == "cnrds" else 1,
                    "columns": 10 if self.site == "cnrds" else 5,
                    "code_filter_mismatches": 0,
                }
            )
        return record

    def _write_zip(self, csv_bytes: bytes, *, unsafe_member: str | None = None) -> None:
        with zipfile.ZipFile(self.zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(self.csv_path.name, csv_bytes)
            archive.writestr("README.txt", "vendor metadata")
            if unsafe_member:
                archive.writestr(unsafe_member, "escape")

    def payload(self) -> dict[str, object]:
        return json.loads(self.receipt_path.read_text(encoding="utf-8"))

    def write_payload(self, payload: dict[str, object]) -> None:
        self.receipt_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def refresh_artifact_records(self) -> None:
        payload = self.payload()
        payload["artifacts"] = [self._artifact(self.zip_path, "zip"), self._artifact(self.csv_path, "csv")]
        self.write_payload(payload)

    def replace_csv(self, csv_bytes: bytes, *, update_zip: bool = True) -> None:
        self.csv_path.write_bytes(csv_bytes)
        if update_zip:
            self._write_zip(csv_bytes)
        self.refresh_artifact_records()

    def verify(self) -> verifier.VerificationReport:
        return verifier.verify_receipt(self.receipt_path, self.repo, self.run, self.runtime)


class CNExtractVerifierTests(unittest.TestCase):
    def test_accepts_real_codex_contract_shape_for_both_sites(self) -> None:
        for site in ("cnrds", "csmar"):
            with self.subTest(site=site), tempfile.TemporaryDirectory() as folder:
                fixture = ExtractFixture(Path(folder), site)
                report = fixture.verify()
                self.assertTrue(report.ok, [check for check in report.checks if not check.ok])

    def test_rejects_non_codex_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = ExtractFixture(Path(folder), "cnrds")
            payload = fixture.payload()
            payload["adapter"] = "external_browser"
            fixture.write_payload(payload)
            report = fixture.verify()

        self.assertFalse(report.ok)
        self.assertIn("runtime adapter", {check.name for check in report.checks if not check.ok})

    def test_accepts_kimi_webbridge_contract_shape_for_both_sites(self) -> None:
        for site in ("cnrds", "csmar"):
            with self.subTest(site=site), tempfile.TemporaryDirectory() as folder:
                fixture = ExtractFixture(Path(folder), site)
                payload = fixture.payload()
                payload["runtime"] = "kimi"
                payload["client_runtime"] = "kimi"
                payload["adapter"] = verifier.KIMI_ADAPTER
                payload.update(verifier.KIMI_BINDINGS)
                fixture.write_payload(payload)
                report = verifier.verify_receipt(
                    fixture.receipt_path, fixture.repo, fixture.run, "kimi"
                )
                self.assertTrue(report.ok, [check for check in report.checks if not check.ok])

    def test_rejects_crossed_runtime_adapter_pair(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = ExtractFixture(Path(folder), "cnrds")
            payload = fixture.payload()
            payload["runtime"] = "kimi"
            payload["client_runtime"] = "kimi"
            payload["adapter"] = verifier.KIMI_ADAPTER
            payload.update(verifier.KIMI_BINDINGS)
            fixture.write_payload(payload)
            report = fixture.verify()  # expected runtime remains codex

        self.assertFalse(report.ok)
        failed = {check.name for check in report.checks if not check.ok}
        self.assertIn("runtime adapter", failed)
        self.assertIn("runtime declaration", failed)

    def test_rejects_wrong_header_even_when_hashes_and_receipt_counters_are_refreshed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = ExtractFixture(Path(folder), "csmar")
            tampered = fixture.csv_path.read_bytes().replace(b"A001000000", b"A001000001")
            fixture.replace_csv(tampered)
            report = fixture.verify()

        self.assertFalse(report.ok)
        failed = {check.name for check in report.checks if not check.ok}
        self.assertIn("CSMAR exact header", failed)

    def test_rejects_wrong_cnrds_company_type_with_self_reported_zero_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = ExtractFixture(Path(folder), "cnrds")
            tampered = fixture.csv_path.read_bytes().replace("上市公司本身".encode(), "其他公司类型".encode())
            fixture.replace_csv(tampered)
            report = fixture.verify()

        self.assertFalse(report.ok)
        self.assertIn("CNRDS company types", {check.name for check in report.checks if not check.ok})

    def test_rejects_csmar_filter_or_total_asset_tampering(self) -> None:
        replacements = (
            (b"2020-12-31", b"2019-12-31", "CSMAR date slice"),
            (b'"A","4468514000000.00"', b'"B","4468514000000.00"', "CSMAR report type"),
            (b"4468514000000.00", b"not-a-number", "CSMAR total assets nonempty"),
        )
        for old, new, expected_check in replacements:
            with self.subTest(expected_check=expected_check), tempfile.TemporaryDirectory() as folder:
                fixture = ExtractFixture(Path(folder), "csmar")
                fixture.replace_csv(fixture.csv_path.read_bytes().replace(old, new))
                report = fixture.verify()
                self.assertFalse(report.ok)
                self.assertIn(expected_check, {check.name for check in report.checks if not check.ok})

    def test_rejects_landed_csv_that_does_not_equal_zip_member(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = ExtractFixture(Path(folder), "csmar")
            fixture.replace_csv(fixture.csv_path.read_bytes().replace(b"4468514", b"5468514"), update_zip=False)
            report = fixture.verify()

        self.assertFalse(report.ok)
        self.assertIn("landed CSV equals ZIP member", {check.name for check in report.checks if not check.ok})

    def test_rejects_unsafe_zip_member_even_with_valid_crc(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = ExtractFixture(Path(folder), "cnrds")
            fixture._write_zip(fixture.csv_path.read_bytes(), unsafe_member="../escape.txt")
            fixture.refresh_artifact_records()
            report = fixture.verify()

        self.assertFalse(report.ok)
        self.assertIn("ZIP members safe", {check.name for check in report.checks if not check.ok})

    def test_rejects_zip_member_crc_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = ExtractFixture(Path(folder), "csmar")
            with zipfile.ZipFile(fixture.zip_path, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr(fixture.csv_path.name, fixture.csv_path.read_bytes())
            with zipfile.ZipFile(fixture.zip_path) as archive:
                info = archive.getinfo(fixture.csv_path.name)
            with fixture.zip_path.open("r+b") as handle:
                handle.seek(info.header_offset)
                header = handle.read(30)
                filename_length, extra_length = struct.unpack_from("<HH", header, 26)
                data_offset = info.header_offset + 30 + filename_length + extra_length
                handle.seek(data_offset + 10)
                original = handle.read(1)
                handle.seek(data_offset + 10)
                handle.write(bytes([original[0] ^ 0x01]))
            fixture.refresh_artifact_records()
            report = fixture.verify()

        self.assertFalse(report.ok)
        failed = {check.name for check in report.checks if not check.ok}
        self.assertTrue({"ZIP CRC", "ZIP readable"} & failed)

    def test_rejects_missing_queue_or_result_page_evidence(self) -> None:
        for site, key, expected_check in (
            ("cnrds", "queue_status", "CNRDS export queue evidence"),
            ("csmar", "export_summary_rows", "CSMAR result-page evidence"),
        ):
            with self.subTest(site=site), tempfile.TemporaryDirectory() as folder:
                fixture = ExtractFixture(Path(folder), site)
                payload = fixture.payload()
                portal = payload["portal_evidence"]
                assert isinstance(portal, dict)
                portal.pop(key)
                fixture.write_payload(payload)
                report = fixture.verify()
                self.assertFalse(report.ok)
                self.assertIn(expected_check, {check.name for check in report.checks if not check.ok})

    def test_rejects_incomplete_csmar_result_page_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = ExtractFixture(Path(folder), "csmar")
            payload = fixture.payload()
            portal = payload["portal_evidence"]
            assert isinstance(portal, dict)
            portal["result_page"] = {
                "reconciled": True,
                "table_id": "FS_Combas",
                "date_start": "2020-12-31",
                "date_end": "2020-12-31",
                "code_count": 1,
                "security_codes": ["000001"],
                "condition": "Typrep=A",
                "record_count": 1,
                "format": "CSV格式（*.csv）",
            }
            fixture.write_payload(payload)
            report = fixture.verify()

        self.assertFalse(report.ok)
        self.assertIn(
            "CSMAR structured result-page reconciliation",
            {check.name for check in report.checks if not check.ok},
        )

    def test_rejects_stale_download_even_when_content_hash_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = ExtractFixture(Path(folder), "cnrds")
            stale = datetime.now(timezone.utc) - timedelta(days=2)
            os.utime(fixture.zip_path, (stale.timestamp(), stale.timestamp()))
            report = fixture.verify()

        self.assertFalse(report.ok)
        failed = {check.name for check in report.checks if not check.ok}
        self.assertIn("download freshness window", failed)
        self.assertIn("artifact not older than evidence run", failed)

    def test_requires_explicit_start_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = ExtractFixture(Path(folder), "csmar")
            payload = fixture.payload()
            payload.pop("started_at")
            fixture.write_payload(payload)
            report = fixture.verify()

        self.assertFalse(report.ok)
        self.assertIn("explicit run start timestamp", {check.name for check in report.checks if not check.ok})

    def test_accepts_frozen_prompt_structured_queue_result_and_legacy_download_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            cnrds = ExtractFixture(Path(folder) / "cnrds", "cnrds")
            payload = cnrds.payload()
            portal = payload["portal_evidence"]
            query = payload["query"]
            assert isinstance(portal, dict) and isinstance(query, dict)
            portal.pop("queue_status")
            portal["queue_compression_complete"] = True
            query.pop("selected_field_count")
            query["selected_fields"] = list(verifier.CNRDS_HEADER)
            cnrds.write_payload(payload)
            self.assertTrue(cnrds.verify().ok)

        with tempfile.TemporaryDirectory() as folder:
            csmar = ExtractFixture(Path(folder) / "csmar", "csmar")
            payload = csmar.payload()
            portal = payload["portal_evidence"]
            transport = payload["download_transport"]
            assert isinstance(portal, dict) and isinstance(transport, dict)
            rows = portal.pop("export_summary_rows")
            output_format = portal.pop("export_summary_format")
            portal["result_page"] = {
                "reconciled": True,
                "table_id": "FS_Combas",
                "date_start": "2020-12-31",
                "date_end": "2020-12-31",
                "code_count": 1,
                "security_codes": ["000001"],
                "selected_fields": list(verifier.CSMAR_HEADER),
                "condition": "Typrep=A",
                "record_count": rows,
                "format": output_format,
            }
            transport.pop("browser_download_event_observed")
            transport["download_event"] = "unsupported"
            transport["completion"] = "fallback_directory_increment"
            csmar.write_payload(payload)
            self.assertTrue(csmar.verify().ok)


if __name__ == "__main__":
    unittest.main()
