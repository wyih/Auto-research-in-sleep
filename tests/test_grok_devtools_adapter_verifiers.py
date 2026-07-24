from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


root_verifier = _load_module(
    "business_e2e_for_devtools_adapter_tests",
    REPO_ROOT / "scripts" / "verify_business_e2e.py",
)
cn_extract_tests = _load_module(
    "cn_extract_fixture_for_devtools_adapter_tests",
    REPO_ROOT / "tests" / "test_cn_extract_verifier.py",
)


DEVTOOLS_BINDINGS = {
    "mcp_server": "browser",
    "implementation": "chrome-devtools-mcp",
    "profile_mode": "dedicated_persistent",
}
EGO_LITE_BINDINGS = {
    "mcp_server": "none",
    "implementation": "ego-browser",
    "profile_mode": "shared_login_isolated_task_space",
    "task_space_isolated": True,
}


class RootBrowserAdapterVerifierTests(unittest.TestCase):
    def _browser_gate(
        self,
        stage: str,
        adapter: str,
        bindings: dict[str, object] | None = None,
    ) -> Any:
        site = "cnki" if stage == "P3" else "csmar"
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            run = repo / ".aris" / "business-e2e" / "run"
            receipt_path = run / "receipts" / f"{stage.lower()}-{site}-grok.json"
            receipt_path.parent.mkdir(parents=True)
            data: dict[str, object] = {
                "runtime": "grok",
                "stage": stage,
                "site": site,
                "status": "passed",
                "adapter": adapter,
                "artifact": {
                    "path": "unused-by-patched-artifact-check",
                    "sha256": "a" * 64,
                    "size_bytes": 1,
                },
            }
            if bindings:
                data.update(bindings)
            if stage == "P4":
                data.update(
                    {
                        "download_transport": {"ui_export_completed": True},
                        "portal_evidence": {"preview_rows": 1},
                    }
                )
            receipt = root_verifier.Receipt(receipt_path, data)
            passing = root_verifier.Check("fixture", "PASS", "isolated adapter fixture")
            context = root_verifier.Context(repo_root=repo, run_dir=run)
            with ExitStack() as stack:
                stack.enter_context(
                    mock.patch.object(root_verifier, "_candidate_receipts", return_value=[receipt])
                )
                stack.enter_context(
                    mock.patch.object(root_verifier, "_verify_artifact", return_value=passing)
                )
                stack.enter_context(
                    mock.patch.object(root_verifier, "_manifest_check", return_value=passing)
                )
                stack.enter_context(
                    mock.patch.object(
                        root_verifier, "_p4_semantic_extract_check", return_value=passing
                    )
                )
                return root_verifier._browser_gate(context, stage, site, "grok")

    def test_devtools_adapter_is_a_grok_runtime_identity(self) -> None:
        self.assertEqual(
            root_verifier._normalize_runtime({"adapter": "grok_chrome_devtools_mcp"}),
            "grok",
        )

    def test_devtools_adapter_passes_p3_and_p4_with_exact_bindings(self) -> None:
        for stage in ("P3", "P4"):
            with self.subTest(stage=stage):
                gate = self._browser_gate(
                    stage, "grok_chrome_devtools_mcp", DEVTOOLS_BINDINGS
                )
                self.assertEqual(gate.status, "PASS", [check.summary for check in gate.checks])

    def test_ego_lite_adapter_passes_grok_p3_and_p4_with_isolated_space(self) -> None:
        for stage in ("P3", "P4"):
            with self.subTest(stage=stage):
                gate = self._browser_gate(
                    stage, "ego_lite_task_space", EGO_LITE_BINDINGS
                )
                self.assertEqual(gate.status, "PASS", [check.summary for check in gate.checks])

    def test_ego_lite_adapter_fails_without_isolated_space(self) -> None:
        for stage in ("P3", "P4"):
            with self.subTest(stage=stage):
                bindings = dict(EGO_LITE_BINDINGS)
                bindings["task_space_isolated"] = False
                gate = self._browser_gate(stage, "ego_lite_task_space", bindings)
                self.assertEqual(gate.status, "FAIL")
                self.assertTrue(
                    any(
                        "ego lite isolated task space" in check.name
                        and check.status == "FAIL"
                        for check in gate.checks
                    )
                )

    def test_devtools_adapter_fails_p3_and_p4_for_each_missing_or_wrong_binding(self) -> None:
        for stage in ("P3", "P4"):
            for field in DEVTOOLS_BINDINGS:
                for mutation in ("missing", "wrong"):
                    with self.subTest(stage=stage, field=field, mutation=mutation):
                        bindings: dict[str, object] = dict(DEVTOOLS_BINDINGS)
                        if mutation == "missing":
                            bindings.pop(field)
                        else:
                            bindings[field] = f"wrong-{field}"
                        gate = self._browser_gate(
                            stage, "grok_chrome_devtools_mcp", bindings
                        )
                        self.assertEqual(gate.status, "FAIL")
                        failed = {check.name for check in gate.checks if check.status == "FAIL"}
                        self.assertIn(
                            f"{stage}_{'CNKI' if stage == 'P3' else 'CSMAR'} "
                            f"adapter binding:{field}",
                            failed,
                        )

    def test_legacy_grok_adapter_keeps_its_field_contract_for_p3_and_p4(self) -> None:
        for stage in ("P3", "P4"):
            with self.subTest(stage=stage):
                gate = self._browser_gate(stage, "grok_chrome_mcp")
                self.assertEqual(gate.status, "PASS", [check.summary for check in gate.checks])
                self.assertFalse(
                    any("adapter binding:" in check.name for check in gate.checks),
                    "legacy receipts must not acquire DevTools-only required fields",
                )

    def test_unknown_grok_adapter_fails_closed_in_p3_and_p4(self) -> None:
        for stage in ("P3", "P4"):
            with self.subTest(stage=stage):
                gate = self._browser_gate(
                    stage, "grok_chrome_devtools_mcp_unknown", DEVTOOLS_BINDINGS
                )
                self.assertEqual(gate.status, "FAIL")
                adapter_check = next(
                    check for check in gate.checks if check.name.endswith(" adapter")
                )
                self.assertEqual(adapter_check.status, "FAIL")


class CNExtractAdapterVerifierTests(unittest.TestCase):
    def _fixture(self, folder: str, site: str) -> Any:
        fixture = cn_extract_tests.ExtractFixture(Path(folder), site, "grok")
        payload = fixture.payload()
        payload.update(
            {
                "adapter": "grok_chrome_devtools_mcp",
                **DEVTOOLS_BINDINGS,
            }
        )
        fixture.write_payload(payload)
        return fixture

    def test_p4_extract_verifier_accepts_devtools_adapter_for_both_sites(self) -> None:
        for site in ("cnrds", "csmar"):
            with self.subTest(site=site), tempfile.TemporaryDirectory() as folder:
                report = self._fixture(folder, site).verify()
                self.assertTrue(report.ok, [check for check in report.checks if not check.ok])

    def test_p4_extract_verifier_requires_each_exact_top_level_binding(self) -> None:
        for field in DEVTOOLS_BINDINGS:
            for mutation in ("missing", "wrong", "nested_only"):
                with self.subTest(field=field, mutation=mutation), tempfile.TemporaryDirectory() as folder:
                    fixture = self._fixture(folder, "csmar")
                    payload = fixture.payload()
                    if mutation == "wrong":
                        payload[field] = f"wrong-{field}"
                    else:
                        payload.pop(field)
                        if mutation == "nested_only":
                            payload["adapter_provenance"] = dict(DEVTOOLS_BINDINGS)
                    fixture.write_payload(payload)
                    report = fixture.verify()
                    self.assertFalse(report.ok)
                    failed = {check.name for check in report.checks if not check.ok}
                    self.assertIn(f"runtime adapter binding:{field}", failed)

    def test_p4_extract_verifier_preserves_legacy_adapter_without_new_bindings(self) -> None:
        for site in ("cnrds", "csmar"):
            with self.subTest(site=site), tempfile.TemporaryDirectory() as folder:
                fixture = cn_extract_tests.ExtractFixture(Path(folder), site, "grok")
                report = fixture.verify()
                self.assertTrue(report.ok, [check for check in report.checks if not check.ok])
                self.assertFalse(any("adapter binding:" in check.name for check in report.checks))

    def test_p4_extract_verifier_rejects_unknown_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = self._fixture(folder, "cnrds")
            payload = fixture.payload()
            payload["adapter"] = "grok_chrome_devtools_mcp_unknown"
            fixture.write_payload(payload)
            report = fixture.verify()

        self.assertFalse(report.ok)
        failed = {check.name for check in report.checks if not check.ok}
        self.assertIn("runtime adapter", failed)

    def test_devtools_csmar_cannot_fall_back_to_legacy_result_summary(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fixture = self._fixture(folder, "csmar")
            payload = fixture.payload()
            portal = payload["portal_evidence"]
            assert isinstance(portal, dict)
            portal.pop("result_page")
            fixture.write_payload(payload)
            report = fixture.verify()

        self.assertFalse(report.ok)
        failed = {check.name for check in report.checks if not check.ok}
        self.assertIn("CSMAR structured result-page reconciliation", failed)


if __name__ == "__main__":
    unittest.main()
