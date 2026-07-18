from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = (
    REPO_ROOT
    / ".aris/business-e2e/20260718T011517Z/integrated-chain/qa/verify_integrated_chain.py"
)


def _load_verifier():
    spec = importlib.util.spec_from_file_location("integrated_chain_verifier", VERIFIER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load verifier: {VERIFIER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IntegratedChainVerifierUnitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.verifier = _load_verifier()

    def test_receipt_check_rejects_semantic_tamper_without_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            receipt_path = Path(temp_dir) / "root.json"
            expected = self.verifier.canonical_json_bytes(
                {"status": "pass", "scope": "current facts", "artifact": {"sha256": "a" * 64}}
            )
            tampered = self.verifier.canonical_json_bytes(
                {"status": "pass", "scope": "tampered semantic scope", "artifact": {"sha256": "a" * 64}}
            )
            receipt_path.write_bytes(tampered)
            before_bytes = receipt_path.read_bytes()
            before_sha = self.verifier.sha256_bytes(before_bytes)
            before_mtime = receipt_path.stat().st_mtime_ns

            with self.assertRaisesRegex(AssertionError, "receipt mismatch"):
                self.verifier.compare_receipt_bytes(receipt_path, expected, "root")

            self.assertEqual(receipt_path.read_bytes(), before_bytes)
            self.assertEqual(self.verifier.sha256_bytes(receipt_path.read_bytes()), before_sha)
            self.assertEqual(receipt_path.stat().st_mtime_ns, before_mtime)

    def test_receipt_double_write_is_byte_stable_and_template_independent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            lineage_path = project / "lineage" / "receipt.json"
            root_path = project / "root.json"
            report = {
                "status": "passed",
                "check_summary": {"total": 3, "passed": 3, "failed": 0},
                "frozen_fact": "unchanged",
            }
            lineage_bytes = self.verifier.canonical_json_bytes(report)

            root_path.write_text(
                json.dumps({"status": "tampered", "scope": "must not survive"}),
                encoding="utf-8",
            )
            first_root = self.verifier.build_root_payload(
                project=project,
                lineage_path=lineage_path,
                lineage_bytes=lineage_bytes,
                lineage_report=report,
                generated_at_utc="2026-07-18T05:04:08+00:00",
            )
            root_path.write_text(
                json.dumps({"status": "different tamper", "arbitrary": [1, 2, 3]}),
                encoding="utf-8",
            )
            second_root = self.verifier.build_root_payload(
                project=project,
                lineage_path=lineage_path,
                lineage_bytes=lineage_bytes,
                lineage_report=report,
                generated_at_utc="2026-07-18T05:04:08+00:00",
            )
            self.assertEqual(first_root, second_root)
            self.assertNotIn("must not survive", json.dumps(first_root))
            root_bytes = self.verifier.canonical_json_bytes(first_root)

            self.verifier.write_receipts(lineage_path, lineage_bytes, root_path, root_bytes)
            first_lineage_bytes = lineage_path.read_bytes()
            first_root_bytes = root_path.read_bytes()
            first_hashes = (
                self.verifier.sha256_bytes(first_lineage_bytes),
                self.verifier.sha256_bytes(first_root_bytes),
            )

            self.verifier.write_receipts(lineage_path, lineage_bytes, root_path, root_bytes)
            self.assertEqual(lineage_path.read_bytes(), first_lineage_bytes)
            self.assertEqual(root_path.read_bytes(), first_root_bytes)
            self.assertEqual(
                (
                    self.verifier.sha256_bytes(lineage_path.read_bytes()),
                    self.verifier.sha256_bytes(root_path.read_bytes()),
                ),
                first_hashes,
            )
            self.assertEqual(first_root["lineage_receipt"]["sha256"], first_hashes[0])
            self.assertEqual(first_root["lineage_receipt"]["bytes"], len(first_lineage_bytes))

    def test_independent_docx_identity_audit_rejects_dirty_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "dirty.docx"
            core = """<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>Mallory</dc:creator><cp:lastModifiedBy>Mallory</cp:lastModifiedBy></cp:coreProperties>"""
            app = """<?xml version="1.0" encoding="UTF-8"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Company>Evil Corp</Company><Manager>Mallory</Manager></Properties>"""
            document = """<?xml version="1.0" encoding="UTF-8"?>
<x:document xmlns:x="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><x:body><x:ins x:author="Mallory" x:rsidR="00AB"><x:r><x:t>dirty</x:t></x:r></x:ins><x:commentReference x:id="0"/></x:body></x:document>"""
            relationships = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/></Relationships>"""
            content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/></Types>"""
            with zipfile.ZipFile(docx_path, "w") as archive:
                archive.writestr("docProps/core.xml", core)
                archive.writestr("docProps/app.xml", app)
                archive.writestr("word/document.xml", document)
                archive.writestr("word/comments.xml", "<comments/>")
                archive.writestr("word/_rels/document.xml.rels", relationships)
                archive.writestr("[Content_Types].xml", content_types)

            # A lying adjacent builder receipt is deliberately irrelevant to the audit.
            (Path(temp_dir) / "RESULTS_DOCX_RECEIPT.json").write_text(
                json.dumps(
                    {
                        "metadata": {
                            "creator": "Yihong Wang",
                            "lastModifiedBy": "Yihong Wang",
                            "company": "",
                            "manager": "",
                            "passed": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
            audit = self.verifier.audit_docx_identity(docx_path)
            self.assertFalse(audit["passed"])
            self.assertEqual(audit["creator"], "Mallory")
            self.assertEqual(audit["lastModifiedBy"], "Mallory")
            self.assertTrue(audit["identity_parts"])
            self.assertTrue(audit["comment_markers"])
            self.assertTrue(audit["tracked_changes"])
            self.assertTrue(audit["rsid_attributes"])
            self.assertTrue(audit["identity_attributes"])
            self.assertTrue(audit["identity_relationships"])
            self.assertTrue(audit["content_type_overrides"])


if __name__ == "__main__":
    unittest.main()
