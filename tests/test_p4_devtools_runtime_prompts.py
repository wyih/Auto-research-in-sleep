from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path
from types import ModuleType


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
    "csmar": PROMPT_ROOT / "p4-csmar-devtools.md",
    "cnrds": PROMPT_ROOT / "p4-cnrds-devtools.md",
}
SPEC_ROOT = PROMPT_ROOT.parent / "acceptance-specs"
SPECS = {
    site: SPEC_ROOT / f"p4-{site}-devtools.json" for site in PROMPTS
}
ACCEPTOR = REPO_ROOT / "scripts" / "accept_grok_browser_candidate.py"
SAFE_TOOLS = {
    "aris_health",
    "aris_tabs",
    "aris_select",
    "aris_navigate",
    "aris_inspect",
    "aris_click",
    "aris_fill",
    "aris_key",
    "aris_wait",
    "aris_challenge_state",
    "aris_trigger_element_download",
    "aris_trigger_loaded_pdf_download",
    "aris_download_baseline",
    "aris_download_wait",
    "aris_copy_download",
}


def candidate_block(text: str) -> dict[str, object]:
    blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.DOTALL)
    if len(blocks) != 1:
        raise AssertionError(f"expected one candidate JSON block, got {len(blocks)}")
    value = json.loads(blocks[0])
    if not isinstance(value, dict):
        raise AssertionError("candidate root must be an object")
    return value


def load_acceptor() -> ModuleType:
    spec = importlib.util.spec_from_file_location("p4_prompt_acceptor", ACCEPTOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


acceptor = load_acceptor()


class P4DevtoolsRuntimePromptTests(unittest.TestCase):
    def test_prompt_candidates_are_bound_to_the_exact_frozen_specs(self) -> None:
        for site, prompt_path in PROMPTS.items():
            with self.subTest(site=site):
                candidate = candidate_block(prompt_path.read_text(encoding="utf-8"))
                spec_bytes = SPECS[site].read_bytes()
                spec = json.loads(spec_bytes)
                self.assertEqual(
                    candidate["acceptance_spec_sha256"],
                    hashlib.sha256(spec_bytes).hexdigest(),
                )
                self.assertEqual(spec["stage"], "P4")
                self.assertEqual(spec["site"], site)
                self.assertEqual(spec["artifact"]["path"], candidate["artifact"]["path"])
                self.assertEqual(spec["artifact"]["format"], "zip")

    def test_frozen_exact_rows_match_the_verified_business_slices(self) -> None:
        cnrds = json.loads(SPECS["cnrds"].read_text(encoding="utf-8"))["p4"]
        self.assertEqual(cnrds["archive_member"], "上市公司专利申请情况.csv")
        self.assertEqual(cnrds["min_rows"], 3)  # description row plus two business rows
        self.assertEqual(
            cnrds["exact_rows"],
            [
                {
                    "Scode": "000001",
                    "Year": "2020",
                    "Ftyp": "集团公司合计",
                    "Aplctm": "上市后",
                    "Invia": "272",
                    "Umia": "1",
                    "Desia": "39",
                    "Invja": "0",
                    "Umja": "0",
                    "Desja": "0",
                },
                {
                    "Scode": "000001",
                    "Year": "2020",
                    "Ftyp": "上市公司本身",
                    "Aplctm": "上市后",
                    "Invia": "272",
                    "Umia": "1",
                    "Desia": "39",
                    "Invja": "0",
                    "Umja": "0",
                    "Desja": "0",
                },
            ],
        )

        csmar = json.loads(SPECS["csmar"].read_text(encoding="utf-8"))["p4"]
        self.assertEqual(csmar["archive_member"], "FS_Combas.csv")
        self.assertEqual(csmar["min_rows"], 1)
        self.assertEqual(
            csmar["exact_rows"],
            [
                {
                    "Stkcd": "000001",
                    "ShortName": "平安银行",
                    "Accper": "2020-12-31",
                    "Typrep": "A",
                    "A001000000": "4468514000000.00",
                }
            ],
        )

    def test_candidate_uses_frozen_external_acceptor_schema(self) -> None:
        expected_top_level = {
            "schema_version",
            "runtime",
            "adapter",
            "mcp_server",
            "implementation",
            "profile_mode",
            "stage",
            "site",
            "acceptance_spec_sha256",
            "artifact",
        }
        expected_artifact = {"path", "format", "size_bytes", "mtime_ns", "sha256"}

        for site, path in PROMPTS.items():
            with self.subTest(site=site):
                text = path.read_text(encoding="utf-8")
                candidate = candidate_block(text)
                self.assertEqual(set(candidate), expected_top_level)
                self.assertEqual(candidate["schema_version"], "aris.grok-browser-candidate.v1")
                self.assertEqual(candidate["runtime"], "grok")
                self.assertEqual(candidate["adapter"], "grok_chrome_devtools_mcp")
                self.assertEqual(candidate["mcp_server"], "browser")
                self.assertEqual(candidate["implementation"], "chrome-devtools-mcp")
                self.assertEqual(candidate["profile_mode"], "dedicated_persistent")
                self.assertEqual(candidate["stage"], "P4")
                self.assertEqual(candidate["site"], site)
                self.assertRegex(str(candidate["acceptance_spec_sha256"]), r"\A[0-9a-f]{64}\Z")

                artifact = candidate["artifact"]
                self.assertIsInstance(artifact, dict)
                self.assertEqual(set(artifact), expected_artifact)
                self.assertEqual(artifact["format"], "zip")
                self.assertGreater(int(artifact["size_bytes"]), 0)
                self.assertIsInstance(artifact["mtime_ns"], str)
                self.assertRegex(artifact["mtime_ns"], r"\A[1-9][0-9]*\Z")
                self.assertRegex(str(artifact["sha256"]), r"\A[0-9a-f]{64}\Z")
                self.assertTrue(
                    str(artifact["path"]).startswith(
                        f".aris/business-e2e/20260718T011517Z/cn-data/raw/{site}/2026-07-18_grok_v1/"
                    )
                )

                # The documented template is structurally valid for the exact
                # frozen acceptor. Runtime instructions require replacing every
                # otherwise-valid sentinel with observed values.
                self.assertEqual(acceptor._validate_candidate(candidate), candidate)
                self.assertIn("sentinels", text)
                self.assertIn("if any sentinel", text)

    def test_only_safe_facade_and_dedicated_profile_are_allowed(self) -> None:
        forbidden_routes = {
            "chrome_mcp_client.mjs",
            "chrome_read_page",
            "chrome_click_element",
            "chrome_handle_download",
            "chrome_javascript",
            "evaluate_script",
            "list_pages",
            "take_snapshot",
            "exact-selector-click",
        }
        for site, path in PROMPTS.items():
            with self.subTest(site=site):
                text = path.read_text(encoding="utf-8")
                for tool in SAFE_TOOLS:
                    self.assertIn(tool, text)
                for route in forbidden_routes:
                    self.assertNotIn(route, text)
                self.assertIn("Raw official tools", text)
                self.assertIn("dedicated_persistent", text)
                self.assertIn("one-action-only", text)
                self.assertIn("immediately preceding inspection", text)
                self.assertIn("never mix references from two inspections", text)
                self.assertIn("the intended action the very next tool call", text)
                self.assertIn("repeat the final targeted-inspect/action pair", text)
                self.assertIn("arbitrary browser JavaScript", text)
                self.assertIn("shell commands", text)
                self.assertIn("web search/fetch", text)

    def test_download_is_atomically_armed_and_clicked_then_waited_and_copied(self) -> None:
        for site, path in PROMPTS.items():
            with self.subTest(site=site):
                text = path.read_text(encoding="utf-8")
                portal_flow = text.split("## Portal sequence", 1)[1].split(
                    "## Candidate output", 1
                )[0]
                trigger = portal_flow.index("aris_trigger_element_download")
                wait = portal_flow.index("aris_download_wait", trigger)
                copy = portal_flow.index("aris_copy_download", wait)
                self.assertLess(trigger, wait)
                self.assertLess(wait, copy)
                self.assertNotIn("aris_download_baseline", portal_flow)
                self.assertIn("atomically snapshot", portal_flow)
                self.assertIn("exactly once", portal_flow)
                self.assertIn("permits no click retry", portal_flow)
                self.assertIn("positive `size_bytes`", portal_flow)
                self.assertIn("decimal-string `mtime_ns`", portal_flow)
                self.assertIn("64-hex `sha256`", portal_flow)

    def test_date_entry_requires_non_echoing_fill_and_commit_proofs(self) -> None:
        required = {
            "value_confirmation_available=true",
            "value_matches_supplied=true",
            "value_matches_last_fill_before_key",
            "value_matches_last_fill_after_key",
            "never request or print the raw observed",
        }
        for site, path in PROMPTS.items():
            with self.subTest(site=site):
                text = path.read_text(encoding="utf-8")
                for marker in required:
                    self.assertIn(marker, text)

    def test_csmar_overlay_is_observed_and_dismissed_at_most_once(self) -> None:
        text = PROMPTS["csmar"].read_text(encoding="utf-8")
        self.assertIn("inspect once for any visible modal", text)
        self.assertIn("dismiss its ordinary close", text)
        self.assertIn("portal_overlay_recurred", text)
        self.assertIn("never click it a second time", text)

    def test_csmar_reset_and_field_selection_order_is_deterministic(self) -> None:
        text = PROMPTS["csmar"].read_text(encoding="utf-8")
        table = text.index("verify table ID `FS_Combas`")
        reset = text.index("global `重置` exactly once")
        dates = text.index("Set and commit each date separately")
        self.assertLess(table, reset)
        self.assertLess(reset, dates)
        for marker in (
            "已选：4/154",
            "This is the only permitted global reset",
            "From this point onward, `重置` is forbidden",
            "000001（平安银行）",
            "已选代码 [1] 个",
            "Do not click `全选`",
            "请输入关键字进行字段搜索",
            "资产总计",
            "已选：5/154",
        ):
            self.assertIn(marker, text)

    def test_browser_run_cannot_write_business_acceptance(self) -> None:
        exact_rule = "Do not write a success receipt, manifest, or root-verifier result."
        for site, path in PROMPTS.items():
            with self.subTest(site=site):
                text = path.read_text(encoding="utf-8")
                self.assertIn(exact_rule, text)
                self.assertIn("external acceptor", text)
                self.assertIn("alone writes the candidate", text)
                self.assertNotIn('"status": "passed"', text)

    def test_csmar_contract_is_frozen(self) -> None:
        text = PROMPTS["csmar"].read_text(encoding="utf-8")
        for value in (
            "FS_Combas",
            "000001",
            "2020-12-31",
            "Typrep=A",
            "Stkcd",
            "ShortName",
            "Accper",
            "Typrep",
            "A001000000",
            "exactly one real row",
            "本地保存数据",
            "sdownload.html",
            "filename token `资产负债表`",
            "result_summary_mismatch",
        ):
            self.assertIn(value, text)

    def test_cnrds_contract_and_saved_login_are_frozen(self) -> None:
        text = PROMPTS["cnrds"].read_text(encoding="utf-8")
        for value in (
            "https://www.cnrds.com/Home/Index#/FeaturedDatabase/DB/CIRD/",
            "创新专利研究 (CIRD)",
            "上市公司专利申请与获得",
            "上市公司专利申请情况",
            "2020-01-01",
            "2020-12-31",
            "Scode",
            "Year",
            "Ftyp",
            "Aplctm",
            "Invia",
            "Umia",
            "Desia",
            "Invja",
            "Umja",
            "Desja",
            "exactly two real rows",
            "上市公司本身",
            "集团公司合计",
            "压缩完成",
            "https://www.cnrds.com/",
            "filename token `.zip`",
        ):
            self.assertIn(value, text)
        self.assertIn("one ordinary saved-login submission", text)
        self.assertIn("does not expose autofilled credential values", text)
        self.assertIn("Do not read, copy, print, or type either", text)
        self.assertIn("Do not inspect password-manager UI", text)
        self.assertIn("do not retry login", text)
        self.assertIn("user-verified direct route", text)
        self.assertIn("Never put", text)
        self.assertIn("the URL's `#` fragment into `aris_tabs`", text)
        self.assertIn("keep that deeper route", text)
        self.assertIn("First call `aris_tabs` with the query-free filter `/ViewName/`", text)
        self.assertIn("Do not begin with a broad `cnrds.com`", text)


if __name__ == "__main__":
    unittest.main()
