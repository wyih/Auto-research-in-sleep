from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER = REPO_ROOT / "skills" / "browser-session-bridge" / "scripts" / "verify_download.py"


def run_verifier(path: Path, expected: str, min_bytes: int | None = None) -> tuple[int, dict[str, object]]:
    command = [sys.executable, str(VERIFIER), str(path), "--expect", expected]
    if min_bytes is not None:
        command.extend(["--min-bytes", str(min_bytes)])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    return result.returncode, json.loads(result.stdout)


class BrowserDownloadVerifierTests(unittest.TestCase):
    def test_accepts_complete_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "paper.pdf"
            path.write_bytes(b"%PDF-1.7\n" + (b"0" * 10_240) + b"\n%%EOF\n")
            returncode, payload = run_verifier(path, "pdf")

        self.assertEqual(returncode, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["detected_format"], "pdf")
        self.assertEqual(len(str(payload["sha256"])), 64)

    def test_rejects_html_masquerading_as_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "paper.pdf"
            path.write_bytes(b"<!doctype html><html>login required</html>" + (b" " * 12_000))
            returncode, payload = run_verifier(path, "pdf")

        self.assertEqual(returncode, 2)
        self.assertFalse(payload["ok"])
        self.assertIn("HTML", str(payload["error"]))

    def test_accepts_minimal_xlsx_container(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "export.xlsx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types />")
                archive.writestr("xl/workbook.xml", "<workbook />")
                archive.writestr("xl/worksheets/sheet1.xml", "<worksheet />")
            returncode, payload = run_verifier(path, "xlsx", min_bytes=1)

        self.assertEqual(returncode, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["detected_format"], "xlsx")

    def test_rejects_zip_without_xlsx_members(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "export.xlsx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("message.txt", "not a workbook")
            returncode, payload = run_verifier(path, "xlsx", min_bytes=1)

        self.assertEqual(returncode, 2)
        self.assertFalse(payload["ok"])
        self.assertIn("missing", str(payload["error"]))

    def test_accepts_gb18030_csv(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "export.csv"
            path.write_bytes("证券代码,年度,资产总额\n000001,2022,100\n".encode("gb18030"))
            returncode, payload = run_verifier(path, "csv")

        self.assertEqual(returncode, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["detected_format"], "csv")


if __name__ == "__main__":
    unittest.main()
