from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER = REPO_ROOT / "skills" / "results-to-docx" / "scripts" / "build_results_docx.py"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
TEST_AUTHOR = "ARIS Test Author"


def _runtime_available() -> bool:
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import docx, lxml"],
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


@unittest.skipUnless(_runtime_available(), "python-docx/lxml runtime unavailable")
class ResultsToDocxIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        (self.inputs / "main_coef.csv").write_text(
            "term,term_label,estimate,std.error,p.value,model_id,model_label,nobs,adj.r.squared,dependent_variable,fixed_effects,cluster,controls\n"
            "culture_score,Corporate culture score,0.084,0.028,0.003,m1,(1),1030,0.221,Tobin's Q,Firm + Year,Firm,Yes\n"
            "leverage,Leverage,-0.031,0.019,0.103,m1,(1),1030,0.221,Tobin's Q,Firm + Year,Firm,Yes\n",
            encoding="utf-8",
        )
        (self.inputs / "descriptives.csv").write_text(
            "variable,variable_label,n,mean,sd,p25,p50,p75,min,max,sample\n"
            "culture_score,Corporate culture score,1030,0.512,0.187,0.378,0.501,0.641,0.102,0.941,Main\n",
            encoding="utf-8",
        )
        (self.inputs / "figure_data.csv").write_text(
            "culture_quartile,mean_tobins_q\n1,1.12\n2,1.18\n3,1.25\n4,1.34\n",
            encoding="utf-8",
        )
        (self.inputs / "figure.png").write_bytes(PNG_1X1)
        (self.inputs / "figure_source.py").write_text("# deterministic figure fixture\n", encoding="utf-8")
        self.spec = self.inputs / "spec.json"
        self.spec.write_text(
            json.dumps(
                {
                    "title": "Corporate Culture and Firm Performance",
                    "subtitle": "Auditable empirical results pack",
                    "run_id": "unit-test",
                    "as_of_date": "2026-07-18",
                    "coefficient_tables": [
                        {
                            "path": "main_coef.csv",
                            "title": "Table 2. Main Regression Results",
                            "primary_term": "culture_score",
                            "primary_model": "m1",
                        }
                    ],
                    "descriptive_tables": [
                        {"path": "descriptives.csv", "title": "Table 1. Descriptive Statistics"}
                    ],
                    "figures": [
                        {
                            "path": "figure.png",
                            "title": "Figure 1. Outcome by Culture Quartile",
                            "source_data": ["figure_data.csv"],
                            "source_script": "figure_source.py",
                            "alt_text": "Mean Tobin's Q increases across corporate culture quartiles.",
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_builds_auditable_three_line_docx(self) -> None:
        output_dir = self.root / "output" / "results_docx"
        output = output_dir / "results.docx"
        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--spec",
                str(self.spec),
                "--out",
                str(output),
                "--author",
                TEST_AUTHOR,
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["metadata_passed"])
        self.assertEqual(payload["tables"], 2)
        self.assertEqual(payload["figures"], 1)
        self.assertEqual(payload["narrative_mode"], "standard")

        receipt = json.loads((output_dir / "RESULTS_DOCX_RECEIPT.json").read_text(encoding="utf-8"))
        self.assertTrue(receipt["metadata"]["passed"])
        self.assertEqual(receipt["narrative_mode"], "standard")
        self.assertEqual(receipt["metadata"]["creator"], TEST_AUTHOR)
        self.assertEqual(receipt["metadata"]["lastModifiedBy"], TEST_AUTHOR)
        self.assertEqual(receipt["metadata"]["rsid_attributes"], [])
        self.assertEqual(len(receipt["narrative_claims"]), 2)
        coef_claim = receipt["narrative_claims"][0]
        self.assertEqual(coef_claim["source_row"], 2)
        self.assertEqual(coef_claim["values"]["estimate"], 0.084)
        self.assertIn("estimated association", coef_claim["text"])
        self.assertIn("statistically distinguishable from zero", coef_claim["text"])

        with zipfile.ZipFile(output) as package:
            document_xml = package.read("word/document.xml")
            root = ET.fromstring(document_xml)
            text = "".join(root.itertext())
            self.assertIn("Corporate culture score", text)
            self.assertIn("0.084***", text)
            self.assertIn("Audit boundary", text)
            self.assertIn("Mean Tobin's Q increases", document_xml.decode("utf-8"))
            drawing_props = root.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr")
            self.assertEqual(len(drawing_props), 1)
            self.assertIn("Mean Tobin's Q increases", drawing_props[0].get("descr", ""))
            ignorable_marker = b'mc:Ignorable="'
            if ignorable_marker in document_xml:
                prefixes = document_xml.split(ignorable_marker, 1)[1].split(b'"', 1)[0].split()
                for prefix in prefixes:
                    self.assertIn(b"xmlns:" + prefix + b'="', document_xml)
            self.assertTrue(any(name.startswith("word/media/") for name in package.namelist()))

            tables = root.findall(".//w:tbl", NS)
            self.assertEqual(len(tables), 2)
            for table in tables:
                width = table.find("./w:tblPr/w:tblW", NS)
                indent = table.find("./w:tblPr/w:tblInd", NS)
                self.assertIsNotNone(width)
                self.assertIsNotNone(indent)
                self.assertEqual(width.get(f"{{{NS['w']}}}w"), "9360")
                self.assertEqual(indent.get(f"{{{NS['w']}}}w"), "120")
                grid = table.findall("./w:tblGrid/w:gridCol", NS)
                self.assertEqual(sum(int(item.get(f"{{{NS['w']}}}w")) for item in grid), 9360)
                inside_vertical = table.find("./w:tblPr/w:tblBorders/w:insideV", NS)
                self.assertEqual(inside_vertical.get(f"{{{NS['w']}}}val"), "nil")

    def test_transport_only_mode_emits_transport_facts_without_interpretation(self) -> None:
        spec_payload = json.loads(self.spec.read_text(encoding="utf-8"))
        spec_payload["narrative_mode"] = "transport-only"
        self.spec.write_text(json.dumps(spec_payload, indent=2), encoding="utf-8")

        output_dir = self.root / "output" / "results_docx"
        output = output_dir / "transport_only.docx"
        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--spec",
                str(self.spec),
                "--out",
                str(output),
                "--author",
                TEST_AUTHOR,
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        cli_payload = json.loads(result.stdout)
        self.assertEqual(cli_payload["narrative_mode"], "transport-only")
        self.assertEqual(cli_payload["figures"], 0)

        receipt = json.loads((output_dir / "RESULTS_DOCX_RECEIPT.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["narrative_mode"], "transport-only")
        self.assertEqual(len(receipt["narrative_claims"]), 2)
        coefficient_text = receipt["narrative_claims"][0]["text"]
        self.assertEqual(
            coefficient_text,
            "Coefficient output C1: term_id=culture_score; model_id=m1; estimate=0.084; "
            "standard_error=0.028; p_value=0.003, N=1,030.",
        )
        self.assertEqual(
            receipt["narrative_claims"][1]["text"],
            "Descriptive output D1: variable_id=culture_score; N=1,030; mean=0.512; SD=0.187.",
        )
        self.assertEqual(receipt["document"]["figures"], 0)
        self.assertFalse(receipt["figures"][0]["embedded"])
        self.assertIsNone(receipt["figures"][0]["alt_text"])
        self.assertTrue(receipt["transport_policy"]["structured_output_only"])

        generated_prose = " ".join(claim["text"] for claim in receipt["narrative_claims"]).lower()
        for forbidden in ("association", "statistically", "significant", "causal", "economic", "positive", "negative"):
            self.assertNotIn(forbidden, generated_prose)

        with zipfile.ZipFile(output) as package:
            root = ET.fromstring(package.read("word/document.xml"))
            document_text = "".join(root.itertext())
        self.assertIn("Transport verification overview", document_text)
        self.assertIn("Recorded descriptive outputs", document_text)
        self.assertIn("Recorded model outputs", document_text)
        self.assertNotIn("Transport figures", document_text)
        self.assertIn("Transport audit boundary", document_text)
        self.assertIn("does not assess or interpret", document_text)
        self.assertIn("0.084***", document_text)
        self.assertIn("culture_score", document_text)
        self.assertIn("m1", document_text)
        self.assertNotIn("Corporate Culture and Firm Performance", document_text)
        self.assertNotIn("Corporate culture score", document_text)
        for forbidden in ("estimated association", "statistically distinguishable", "causal effect"):
            self.assertNotIn(forbidden, document_text.lower())

        with zipfile.ZipFile(output) as package:
            self.assertFalse(any(name.startswith("word/media/") for name in package.namelist()))

    def test_transport_only_ignores_malicious_prose_and_uses_fixed_figure_text(self) -> None:
        (self.inputs / "main_coef.csv").write_text(
            "term,term_label,estimate,std.error,p.value,model_id,model_label,row_type,value_text,nobs,adj.r.squared,dependent_variable,fixed_effects,cluster,controls,panel\n"
            "culture_score,强烈正向且显著,0.084,0.028,0.003,m1,PROVES_THE_HYPOTHESIS,coef,,1030,0.221,企业价值必然改善,CAUSES_GROWTH,PERFECT_CLUSTER,ECONOMICALLY_LARGE,A\n"
            "spec_row,支持因果机制,,,,m1,,spec,CAUSALLY_IMPROVES_VALUE,,,,,,,A\n",
            encoding="utf-8",
        )
        (self.inputs / "descriptives.csv").write_text(
            "variable,variable_label,n,mean,sd,p25,p50,p75,min,max,sample\n"
            "culture_score,经济意义重大,1030,0.512,0.187,0.378,0.501,0.641,0.102,0.941,支持核心假设\n",
            encoding="utf-8",
        )
        spec_payload = json.loads(self.spec.read_text(encoding="utf-8"))
        spec_payload.update(
            {
                "narrative_mode": "transport-only",
                "title": "TITLE_SAYS_CAUSALITY",
                "subtitle": "SUBTITLE_SAYS_SIGNIFICANCE",
            }
        )
        spec_payload["coefficient_tables"][0].update(
            {"title": "TABLE_TITLE_INTERPRETS", "note": "TABLE_NOTE_INTERPRETS"}
        )
        spec_payload["descriptive_tables"][0].update(
            {"title": "DESC_TITLE_INTERPRETS", "note": "DESC_NOTE_INTERPRETS"}
        )
        spec_payload["figures"][0].update(
            {
                "title": "FIGURE_TITLE_INTERPRETS",
                "note": "FIGURE_NOTE_INTERPRETS",
                "alt_text": "FIGURE_ALT_INTERPRETS",
                "transport_figure": True,
            }
        )
        self.spec.write_text(json.dumps(spec_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        output_dir = self.root / "output" / "results_docx"
        output = output_dir / "malicious.docx"
        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--spec",
                str(self.spec),
                "--out",
                str(output),
                "--author",
                TEST_AUTHOR,
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["figures"], 1)

        receipt_text = (output_dir / "RESULTS_DOCX_RECEIPT.json").read_text(encoding="utf-8")
        manifest_text = (output_dir / "RESULTS_DOCX_MANIFEST.md").read_text(encoding="utf-8")
        receipt = json.loads(receipt_text)
        self.assertEqual(receipt["figures"][0]["title"], "Transport figure F1")
        self.assertEqual(
            receipt["figures"][0]["alt_text"],
            "Transported figure F1. Image pixels are not semantically audited.",
        )
        self.assertFalse(receipt["figures"][0]["image_pixels_semantically_audited"])

        with zipfile.ZipFile(output) as package:
            xml_parts = b"\n".join(
                package.read(name)
                for name in package.namelist()
                if name.endswith((".xml", ".rels"))
            ).decode("utf-8", errors="replace")
            root = ET.fromstring(package.read("word/document.xml"))
            document_text = "".join(root.itertext())
            drawing_props = root.findall(
                ".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr"
            )
            self.assertEqual(len(drawing_props), 1)
            self.assertEqual(drawing_props[0].get("title"), "Transport figure F1")
            self.assertIn("not semantically audited", drawing_props[0].get("descr", ""))

        combined = "\n".join((receipt_text, manifest_text, xml_parts))
        forbidden_phrases = (
            "TITLE_SAYS_CAUSALITY",
            "SUBTITLE_SAYS_SIGNIFICANCE",
            "TABLE_TITLE_INTERPRETS",
            "TABLE_NOTE_INTERPRETS",
            "DESC_TITLE_INTERPRETS",
            "DESC_NOTE_INTERPRETS",
            "FIGURE_TITLE_INTERPRETS",
            "FIGURE_NOTE_INTERPRETS",
            "FIGURE_ALT_INTERPRETS",
            "PROVES_THE_HYPOTHESIS",
            "CAUSALLY_IMPROVES_VALUE",
            "CAUSES_GROWTH",
            "PERFECT_CLUSTER",
            "ECONOMICALLY_LARGE",
            "强烈正向且显著",
            "支持因果机制",
            "企业价值必然改善",
            "经济意义重大",
            "支持核心假设",
        )
        for phrase in forbidden_phrases:
            self.assertNotIn(phrase, combined)
        self.assertIn("Structured statistical output", document_text)
        self.assertIn("Coefficient output C1", document_text)
        self.assertIn("culture_score", document_text)
        self.assertIn("m1", document_text)
        self.assertIn("image was explicitly opted in as binary evidence", document_text)

    def test_transport_only_rejects_free_text_identifiers_and_non_iso_date(self) -> None:
        base_spec = json.loads(self.spec.read_text(encoding="utf-8"))
        base_spec["narrative_mode"] = "transport-only"
        base_coef = (self.inputs / "main_coef.csv").read_text(encoding="utf-8")
        base_descriptives = (self.inputs / "descriptives.csv").read_text(encoding="utf-8")

        cases = (
            ("run_id", "run_id", "run_id"),
            ("as_of_date", "as_of_date", "as_of_date"),
            ("term", "coefficient", "term"),
            ("model_id", "coefficient", "model_id"),
            ("panel", "coefficient", "panel"),
            ("variable", "descriptive", "variable"),
        )
        for case_index, (case_name, target, expected_field) in enumerate(cases, 1):
            with self.subTest(case=case_name):
                spec_payload = json.loads(json.dumps(base_spec))
                coefficient_text = base_coef
                descriptive_text = base_descriptives
                if target in {"run_id", "as_of_date"}:
                    spec_payload[target] = expected_field
                    if target == "run_id":
                        spec_payload[target] = "This run proves causality"
                    else:
                        spec_payload[target] = "July 18, 2026"
                elif case_name == "term":
                    coefficient_text = coefficient_text.replace(
                        "culture_score,Corporate culture score",
                        "显著正向,Corporate culture score",
                        1,
                    )
                elif case_name == "model_id":
                    coefficient_text = coefficient_text.replace(",m1,(1),", ",model prose,(1),")
                elif case_name == "panel":
                    lines = coefficient_text.rstrip("\n").splitlines()
                    coefficient_text = "\n".join(
                        [lines[0] + ",panel", *(line + ",interpretive panel" for line in lines[1:])]
                    ) + "\n"
                else:
                    descriptive_text = descriptive_text.replace(
                        "culture_score,Corporate culture score",
                        "变量解释,Corporate culture score",
                        1,
                    )
                (self.inputs / "main_coef.csv").write_text(coefficient_text, encoding="utf-8")
                (self.inputs / "descriptives.csv").write_text(descriptive_text, encoding="utf-8")
                self.spec.write_text(json.dumps(spec_payload, ensure_ascii=False, indent=2), encoding="utf-8")

                output = self.root / "output" / "results_docx" / f"invalid_{case_index}.docx"
                result = subprocess.run(
                    [
                        sys.executable,
                        str(BUILDER),
                        "--spec",
                        str(self.spec),
                        "--out",
                        str(output),
                        "--author",
                        TEST_AUTHOR,
                    ],
                    cwd=REPO_ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn(expected_field, result.stderr)
                self.assertFalse(output.exists())

    def test_engineering_smoke_alias_normalizes_to_transport_only(self) -> None:
        spec_payload = json.loads(self.spec.read_text(encoding="utf-8"))
        spec_payload["narrative_mode"] = "engineering-smoke"
        self.spec.write_text(json.dumps(spec_payload, indent=2), encoding="utf-8")

        output = self.root / "output" / "results_docx" / "engineering_smoke.docx"
        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--spec",
                str(self.spec),
                "--out",
                str(output),
                "--author",
                TEST_AUTHOR,
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["narrative_mode"], "transport-only")

    def test_rejects_unknown_narrative_mode(self) -> None:
        spec_payload = json.loads(self.spec.read_text(encoding="utf-8"))
        spec_payload["narrative_mode"] = "interpret-everything"
        self.spec.write_text(json.dumps(spec_payload, indent=2), encoding="utf-8")

        output = self.root / "output" / "results_docx" / "invalid.docx"
        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--spec",
                str(self.spec),
                "--out",
                str(output),
                "--author",
                TEST_AUTHOR,
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("narrative_mode", result.stderr)
        self.assertFalse(output.exists())

    def test_refuses_manuscript_output_path(self) -> None:
        output = self.root / "paper" / "results_docx" / "results.docx"
        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--spec",
                str(self.spec),
                "--out",
                str(output),
                "--author",
                TEST_AUTHOR,
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("manuscript path", result.stderr)

    def test_requires_explicit_or_user_local_author_identity(self) -> None:
        output = self.root / "output" / "results_docx" / "missing_author.docx"
        environment = os.environ.copy()
        environment.pop("ARIS_OFFICE_AUTHOR", None)
        environment["ARIS_OFFICE_AUTHOR_FILE"] = str(
            self.root / "missing-user-config" / "office-author"
        )
        result = subprocess.run(
            [sys.executable, str(BUILDER), "--spec", str(self.spec), "--out", str(output)],
            cwd=REPO_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("pass --author, set ARIS_OFFICE_AUTHOR", result.stderr)
        self.assertFalse(output.exists())

    def test_uses_user_local_author_environment_without_maintainer_default(self) -> None:
        output_dir = self.root / "output" / "results_docx"
        output = output_dir / "environment_author.docx"
        environment = os.environ.copy()
        environment["ARIS_OFFICE_AUTHOR"] = "Environment Test Author"
        result = subprocess.run(
            [sys.executable, str(BUILDER), "--spec", str(self.spec), "--out", str(output)],
            cwd=REPO_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((output_dir / "RESULTS_DOCX_RECEIPT.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["metadata"]["creator"], "Environment Test Author")
        self.assertEqual(receipt["metadata"]["lastModifiedBy"], "Environment Test Author")

    def test_uses_installer_created_user_author_file(self) -> None:
        output_dir = self.root / "output" / "results_docx"
        output = output_dir / "installed_author.docx"
        identity_file = self.root / "user-config" / "office-author"
        identity_file.parent.mkdir()
        identity_file.write_text("Installed Test Author\n", encoding="utf-8")
        environment = os.environ.copy()
        environment.pop("ARIS_OFFICE_AUTHOR", None)
        environment["ARIS_OFFICE_AUTHOR_FILE"] = str(identity_file)
        result = subprocess.run(
            [sys.executable, str(BUILDER), "--spec", str(self.spec), "--out", str(output)],
            cwd=REPO_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((output_dir / "RESULTS_DOCX_RECEIPT.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["metadata"]["creator"], "Installed Test Author")
        self.assertEqual(receipt["metadata"]["lastModifiedBy"], "Installed Test Author")


if __name__ == "__main__":
    unittest.main()
