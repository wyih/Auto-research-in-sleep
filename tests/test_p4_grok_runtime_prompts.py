from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPT_ROOT = (
    REPO_ROOT
    / ".aris"
    / "business-e2e"
    / "20260718T011517Z"
    / "grok-workspace"
    / "prompts"
)
PROMPTS = {
    "cnrds": PROMPT_ROOT / "p4-cnrds-runtime.md",
    "csmar": PROMPT_ROOT / "p4-csmar-runtime.md",
}


def json_block_after(text: str, marker: str) -> dict[str, object]:
    tail = text.split(marker, 1)[1]
    match = re.search(r"```json\n(.*?)\n```", tail, flags=re.DOTALL)
    if match is None:
        raise AssertionError(f"missing JSON block after {marker!r}")
    value = json.loads(match.group(1))
    if not isinstance(value, dict):
        raise AssertionError("JSON block root must be an object")
    return value


class P4GrokRuntimePromptTests(unittest.TestCase):
    def test_receipt_uses_distinct_planned_and_completed_spec_hashes(self) -> None:
        for site, path in PROMPTS.items():
            with self.subTest(site=site):
                text = path.read_text(encoding="utf-8")
                candidate = json_block_after(
                    text, "The candidate must use this exact semantic shape"
                )
                spec = candidate["DOWNLOAD_SPEC"]
                self.assertIsInstance(spec, dict)
                self.assertEqual(
                    set(spec), {"path", "input_sha256", "completed_sha256"}
                )
                self.assertIn("still-`planned` live spec", text)
                self.assertIn("unchanged completed draft", text)
                self.assertIn("must not contain the receipt hash", text)

    def test_semantic_result_is_external_and_hash_bound_without_self_reference(self) -> None:
        forbidden_top_level = {
            "stage",
            "site",
            "source",
            "runtime",
            "adapter",
            "gate",
            "acceptance_id",
        }
        for site, path in PROMPTS.items():
            with self.subTest(site=site):
                text = path.read_text(encoding="utf-8")
                candidate = json_block_after(
                    text, "The candidate must use this exact semantic shape"
                )
                semantic_pointer = candidate["semantic_verifier"]
                self.assertEqual(
                    set(semantic_pointer),
                    {"mode", "report_path", "report_schema_version"},
                )
                self.assertEqual(
                    semantic_pointer["mode"], "external_hash_bound_report"
                )
                report_name = Path(str(semantic_pointer["report_path"])).name
                self.assertEqual(report_name, f"semantic-extract-{site}.json")
                self.assertNotIn("p4", report_name)
                self.assertNotIn("grok", report_name)

                external = json_block_after(
                    text,
                    "The external semantic report must be independently re-verifiable",
                )
                self.assertFalse(forbidden_top_level.intersection(external))
                self.assertEqual(
                    external["subject"],
                    {"stage": "P4", "site": site, "runtime": "grok"},
                )
                self.assertRegex(
                    str(external["receipt"]["sha256"]), r"receipt_64_hex$"
                )
                self.assertEqual(
                    set(external["DOWNLOAD_SPEC"]),
                    {"path", "input_sha256", "completed_sha256"},
                )
                self.assertIn("never put the external report's hash back", text.lower())

    def test_two_semantic_passes_precede_spec_and_manifest_commit(self) -> None:
        for site, path in PROMPTS.items():
            with self.subTest(site=site):
                text = path.read_text(encoding="utf-8")
                candidate = text.index("Write the complete candidate receipt")
                first_pass = text.index("Require exit 0", candidate)
                final_receipt = text.index("atomically change only the candidate receipt's `status`")
                second_pass = text.index("Run the same semantic-verifier command once more")
                spec_install = text.index("atomically replace the live spec")
                manifest_install = text.index("atomically append the manifest row")
                report_install = text.index(
                    "Finally, atomically create the external semantic report"
                )
                self.assertLess(candidate, first_pass)
                self.assertLess(first_pass, final_receipt)
                self.assertLess(final_receipt, second_pass)
                self.assertLess(second_pass, spec_install)
                self.assertLess(spec_install, manifest_install)
                self.assertLess(manifest_install, report_install)
                self.assertIn("final receipt's SHA-256 is unchanged", text)

    def test_route_specific_and_security_constraints_remain_frozen(self) -> None:
        cnrds = PROMPTS["cnrds"].read_text(encoding="utf-8")
        self.assertIn('tabs --url-contains "cnrds.com"', cnrds)
        self.assertIn("saved_login_submitted", cnrds)
        self.assertIn('"preview_rows": 2', cnrds)
        self.assertIn('"queue_compression_complete": true', cnrds)

        csmar = PROMPTS["csmar"].read_text(encoding="utf-8")
        self.assertIn("https://data.csmar.com/csmar.html#/datacenter/singletable", csmar)
        self.assertIn('tabs --url-contains "csmar.html"', csmar)
        self.assertIn("old chrome-mcp may omit the SPA fragment", csmar)
        self.assertIn("confirm the single-table builder state", csmar)
        self.assertIn('tabs --url-contains "sdownload.html"', csmar)
        self.assertIn('"result_page": {', csmar)
        self.assertIn('"condition": "Typrep=A"', csmar)

        for text in (cnrds, csmar):
            self.assertIn("Never request, inspect, print, or persist credentials", text)
            self.assertIn("Never call `chrome_get_web_content` or `chrome_javascript`", text)
            self.assertIn("Never use an element `ref`", text)


if __name__ == "__main__":
    unittest.main()
