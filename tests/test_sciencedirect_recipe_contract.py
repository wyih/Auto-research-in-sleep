from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LIT_SKILL = REPO_ROOT / "skills" / "business-lit-review" / "SKILL.md"
DISCOVERY = (
    REPO_ROOT
    / "skills"
    / "business-lit-review"
    / "references"
    / "sciencedirect-discovery.md"
)
FULLTEXT = (
    REPO_ROOT
    / "skills"
    / "fulltext-acquire"
    / "references"
    / "sciencedirect.md"
)


class ScienceDirectRecipeContractTests(unittest.TestCase):
    def test_discovery_reference_is_routed_and_has_bounded_search_fields(self) -> None:
        skill = LIT_SKILL.read_text(encoding="utf-8")
        text = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn("references/sciencedirect-discovery.md", skill)
        for parameter in (
            "`qs`",
            "`tak`",
            "`title`",
            "`authors`",
            "`pub`",
            "`date`",
            "`volume`",
            "`issue`",
            "`page`",
            "`docId`",
            "`affiliations`",
            "`references`",
        ):
            self.assertIn(parameter, text)
        self.assertIn("bounded hit list", text)
        self.assertIn("session-bound PDF", text)

    def test_pagination_and_journal_routes_are_explicit_but_fail_closed(self) -> None:
        text = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn("offset=(n-1)*show", text)
        for size in ("`25`", "`50`", "`100`"):
            self.assertIn(size, text)
        self.assertIn("`sortBy=date`", text)
        for route in (
            "/journal/<official-slug>/issues",
            "/journal/<official-slug>/vol/<volume>/issue/<issue>",
            "/journal/<official-slug>/about/editorial-board",
            "/journal/<official-slug>/about/insights",
        ):
            self.assertIn(route, text)
        self.assertIn("do not derive it by lowercasing", text)

    def test_metadata_and_export_never_substitute_for_verified_fulltext(self) -> None:
        text = DISCOVERY.read_text(encoding="utf-8")
        for field in (
            "affiliations",
            "abstract",
            "highlights",
            "keywords",
            "section headings",
            "DOI and PII",
        ):
            self.assertIn(field, text)
        self.assertIn("must not populate sample construction", text)
        self.assertIn("outside the P1–P5 acceptance chain", text)
        self.assertIn("do not mutate Zotero", text)
        self.assertIn("Route a needed paper to `fulltext-acquire`", text)

    def test_site_recipes_are_runtime_neutral_and_loaded_pdf_is_verified(self) -> None:
        text = DISCOVERY.read_text(encoding="utf-8") + FULLTEXT.read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "mcp__chrome-devtools__",
            "evaluate_script",
            "initScript",
            "window.location.href",
            "AutomationControlled",
        ):
            self.assertNotIn(forbidden, text)
        self.assertIn("`application/pdf`", text)
        self.assertIn("bounded\n   fixed loaded-PDF download action", text)
        self.assertIn("Verify PDF integrity and identity", text)


if __name__ == "__main__":
    unittest.main()
