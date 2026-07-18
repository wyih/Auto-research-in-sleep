from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "accept_grok_browser_candidate.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("accept_grok_browser_candidate_tests", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


acceptor = _load_module()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _pdf_bytes(lines: list[str]) -> bytes:
    escaped = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
    operations = ["BT", "/F1 11 Tf", "72 740 Td", "14 TL"]
    for index, line in enumerate(escaped):
        if index:
            operations.append("T*")
        operations.append(f"({line}) Tj")
    operations.append("ET")
    stream = ("\n".join(operations) + "\n").encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream",
        b"<< /Title (Capital Structure Evidence) /Author (Ada Lovelace and Grace Hopper) >>",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info 6 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def _xlsx_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
    def cell(column: int, row: int, value: str) -> str:
        letters = ""
        number = column
        while number:
            number, remainder = divmod(number - 1, 26)
            letters = chr(ord("A") + remainder) + letters
        escaped = (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        return f'<c r="{letters}{row}" t="inlineStr"><is><t>{escaped}</t></is></c>'

    all_rows = [headers, *rows]
    row_xml = "".join(
        f'<row r="{row_number}">'
        + "".join(cell(column, row_number, value) for column, value in enumerate(values, 1))
        + "</row>"
        for row_number, values in enumerate(all_rows, 1)
    )
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{row_xml}</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Data" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '</Types>'
    )
    from io import BytesIO

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", relationships)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return buffer.getvalue()


class CandidateFixture:
    def __init__(self, folder: str, stage: str = "P4", artifact_format: str = "csv") -> None:
        self.workspace = Path(folder) / "workspace"
        self.run_root = self.workspace / "run"
        self.artifact = self.run_root / "artifacts" / f"download.{artifact_format}"
        self.spec = self.workspace / "acceptance-spec.json"
        self.candidate = self.run_root / "candidate.json"
        self.output = self.run_root / "receipts" / "external-acceptance.json"
        self.run_root.mkdir(parents=True)
        self.artifact.parent.mkdir()
        self.output.parent.mkdir()
        self.stage = stage
        self.artifact_format = artifact_format
        self.site = "sciencedirect" if stage == "P3" else "csmar"

    def write_artifact(self) -> None:
        if self.artifact_format == "pdf":
            self.artifact.write_bytes(
                _pdf_bytes(
                    [
                        "Capital Structure Evidence",
                        "Ada Lovelace and Grace Hopper",
                        "DOI: 10.1234/example.2026.7",
                        "PII S0123456789012345",
                        "SSRN ID: 875844",
                    ]
                )
            )
        elif self.artifact_format == "csv":
            self.artifact.write_text(
                "Stkcd,Accper,Assets\n000001,2020-12-31,100\n000002,2020-12-31,200\n",
                encoding="utf-8",
            )
        elif self.artifact_format == "xlsx":
            self.artifact.write_bytes(
                _xlsx_bytes(
                    ["Stkcd", "Accper", "Assets"],
                    [["000001", "2020-12-31", "100"], ["000002", "2020-12-31", "200"]],
                )
            )
        else:
            with zipfile.ZipFile(self.artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    "tables/data.csv",
                    "Stkcd,Accper,Assets\n000001,2020-12-31,100\n000002,2020-12-31,200\n",
                )

    def spec_payload(self) -> dict[str, Any]:
        artifact = {
            "path": self.artifact.relative_to(self.workspace).as_posix(),
            "format": self.artifact_format,
            "min_bytes": 1,
        }
        common: dict[str, Any] = {
            "schema_version": acceptor.SPEC_SCHEMA,
            "stage": self.stage,
            "site": self.site,
            "artifact": artifact,
        }
        if self.stage == "P3":
            common["p3"] = {
                "expected_title": "Capital Structure Evidence",
                "expected_authors": ["Ada Lovelace", "Grace Hopper"],
                "expected_doi": "10.1234/example.2026.7",
                "expected_pii": "S0123456789012345",
                "expected_ssrn_id": "875844",
            }
        else:
            p4: dict[str, Any] = {
                "expected_headers": ["Stkcd", "Accper", "Assets"],
                "exact_rows": [
                    {"Stkcd": "000001", "Accper": "2020-12-31", "Assets": "100"}
                ],
                "min_rows": 2,
            }
            if self.artifact_format == "xlsx":
                p4["sheet"] = "Data"
            elif self.artifact_format == "zip":
                p4.update({"archive_member": "tables/data.csv", "member_format": "csv"})
            common["p4"] = p4
        return common

    def candidate_payload(self) -> dict[str, Any]:
        status = self.artifact.stat()
        return {
            "schema_version": acceptor.CANDIDATE_SCHEMA,
            **acceptor.EXACT_BINDINGS,
            "stage": self.stage,
            "site": self.site,
            "acceptance_spec_sha256": _sha256(self.spec),
            "artifact": {
                "path": self.artifact.relative_to(self.workspace).as_posix(),
                "format": self.artifact_format,
                "size_bytes": status.st_size,
                "mtime_ns": str(status.st_mtime_ns),
                "sha256": _sha256(self.artifact),
            },
        }

    def build(self) -> None:
        self.write_artifact()
        _write_json(self.spec, self.spec_payload())
        _write_json(self.candidate, self.candidate_payload())

    def accept(self) -> dict[str, Any]:
        return acceptor.accept_candidate(
            workspace=self.workspace,
            run_root=self.run_root,
            candidate=self.candidate,
            spec=self.spec,
            output=self.output,
        )


class GrokBrowserCandidateAcceptanceTests(unittest.TestCase):
    def test_accepts_p3_pdf_with_all_generic_identity_fields(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = CandidateFixture(folder, "P3", "pdf")
            fixture.build()
            payload = fixture.accept()

            self.assertEqual(payload["status"], "passed")
            self.assertEqual(payload["runtime"], "grok")
            report = payload["verifier_report"]["stage_content"]
            self.assertEqual(report["pages"], 1)
            self.assertTrue(all(value is True for key, value in report["identity_matches"].items() if key != "authors"))
            self.assertTrue(all(report["identity_matches"]["authors"].values()))
            self.assertFalse(report["raw_tool_output_recorded"])

    def test_accepts_route_ids_from_frozen_filename_when_pdf_omits_them(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = CandidateFixture(folder, "P3", "pdf")
            fixture.artifact = (
                fixture.run_root
                / "artifacts"
                / "S0123456789012345-ssrn-875844-capital-structure.pdf"
            )
            fixture.artifact.write_bytes(
                _pdf_bytes(
                    [
                        "Capital Structure Evidence",
                        "Ada Lovelace and Grace Hopper",
                        "DOI: 10.1234/example.2026.7",
                    ]
                )
            )
            _write_json(fixture.spec, fixture.spec_payload())
            _write_json(fixture.candidate, fixture.candidate_payload())

            report = fixture.accept()["verifier_report"]["stage_content"]

            self.assertTrue(report["identity_matches"]["pii"])
            self.assertTrue(report["identity_matches"]["ssrn_id"])

    def test_accepts_p4_csv_xlsx_and_zip_with_structure_checks(self) -> None:
        for artifact_format in ("csv", "xlsx", "zip"):
            with self.subTest(artifact_format=artifact_format), tempfile.TemporaryDirectory() as folder:
                fixture = CandidateFixture(folder, "P4", artifact_format)
                fixture.build()
                payload = fixture.accept()
                report = payload["verifier_report"]["stage_content"]
                self.assertEqual(report["headers"], ["Stkcd", "Accper", "Assets"])
                self.assertEqual(report["row_count"], 2)
                self.assertEqual(report["matched_exact_row_occurrences"], 1)
                self.assertTrue(fixture.output.is_file())

    def test_output_is_candidate_only_atomic_inventory_not_business_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = CandidateFixture(folder)
            fixture.build()
            before = {path.relative_to(fixture.workspace) for path in fixture.workspace.rglob("*")}
            payload = fixture.accept()
            after = {path.relative_to(fixture.workspace) for path in fixture.workspace.rglob("*")}

            self.assertEqual(after - before, {fixture.output.relative_to(fixture.workspace)})
            self.assertEqual(payload["record_kind"], "external_candidate_acceptance")
            self.assertEqual(payload["acceptance_scope"], "frozen_candidate_only")
            self.assertFalse(payload["business_success_receipt_created"])
            self.assertFalse(payload["manifest_modified"])
            self.assertFalse(payload["spec_modified"])
            self.assertEqual(payload["candidate_sha256"], _sha256(fixture.candidate))
            self.assertEqual(payload["artifact_sha256"], _sha256(fixture.artifact))
            self.assertEqual(payload["acceptance_spec_sha256"], _sha256(fixture.spec))
            artifact_snapshot = payload["hash_inventory"]["artifact"]
            self.assertIsInstance(artifact_snapshot["mtime_ns"], int)
            self.assertEqual(artifact_snapshot["mtime_ns"], fixture.artifact.stat().st_mtime_ns)
            self.assertEqual(
                set(payload["hash_inventory"]),
                {"candidate", "spec", "artifact", "download_verifier"},
            )
            self.assertEqual(fixture.output.stat().st_mode & 0o777, 0o600)

    def test_cli_requires_and_uses_all_five_explicit_paths(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = CandidateFixture(folder)
            fixture.build()
            command = [
                sys.executable,
                str(SCRIPT),
                "--candidate",
                str(fixture.candidate),
                "--spec",
                str(fixture.spec),
                "--output",
                str(fixture.output),
                "--workspace",
                str(fixture.workspace),
                "--run-root",
                str(fixture.run_root),
            ]
            result = subprocess.run(command, text=True, capture_output=True, check=False)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertTrue(summary["ok"])
            self.assertEqual(summary["sha256"], _sha256(fixture.output))

    def test_rejects_each_wrong_exact_runtime_binding(self) -> None:
        for field, expected in acceptor.EXACT_BINDINGS.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                fixture = CandidateFixture(folder)
                fixture.build()
                candidate = fixture.candidate_payload()
                candidate[field] = f"wrong-{expected}"
                _write_json(fixture.candidate, candidate)
                with self.assertRaisesRegex(acceptor.AcceptanceError, field):
                    fixture.accept()

    def test_rejects_query_fragment_secret_raw_output_and_browser_ids(self) -> None:
        mutations = {
            "query URL": ("source_url", "https://example.test/paper?token=secret"),
            "fragment URL": ("source_url", "https://example.test/paper#download"),
            "secret field": ("session_token", "opaque"),
            "secret value": ("note", "Authorization: Bearer abc.def"),
            "raw output": ("raw_tool_output", {"text": "anything"}),
            "tab id": ("tab_id", 12),
            "page id": ("pageId", "page-2"),
            "uid": ("uid", "abc"),
            "lease id": ("lease_id", "lease-3"),
        }
        for label, (field, value) in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as folder:
                fixture = CandidateFixture(folder)
                fixture.build()
                candidate = fixture.candidate_payload()
                candidate[field] = value
                _write_json(fixture.candidate, candidate)
                with self.assertRaises(acceptor.AcceptanceError):
                    fixture.accept()
                self.assertFalse(fixture.output.exists())

    def test_rejects_query_or_fragment_in_artifact_path(self) -> None:
        for suffix in ("?download=1", "#fragment"):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as folder:
                fixture = CandidateFixture(folder)
                fixture.build()
                candidate = fixture.candidate_payload()
                candidate["artifact"]["path"] += suffix
                _write_json(fixture.candidate, candidate)
                with self.assertRaisesRegex(acceptor.AcceptanceError, "query-free"):
                    fixture.accept()

    def test_rejects_duplicate_json_fields(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = CandidateFixture(folder)
            fixture.build()
            raw = fixture.candidate.read_text(encoding="utf-8")
            fixture.candidate.write_text(
                raw.replace('"stage": "P4"', '"stage": "P4",\n  "stage": "P4"'),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(acceptor.AcceptanceError, "duplicate JSON field"):
                fixture.accept()

    def test_rejects_spec_hash_stage_site_path_and_format_mismatch(self) -> None:
        cases = ("spec_hash", "stage", "site", "path", "format")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as folder:
                fixture = CandidateFixture(folder)
                fixture.build()
                candidate = fixture.candidate_payload()
                if case == "spec_hash":
                    candidate["acceptance_spec_sha256"] = "0" * 64
                elif case in {"stage", "site"}:
                    candidate[case] = "P3" if case == "stage" else "cnrds"
                elif case == "path":
                    candidate["artifact"]["path"] = "run/artifacts/other.csv"
                else:
                    candidate["artifact"]["format"] = "xlsx"
                _write_json(fixture.candidate, candidate)
                with self.assertRaises(acceptor.AcceptanceError):
                    fixture.accept()

    def test_rejects_artifact_size_mtime_and_hash_mismatch(self) -> None:
        for field, mutation in (
            ("size_bytes", lambda value: value + 1),
            ("mtime_ns", lambda value: str(int(value) + 1)),
            ("sha256", lambda _value: "0" * 64),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                fixture = CandidateFixture(folder)
                fixture.build()
                candidate = fixture.candidate_payload()
                candidate["artifact"][field] = mutation(candidate["artifact"][field])
                _write_json(fixture.candidate, candidate)
                pattern = "SHA-256" if field == "sha256" else field.split("_")[0]
                with self.assertRaisesRegex(acceptor.AcceptanceError, pattern):
                    fixture.accept()

    def test_candidate_mtime_ns_requires_canonical_positive_decimal_string(self) -> None:
        invalid_values: tuple[Any, ...] = (
            1_725_000_000_000_000_000,
            0,
            "0",
            "01",
            "-1",
            "+1",
            "1.0",
            " 1",
            "1 ",
            "",
        )
        for value in invalid_values:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as folder:
                fixture = CandidateFixture(folder)
                fixture.build()
                candidate = fixture.candidate_payload()
                candidate["artifact"]["mtime_ns"] = value
                _write_json(fixture.candidate, candidate)
                with self.assertRaisesRegex(
                    acceptor.AcceptanceError,
                    "positive decimal string without leading zero|non-empty string",
                ):
                    fixture.accept()

    def test_rejects_browser_filename_collision_and_partial_sibling(self) -> None:
        for sibling_name in ("download (1).csv", "download.csv.crdownload"):
            with self.subTest(sibling=sibling_name), tempfile.TemporaryDirectory() as folder:
                fixture = CandidateFixture(folder)
                fixture.build()
                fixture.artifact.with_name(sibling_name).write_text("collision", encoding="utf-8")
                with self.assertRaisesRegex(acceptor.AcceptanceError, "collision|incomplete"):
                    fixture.accept()

    def test_rejects_artifact_named_with_browser_collision_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = CandidateFixture(folder)
            fixture.artifact = fixture.artifact.with_name("download (2).csv")
            fixture.build()
            with self.assertRaisesRegex(acceptor.AcceptanceError, "collision suffix"):
                fixture.accept()

    def test_rejects_symlink_artifact_even_when_target_stays_inside_run_root(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = CandidateFixture(folder)
            fixture.write_artifact()
            real = fixture.artifact.with_name("real.csv")
            fixture.artifact.rename(real)
            fixture.artifact.symlink_to(real)
            _write_json(fixture.spec, fixture.spec_payload())
            _write_json(fixture.candidate, fixture.candidate_payload())
            with self.assertRaisesRegex(acceptor.AcceptanceError, "symlink"):
                fixture.accept()

    def test_rejects_artifact_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outside:
            fixture = CandidateFixture(folder)
            fixture.run_root.mkdir(parents=True, exist_ok=True)
            external = Path(outside) / "external.csv"
            external.write_text("Stkcd\n000001\n", encoding="utf-8")
            fixture.artifact.parent.mkdir(exist_ok=True)
            fixture.artifact.symlink_to(external)
            _write_json(fixture.spec, fixture.spec_payload())
            _write_json(fixture.candidate, fixture.candidate_payload())
            with self.assertRaises(acceptor.AcceptanceError):
                fixture.accept()

    def test_rejects_candidate_and_output_outside_run_root(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = CandidateFixture(folder)
            fixture.build()
            outside_candidate = fixture.workspace / "candidate.json"
            outside_candidate.write_bytes(fixture.candidate.read_bytes())
            with self.assertRaisesRegex(acceptor.AcceptanceError, "candidate escapes"):
                acceptor.accept_candidate(
                    workspace=fixture.workspace,
                    run_root=fixture.run_root,
                    candidate=outside_candidate,
                    spec=fixture.spec,
                    output=fixture.output,
                )
            outside_output = fixture.workspace / "external.json"
            with self.assertRaisesRegex(acceptor.AcceptanceError, "output(?: parent)? escapes"):
                acceptor.accept_candidate(
                    workspace=fixture.workspace,
                    run_root=fixture.run_root,
                    candidate=fixture.candidate,
                    spec=fixture.spec,
                    output=outside_output,
                )

    def test_rejects_existing_or_racing_output_collision_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = CandidateFixture(folder)
            fixture.build()
            fixture.output.write_text("user-owned\n", encoding="utf-8")
            with self.assertRaisesRegex(acceptor.AcceptanceError, "output collision"):
                fixture.accept()
            self.assertEqual(fixture.output.read_text(encoding="utf-8"), "user-owned\n")

        with tempfile.TemporaryDirectory() as folder:
            fixture = CandidateFixture(folder)
            fixture.build()
            original_link = os.link

            def racing_link(source: Any, destination: Any, **kwargs: Any) -> None:
                Path(destination).write_text("racer\n", encoding="utf-8")
                original_link(source, destination, **kwargs)

            with mock.patch.object(acceptor.os, "link", side_effect=racing_link):
                with self.assertRaisesRegex(acceptor.AcceptanceError, "output collision"):
                    fixture.accept()
            self.assertEqual(fixture.output.read_text(encoding="utf-8"), "racer\n")

    def test_rejects_candidate_or_artifact_mutation_during_verification(self) -> None:
        for target in ("candidate", "artifact"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as folder:
                fixture = CandidateFixture(folder)
                fixture.build()
                original = acceptor._verify_p4_table

                def mutate_then_verify(*args: Any, **kwargs: Any) -> dict[str, Any]:
                    report = original(*args, **kwargs)
                    path = fixture.candidate if target == "candidate" else fixture.artifact
                    if target == "candidate":
                        path.write_bytes(path.read_bytes() + b" ")
                    else:
                        path.write_bytes(path.read_bytes() + b"\n")
                    return report

                with mock.patch.object(acceptor, "_verify_p4_table", side_effect=mutate_then_verify):
                    with self.assertRaisesRegex(acceptor.AcceptanceError, "changed"):
                        fixture.accept()
                self.assertFalse(fixture.output.exists())

    def test_rejects_p3_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = CandidateFixture(folder, "P3", "pdf")
            fixture.write_artifact()
            spec = fixture.spec_payload()
            spec["p3"]["expected_doi"] = "10.9999/not-this-paper"
            _write_json(fixture.spec, spec)
            _write_json(fixture.candidate, fixture.candidate_payload())
            with self.assertRaisesRegex(acceptor.AcceptanceError, "DOI"):
                fixture.accept()

    def test_rejects_p4_header_row_count_and_exact_row_mismatch(self) -> None:
        for case in ("header", "min_rows", "exact_row"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as folder:
                fixture = CandidateFixture(folder)
                fixture.write_artifact()
                spec = fixture.spec_payload()
                if case == "header":
                    spec["p4"]["expected_headers"][2] = "Liabilities"
                    spec["p4"]["exact_rows"][0] = {
                        "Stkcd": "000001",
                        "Accper": "2020-12-31",
                        "Liabilities": "100",
                    }
                elif case == "min_rows":
                    spec["p4"]["min_rows"] = 3
                else:
                    spec["p4"]["exact_rows"][0]["Assets"] = "999"
                _write_json(fixture.spec, spec)
                _write_json(fixture.candidate, fixture.candidate_payload())
                with self.assertRaises(acceptor.AcceptanceError):
                    fixture.accept()

    def test_rejects_duplicate_archive_member_collision(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = CandidateFixture(folder, "P4", "zip")
            fixture.artifact.parent.mkdir(parents=True, exist_ok=True)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(fixture.artifact, "w") as archive:
                    archive.writestr("tables/data.csv", "Stkcd,Accper,Assets\n000001,x,1\n")
                    archive.writestr("tables/data.csv", "Stkcd,Accper,Assets\n000002,x,2\n")
            _write_json(fixture.spec, fixture.spec_payload())
            _write_json(fixture.candidate, fixture.candidate_payload())
            with self.assertRaisesRegex(acceptor.AcceptanceError, "duplicate member"):
                fixture.accept()


if __name__ == "__main__":
    unittest.main()
