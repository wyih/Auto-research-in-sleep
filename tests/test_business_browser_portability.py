from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS = REPO_ROOT / "skills"


def read_tree(root: Path) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.md")))


class BusinessBrowserPortabilityTests(unittest.TestCase):
    def test_business_site_consumers_do_not_call_runtime_tools_directly(self) -> None:
        consumers = [
            SKILLS / "fulltext-acquire",
            SKILLS / "method-harvest",
            SKILLS / "cn-data-bridge",
        ]
        forbidden = (
            "mcp__chrome-devtools__",
            "navigate_page",
            "evaluate_script",
            "chrome_navigate",
            "chrome_read_page",
            "chrome_handle_download",
            "get_windows_and_tabs",
        )
        failures: list[str] = []
        for root in consumers:
            text = read_tree(root)
            for token in forbidden:
                if token in text:
                    failures.append(f"{root.name}: {token}")
        self.assertEqual(failures, [])

    def test_protected_site_consumers_route_through_bridge(self) -> None:
        fulltext = (SKILLS / "fulltext-acquire" / "SKILL.md").read_text(encoding="utf-8")
        cn_data = (SKILLS / "cn-data-bridge" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("browser-session-bridge", fulltext)
        self.assertIn("browser-session-bridge", cn_data)

    def test_method_harvest_is_extraction_only(self) -> None:
        text = read_tree(SKILLS / "method-harvest")
        self.assertIn("invoke `fulltext-acquire`", text)
        self.assertNotRegex(text, re.compile(r"\b(?:cnki|sd)-(?:search|download|paper-detail)\b"))
        self.assertNotIn("Browser requirement", text)

    def test_codex_and_grok_adapters_are_partitioned(self) -> None:
        adapters = SKILLS / "browser-session-bridge" / "references"
        codex = (adapters / "codex-chrome.md").read_text(encoding="utf-8")
        devtools = (adapters / "grok-chrome-devtools-mcp.md").read_text(
            encoding="utf-8"
        )
        legacy = (adapters / "grok-chrome-mcp.md").read_text(encoding="utf-8")
        self.assertIn("chrome:control-chrome", codex)
        self.assertNotIn("chrome-mcp", codex)
        self.assertIn("chrome-devtools-mcp", devtools)
        self.assertIn("dedicated_persistent", devtools)
        self.assertNotIn("chrome:control-chrome", devtools)
        self.assertIn("chrome-mcp", legacy)
        self.assertNotIn("chrome:control-chrome", legacy)

    def test_devtools_adapter_requires_bounded_facade(self) -> None:
        adapter = (
            SKILLS
            / "browser-session-bridge"
            / "references"
            / "grok-chrome-devtools-mcp.md"
        ).read_text(encoding="utf-8")
        for tool in (
            "aris_tabs",
            "aris_select",
            "aris_inspect",
            "aris_click",
            "aris_trigger_element_download",
            "aris_trigger_loaded_pdf_download",
            "aris_download_baseline",
            "aris_download_wait",
            "aris_copy_download",
        ):
            self.assertIn(tool, adapter)
        for forbidden in (
            "evaluate_script",
            "initScript",
            "take_heapsnapshot",
            "list_network_requests",
        ):
            self.assertIn(forbidden, adapter)
        self.assertIn("action-time confirmation", adapter)
        self.assertIn("fallback_directory_increment", adapter)

    def test_acceptance_requires_separate_runtime_receipts(self) -> None:
        acceptance = (REPO_ROOT / "docs" / "BUSINESS_RESEARCH_E2E_ACCEPTANCE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("adapter = codex_native_chrome", acceptance)
        self.assertIn("adapter = grok_chrome_devtools_mcp", acceptance)
        self.assertIn("adapter = grok_chrome_mcp", acceptance)
        self.assertIn("Full chain", acceptance)

    def test_challenge_and_download_fallback_rules_cover_observed_edge_cases(self) -> None:
        contract = (SKILLS / "shared-references" / "browser-session-contract.md").read_text(
            encoding="utf-8"
        )
        cnki = (SKILLS / "fulltext-acquire" / "references" / "cnki.md").read_text(
            encoding="utf-8"
        )
        ssrn = (SKILLS / "fulltext-acquire" / "references" / "ssrn.md").read_text(
            encoding="utf-8"
        )
        sciencedirect = (
            SKILLS / "fulltext-acquire" / "references" / "sciencedirect.md"
        ).read_text(encoding="utf-8")
        wiley = (SKILLS / "fulltext-acquire" / "references" / "wiley.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("viewport", contract)
        self.assertIn("fallback_directory_increment", contract)
        self.assertIn("y=-1000000", cnki)
        self.assertIn("#tcaptcha_transform_dy", cnki)
        self.assertIn("#tCaptchaDyMainWrap", cnki)
        self.assertIn("non-zero width and height", cnki)
        self.assertIn("intersects the current viewport on both axes", cnki)
        self.assertIn("actually blocks the intended", cnki)
        self.assertIn("non-negative top coordinate alone is insufficient", cnki)
        self.assertIn("completes automatically without a click", ssrn)
        self.assertIn("ordinary checkbox", ssrn)
        self.assertIn("action-time confirmation", ssrn)
        self.assertIn("action-time confirmation", sciencedirect)
        self.assertIn("/doi/pdf/<DOI>", wiley)
        self.assertIn("/doi/epdf/<DOI>", wiley)
        self.assertIn("/doi/pdfdirect/<DOI>", wiley)
        self.assertIn("exactly once", wiley)
        self.assertIn("Never create a refresh loop", wiley)
        self.assertIn("fixed loaded-PDF/wrapper action", wiley)
        self.assertIn("fallback_directory_increment", wiley)

    def test_cnki_recipe_preserves_bounded_discovery_and_artifact_acceptance(self) -> None:
        cnki = (SKILLS / "fulltext-acquire" / "references" / "cnki.md").read_text(
            encoding="utf-8"
        )

        for field in (
            "`sequence`",
            "`title`",
            "`authors`",
            "`source`",
            "`date`",
            "`database_type`",
            "`citations`",
            "`downloads`",
            "`online_first`",
        ):
            self.assertIn(field, cnki)

        for dimension in (
            "Search field",
            "Author affiliation",
            "Journal/source",
            "Date range",
            "Source categories",
            "SCI, EI, 北大核心, CSSCI, or CSCD",
        ):
            self.assertIn(dimension, cnki)

        for operation in (
            "Pagination And Sorting",
            "relevance",
            "publication date",
            "citation count",
            "download count",
            "comprehensive rank",
        ):
            self.assertIn(operation, cnki)

        for detail_field in (
            "`affiliations`",
            "`abstract`",
            "`keywords`",
            "`fund`",
            "`classification`",
            "`publication_info`",
            "`citation_network`",
        ):
            self.assertIn(detail_field, cnki)

        for acceptance_rule in (
            "snapshot the approved landing directory",
            "stable non-zero size",
            "PDF magic",
            "EOF",
            "SHA-256",
            "runtime receipt",
            "CAJ is not a PDF fallback",
        ):
            self.assertIn(acceptance_rule, cnki)

        self.assertIn("must be revalidated", cnki)
        self.assertIn("Never export browser session material", cnki)
        self.assertIn("Never reuse result references from the prior page", cnki)
        for forbidden in (
            "mcp__chrome-devtools__",
            "evaluate_script",
            "document.cookie",
            "Cookie:",
            "urllib.request",
            "fetch(",
        ):
            self.assertNotIn(forbidden, cnki)

    def test_saved_login_submit_is_narrow_and_never_reads_credentials(self) -> None:
        contract = (SKILLS / "shared-references" / "browser-session-contract.md").read_text(
            encoding="utf-8"
        )
        bridge = (SKILLS / "browser-session-bridge" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        cn_data = (SKILLS / "cn-data-bridge" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("auth.submit_saved", contract)
        self.assertIn("do not read form values", contract)
        self.assertIn("saved_login_submitted", contract)
        self.assertIn("saved_login_submitted", bridge)
        self.assertIn("one-time submit", bridge)
        self.assertIn("Chrome has already filled", cn_data)
        for text in (contract, bridge, cn_data):
            self.assertIn("hard CAPTCHA", text)

    def test_csmar_recipe_covers_real_two_stage_download_and_filter_commit(self) -> None:
        recipe = (
            SKILLS / "cn-data-bridge" / "references" / "cnrds-csmar-adapters.md"
        ).read_text(encoding="utf-8")
        self.assertIn("sdownload.html", recipe)
        self.assertIn("本地保存数据", recipe)
        self.assertIn("Typrep = A", recipe)
        self.assertIn("silently revert", recipe)
        self.assertIn("inner CSV", recipe)

    def test_soft_timeout_recovery_precedes_login_or_access_gap(self) -> None:
        contract = (SKILLS / "shared-references" / "browser-session-contract.md").read_text(
            encoding="utf-8"
        )
        bridge = (SKILLS / "browser-session-bridge" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        cn_data = (SKILLS / "cn-data-bridge" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        recipe = (
            SKILLS / "cn-data-bridge" / "references" / "cnrds-csmar-adapters.md"
        ).read_text(encoding="utf-8")
        codex = (
            SKILLS / "browser-session-bridge" / "references" / "codex-chrome.md"
        ).read_text(encoding="utf-8")
        grok = (
            SKILLS
            / "browser-session-bridge"
            / "references"
            / "grok-chrome-devtools-mcp.md"
        ).read_text(encoding="utf-8")

        self.assertIn("auth.recover_soft_timeout", contract)
        self.assertIn("dismiss_refresh_restored", contract)
        self.assertIn("close → single refresh → re-inspect", cn_data)
        self.assertIn("top-right `×`", recipe)
        self.assertIn("do **not** click **重新登录**", recipe)
        self.assertLess(
            recipe.index("Soft-Timeout Recovery"),
            recipe.index("Operator Sequence", recipe.index("## CSMAR Adapter")),
        )
        for text in (bridge, codex, grok):
            self.assertIn("recover_soft_timeout", text)
            self.assertIn("reload", text.lower())


if __name__ == "__main__":
    unittest.main()
