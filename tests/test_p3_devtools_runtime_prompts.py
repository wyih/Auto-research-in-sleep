from __future__ import annotations

import json
import importlib.util
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
    "cnki": PROMPT_ROOT / "p3-cnki-devtools.md",
    "ssrn": PROMPT_ROOT / "p3-ssrn-devtools.md",
    "sciencedirect": PROMPT_ROOT / "p3-sciencedirect-devtools.md",
    "wiley": PROMPT_ROOT / "p3-wiley-devtools.md",
}
ACCEPTOR = REPO_ROOT / "scripts" / "accept_grok_browser_candidate.py"
SPEC_ROOT = PROMPT_ROOT.parent / "acceptance-specs"


def load_acceptor() -> ModuleType:
    spec = importlib.util.spec_from_file_location("p3_prompt_acceptor", ACCEPTOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


acceptor = load_acceptor()


def candidate_block(text: str) -> dict[str, object]:
    blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.DOTALL)
    if len(blocks) != 1:
        raise AssertionError(f"expected one candidate JSON block, got {len(blocks)}")
    value = json.loads(blocks[0])
    if not isinstance(value, dict):
        raise AssertionError("candidate root must be an object")
    return value


class P3DevtoolsRuntimePromptTests(unittest.TestCase):
    def test_exact_adapter_identity_and_candidate_only_boundary(self) -> None:
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
                self.assertEqual(
                    candidate["schema_version"], "aris.grok-browser-candidate.v1"
                )
                self.assertEqual(candidate["runtime"], "grok")
                self.assertEqual(candidate["adapter"], "grok_chrome_devtools_mcp")
                self.assertEqual(candidate["mcp_server"], "browser")
                self.assertEqual(candidate["implementation"], "chrome-devtools-mcp")
                self.assertEqual(candidate["profile_mode"], "dedicated_persistent")
                self.assertEqual(candidate["stage"], "P3")
                self.assertEqual(candidate["site"], site)
                artifact = candidate["artifact"]
                self.assertIsInstance(artifact, dict)
                self.assertEqual(set(artifact), expected_artifact)
                self.assertEqual(artifact["format"], "pdf")
                self.assertIsInstance(artifact["mtime_ns"], str)
                self.assertRegex(artifact["mtime_ns"], r"^[1-9][0-9]*$")
                self.assertEqual(acceptor._validate_candidate(candidate), candidate)
                self.assertIn("external verif", text.lower())
                self.assertIn("do not write a success receipt", text.lower())

    def test_candidate_binds_the_exact_frozen_spec_hash(self) -> None:
        import hashlib

        for site, path in PROMPTS.items():
            with self.subTest(site=site):
                candidate = candidate_block(path.read_text(encoding="utf-8"))
                spec_path = SPEC_ROOT / f"p3-{site}-devtools.json"
                expected = hashlib.sha256(spec_path.read_bytes()).hexdigest()
                self.assertEqual(candidate["acceptance_spec_sha256"], expected)
                self.assertEqual(
                    candidate["artifact"]["path"],
                    json.loads(spec_path.read_text(encoding="utf-8"))["artifact"]["path"],
                )

    def test_only_safe_facade_surface_is_prescribed(self) -> None:
        required = {
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
        forbidden_routes = {
            "chrome_mcp_client.mjs",
            "chrome_read_page",
            "chrome_click_element",
            "chrome_handle_download",
            "get_windows_and_tabs",
            "exact-selector-click",
        }
        for site, path in PROMPTS.items():
            with self.subTest(site=site):
                text = path.read_text(encoding="utf-8")
                for tool in required:
                    self.assertIn(tool, text)
                for route in forbidden_routes:
                    self.assertNotIn(route, text)
                self.assertIn("Raw official tools", text)
                self.assertIn("one-action-only", text)

    def test_security_contract_is_fail_closed_and_not_self_attested(self) -> None:
        for site, path in PROMPTS.items():
            with self.subTest(site=site):
                text = path.read_text(encoding="utf-8")
                candidate = candidate_block(text)
                for forbidden_self_attestation in (
                    "security",
                    "browser_evidence",
                    "target",
                    "status",
                    "gate",
                ):
                    self.assertNotIn(forbidden_self_attestation, candidate)
                self.assertIn("Do not emit raw tool output", text)
                self.assertIn("target_tab_ambiguous", text)
                self.assertIn("destination_collision", text)
                self.assertIn("permits no click retry", text)

    def test_site_specific_challenge_contracts_cover_observed_paths(self) -> None:
        cnki = PROMPTS["cnki"].read_text(encoding="utf-8")
        self.assertIn("fixed\n   rendered-geometry classification", cnki)
        self.assertIn("Hidden, zero-size, offscreen", cnki)
        self.assertIn("is not a challenge", cnki)
        self.assertIn("never click, drag, or\n   solve it", cnki)
        self.assertNotIn("action_time_confirmation: true", cnki)

        ssrn = PROMPTS["ssrn"].read_text(encoding="utf-8")
        ssrn_flat = " ".join(ssrn.split())
        self.assertIn("passive challenge", ssrn)
        self.assertIn("bounded passive phase", ssrn)
        self.assertIn("action-time confirmation", ssrn)
        self.assertIn("challenge token", ssrn_flat)
        self.assertIn("Never retry the checkbox", ssrn_flat)

        for site in ("sciencedirect", "wiley"):
            text = PROMPTS[site].read_text(encoding="utf-8")
            flat = " ".join(text.split())
            with self.subTest(site=site):
                self.assertIn("this invocation carries action-time confirmation", text)
                self.assertIn("challenge token", flat)
                self.assertIn("action_time_confirmation", text)
                self.assertIn("Never retry the checkbox", flat)
                self.assertIn("slider", text)
                self.assertIn("press-and-hold", text)

    def test_sciencedirect_uses_fixed_loaded_pdf_action_not_viewer_toolbar(self) -> None:
        text = PROMPTS["sciencedirect"].read_text(encoding="utf-8")
        flow = text.split("## Browser flow", 1)[1].split("## Candidate output", 1)[0]
        article_click = flow.index("`aris_trigger_element_download` exactly once")
        trigger = flow.index("`aris_trigger_loaded_pdf_download`", article_click)
        wait = flow.index("`aris_download_wait`", trigger)
        copy = flow.index("`aris_copy_download`", wait)
        self.assertLess(article_click, trigger)
        self.assertLess(trigger, wait)
        self.assertLess(wait, copy)
        self.assertIn("inline PDF tab", flow)
        self.assertIn("exposes no programmable JavaScript", " ".join(flow.split()))
        self.assertIn("filename token", " ".join(flow.split()))

    def test_sciencedirect_and_wiley_atomically_snapshot_the_article_click(self) -> None:
        for site in ("sciencedirect", "wiley"):
            with self.subTest(site=site):
                text = PROMPTS[site].read_text(encoding="utf-8")
                flow = text.split("## Browser flow", 1)[1].split(
                    "## Candidate output", 1
                )[0]
                self.assertIn("`aris_trigger_element_download` exactly once", flow)
                self.assertIn("atomically", flow)
                self.assertNotIn("`aris_download_baseline`", flow)

    def test_each_destination_is_runtime_specific_and_inside_run(self) -> None:
        destinations: set[str] = set()
        for site, path in PROMPTS.items():
            candidate = candidate_block(path.read_text(encoding="utf-8"))
            artifact = candidate["artifact"]
            self.assertIsInstance(artifact, dict)
            destination = str(artifact["path"])
            self.assertTrue(destination.startswith(".aris/business-e2e/20260718T011517Z/"))
            self.assertIn("grok-devtools", destination)
            self.assertNotIn(destination, destinations)
            destinations.add(destination)

    def test_wiley_identity_and_wrapper_match_the_live_doi_artifact(self) -> None:
        text = PROMPTS["wiley"].read_text(encoding="utf-8")
        for value in (
            "Corporate culture: The interview evidence",
            "John R. Graham",
            "Jillian A. Grennan",
            "Campbell R. Harvey",
            "Shivaram Rajgopal",
            "historical hash is not a byte-equality",
            "only permitted same-page refresh",
            "persistent login shell",
            "/doi/pdf/",
            "/doi/epdf/",
            "/doi/pdfdirect/",
            "same-origin",
            "no visible\n   reader control",
        ):
            self.assertIn(value, text)
        self.assertNotIn(
            "e147dbb6ce77284830f320354e8d22a3a056ef05eacf6c4970f7a6acb8efe53f",
            text,
        )
        self.assertNotIn("The Value of Corporate Culture", text)

    def test_ssrn_reconciles_live_author_aliases_but_freezes_pdf_identity(self) -> None:
        text = PROMPTS["ssrn"].read_text(encoding="utf-8")
        for value in (
            "Frozen PDF authors",
            "Jillian Popadak",
            "Jillian Grennan",
            "Shivaram Rajgopal",
            "frozen historical author text",
        ):
            self.assertIn(value, text)
        self.assertNotIn("Shiva Rajgopal", text)


if __name__ == "__main__":
    unittest.main()
