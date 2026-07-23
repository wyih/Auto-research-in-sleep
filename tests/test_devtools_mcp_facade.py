from __future__ import annotations

import json
import hashlib
import os
import select
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FACADE = (
    REPO_ROOT
    / "skills"
    / "browser-session-bridge"
    / "scripts"
    / "devtools_mcp_facade.mjs"
)
FAKE_CHILD = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "devtools_mcp_facade"
    / "fake_child.mjs"
)

PUBLIC_TOOL_NAMES = {
    "aris_health",
    "aris_tabs",
    "aris_select",
    "aris_navigate",
    "aris_inspect",
    "aris_click",
    "aris_fill",
    "aris_upload_file",
    "aris_key",
    "aris_wait",
    "aris_challenge_state",
    "aris_trigger_element_download",
    "aris_trigger_loaded_pdf_download",
    "aris_download_baseline",
    "aris_download_wait",
    "aris_copy_download",
    "aris_release",
}

FORBIDDEN_CHILD_TOOLS = {
    "evaluate_script",
    "fill_form",
    "drag",
    "upload_file",
    "list_network_requests",
    "take_memory_snapshot",
}


class FacadeProcess:
    def __init__(
        self,
        root: Path,
        *,
        browser_url: str | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> None:
        self.root = root
        self.home = root / "home"
        self.downloads = self.home / "Downloads"
        self.workspace = root / "workspace"
        self.log_path = root / "child.jsonl"
        self.downloads.mkdir(parents=True)
        (self.workspace / ".aris").mkdir(parents=True)
        if browser_url is not None:
            parsed_port = int(browser_url.rsplit(":", 1)[1])
            config_file = (
                self.home
                / ".config"
                / "agent-skills"
                / "my-agent-browser"
                / "config.json"
            )
            config_file.parent.mkdir(parents=True)
            config_file.write_text(
                json.dumps(
                    {
                        "browser": {
                            "userDataDir": str(config_file.parent / "user-data"),
                            "debuggingPort": parsed_port,
                            "browserUrl": browser_url,
                            "lazyStart": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.home),
                "ARIS_WORKSPACE_ROOT": str(self.workspace),
                "ARIS_DEVTOOLS_MCP_TEST_MODE": "1",
                "ARIS_DEVTOOLS_MCP_TEST_CHILD_JSON": json.dumps(
                    ["node", str(FAKE_CHILD)]
                ),
                "ARIS_FAKE_CHILD_LOG": str(self.log_path),
                "ARIS_DEVTOOLS_DOWNLOAD_POLL_MS": "20",
            }
        )
        if extra_env:
            env.update(extra_env)
        self.process = subprocess.Popen(
            ["node", str(FACADE)],
            cwd=REPO_ROOT,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self.next_id = 1
        initialized = self.request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "offline-test", "version": "1"},
            },
        )
        assert initialized["result"]["serverInfo"]["name"] == "aris-devtools-safe-facade"
        self.notify("notifications/initialized", {})

    def request(self, method: str, params: dict | None = None, timeout: float = 8) -> dict:
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        request_id = self.next_id
        self.next_id += 1
        self.process.stdin.write(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": method,
                    "params": params or {},
                }
            )
            + "\n"
        )
        self.process.stdin.flush()
        ready, _, _ = select.select([self.process.stdout], [], [], timeout)
        if not ready:
            stderr = ""
            if self.process.poll() is not None and self.process.stderr is not None:
                stderr = self.process.stderr.read()
            raise AssertionError(f"facade response timed out; stderr={stderr!r}")
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr is not None else ""
            raise AssertionError(f"facade exited before responding; stderr={stderr!r}")
        response = json.loads(line)
        assert response["id"] == request_id
        return response

    def notify(self, method: str, params: dict | None = None) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(
            json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}})
            + "\n"
        )
        self.process.stdin.flush()

    def call_raw(self, name: str, arguments: dict | None = None, timeout: float = 8) -> dict:
        return self.request(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
            timeout=timeout,
        )["result"]

    def call(self, name: str, arguments: dict | None = None, timeout: float = 8) -> dict:
        result = self.call_raw(name, arguments, timeout=timeout)
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        return json.loads(result["content"][0]["text"])

    def select_example(self) -> str:
        tabs = self.call("aris_tabs", {"url_contains": "example.test/paper"})
        assert tabs["unique"] is True
        selected = self.call(
            "aris_select", {"page_ref": tabs["matches"][0]["page_ref"]}
        )
        return selected["lease_id"]

    def child_calls(self) -> list[dict]:
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def close(self) -> None:
        if self.process.poll() is None:
            if self.process.stdin is not None:
                self.process.stdin.close()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=3)
        if self.process.stdout is not None:
            self.process.stdout.close()
        if self.process.stderr is not None:
            self.process.stderr.close()


class DevtoolsMcpFacadeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.client = FacadeProcess(Path(self.temp.name))

    def tearDown(self) -> None:
        self.client.close()
        self.temp.cleanup()

    def test_public_tool_surface_is_exact_and_forbidden_child_capabilities_are_hidden(self) -> None:
        response = self.client.request("tools/list")
        tools = response["result"]["tools"]
        self.assertEqual({tool["name"] for tool in tools}, PUBLIC_TOOL_NAMES)
        rendered = json.dumps(tools)
        for forbidden in FORBIDDEN_CHILD_TOOLS:
            self.assertNotIn(f'"name": "{forbidden}"', rendered)
        navigate = next(tool for tool in tools if tool["name"] == "aris_navigate")
        self.assertNotIn("initScript", navigate["inputSchema"]["properties"])
        self.assertFalse(navigate["inputSchema"]["additionalProperties"])

        for forbidden in FORBIDDEN_CHILD_TOOLS | {"aris_evaluate", "aris_upload"}:
            with self.subTest(forbidden=forbidden):
                result = self.client.call_raw(forbidden, {"function": "document.cookie"})
                self.assertTrue(result["isError"])
                payload = json.loads(result["content"][0]["text"])
                self.assertEqual(payload["error"], "tool_not_exposed")
        self.assertEqual(self.client.child_calls(), [])

    def test_health_proves_official_child_contract_without_legacy_http(self) -> None:
        health = self.client.call("aris_health")
        self.assertTrue(health["ok"])
        self.assertEqual(health["child"]["name"], "chrome_devtools")
        self.assertEqual(health["child"]["version"], "1.6.0-test")
        self.assertTrue(health["safe_facade"])
        self.assertEqual(health["adapter"], "grok_chrome_devtools_mcp")
        self.assertEqual(health["mcp_server"], "browser")
        self.assertEqual(health["implementation"], "chrome-devtools-mcp")
        self.assertEqual(health["profile_mode"], "dedicated_persistent")
        self.assertFalse(health["legacy_http_dependency"])
        self.assertEqual(health["connection_mode"], "managed_launch")
        self.assertFalse(health["browser_transport_verified"])

    def test_external_browser_url_health_probes_transport_and_fails_closed(self) -> None:
        class DevtoolsVersionHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - stdlib callback spelling
                if self.path != "/json/version":
                    self.send_response(404)
                    self.end_headers()
                    return
                port = self.server.server_address[1]
                body = json.dumps(
                    {
                        "Browser": "Chrome/Fake",
                        "webSocketDebuggerUrl": (
                            f"ws://127.0.0.1:{port}/devtools/browser/fake"
                        ),
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), DevtoolsVersionHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        root = Path(self.temp.name) / "external-client"
        client = FacadeProcess(
            root, browser_url=f"http://127.0.0.1:{server.server_address[1]}"
        )
        try:
            health = client.call("aris_health")
            self.assertEqual(health["connection_mode"], "external_browser_url")
            self.assertTrue(health["browser_transport_verified"])
            self.assertEqual(
                health["external_browser_lifecycle"], "not_owned_not_stopped"
            )
            self.assertTrue(
                any(call.get("name") == "list_pages" for call in client.child_calls())
            )

            server.shutdown()
            server.server_close()
            failed = client.call_raw("aris_health", timeout=5)
            self.assertTrue(failed["isError"])
            payload = json.loads(failed["content"][0]["text"])
            self.assertEqual(payload["error"], "external_browser_unavailable")
        finally:
            client.close()
            if thread.is_alive():
                server.shutdown()
                server.server_close()
            thread.join(timeout=2)

    def test_tabs_can_claim_the_only_selected_match_and_redact_queries_and_credentials(self) -> None:
        broad = self.client.call("aris_tabs", {"url_contains": "https://"})
        self.assertEqual(broad["match_count"], 2)
        self.assertEqual(broad["selected_match_count"], 1)
        self.assertTrue(broad["unique"])
        self.assertEqual(broad["selection_basis"], "only_selected_match")
        self.assertTrue(broad["matches"][0]["selected"])
        self.assertIn("page_ref", broad["matches"][0])
        self.assertTrue(all("page_ref" not in match for match in broad["matches"][1:]))

        tabs = self.client.call("aris_tabs", {"url_contains": "example.test/paper"})
        rendered = json.dumps(tabs)
        self.assertTrue(tabs["unique"])
        self.assertEqual(tabs["selection_basis"], "only_match")
        self.assertEqual(tabs["matches"][0]["url"], "https://example.test/paper")
        self.assertIn("page_ref", tabs["matches"][0])
        for secret in (
            "RAW-QUERY-SECRET",
            "RAW-TITLE-SECRET",
            "sessionId=",
            "token=RAW",
        ):
            self.assertNotIn(secret, rendered)

        rejected = self.client.call_raw(
            "aris_tabs", {"url_contains": "paper?sessionId=FILTER-SECRET"}
        )
        self.assertTrue(rejected["isError"])
        self.assertNotIn("FILTER-SECRET", json.dumps(rejected))

    def test_tabs_remain_ambiguous_when_duplicate_matches_have_no_selected_page(self) -> None:
        root = Path(self.temp.name) / "no-selected"
        client = FacadeProcess(root, extra_env={"ARIS_FAKE_SELECTED_PAGE": "0"})
        try:
            tabs = client.call("aris_tabs", {"url_contains": "https://"})
            self.assertEqual(tabs["match_count"], 2)
            self.assertEqual(tabs["selected_match_count"], 0)
            self.assertFalse(tabs["unique"])
            self.assertEqual(
                tabs["next_action"], "narrow_url_contains_or_focus_one_match"
            )
            self.assertTrue(
                all("page_ref" not in match for match in tabs["matches"])
            )
        finally:
            client.close()

    def test_tabs_claim_last_identical_url_match_and_lease_by_page_id(self) -> None:
        """CSMAR may leave multiple sdownload.html tabs with the same URL."""
        root = Path(self.temp.name) / "identical-url"
        client = FacadeProcess(
            root,
            extra_env={
                "ARIS_FAKE_SELECTED_PAGE": "0",
                "ARIS_FAKE_IDENTICAL_URL_DUP": "1",
            },
        )
        try:
            tabs = client.call("aris_tabs", {"url_contains": "sdownload"})
            self.assertEqual(tabs["match_count"], 3)
            self.assertEqual(tabs["selected_match_count"], 0)
            self.assertTrue(tabs["unique"])
            self.assertEqual(tabs["selection_basis"], "identical_url_matches")
            self.assertIn("page_ref", tabs["matches"][0])
            self.assertEqual(tabs["matches"][0]["url"], "https://data.csmar.com/sdownload.html")
            selected = client.call(
                "aris_select", {"page_ref": tabs["matches"][0]["page_ref"]}
            )
            self.assertTrue(selected["selected"])
            self.assertEqual(selected["url"], "https://data.csmar.com/sdownload.html")
            lease = selected["lease_id"]
            snap = client.call("aris_inspect", {"lease_id": lease})
            self.assertTrue(snap["ok"])
            self.assertIn("snapshot_id", snap)
        finally:
            client.close()

    def test_tabs_do_not_auto_claim_identical_urls_outside_csmar_result_page(self) -> None:
        root = Path(self.temp.name) / "identical-url-other-site"
        client = FacadeProcess(
            root,
            extra_env={
                "ARIS_FAKE_SELECTED_PAGE": "0",
                "ARIS_FAKE_IDENTICAL_URL_DUP": "other",
            },
        )
        try:
            tabs = client.call("aris_tabs", {"url_contains": "duplicate"})
            self.assertEqual(tabs["match_count"], 3)
            self.assertEqual(tabs["selected_match_count"], 0)
            self.assertFalse(tabs["unique"])
            self.assertNotIn("selection_basis", tabs)
            self.assertTrue(
                all("page_ref" not in match for match in tabs["matches"])
            )
        finally:
            client.close()

    def test_tabs_can_select_one_exact_about_blank_bootstrap_page(self) -> None:
        tabs = self.client.call("aris_tabs", {"url_contains": "about:blank"})
        self.assertTrue(tabs["unique"])
        self.assertEqual(tabs["matches"][0]["url"], "about:blank")
        selected = self.client.call(
            "aris_select", {"page_ref": tabs["matches"][0]["page_ref"]}
        )
        self.assertTrue(selected["selected"])
        self.assertEqual(selected["url"], "about:blank")

    def test_official_unstructured_page_listing_fallback_is_parsed_without_queries(self) -> None:
        javascript = f"""
          import {{ projectPages, stripUrlDetails }} from {json.dumps(FACADE.as_uri())};
          const result = {{
            content: [{{ type: 'text', text: `## Pages
1: Article title (https://example.test/article?id=QUERY-SECRET) [selected]
2: https://other.test/path?sessionId=OTHER-SECRET
3: about:blank` }}],
          }};
          const pages = projectPages(result).map(page => ({{
            id: page.id,
            url: stripUrlDetails(page.rawUrl),
            title: page.title,
            selected: page.selected,
          }}));
          console.log(JSON.stringify(pages));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        pages = json.loads(result.stdout)
        self.assertEqual(
            pages,
            [
                {
                    "id": 1,
                    "url": "https://example.test/article",
                    "title": "Article title",
                    "selected": True,
                },
                {
                    "id": 2,
                    "url": "https://other.test/path",
                    "title": "",
                    "selected": False,
                },
                {
                    "id": 3,
                    "url": "about:blank",
                    "title": "",
                    "selected": False,
                },
            ],
        )
        self.assertNotIn("QUERY-SECRET", json.dumps(pages))
        self.assertNotIn("OTHER-SECRET", json.dumps(pages))

    def test_snapshot_uses_opaque_fresh_refs_and_projects_no_values_or_raw_uids(self) -> None:
        lease = self.client.select_example()
        inspected = self.client.call("aris_inspect", {"lease_id": lease})
        rendered = json.dumps(inspected)
        self.assertTrue(inspected["ok"])
        self.assertTrue(inspected["snapshot_id"].startswith("snapshot_"))
        self.assertTrue(all(item["element_ref"].startswith("element_") for item in inspected["elements"]))
        for secret in (
            "uid=",
            "5_1",
            "INPUT-VALUE-SECRET",
            "STATIC-PASSWORD-SECRET",
            "SNAPSHOT-QUERY-SECRET",
            "PASSWORD-FIELD-SECRET",
            "X-Amz-Signature",
        ):
            self.assertNotIn(secret, rendered)
        self.assertIn("password=[REDACTED]", rendered)
        self.assertIn("https://example.test/file.pdf", rendered)

        button = next(item for item in inspected["elements"] if item["name"] == "View PDF")
        clicked = self.client.call(
            "aris_click",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": button["element_ref"],
            },
        )
        self.assertTrue(clicked["state_check_required"])
        stale = self.client.call_raw(
            "aris_click",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": button["element_ref"],
            },
        )
        self.assertTrue(stale["isError"])
        self.assertEqual(
            json.loads(stale["content"][0]["text"])["error"], "snapshot_stale"
        )
        click_calls = [
            call for call in self.client.child_calls() if call.get("name") == "click"
        ]
        self.assertEqual(len(click_calls), 1)
        self.assertEqual(
            click_calls[0]["arguments"],
            {"uid": "5_1", "dblClick": False, "includeSnapshot": False},
        )

    def test_large_snapshot_projection_has_a_total_public_output_budget(self) -> None:
        client = FacadeProcess(
            Path(self.temp.name) / "large-snapshot",
            extra_env={"ARIS_FAKE_LARGE_SNAPSHOT": "1"},
        )
        try:
            lease = client.select_example()
            raw = client.call_raw("aris_inspect", {"lease_id": lease})
            serialized = json.dumps(raw)
            payload = json.loads(raw["content"][0]["text"])
            self.assertTrue(payload["truncated"])
            self.assertLess(len(serialized.encode("utf-8")), 30_000)
            self.assertLess(payload["element_count"], 240)
        finally:
            client.close()

    def test_fill_never_echoes_input_or_raw_child_error(self) -> None:
        lease = self.client.select_example()
        inspected = self.client.call(
            "aris_inspect", {"lease_id": lease, "text_query": "Email"}
        )
        textbox = inspected["elements"][0]
        supplied = "PRIVATE-FILL-VALUE"
        filled_raw = self.client.call_raw(
            "aris_fill",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": textbox["element_ref"],
                "text": supplied,
            },
        )
        self.assertFalse(filled_raw.get("isError", False))
        self.assertNotIn(supplied, json.dumps(filled_raw))
        self.assertEqual(
            json.loads(filled_raw["content"][0]["text"])["characters_supplied"],
            len(supplied),
        )
        filled = json.loads(filled_raw["content"][0]["text"])
        self.assertTrue(filled["value_confirmation_available"])
        self.assertTrue(filled["value_matches_supplied"])

        inspected = self.client.call(
            "aris_inspect", {"lease_id": lease, "text_query": "Email"}
        )
        textbox = inspected["elements"][0]
        failed = self.client.call_raw(
            "aris_fill",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": textbox["element_ref"],
                "text": "TRIGGER-RAW-ERROR",
            },
        )
        rendered = json.dumps(failed)
        self.assertTrue(failed["isError"])
        self.assertEqual(
            json.loads(failed["content"][0]["text"])["error"],
            "browser_operation_failed",
        )
        for secret in (
            "TRIGGER-RAW-ERROR",
            "CHILD-ERROR-SECRET",
            "CHILD-QUERY-SECRET",
            "private.test",
        ):
            self.assertNotIn(secret, rendered)

        inspected = self.client.call(
            "aris_inspect", {"lease_id": lease, "text_query": "Password"}
        )
        password = inspected["elements"][0]
        probes_before = len(
            [
                call
                for call in self.client.child_calls()
                if call.get("name") == "evaluate_script"
            ]
        )
        credential_fill = self.client.call_raw(
            "aris_fill",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": password["element_ref"],
                "text": "NEVER-FORWARD-THIS-CREDENTIAL",
            },
        )
        self.assertTrue(credential_fill["isError"])
        self.assertEqual(
            json.loads(credential_fill["content"][0]["text"])["error"],
            "credential_fill_rejected",
        )
        self.assertNotIn("NEVER-FORWARD", json.dumps(credential_fill))
        self.assertFalse(
            any(
                call.get("name") == "fill"
                and call.get("arguments", {}).get("value")
                == "NEVER-FORWARD-THIS-CREDENTIAL"
                for call in self.client.child_calls()
            )
        )
        probes_after = len(
            [
                call
                for call in self.client.child_calls()
                if call.get("name") == "evaluate_script"
            ]
        )
        self.assertEqual(probes_after, probes_before)

    def test_fill_value_proof_survives_same_page_reacquire_and_enter_commit(self) -> None:
        lease = self.client.select_example()
        inspected = self.client.call(
            "aris_inspect", {"lease_id": lease, "text_query": "Start date"}
        )
        date_input = inspected["elements"][0]
        supplied = "2020-12-31"
        filled_raw = self.client.call_raw(
            "aris_fill",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": date_input["element_ref"],
                "text": supplied,
            },
        )
        self.assertNotIn(supplied, json.dumps(filled_raw))
        filled = json.loads(filled_raw["content"][0]["text"])
        self.assertTrue(filled["value_confirmation_available"])
        self.assertTrue(filled["value_matches_supplied"])

        reacquired_lease = self.client.select_example()
        self.client.call(
            "aris_inspect",
            {"lease_id": reacquired_lease, "text_query": "Start date"},
        )
        committed_raw = self.client.call_raw(
            "aris_key", {"lease_id": reacquired_lease, "key": "Enter"}
        )
        self.assertNotIn(supplied, json.dumps(committed_raw))
        committed = json.loads(committed_raw["content"][0]["text"])
        self.assertTrue(committed["value_confirmation_available_before_key"])
        self.assertTrue(committed["value_matches_last_fill_before_key"])
        self.assertTrue(committed["value_confirmation_available_after_key"])
        self.assertTrue(committed["value_matches_last_fill_after_key"])

    def test_navigation_rejects_signed_urls_before_the_child_and_redacts_queries(self) -> None:
        lease = self.client.select_example()
        signed = "https://example.test/file?X-Amz-Signature=SIGNED-NAV-SECRET"
        rejected = self.client.call_raw(
            "aris_navigate", {"lease_id": lease, "url": signed}
        )
        self.assertTrue(rejected["isError"])
        self.assertNotIn("SIGNED-NAV-SECRET", json.dumps(rejected))
        self.assertFalse(
            any(
                call.get("name") == "navigate_page" and "SIGNED-NAV-SECRET" in json.dumps(call)
                for call in self.client.child_calls()
            )
        )

        navigated = self.client.call(
            "aris_navigate",
            {"lease_id": lease, "url": "https://example.test/ordinary?article=42"},
        )
        self.assertEqual(navigated["url"], "https://example.test/ordinary")
        self.assertNotIn("article=42", json.dumps(navigated))

        with_init_script = self.client.call_raw(
            "aris_navigate",
            {
                "lease_id": lease,
                "url": "https://example.test/",
                "initScript": "document.cookie",
            },
        )
        self.assertTrue(with_init_script["isError"])
        self.assertNotIn("document.cookie", json.dumps(with_init_script))

    def test_key_is_allowlisted_requires_fresh_inspection_and_never_supports_hold(self) -> None:
        lease = self.client.select_example()
        no_snapshot = self.client.call_raw(
            "aris_key", {"lease_id": lease, "key": "Enter"}
        )
        self.assertTrue(no_snapshot["isError"])
        self.client.call("aris_inspect", {"lease_id": lease, "text_query": "View PDF"})
        held = self.client.call_raw(
            "aris_key", {"lease_id": lease, "key": "Space"}
        )
        self.assertTrue(held["isError"])
        self.assertEqual(
            json.loads(held["content"][0]["text"])["error"], "key_not_allowlisted"
        )
        pressed = self.client.call("aris_key", {"lease_id": lease, "key": "Enter"})
        self.assertTrue(pressed["state_check_required"])
        self.assertEqual(pressed["key"], "Enter")

    def test_upload_is_single_file_workspace_scoped_and_uses_one_fresh_upload_control(
        self,
    ) -> None:
        source = self.client.workspace / "handoff.zip"
        source.write_bytes(b"PK\x03\x04safe handoff")
        lease = self.client.select_example()
        inspected = self.client.call(
            "aris_inspect", {"lease_id": lease, "text_query": "Add files"}
        )
        uploaded = self.client.call(
            "aris_upload_file",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": inspected["elements"][0]["element_ref"],
                "source": "handoff.zip",
            },
        )
        self.assertEqual(uploaded["source"], "handoff.zip")
        self.assertEqual(uploaded["format"], "zip")
        self.assertEqual(uploaded["size_bytes"], str(source.stat().st_size))
        self.assertEqual(
            uploaded["sha256"], hashlib.sha256(source.read_bytes()).hexdigest()
        )
        self.assertEqual(uploaded["upload_budget_consumed"], 1)
        upload_calls = [
            call
            for call in self.client.child_calls()
            if call.get("name") == "upload_file"
        ]
        self.assertEqual(len(upload_calls), 1)
        self.assertEqual(
            upload_calls[0]["arguments"],
            {
                "uid": "5_10",
                "filePath": str(source.resolve()),
                "includeSnapshot": False,
            },
        )

        stale = self.client.call_raw(
            "aris_upload_file",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": inspected["elements"][0]["element_ref"],
                "source": "handoff.zip",
            },
        )
        self.assertTrue(stale["isError"])
        self.assertEqual(
            json.loads(stale["content"][0]["text"])["error"], "snapshot_stale"
        )
        self.assertEqual(
            len([
                call
                for call in self.client.child_calls()
                if call.get("name") == "upload_file"
            ]),
            1,
        )

    def test_upload_rejects_absolute_traversal_symlink_format_and_wrong_control(
        self,
    ) -> None:
        valid = self.client.workspace / "valid.txt"
        valid.write_text("safe", encoding="utf-8")
        executable = self.client.workspace / "payload.sh"
        executable.write_text("#!/bin/sh\n", encoding="utf-8")
        outside = self.client.root / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        symlink = self.client.workspace / "linked.txt"
        symlink.symlink_to(outside)
        lease = self.client.select_example()

        for source in [str(valid), "../outside.txt", "linked.txt", "payload.sh"]:
            with self.subTest(source=source):
                inspected = self.client.call(
                    "aris_inspect", {"lease_id": lease, "text_query": "Add files"}
                )
                rejected = self.client.call_raw(
                    "aris_upload_file",
                    {
                        "lease_id": lease,
                        "snapshot_id": inspected["snapshot_id"],
                        "element_ref": inspected["elements"][0]["element_ref"],
                        "source": source,
                    },
                )
                self.assertTrue(rejected["isError"])

        inspected = self.client.call(
            "aris_inspect", {"lease_id": lease, "text_query": "View PDF"}
        )
        wrong_control = self.client.call_raw(
            "aris_upload_file",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": inspected["elements"][0]["element_ref"],
                "source": "valid.txt",
            },
        )
        self.assertTrue(wrong_control["isError"])
        self.assertEqual(
            json.loads(wrong_control["content"][0]["text"])["error"],
            "upload_target_rejected",
        )
        self.assertFalse(
            any(
                call.get("name") == "upload_file"
                for call in self.client.child_calls()
            )
        )

    def test_challenge_requires_observation_action_time_confirmation_and_one_checkbox_click(self) -> None:
        lease = self.client.select_example()
        self.client.call(
            "aris_navigate",
            {"lease_id": lease, "url": "https://example.test/challenge-checkbox"},
        )
        state = self.client.call("aris_challenge_state", {"lease_id": lease})
        self.assertTrue(state["observed"])
        self.assertEqual(state["kind"], "checkbox")
        self.assertTrue(state["supported"])
        self.assertEqual(state["click_budget"], 1)

        missing_confirmation = self.client.call_raw(
            "aris_click",
            {
                "lease_id": lease,
                "snapshot_id": state["snapshot_id"],
                "element_ref": state["element_ref"],
            },
        )
        self.assertTrue(missing_confirmation["isError"])
        self.assertEqual(
            json.loads(missing_confirmation["content"][0]["text"])["error"],
            "challenge_action_confirmation_required",
        )
        confirmed = self.client.call(
            "aris_click",
            {
                "lease_id": lease,
                "snapshot_id": state["snapshot_id"],
                "element_ref": state["element_ref"],
                "challenge_observed": True,
                "action_time_confirmation": True,
                "challenge_token": state["challenge_token"],
            },
        )
        self.assertTrue(confirmed["challenge_checkbox_clicked_once"])
        second_state = self.client.call(
            "aris_challenge_state", {"lease_id": lease}
        )
        self.assertEqual(second_state["click_budget"], 0)
        self.assertNotIn("element_ref", second_state)
        click_calls = [
            call for call in self.client.child_calls() if call.get("name") == "click"
        ]
        self.assertEqual(len(click_calls), 1)

    def test_slider_image_and_press_hold_challenges_are_observable_but_never_actionable(self) -> None:
        lease = self.client.select_example()
        cases = [
            ("challenge-slider", "slider"),
            ("challenge-image", "image"),
            ("challenge-press-hold", "press_hold"),
        ]
        for route, kind in cases:
            with self.subTest(kind=kind):
                self.client.call(
                    "aris_navigate",
                    {"lease_id": lease, "url": f"https://example.test/{route}"},
                )
                state = self.client.call(
                    "aris_challenge_state", {"lease_id": lease}
                )
                self.assertTrue(state["observed"])
                self.assertEqual(state["kind"], kind)
                self.assertFalse(state["supported"])
                self.assertEqual(state["click_budget"], 0)
                self.assertNotIn("element_ref", state)
        self.assertFalse(
            any(call.get("name") in {"drag", "evaluate_script"} for call in self.client.child_calls())
        )

    def test_ordinary_preview_slider_does_not_block_download_or_upload(self) -> None:
        source = self.client.workspace / "preview.txt"
        source.write_text("safe", encoding="utf-8")
        lease = self.client.select_example()
        self.client.call(
            "aris_navigate",
            {"lease_id": lease, "url": "https://example.test/ordinary-slider"},
        )
        state = self.client.call("aris_challenge_state", {"lease_id": lease})
        self.assertFalse(state["observed"])
        self.assertEqual(state["kind"], "none")

        inspected = self.client.call(
            "aris_inspect", {"lease_id": lease, "text_query": "Download"}
        )
        triggered = self.client.call(
            "aris_trigger_element_download",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": inspected["elements"][0]["element_ref"],
            },
        )
        self.assertTrue(triggered["baseline_id"].startswith("baseline_"))

        inspected = self.client.call(
            "aris_inspect", {"lease_id": lease, "text_query": "Add files"}
        )
        uploaded = self.client.call(
            "aris_upload_file",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": inspected["elements"][0]["element_ref"],
                "source": "preview.txt",
            },
        )
        self.assertEqual(uploaded["format"], "txt")

        inspected = self.client.call(
            "aris_inspect", {"lease_id": lease, "text_query": "Add photos & files"}
        )
        uploaded_from_proxy_text = self.client.call(
            "aris_upload_file",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": inspected["elements"][0]["element_ref"],
                "source": "preview.txt",
            },
        )
        self.assertEqual(uploaded_from_proxy_text["format"], "txt")

    def test_cnki_challenge_requires_fixed_rendered_blocking_geometry(self) -> None:
        lease = self.client.select_example()
        cases = [
            ("hidden", False, "none"),
            ("nonblocking", False, "none"),
            ("visible", True, "slider"),
        ]
        for route, observed, kind in cases:
            with self.subTest(route=route):
                self.client.call(
                    "aris_navigate",
                    {
                        "lease_id": lease,
                        "url": f"https://kns.cnki.net/kns8s/search/{route}",
                    },
                )
                state = self.client.call(
                    "aris_challenge_state", {"lease_id": lease}
                )
                self.assertEqual(state["observed"], observed)
                self.assertEqual(state["kind"], kind)
                self.assertTrue(state["rendered_geometry_verified"])
                if observed:
                    self.assertFalse(state["supported"])
                    self.assertEqual(state["click_budget"], 0)

        evaluate_calls = [
            call
            for call in self.client.child_calls()
            if call.get("name") == "evaluate_script"
        ]
        self.assertEqual(len(evaluate_calls), 3)
        for call in evaluate_calls:
            self.assertEqual(set(call["arguments"]), {"function"})
            function = call["arguments"]["function"]
            self.assertIn("#tcaptcha_transform_dy", function)
            self.assertIn("#tCaptchaDyMainWrap", function)
            self.assertIn("document.elementFromPoint", function)
            self.assertNotIn("document.cookie", function)

    def test_wait_does_not_relay_child_snapshot_and_invalidates_old_refs(self) -> None:
        lease = self.client.select_example()
        inspected = self.client.call("aris_inspect", {"lease_id": lease})
        waited_raw = self.client.call_raw(
            "aris_wait", {"lease_id": lease, "text": "Loaded", "timeout_ms": 500}
        )
        rendered = json.dumps(waited_raw)
        self.assertNotIn("RAW CHILD SUCCESS", rendered)
        self.assertNotIn("Loaded", rendered)
        old_element = inspected["elements"][0]
        stale = self.client.call_raw(
            "aris_click",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": old_element["element_ref"],
            },
        )
        self.assertTrue(stale["isError"])

    def test_downloads_use_opaque_baseline_stability_partial_rejection_and_scoped_copy(self) -> None:
        lease = self.client.select_example()
        existing = self.client.downloads / "existing.pdf"
        existing.write_bytes(b"old")
        baseline = self.client.call("aris_download_baseline")
        rendered_baseline = json.dumps(baseline)
        self.assertTrue(baseline["opaque"])
        self.assertNotIn("existing.pdf", rendered_baseline)
        self.assertNotIn(str(self.client.downloads), rendered_baseline)

        partial = self.client.downloads / "paper.pdf.crdownload"
        partial.write_bytes(b"partial")
        timed_out = self.client.call_raw(
            "aris_download_wait",
            {
                "baseline_id": baseline["baseline_id"],
                "filename_contains": "paper.pdf",
                "timeout_ms": 120,
            },
            timeout=3,
        )
        self.assertTrue(timed_out["isError"])
        self.assertEqual(
            json.loads(timed_out["content"][0]["text"])["error"],
            "download_wait_timeout",
        )

        partial.unlink()
        completed = self.client.downloads / "paper.pdf"
        completed.write_bytes(b"%PDF-1.7\ncomplete\n%%EOF")
        download = self.client.call(
            "aris_download_wait",
            {
                "baseline_id": baseline["baseline_id"],
                "filename_contains": "paper.pdf",
                "timeout_ms": 1000,
            },
            timeout=3,
        )
        self.assertEqual(download["state"], "stable_complete")
        self.assertTrue(download["download_ref"].startswith("download_"))
        self.assertNotIn(str(self.client.downloads), json.dumps(download))

        traversal = self.client.call_raw(
            "aris_copy_download",
            {
                "download_ref": download["download_ref"],
                "destination": ".aris/../escape.pdf",
            },
        )
        self.assertTrue(traversal["isError"])
        self.assertFalse((self.client.workspace / "escape.pdf").exists())

        credential_destination = self.client.call_raw(
            "aris_copy_download",
            {
                "download_ref": download["download_ref"],
                "destination": ".aris/token=DESTINATION-SECRET/paper.pdf",
            },
        )
        self.assertTrue(credential_destination["isError"])
        self.assertNotIn("DESTINATION-SECRET", json.dumps(credential_destination))

        copied = self.client.call(
            "aris_copy_download",
            {
                "download_ref": download["download_ref"],
                "destination": ".aris/run/paper.pdf",
            },
        )
        destination = self.client.workspace / copied["destination"]
        self.assertEqual(destination.read_bytes(), completed.read_bytes())
        self.assertEqual(copied["format"], "pdf")
        self.assertEqual(copied["size_bytes"], destination.stat().st_size)
        self.assertRegex(copied["mtime_ns"], r"^[1-9][0-9]*$")
        self.assertEqual(int(copied["mtime_ns"]), destination.stat().st_mtime_ns)
        self.assertEqual(
            copied["sha256"], hashlib.sha256(destination.read_bytes()).hexdigest()
        )
        self.assertEqual(copied["collision_policy"], "fail")
        released = self.client.call("aris_release", {"lease_id": lease})
        self.assertTrue(released["released"])

    def test_shared_controller_lease_serializes_independent_facade_processes(self) -> None:
        self.client.close()
        shared_lock = Path(self.temp.name) / "shared-controller.lock"
        first = FacadeProcess(
            Path(self.temp.name) / "controller-first",
            extra_env={"ARIS_BROWSER_CONTROLLER_LOCK_DIR": str(shared_lock)},
        )
        second = FacadeProcess(
            Path(self.temp.name) / "controller-second",
            extra_env={"ARIS_BROWSER_CONTROLLER_LOCK_DIR": str(shared_lock)},
        )
        self.addCleanup(first.close)
        self.addCleanup(second.close)

        first_lease = first.select_example()
        self.assertEqual(
            first.call("aris_health")["controller_lease_state"],
            "owned_by_this_process",
        )
        self.assertEqual(
            second.call("aris_health")["controller_lease_state"],
            "held_by_other",
        )

        tabs = second.call("aris_tabs", {"url_contains": "example.test/paper"})
        blocked = second.call_raw(
            "aris_select", {"page_ref": tabs["matches"][0]["page_ref"]}
        )
        self.assertTrue(blocked["isError"])
        self.assertEqual(
            json.loads(blocked["content"][0]["text"])["error"],
            "browser_controller_lease_held_by_other",
        )
        self.assertFalse(
            any(call.get("name") == "select_page" for call in second.child_calls())
        )

        self.assertTrue(
            first.call("aris_release", {"lease_id": first_lease})["released"]
        )
        second_selected = second.call(
            "aris_select", {"page_ref": tabs["matches"][0]["page_ref"]}
        )
        self.assertTrue(second_selected["selected"])
        self.assertTrue(
            second.call(
                "aris_release", {"lease_id": second_selected["lease_id"]}
            )["released"]
        )

    def test_loaded_pdf_download_uses_one_fixed_script_and_returns_only_opaque_baseline(self) -> None:
        lease = self.client.select_example()
        rejected = self.client.call_raw(
            "aris_trigger_loaded_pdf_download", {"lease_id": lease}
        )
        self.assertTrue(rejected["isError"])
        self.assertEqual(
            json.loads(rejected["content"][0]["text"])["error"],
            "loaded_pdf_url_rejected",
        )
        self.assertFalse(
            any(
                call.get("name") == "evaluate_script"
                for call in self.client.child_calls()
            )
        )

        self.client.call(
            "aris_navigate",
            {"lease_id": lease, "url": "https://assets.example.test/session/main.pdf"},
        )
        triggered = self.client.call(
            "aris_trigger_loaded_pdf_download", {"lease_id": lease}
        )
        rendered = json.dumps(triggered)
        self.assertTrue(triggered["state_check_required"])
        self.assertEqual(triggered["expected_format"], "pdf")
        self.assertEqual(triggered["filename_policy"], "server_controlled")
        self.assertTrue(triggered["baseline_id"].startswith("baseline_"))
        self.assertNotIn("RAW-PDF-SECRET", rendered)
        self.assertNotIn("X-Amz", rendered)
        self.assertNotIn("assets.example.test", rendered)

        evaluate_calls = [
            call
            for call in self.client.child_calls()
            if call.get("name") == "evaluate_script"
        ]
        self.assertEqual(len(evaluate_calls), 1)
        self.assertEqual(set(evaluate_calls[0]["arguments"]), {"function"})
        fixed_function = evaluate_calls[0]["arguments"]["function"]
        self.assertIn('document.contentType', fixed_function)
        self.assertIn('downloadUrl = new URL(window.location.href)', fixed_function)
        self.assertIn('url.pathname.startsWith("/doi/pdfdirect/")', fixed_function)
        self.assertIn('url.origin === window.location.origin', fixed_function)
        self.assertIn('link.href = downloadUrl.href', fixed_function)
        self.assertIn('link.click()', fixed_function)
        self.assertNotIn("document.cookie", fixed_function)

        downloaded = self.client.call(
            "aris_download_wait",
            {
                "baseline_id": triggered["baseline_id"],
                "filename_contains": "1-s2.0-TEST-main.pdf",
                "timeout_ms": 1000,
            },
            timeout=3,
        )
        copied = self.client.call(
            "aris_copy_download",
            {
                "download_ref": downloaded["download_ref"],
                "destination": ".aris/run/sciencedirect.pdf",
            },
        )
        artifact = self.client.workspace / copied["destination"]
        self.assertTrue(artifact.read_bytes().startswith(b"%PDF-"))
        self.assertTrue(artifact.read_bytes().endswith(b"%%EOF"))

        self.client.call(
            "aris_navigate",
            {
                "lease_id": lease,
                "url": "https://onlinelibrary.wiley.com/doi/pdf/10.1111/test",
            },
        )
        wiley_triggered = self.client.call(
            "aris_trigger_loaded_pdf_download", {"lease_id": lease}
        )
        wiley_downloaded = self.client.call(
            "aris_download_wait",
            {
                "baseline_id": wiley_triggered["baseline_id"],
                "filename_contains": "wiley-wrapper.pdf",
                "timeout_ms": 1000,
            },
            timeout=3,
        )
        wiley_copied = self.client.call(
            "aris_copy_download",
            {
                "download_ref": wiley_downloaded["download_ref"],
                "destination": ".aris/run/wiley.pdf",
            },
        )
        self.assertEqual(wiley_copied["format"], "pdf")
        self.assertNotIn("pdfdirect", json.dumps(wiley_triggered))

    def test_element_download_trigger_atomically_baselines_and_clicks_one_fresh_control(self) -> None:
        lease = self.client.select_example()
        inspected = self.client.call(
            "aris_inspect", {"lease_id": lease, "text_query": "View PDF"}
        )
        triggered = self.client.call(
            "aris_trigger_element_download",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": inspected["elements"][0]["element_ref"],
            },
        )
        self.assertTrue(triggered["baseline_id"].startswith("baseline_"))
        self.assertEqual(triggered["click_budget_consumed"], 1)
        click_calls = [
            call for call in self.client.child_calls() if call.get("name") == "click"
        ]
        self.assertEqual(len(click_calls), 1)
        self.assertEqual(
            click_calls[0]["arguments"],
            {"uid": "5_1", "dblClick": False, "includeSnapshot": False},
        )

        completed = self.client.downloads / "portal-export.zip"
        completed.write_bytes(b"PK\x03\x04stable export")
        downloaded = self.client.call(
            "aris_download_wait",
            {
                "baseline_id": triggered["baseline_id"],
                "filename_contains": "portal-export.zip",
                "timeout_ms": 1000,
            },
            timeout=3,
        )
        copied = self.client.call(
            "aris_copy_download",
            {
                "download_ref": downloaded["download_ref"],
                "destination": ".aris/run/portal-export.zip",
            },
        )
        self.assertEqual(copied["format"], "zip")

        inspected = self.client.call(
            "aris_inspect", {"lease_id": lease, "text_query": "Email"}
        )
        rejected = self.client.call_raw(
            "aris_trigger_element_download",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": inspected["elements"][0]["element_ref"],
            },
        )
        self.assertTrue(rejected["isError"])
        self.assertEqual(
            json.loads(rejected["content"][0]["text"])["error"],
            "download_trigger_target_rejected",
        )
        self.assertEqual(
            len(
                [
                    call
                    for call in self.client.child_calls()
                    if call.get("name") == "click"
                ]
            ),
            1,
        )

    def test_element_download_trigger_allows_icon_font_statictext_not_status_labels(
        self,
    ) -> None:
        """CNRDS queue rows use PUA icon-font StaticText for the download action.

        Status labels such as 未下载 / 压缩完成 must still be rejected.
        """
        lease = self.client.select_example()
        inspected = self.client.call("aris_inspect", {"lease_id": lease})
        icon = next(
            item
            for item in inspected["elements"]
            if item.get("role") == "StaticText" and item.get("name") == "\ue618"
        )
        triggered = self.client.call(
            "aris_trigger_element_download",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": icon["element_ref"],
            },
        )
        self.assertTrue(triggered["baseline_id"].startswith("baseline_"))
        # Icon-font StaticText must use the fixed leaf-click script, not raw child click.
        click_calls = [
            call for call in self.client.child_calls() if call.get("name") == "click"
        ]
        self.assertEqual(len(click_calls), 0)
        eval_calls = [
            call
            for call in self.client.child_calls()
            if call.get("name") == "evaluate_script"
            and "aris-icon-font-leaf-click-v1" in str(call.get("arguments", {}))
        ]
        self.assertEqual(len(eval_calls), 1)
        self.assertNotIn("args", eval_calls[0]["arguments"])
        fixed_function = eval_calls[0]["arguments"]["function"]
        self.assertIn("minimalRows.length !== 1", fixed_function)
        self.assertIn("candidates.length !== 1", fixed_function)
        self.assertIn("candidates[0].click();", fixed_function)
        self.assertNotIn("dispatchEvent", fixed_function)
        self.assertNotIn("scored.slice", fixed_function)
        self.assertEqual(fixed_function.count(".click();"), 1)

        inspected = self.client.call(
            "aris_inspect", {"lease_id": lease, "text_query": "未下载"}
        )
        rejected_status = self.client.call_raw(
            "aris_trigger_element_download",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": inspected["elements"][0]["element_ref"],
            },
        )
        self.assertTrue(rejected_status["isError"])
        self.assertEqual(
            json.loads(rejected_status["content"][0]["text"])["error"],
            "download_trigger_target_rejected",
        )

        inspected = self.client.call(
            "aris_inspect", {"lease_id": lease, "text_query": "压缩完成"}
        )
        rejected_progress = self.client.call_raw(
            "aris_trigger_element_download",
            {
                "lease_id": lease,
                "snapshot_id": inspected["snapshot_id"],
                "element_ref": inspected["elements"][0]["element_ref"],
            },
        )
        self.assertTrue(rejected_progress["isError"])
        self.assertEqual(
            json.loads(rejected_progress["content"][0]["text"])["error"],
            "download_trigger_target_rejected",
        )
        # Rejections must not issue child clicks; icon success used fixed script only.
        self.assertEqual(
            len(
                [
                    call
                    for call in self.client.child_calls()
                    if call.get("name") == "click"
                ]
            ),
            0,
        )
        self.assertEqual(
            len(
                [
                    call
                    for call in self.client.child_calls()
                    if call.get("name") == "evaluate_script"
                    and "aris-icon-font-leaf-click-v1" in str(call.get("arguments", {}))
                ]
            ),
            1,
        )

    def test_downloads_directory_missing_under_sandbox_home_fails_closed(self) -> None:
        """Strict sandbox fake HOME without Downloads must not invent a path."""
        self.client.close()
        root = Path(self.temp.name) / "no-downloads-home"
        client = FacadeProcess(root)
        self.addCleanup(client.close)
        # Remove the Downloads dir that FacadeProcess creates by default.
        import shutil

        shutil.rmtree(client.downloads)
        client.select_example()
        raw = client.call_raw("aris_download_baseline")
        self.assertTrue(raw["isError"])
        payload = json.loads(raw["content"][0]["text"])
        self.assertEqual(payload["error"], "downloads_directory_unavailable")
        self.assertNotIn(str(client.home), json.dumps(raw))
        self.assertNotIn("Downloads", json.dumps(payload.get("path", "")))

    def test_downloads_dir_env_override_bridges_sandbox_without_leaking_path(self) -> None:
        """Host ARIS_DEVTOOLS_DOWNLOADS_DIR may point at the real landing Downloads.

        The model never supplies this path; responses stay opaque.
        """
        self.client.close()
        root = Path(self.temp.name) / "bridge-home"
        bridge_downloads = Path(self.temp.name) / "chrome-landing" / "Downloads"
        bridge_downloads.mkdir(parents=True)
        client = FacadeProcess(
            root,
            extra_env={"ARIS_DEVTOOLS_DOWNLOADS_DIR": str(bridge_downloads)},
        )
        self.addCleanup(client.close)
        # Sandbox HOME Downloads stays empty / unused.
        for leftover in client.downloads.iterdir():
            leftover.unlink()
        client.select_example()
        baseline = client.call("aris_download_baseline")
        rendered = json.dumps(baseline)
        self.assertTrue(baseline["baseline_id"].startswith("baseline_"))
        self.assertTrue(baseline["opaque"])
        self.assertNotIn(str(bridge_downloads), rendered)
        self.assertNotIn(str(client.home), rendered)
        self.assertNotIn("chrome-landing", rendered)

        landed = bridge_downloads / "cnrds-export.zip"
        landed.write_bytes(b"PK\x03\x04bridge-ok")
        download = client.call(
            "aris_download_wait",
            {
                "baseline_id": baseline["baseline_id"],
                "filename_contains": "cnrds-export.zip",
                "timeout_ms": 1000,
            },
            timeout=3,
        )
        self.assertEqual(download["state"], "stable_complete")
        self.assertTrue(download["download_ref"].startswith("download_"))
        # Filename may be projected; absolute landing paths must never be.
        self.assertNotIn(str(bridge_downloads), json.dumps(download))
        self.assertNotIn(str(client.home), json.dumps(download))
        self.assertNotIn("chrome-landing", json.dumps(download))

        copied = client.call(
            "aris_copy_download",
            {
                "download_ref": download["download_ref"],
                "destination": ".aris/run/cnrds-export.zip",
            },
        )
        dest = client.workspace / copied["destination"]
        self.assertEqual(dest.read_bytes(), landed.read_bytes())
        self.assertEqual(copied["format"], "zip")
        self.assertNotIn(str(bridge_downloads), json.dumps(copied))
        self.assertNotIn("chrome-landing", json.dumps(copied))

    def test_downloads_dir_env_override_rejects_non_downloads_basename(self) -> None:
        self.client.close()
        root = Path(self.temp.name) / "bad-override-home"
        other = Path(self.temp.name) / "not-the-boundary"
        other.mkdir(parents=True)
        client = FacadeProcess(
            root,
            extra_env={"ARIS_DEVTOOLS_DOWNLOADS_DIR": str(other)},
        )
        self.addCleanup(client.close)
        client.select_example()
        raw = client.call_raw("aris_download_baseline")
        self.assertTrue(raw["isError"])
        self.assertEqual(
            json.loads(raw["content"][0]["text"])["error"],
            "downloads_directory_unavailable",
        )
        self.assertNotIn(str(other), json.dumps(raw))

    def test_downloads_dir_env_override_rejects_symlink_escape(self) -> None:
        self.client.close()
        root = Path(self.temp.name) / "symlink-escape-home"
        outside = Path(self.temp.name) / "secret-store"
        outside.mkdir(parents=True)
        (outside / "secret.bin").write_bytes(b"secret")
        link_parent = Path(self.temp.name) / "link-parent"
        link_parent.mkdir(parents=True)
        downloads_link = link_parent / "Downloads"
        downloads_link.symlink_to(outside, target_is_directory=True)
        client = FacadeProcess(
            root,
            extra_env={"ARIS_DEVTOOLS_DOWNLOADS_DIR": str(downloads_link)},
        )
        self.addCleanup(client.close)
        client.select_example()
        raw = client.call_raw("aris_download_baseline")
        self.assertTrue(raw["isError"])
        self.assertEqual(
            json.loads(raw["content"][0]["text"])["error"],
            "downloads_directory_unavailable",
        )
        self.assertNotIn("secret", json.dumps(raw))
        self.assertNotIn(str(outside), json.dumps(raw))

    def test_download_copy_fails_on_collision_and_symlink_sources_never_qualify(self) -> None:
        self.client.select_example()
        baseline = self.client.call("aris_download_baseline")
        outside = Path(self.temp.name) / "outside.pdf"
        outside.write_bytes(b"outside")
        symlink = self.client.downloads / "linked.pdf"
        symlink.symlink_to(outside)
        timed_out = self.client.call_raw(
            "aris_download_wait",
            {
                "baseline_id": baseline["baseline_id"],
                "filename_contains": "linked.pdf",
                "timeout_ms": 120,
            },
            timeout=3,
        )
        self.assertTrue(timed_out["isError"])

        regular = self.client.downloads / "fresh.pdf"
        regular.write_bytes(b"fresh")
        download = self.client.call(
            "aris_download_wait",
            {
                "baseline_id": baseline["baseline_id"],
                "filename_contains": "fresh.pdf",
                "timeout_ms": 1000,
            },
            timeout=3,
        )
        collision = self.client.workspace / ".aris" / "run" / "existing.pdf"
        collision.parent.mkdir(parents=True)
        collision.write_bytes(b"keep")
        failed = self.client.call_raw(
            "aris_copy_download",
            {
                "download_ref": download["download_ref"],
                "destination": ".aris/run/existing.pdf",
            },
        )
        self.assertTrue(failed["isError"])
        self.assertEqual(
            json.loads(failed["content"][0]["text"])["error"], "copy_collision"
        )
        self.assertEqual(collision.read_bytes(), b"keep")

    def test_source_has_no_old_http_client_dependency_or_dangerous_child_calls(self) -> None:
        source = FACADE.read_text(encoding="utf-8")
        self.assertNotIn("chrome_mcp_client", source)
        self.assertNotIn("127.0.0.1:12306", source)
        self.assertEqual(source.count('callTool("evaluate_script"'), 1)
        self.assertIn("script !== FIXED_PDF_DOWNLOAD_SCRIPT", source)
        self.assertIn("script !== FIXED_CNKI_CHALLENGE_PROBE_SCRIPT", source)
        self.assertIn("script !== FIXED_ACTIVE_EDITABLE_VALUE_SCRIPT", source)
        self.assertIn("script !== FIXED_PINNED_EDITABLE_VALUE_SCRIPT", source)
        self.assertIn("aris-active-editable-value-v1", source)
        self.assertIn("aris-pinned-editable-value-v1", source)
        self.assertIn('callTool("evaluate_script", { function: script })', source)
        self.assertNotIn('callTool("fill_form"', source)
        self.assertNotIn('callTool("drag"', source)
        self.assertEqual(source.count('callTool("upload_file"'), 1)
        self.assertIn("await this.#assertSafeUploadSource(args.source)", source)
        self.assertIn("if (!isUploadTarget(target))", source)
        self.assertIn('capabilities: { roots: { listChanged: false } }', source)
        self.assertIn('message.method === "roots/list"', source)
        self.assertIn("pathToFileURL(this.workspaceRoot).href", source)
        self.assertNotIn("--allowUnrestrictedPaths", source)
        self.assertNotIn('callTool("list_network_requests"', source)
        self.assertNotIn('callTool("take_memory_snapshot"', source)
        self.assertIn('await this.child.callTool("click"', source)
        self.assertIn('dblClick: false', source)

    def test_profile_cli_status_is_non_mutating_and_stop_refuses_unverified_pid(self) -> None:
        root = Path(self.temp.name) / "profile-cli"
        home = root / "home"
        config_home = (
            home / ".config" / "agent-skills" / "my-agent-browser"
        )
        profile = config_home / "user-data"
        profile.mkdir(parents=True)
        config_home.mkdir(parents=True, exist_ok=True)
        (config_home / "config.json").write_text(
            json.dumps(
                {
                    "browser": {
                        "userDataDir": str(profile),
                        "debuggingPort": 45123,
                        "browserUrl": "",
                    }
                }
            ),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["HOME"] = str(home)

        status = subprocess.run(
            ["node", str(FACADE), "profile", "status"],
            cwd=REPO_ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(
            json.loads(status.stdout),
            {"ok": True, "running": False, "verified": False, "reason": "lock_absent"},
        )

        lock = {
            "version": 1,
            "pid": os.getpid(),
            "port": 45123,
            "profileDir": str(profile),
            "executable": "/definitely/not/the-current-process",
            "createdAt": "2026-07-18T00:00:00.000Z",
        }
        (config_home / "aris-external-profile.lock.json").write_text(
            json.dumps(lock), encoding="utf-8"
        )
        stopped = subprocess.run(
            ["node", str(FACADE), "profile", "stop"],
            cwd=REPO_ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(stopped.returncode, 1, stopped.stderr)
        self.assertEqual(
            json.loads(stopped.stdout)["error"],
            "profile_stop_refused_unverified_owner",
        )
        os.kill(os.getpid(), 0)

    def test_profile_chrome_args_are_dedicated_and_explicit(self) -> None:
        javascript = f"""
          import {{ buildProfileChromeArgs, processCommandMatchesProfile }} from {json.dumps(FACADE.as_uri())};
          const args = buildProfileChromeArgs({{
            port: 45123,
            profileDir: '/safe/dedicated-profile',
            viewport: 'maximized',
          }});
          const lock = {{
            executable: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            port: 45123,
            profileDir: '/safe/dedicated-profile',
          }};
          const exact = `${{lock.executable}} ${{args.join(' ')}}`;
          console.log(JSON.stringify({{
            args,
            matches: processCommandMatchesProfile(exact, lock),
            wrongPort: processCommandMatchesProfile(exact.replace('45123', '45124'), lock),
            wrongProfile: processCommandMatchesProfile(exact.replace('/safe/dedicated-profile', '/tmp/other'), lock),
          }}));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("--remote-debugging-port=45123", payload["args"])
        self.assertIn("--user-data-dir=/safe/dedicated-profile", payload["args"])
        self.assertIn("--start-maximized", payload["args"])
        self.assertTrue(payload["matches"])
        self.assertFalse(payload["wrongPort"])
        self.assertFalse(payload["wrongProfile"])


if __name__ == "__main__":
    unittest.main()
