from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLIENT = REPO_ROOT / "skills" / "browser-session-bridge" / "scripts" / "chrome_mcp_client.mjs"


def run_client(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(CLIENT), *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )


class ChromeMcpClientTests(unittest.TestCase):
    def test_help_is_offline_and_documents_commands(self) -> None:
        result = run_client("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("list-tools", result.stdout)
        self.assertIn("schema TOOL", result.stdout)
        self.assertIn("tabs --url-contains STR", result.stdout)
        self.assertIn("call SAFE_TOOL --args-json JSON", result.stdout)
        self.assertIn("exact-text --text TEXT", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_symlinked_installed_entrypoint_runs_main(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            linked_client = Path(temp_dir) / "chrome_mcp_client.mjs"
            linked_client.symlink_to(CLIENT)
            result = subprocess.run(
                ["node", str(linked_client), "--help"],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tabs --url-contains STR", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_argument_errors_are_json_and_exit_two_without_connecting(self) -> None:
        cases = [
            ("tabs",),
            ("call", "chrome_read_page", "--args-json", "not-json"),
            ("call", "chrome_read_page", "--args-json", "[]"),
            ("schema",),
            ("list-tools", "unexpected"),
            ("exact-text",),
            ("exact-text", "--text", "target", "--scope-selector", ""),
            ("exact-text", "--text", "target", "--scope-selector", "main", "--tab-id", "7", "--click"),
            ("exact-selector-click", "--text", "target", "--scope-selector", "main", "--tab-id", "7"),
        ]
        for args in cases:
            with self.subTest(args=args):
                result = run_client(*args)
                self.assertEqual(result.returncode, 2, result.stdout)
                payload = json.loads(result.stdout)
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["exit_code"], 2)
                self.assertEqual(result.stderr, "")

    def test_tabs_filter_can_match_stable_spa_route_without_exposing_fragment(self) -> None:
        module_script = f"""
          import {{ extractMatchingTabs }} from {json.dumps(CLIENT.as_uri())};
          const result = {{ content: [{{ type: 'text', text: JSON.stringify({{
            windows: [{{ id: 9, focused: true, tabs: [{{
              id: 17,
              active: true,
              url: 'https://data.csmar.com/csmar.html#/datacenter/singletable'
            }}] }}]
          }}) }}] }};
          process.stdout.write(JSON.stringify(extractMatchingTabs(result, 'csmar.html#/datacenter/singletable')));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", module_script],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        tabs = json.loads(result.stdout)
        self.assertEqual(len(tabs), 1)
        self.assertEqual(tabs[0]["tabId"], 17)
        self.assertEqual(tabs[0]["url"], "https://data.csmar.com/csmar.html")
        self.assertNotIn("#", result.stdout)

    def test_tabs_reports_unknown_focus_as_unsupported_not_false(self) -> None:
        # The public CLI is exercised against the live-shape fixture in the
        # compatibility test below; keep this assertion close to the source so
        # a future refactor cannot silently restore unknown == false.
        source = CLIENT.read_text(encoding="utf-8")
        self.assertIn('windowFocused: windowFocusStates.get(String(tab.windowId)) ?? null', source)
        self.assertIn('? "supported"', source)
        self.assertIn(': "unsupported"', source)

    def test_legacy_read_accepts_active_unique_tab_when_old_extension_omits_focus_telemetry(self) -> None:
        javascript = f"""
          import {{ callToolWithCompatibility }} from {json.dumps(CLIENT.as_uri())};
          const calls = [];
          const client = {{
            async callTool(request) {{
              calls.push(request.name);
              if (request.name === 'chrome_read_page') return {{
                isError: true,
                content: [{{ type: 'text', text: 'Tool chrome_read_page not found' }}],
              }};
              if (request.name === 'get_windows_and_tabs') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  windows: [{{ windowId: 1, tabs: [{{
                    tabId: 7, active: true, url: 'https://example.test/unique'
                  }}] }}],
                }}) }}],
              }};
              if (request.name === 'chrome_get_interactive_elements') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  success: true, count: 1, elements: [{{ selector: '#safe', text: 'Safe' }}]
                }}) }}],
              }};
              throw new Error(`unexpected ${{request.name}}`);
            }},
          }};
          const result = await callToolWithCompatibility(
            client,
            [{{ name: 'chrome_read_page' }}],
            'chrome_read_page',
            {{ tabId: 7, selector: '#safe', includeCoordinates: false }},
            1000,
          );
          console.log(JSON.stringify({{ calls, compatibility: result._meta['aris.compatibility'] }}));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["calls"],
            ["chrome_read_page", "get_windows_and_tabs", "chrome_get_interactive_elements"],
        )
        self.assertEqual(payload["compatibility"], "chrome_extension_0_0_6")

    def test_missing_target_focus_is_rejected_when_extension_reports_focus_elsewhere(self) -> None:
        javascript = f"""
          import {{ callToolWithCompatibility }} from {json.dumps(CLIENT.as_uri())};
          const calls = [];
          const client = {{
            async callTool(request) {{
              calls.push(request.name);
              if (request.name === 'chrome_read_page') return {{
                isError: true,
                content: [{{ type: 'text', text: 'Tool chrome_read_page not found' }}],
              }};
              if (request.name === 'get_windows_and_tabs') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  windows: [
                    {{ windowId: 1, focused: true, tabs: [{{ tabId: 1, active: true, url: 'https://other.test/' }}] }},
                    {{ windowId: 2, tabs: [{{ tabId: 7, active: true, url: 'https://example.test/unique' }}] }}
                  ],
                }}) }}],
              }};
              throw new Error('read must not continue');
            }},
          }};
          try {{
            await callToolWithCompatibility(
              client,
              [{{ name: 'chrome_read_page' }}],
              'chrome_read_page',
              {{ tabId: 7, selector: '#safe' }},
              1000,
            );
          }} catch (error) {{
            console.log(JSON.stringify({{ calls, message: error.message, exitCode: error.exitCode }}));
          }}
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["calls"], ["chrome_read_page", "get_windows_and_tabs"])
        self.assertIn("focus_telemetry_missing", payload["message"])
        self.assertEqual(payload["exitCode"], 6)

    def test_redaction_self_test_is_offline(self) -> None:
        result = run_client("self-test")
        self.assertEqual(result.returncode, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertIn("deep-redaction", payload["checks"])
        self.assertNotIn("do-not-print", result.stdout)

    def test_cli_rejects_non_allowlisted_tool_before_connecting(self) -> None:
        cases = [
            ("chrome_inject_script", '{"jsScript":"document.cookie"}'),
            ("chrome_get_web_content", '{"selector":"body","htmlContent":true}'),
        ]
        for tool, arguments in cases:
            with self.subTest(tool=tool):
                result = run_client("call", tool, "--args-json", arguments)
                self.assertEqual(result.returncode, 2, result.stdout)
                payload = json.loads(result.stdout)
                self.assertIn("non-allowlisted", payload["error"])
                self.assertNotIn("document.cookie", result.stdout)

    def test_cli_rejects_signed_navigation_url_before_connecting(self) -> None:
        cases = [
            "https://example.test/file?X-Amz-Signature=FABRICATED",
            "https://example.test/file?apiKey=FABRICATED",
            "https://example.test/file?apikey=FABRICATED",
            "https://example.test/file?authToken=FABRICATED",
            "https://example.test/file?sessionId=FABRICATED",
            "https://example.test/file?AWSAccessKeyId=FABRICATED",
            "https://example.test/file#access_token=FABRICATED",
            "https://example.test/file#id_token=FABRICATED",
            "https://example.test/file#apiKey=FABRICATED",
            "https://example.test/file#sessionId=FABRICATED",
            "https://example.test/file#%73ig=FABRICATED",
            "https://example.test/file#/callback?access_token=FABRICATED",
            "https://example.test/file?code=FABRICATED",
            "https://example.test/file?SAMLResponse=FABRICATED",
            "https://example.test/file?next=https%3A%2F%2Fprivate.test%2Fcb%3Faccess_token%3DFABRICATED",
            "https://example.test/file?payload=%257B%2522apiKey%2522%253A%2522FABRICATED%2522%257D",
            "https://example.test/file#next=https%253A%252F%252Fprivate.test%252Fcb%253FsessionId%253DFABRICATED",
        ]
        for url in cases:
            with self.subTest(url=url):
                result = run_client(
                    "call",
                    "chrome_navigate",
                    "--args-json",
                    json.dumps({"tabId": 7, "url": url}),
                )
                self.assertEqual(result.returncode, 2, result.stdout)
                payload = json.loads(result.stdout)
                self.assertIn("signed or credential-bearing", payload["error"])
                self.assertNotIn("FABRICATED", result.stdout)

    def test_legacy_exact_text_rejects_sensitive_url_before_injection(self) -> None:
        sensitive_urls = [
            "https://example.test/private?apiKey=FIXTURE",
            "https://example.test/private?authToken=FIXTURE",
            "https://example.test/private?sessionId=FIXTURE",
            "https://example.test/private?AWSAccessKeyId=FIXTURE",
            "https://example.test/private#access_token=FIXTURE",
            "https://example.test/private#id_token=FIXTURE",
            "https://example.test/private#apiKey=FIXTURE",
            "https://example.test/private#sessionId=FIXTURE",
            "https://example.test/private#%73ig=FIXTURE",
            "https://example.test/private?next=https%3A%2F%2Fprivate.test%2Fcb%3Faccess_token%3DFIXTURE",
            "https://example.test/private#payload=%257B%2522SAMLResponse%2522%253A%2522FIXTURE%2522%257D",
        ]
        for url in sensitive_urls:
            with self.subTest(url=url):
                javascript = f"""
                  import {{ legacyExactTextOperation }} from {json.dumps(CLIENT.as_uri())};
                  const calls = [];
                  const client = {{
                    async callTool(request) {{
                      calls.push(request);
                      if (request.name !== 'get_windows_and_tabs') {{
                        throw new Error('sensitive URL reached a mutation tool');
                      }}
                      return {{
                        isError: false,
                        content: [{{ type: 'text', text: JSON.stringify({{
                          windows: [{{ windowId: 1, focused: true, tabs: [{{
                            tabId: 7, active: true, url: {json.dumps(url)}
                          }}] }}],
                        }}) }}],
                      }};
                    }},
                  }};
                  try {{
                    await legacyExactTextOperation(
                      client,
                      {{ text: 'target', scopeSelector: 'main', tabId: 7 }},
                      1000,
                    );
                  }} catch (error) {{
                    console.log(JSON.stringify({{
                      callNames: calls.map((call) => call.name),
                      leakedArguments: calls.some((call) => JSON.stringify(call.arguments ?? {{}}).includes('FIXTURE')),
                      message: error.message,
                      exitCode: error.exitCode,
                    }}));
                  }}
                """
                result = subprocess.run(
                    ["node", "--input-type=module", "--eval", javascript],
                    cwd=REPO_ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["callNames"], ["get_windows_and_tabs"])
                self.assertFalse(payload["leakedArguments"])
                self.assertIn("signed or credential-bearing", payload["message"])
                self.assertEqual(payload["exitCode"], 6)

    def test_exported_redactor_removes_deep_secrets_queries_and_payloads(self) -> None:
        javascript = f"""
          import {{ sanitizeDeep, serializeCapped, extractMatchingTabs }} from {json.dumps(CLIENT.as_uri())};
          const input = {{
            password: 'pw-leak',
            nested: {{
              token: 'token-leak',
              url: 'https://example.test/a.pdf?sig=query-leak#frag',
              signed_url: '/download/a.pdf?X-Amz-Signature=relative-query-leak',
              callback: '/download?auth=relative-auth-leak',
              csrfToken: 'csrf-token-leak',
              raw_html: '<input type="hidden" name="csrfToken" value="html-csrf-leak">',
              header: {{ name: 'Cookie', value: 'header-leak' }},
              content: {{ type: 'image', data: '{'Q' * 160}' }},
              text: 'ordinary browser text '.repeat(180),
            }},
          }};
          const result = {{ content: [{{ type: 'text', text: JSON.stringify({{
            windows: [
              {{ windowId: 10, tabs: [
                {{ tabId: 11, active: true, url: 'https://cnki.net/paper?id=query-leak' }},
                {{ tabId: 12, active: false, url: 'https://private.test/mail?secret=private-leak' }},
              ] }},
            ],
          }}) }}] }};
          console.log(JSON.stringify({{
            sanitized: sanitizeDeep(input),
            capped: serializeCapped({{ text: 'z'.repeat(10000) }}, 1024),
            tabs: extractMatchingTabs(result, 'cnki.net'),
          }}));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        rendered = json.dumps(payload, ensure_ascii=False)
        for secret in (
            "pw-leak",
            "token-leak",
            "query-leak",
            "relative-query-leak",
            "relative-auth-leak",
            "csrf-token-leak",
            "html-csrf-leak",
            "header-leak",
            "private-leak",
        ):
            self.assertNotIn(secret, rendered)
        self.assertIn("REDACTED_SENSITIVE_FIELD", rendered)
        self.assertIn("REDACTED_ENCODED_STRING", rendered)
        self.assertIn("TRUNCATED_LONG_STRING", rendered)
        self.assertLessEqual(len(payload["capped"].encode("utf-8")), 1024)
        self.assertEqual(
            payload["tabs"],
            [{"tabId": 11, "windowId": 10, "active": True, "url": "https://cnki.net/paper"}],
        )

    def test_reference_defines_mcp_only_fallback_and_short_sessions(self) -> None:
        reference = (
            REPO_ROOT
            / "skills"
            / "browser-session-bridge"
            / "references"
            / "grok-chrome-mcp.md"
        ).read_text(encoding="utf-8")
        self.assertIn("dynamic `search_tool` / `use_tool`", reference)
        self.assertIn("Tool not found", reference)
        self.assertIn("HTTP 413", reference)
        self.assertIn("Streamable HTTP", reference)
        self.assertIn("one short operation", reference)
        self.assertIn("version skew", reference)
        self.assertIn("filenameContains", reference)
        self.assertIn("CSS selectors only", reference)
        self.assertNotIn("browser` MCP is an acceptable fallback", reference)

    def test_read_page_falls_back_when_extension_lacks_advertised_tool(self) -> None:
        javascript = f"""
          import {{ callToolWithCompatibility }} from {json.dumps(CLIENT.as_uri())};
          const calls = [];
          const client = {{
            async callTool(request) {{
              calls.push(request);
              if (request.name === 'chrome_read_page') return {{
                isError: true,
                content: [{{ type: 'text', text: 'Tool chrome_read_page not found' }}],
              }};
              if (request.name === 'get_windows_and_tabs') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  windows: [{{ windowId: 1, focused: true, tabs: [{{
                    tabId: 7, active: true, url: 'https://example.test/private?opaque=never-output'
                  }}] }}],
                }}) }}],
              }};
              if (request.name === 'chrome_get_interactive_elements') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  success: true,
                  count: 1,
                  elements: [{{ selector: '#preview', text: 'Preview' }}],
                }}) }}],
              }};
              throw new Error(`unexpected ${{request.name}}`);
            }},
          }};
          const result = await callToolWithCompatibility(
            client,
            [{{ name: 'chrome_read_page' }}],
            'chrome_read_page',
            {{ tabId: 7, selector: '#preview', includeCoordinates: false }},
            1000,
          );
          console.log(JSON.stringify({{ calls, result }}));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            [call["name"] for call in payload["calls"]],
            ["chrome_read_page", "get_windows_and_tabs", "chrome_get_interactive_elements"],
        )
        self.assertEqual(payload["calls"][-1]["arguments"]["selector"], "#preview")
        self.assertFalse(payload["calls"][-1]["arguments"]["includeCoordinates"])
        self.assertEqual(
            payload["result"]["_meta"]["aris.compatibility"],
            "chrome_extension_0_0_6",
        )

    def test_switch_tab_refuses_legacy_background_target_without_navigation(self) -> None:
        javascript = f"""
          import {{ callToolWithCompatibility }} from {json.dumps(CLIENT.as_uri())};
          const calls = [];
          const client = {{
            async callTool(request) {{
              calls.push(request);
              if (request.name === 'chrome_switch_tab') return {{
                isError: true,
                content: [{{ type: 'text', text: 'Tool chrome_switch_tab not found' }}],
              }};
              if (request.name === 'get_windows_and_tabs') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  windows: [{{ windowId: 1, focused: true, tabs: [{{
                    tabId: 9, active: false, url: 'https://example.test/path?opaque=value'
                  }}] }}],
                }}) }}],
              }};
              throw new Error(`unexpected ${{request.name}}`);
            }},
          }};
          try {{
            await callToolWithCompatibility(
              client,
              [{{ name: 'chrome_switch_tab' }}],
              'chrome_switch_tab',
              {{ tabId: 9 }},
              1000,
            );
          }} catch (error) {{
            console.log(JSON.stringify({{ calls, message: error.message, exitCode: error.exitCode }}));
          }}
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            [call["name"] for call in payload["calls"]],
            ["chrome_switch_tab", "get_windows_and_tabs"],
        )
        self.assertIn("target_tab_not_foreground", payload["message"])
        self.assertEqual(payload["exitCode"], 6)

    def test_modern_switch_semantic_failure_stops_before_mutation(self) -> None:
        javascript = f"""
          import {{ callToolWithCompatibility }} from {json.dumps(CLIENT.as_uri())};
          const calls = [];
          const client = {{
            async callTool(request) {{
              calls.push(request);
              if (request.name === 'chrome_switch_tab') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{ success: false }}) }}],
              }};
              throw new Error('mutation must not run');
            }},
          }};
          try {{
            await callToolWithCompatibility(
              client,
              [{{ name: 'chrome_switch_tab' }}, {{ name: 'chrome_click_element' }}],
              'chrome_click_element',
              {{ tabId: 99, selector: '#danger' }},
              1000,
            );
          }} catch (error) {{
            console.log(JSON.stringify({{
              calls, message: error.message, exitCode: error.exitCode, details: error.details,
            }}));
          }}
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual([call["name"] for call in payload["calls"]], ["chrome_switch_tab"])
        self.assertIn("semantic failure", payload["message"])
        self.assertEqual(payload["exitCode"], 6)
        self.assertFalse(payload["details"]["retryable"])
        self.assertEqual(payload["details"]["effect_state"], "unknown")
        self.assertTrue(payload["details"]["state_check_required"])

    def test_modern_switch_is_reverified_and_target_tool_keeps_tab_id(self) -> None:
        javascript = f"""
          import {{ callToolWithCompatibility }} from {json.dumps(CLIENT.as_uri())};
          const calls = [];
          const client = {{
            async callTool(request) {{
              calls.push(request);
              if (request.name === 'chrome_switch_tab') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{ success: true }}) }}],
              }};
              if (request.name === 'get_windows_and_tabs') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  windows: [{{ windowId: 3, focused: true, tabs: [{{
                    tabId: 99, active: true, url: 'https://example.test/target'
                  }}] }}],
                }}) }}],
              }};
              if (request.name === 'chrome_click_element') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{ success: true }}) }}],
              }};
              throw new Error(`unexpected ${{request.name}}`);
            }},
          }};
          await callToolWithCompatibility(
            client,
            [{{ name: 'chrome_switch_tab' }}, {{ name: 'chrome_click_element' }}],
            'chrome_click_element',
            {{ tabId: 99, selector: '#safe' }},
            1000,
          );
          console.log(JSON.stringify(calls));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = json.loads(result.stdout)
        self.assertEqual(
            [call["name"] for call in calls],
            ["chrome_switch_tab", "get_windows_and_tabs", "chrome_click_element"],
        )
        self.assertEqual(calls[-1]["arguments"]["tabId"], 99)

    def test_direct_modern_switch_is_reverified_before_success(self) -> None:
        javascript = f"""
          import {{ callToolWithCompatibility }} from {json.dumps(CLIENT.as_uri())};
          const calls = [];
          const client = {{
            async callTool(request) {{
              calls.push(request);
              if (request.name === 'chrome_switch_tab') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{ success: true }}) }}],
              }};
              if (request.name === 'get_windows_and_tabs') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  windows: [{{ windowId: 3, focused: true, tabs: [{{
                    tabId: 99, active: true, url: 'https://example.test/target'
                  }}] }}],
                }}) }}],
              }};
              throw new Error(`unexpected ${{request.name}}`);
            }},
          }};
          const result = await callToolWithCompatibility(
            client,
            [{{ name: 'chrome_switch_tab' }}],
            'chrome_switch_tab',
            {{ tabId: 99 }},
            1000,
          );
          console.log(JSON.stringify({{ calls, result }}));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            [call["name"] for call in payload["calls"]],
            ["chrome_switch_tab", "get_windows_and_tabs"],
        )
        public = json.loads(payload["result"]["content"][0]["text"])
        self.assertTrue(public["success"])
        self.assertTrue(public["activated"])
        self.assertEqual(public["tabId"], 99)

    def test_legacy_double_click_is_rejected_before_any_click(self) -> None:
        javascript = f"""
          import {{ callToolWithCompatibility }} from {json.dumps(CLIENT.as_uri())};
          let calls = 0;
          try {{
            await callToolWithCompatibility(
              {{ async callTool() {{ calls += 1; throw new Error('must not call'); }} }},
              [],
              'chrome_computer',
              {{ action: 'double_click', selector: '#item' }},
              1000,
            );
          }} catch (error) {{
            console.log(JSON.stringify({{
              calls, message: error.message, exitCode: error.exitCode, details: error.details,
            }}));
          }}
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["calls"], 0)
        self.assertIn("non-atomic double_click", payload["message"])
        self.assertFalse(payload["details"]["retryable"])
        self.assertEqual(payload["details"]["effect_state"], "not_started")

    def test_legacy_click_failure_reports_unknown_effect_state(self) -> None:
        javascript = f"""
          import {{ callToolWithCompatibility }} from {json.dumps(CLIENT.as_uri())};
          const calls = [];
          const client = {{
            async callTool(request) {{
              calls.push(request.name);
              if (request.name === 'chrome_computer') return {{
                isError: true,
                content: [{{ type: 'text', text: 'Tool chrome_computer not found' }}],
              }};
              if (request.name === 'get_windows_and_tabs') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  windows: [{{ windowId: 1, focused: true, tabs: [{{
                    tabId: 7, active: true, url: 'https://example.test/target'
                  }}] }}],
                }}) }}],
              }};
              if (request.name === 'chrome_click_element') return {{
                isError: true,
                content: [{{ type: 'text', text: 'fabricated click timeout' }}],
              }};
              throw new Error(`unexpected ${{request.name}}`);
            }},
          }};
          try {{
            await callToolWithCompatibility(
              client,
              [{{ name: 'chrome_computer' }}],
              'chrome_computer',
              {{ tabId: 7, action: 'click', selector: '#target' }},
              1000,
            );
          }} catch (error) {{
            console.log(JSON.stringify({{
              calls, message: error.message, exitCode: error.exitCode, details: error.details,
            }}));
          }}
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["calls"],
            ["chrome_computer", "get_windows_and_tabs", "chrome_click_element"],
        )
        self.assertIn("fabricated click timeout", payload["message"])
        self.assertFalse(payload["details"]["retryable"])
        self.assertEqual(payload["details"]["effect_state"], "unknown")
        self.assertTrue(payload["details"]["state_check_required"])

    def test_compatibility_layer_rejects_non_allowlisted_advertised_tool(self) -> None:
        javascript = f"""
          import {{ callToolWithCompatibility }} from {json.dumps(CLIENT.as_uri())};
          let calls = 0;
          try {{
            await callToolWithCompatibility(
              {{ async callTool() {{ calls += 1; return {{ isError: false }}; }} }},
              [{{ name: 'chrome_inject_script' }}],
              'chrome_inject_script',
              {{ jsScript: 'fetch("https://example.test")' }},
              1000,
            );
          }} catch (error) {{
            console.log(JSON.stringify({{ calls, message: error.message, exitCode: error.exitCode }}));
          }}
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["calls"], 0)
        self.assertIn("non-allowlisted", payload["message"])
        self.assertEqual(payload["exitCode"], 2)

    def test_exact_text_rejects_duplicate_url_before_injection(self) -> None:
        javascript = f"""
          import {{ legacyExactTextOperation }} from {json.dumps(CLIENT.as_uri())};
          const calls = [];
          const client = {{
            async callTool(request) {{
              calls.push(request.name);
              if (request.name !== 'get_windows_and_tabs') throw new Error('unexpected mutation');
              return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  windows: [{{ windowId: 1, focused: true, tabs: [
                    {{ tabId: 7, active: true, url: 'https://example.test/same' }},
                    {{ tabId: 8, active: false, url: 'https://example.test/same' }},
                  ] }}],
                }}) }}],
              }};
            }},
          }};
          try {{
            await legacyExactTextOperation(
              client,
              {{ text: 'target', scopeSelector: 'main', tabId: 7, click: false }},
              1000,
            );
          }} catch (error) {{
            console.log(JSON.stringify({{ calls, message: error.message, exitCode: error.exitCode }}));
          }}
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["calls"], ["get_windows_and_tabs"])
        self.assertIn("exact URL is duplicated", payload["message"])
        self.assertEqual(payload["exitCode"], 6)

    def test_legacy_download_requires_narrow_filename_filter(self) -> None:
        javascript = f"""
          import {{ callToolWithCompatibility }} from {json.dumps(CLIENT.as_uri())};
          try {{
            await callToolWithCompatibility(
              {{ async callTool() {{ throw new Error('must not call'); }} }},
              [],
              'chrome_handle_download',
              {{}},
              1000,
            );
          }} catch (error) {{
            console.log(JSON.stringify({{ message: error.message, exitCode: error.exitCode }}));
          }}
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("filenameContains", payload["message"])
        self.assertEqual(payload["exitCode"], 2)

    def test_exact_text_only_scrolls_and_projects_hmac_authenticated_fields(self) -> None:
        javascript = f"""
          import {{ createHmac }} from 'node:crypto';
          import {{ legacyExactTextOperation }} from {json.dumps(CLIENT.as_uri())};
          const calls = [];
          let nonce;
          let hmacKeyHex;
          const evidence = {{
            status: 'ready', candidate_count: 2, deepest_candidate_count: 1, scanned_nodes: 120,
            target_tag: 'span', action_target_tag: 'div', semantic_interactive: true,
            initially_in_viewport: false, before_top: 2069, after_scroll_top: 400,
            viewport_height: 900, attacker_note: 'LEAK-FROM-PAGE-STORAGE-777',
          }};
          const client = {{
            async callTool(request) {{
              calls.push(request);
              if (request.name === 'get_windows_and_tabs') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  windows: [{{ windowId: 1, focused: true, tabs: [{{
                    tabId: 7, active: true, url: 'https://example.test/private?opaque=value'
                  }}] }}],
                }}) }}],
              }};
              if (request.name === 'chrome_inject_script') {{
                const script = request.arguments.jsScript;
                const nonceMatch = script.match(/const nonce = "([0-9a-f]+)"/);
                const keyMatch = script.match(/const hmacKeyHex = "([0-9a-f]+)"/);
                if (nonceMatch && keyMatch) {{ nonce = nonceMatch[1]; hmacKeyHex = keyMatch[1]; }}
                return {{ isError: false, content: [] }};
              }}
              if (request.name === 'chrome_get_web_content') {{
                const signedPayload = {{ ...evidence, nonce }};
                const signature = createHmac('sha256', Buffer.from(hmacKeyHex, 'hex'))
                  .update(JSON.stringify(signedPayload), 'utf8').digest('base64url');
                const envelope = {{ payload: signedPayload, signature }};
                return {{
                  isError: false,
                  content: [{{ type: 'text', text: JSON.stringify({{
                    success: true,
                    htmlContent: `<meta data-aris-result="${{encodeURIComponent(JSON.stringify(envelope))}}">`,
                  }}) }}],
                }};
              }}
              throw new Error(`unexpected ${{request.name}}`);
            }},
          }};
          const result = await legacyExactTextOperation(
            client,
            {{ text: '财务报表', scopeSelector: 'main', tabId: 7 }},
            1000,
          );
          console.log(JSON.stringify({{ calls, result }}));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            [call["name"] for call in payload["calls"]],
            [
                "get_windows_and_tabs",
                "chrome_inject_script",
                "get_windows_and_tabs",
                "chrome_get_web_content",
                "chrome_inject_script",
            ],
        )
        injected = payload["calls"][1]["arguments"]["jsScript"]
        evidence_read = payload["calls"][3]["arguments"]
        self.assertEqual(payload["calls"][1]["arguments"]["type"], "MAIN")
        self.assertEqual(payload["calls"][4]["arguments"]["type"], "MAIN")
        self.assertEqual(evidence_read["url"], "https://example.test/private?opaque=value")
        self.assertTrue(evidence_read["htmlContent"])
        self.assertFalse(evidence_read["textContent"])
        self.assertIn('document.createElement("div")', injected)
        self.assertIn("marker.hidden = true", injected)
        self.assertIn("财务报表", injected)
        self.assertIn("scrollIntoView", injected)
        self.assertIn("elementFromPoint", injected)
        self.assertIn("crypto.subtle", injected)
        self.assertNotIn("target.click()", injected)
        self.assertNotIn("localStorage", injected)
        self.assertNotIn("document.cookie", injected)
        self.assertNotIn("attacker_note", payload["result"])
        self.assertNotIn("LEAK-FROM-PAGE-STORAGE-777", json.dumps(payload["result"]))
        self.assertEqual(payload["result"]["status"], "ready")
        self.assertFalse(payload["result"]["acceptance_evidence"])
        self.assertEqual(payload["result"]["operation"], "exact_text_inspect_and_scroll")
        self.assertEqual(payload["result"]["compatibility"], "chrome_extension_0_0_6")

    def test_exact_selector_click_is_fixed_single_click_and_requires_post_state_read(self) -> None:
        javascript = f"""
          import {{ legacyExactSelectorClickOperation }} from {json.dumps(CLIENT.as_uri())};
          const calls = [];
          const client = {{
            async callTool(request) {{
              calls.push(request);
              if (request.name === 'get_windows_and_tabs') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  windows: [{{ windowId: 1, tabs: [{{
                    tabId: 7, active: true, url: 'https://example.test/unique'
                  }}] }}],
                }}) }}],
              }};
              if (request.name === 'chrome_inject_script') return {{ isError: false, content: [] }};
              throw new Error(`unexpected ${{request.name}}`);
            }},
          }};
          const result = await legacyExactSelectorClickOperation(
            client,
            {{
              text: '财务报表',
              scopeSelector: 'main',
              targetSelector: 'main > section > div:nth-of-type(2)',
              tabId: 7,
            }},
            1000,
          );
          console.log(JSON.stringify({{ calls, result }}));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            [call["name"] for call in payload["calls"]],
            ["get_windows_and_tabs", "chrome_inject_script"],
        )
        injection = payload["calls"][1]["arguments"]
        self.assertEqual(injection["url"], "https://example.test/unique")
        self.assertEqual(injection["type"], "MAIN")
        script = injection["jsScript"]
        self.assertIn("财务报表", script)
        self.assertIn("main > section > div:nth-of-type(2)", script)
        self.assertIn("actionTarget.scrollIntoView", script)
        self.assertEqual(script.count("HTMLElement.prototype.click.call(actionTarget)"), 1)
        for forbidden in ["fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "document.cookie"]:
            self.assertNotIn(forbidden, script)
        self.assertEqual(payload["result"]["effect_state"], "attempted")
        self.assertTrue(payload["result"]["state_check_required"])
        self.assertFalse(payload["result"]["acceptance_evidence"])

    def test_exact_selector_click_rejects_signed_url_before_injection(self) -> None:
        javascript = f"""
          import {{ legacyExactSelectorClickOperation }} from {json.dumps(CLIENT.as_uri())};
          const calls = [];
          const client = {{
            async callTool(request) {{
              calls.push(request.name);
              if (request.name !== 'get_windows_and_tabs') throw new Error('must not inject');
              return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  windows: [{{ windowId: 1, tabs: [{{
                    tabId: 7, active: true,
                    url: 'https://example.test/private?access_token=FIXTURE'
                  }}] }}],
                }}) }}],
              }};
            }},
          }};
          try {{
            await legacyExactSelectorClickOperation(
              client,
              {{ text: 'target', scopeSelector: 'main', targetSelector: '#target', tabId: 7 }},
              1000,
            );
          }} catch (error) {{
            console.log(JSON.stringify({{ calls, message: error.message, exitCode: error.exitCode }}));
          }}
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["calls"], ["get_windows_and_tabs"])
        self.assertIn("signed or credential-bearing", payload["message"])
        self.assertEqual(payload["exitCode"], 6)

    def test_exact_text_rejects_forged_hmac_envelope(self) -> None:
        javascript = f"""
          import {{ legacyExactTextOperation }} from {json.dumps(CLIENT.as_uri())};
          const calls = [];
          let nonce;
          const client = {{
            async callTool(request) {{
              calls.push(request.name);
              if (request.name === 'get_windows_and_tabs') return {{
                isError: false,
                content: [{{ type: 'text', text: JSON.stringify({{
                  windows: [{{ windowId: 1, focused: true, tabs: [{{
                    tabId: 7, active: true, url: 'https://example.test/private'
                  }}] }}],
                }}) }}],
              }};
              if (request.name === 'chrome_inject_script') {{
                const match = request.arguments.jsScript.match(/const nonce = "([0-9a-f]+)"/);
                if (match) nonce = match[1];
                return {{ isError: false, content: [] }};
              }}
              if (request.name === 'chrome_get_web_content') {{
                const envelope = {{
                  payload: {{
                    status: 'ready', nonce, candidate_count: 1,
                    deepest_candidate_count: 1, scanned_nodes: 3,
                    target_tag: 'span', action_target_tag: 'button',
                    semantic_interactive: true, initially_in_viewport: true,
                    before_top: 10, after_scroll_top: 10, viewport_height: 900,
                  }},
                  signature: 'A'.repeat(43),
                }};
                return {{
                  isError: false,
                  content: [{{ type: 'text', text: JSON.stringify({{
                    success: true,
                    htmlContent: `<meta data-aris-result="${{encodeURIComponent(JSON.stringify(envelope))}}">`,
                  }}) }}],
                }};
              }}
              throw new Error(`unexpected ${{request.name}}`);
            }},
          }};
          try {{
            await legacyExactTextOperation(
              client,
              {{ text: 'target', scopeSelector: 'main', tabId: 7 }},
              1000,
            );
          }} catch (error) {{
            console.log(JSON.stringify({{
              calls, message: error.message, exitCode: error.exitCode,
            }}));
          }}
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("signature mismatch", payload["message"])
        self.assertEqual(payload["exitCode"], 6)
        self.assertEqual(payload["calls"].count("chrome_get_web_content"), 1)

    def test_exact_text_script_rejects_disabled_target_without_click_primitive(self) -> None:
        javascript = f"""
          import {{ buildLegacyExactTextScript }} from {json.dumps(CLIENT.as_uri())};
          const attributes = new Map();
          const marker = {{
            id: '',
            setAttribute(name, value) {{ attributes.set(name, value); }},
            remove() {{}},
          }};
          const target = {{
            tagName: 'BUTTON', textContent: '财务报表', parentElement: null,
            hidden: false, inert: false,
            contains(other) {{ return other === this; }},
            closest(selector) {{ return selector.includes('[disabled]') ? this : this; }},
            matches(selector) {{ return selector === ':disabled'; }},
            getAttribute() {{ return null; }},
            hasAttribute() {{ return false; }},
            getBoundingClientRect() {{
              return {{ width: 120, height: 30, top: 10, bottom: 40, left: 10, right: 130 }};
            }},
            scrollIntoView() {{ throw new Error('must not scroll disabled target'); }},
          }};
          const scope = {{
            tagName: 'MAIN', textContent: 'scope', parentElement: null,
            hidden: false, inert: false,
            querySelectorAll() {{ return [target]; }},
            contains(item) {{ return item === scope || item === target; }},
            getAttribute() {{ return null; }},
            getBoundingClientRect() {{
              return {{ width: 800, height: 600, top: 0, bottom: 600, left: 0, right: 800 }};
            }},
          }};
          globalThis.document = {{
            head: {{ appendChild() {{}} }},
            documentElement: {{ appendChild() {{}} }},
            getElementById() {{ return null; }},
            createElement() {{ return marker; }},
            querySelectorAll() {{ return [scope]; }},
            elementFromPoint() {{ return target; }},
          }};
          globalThis.window = {{ innerWidth: 800, innerHeight: 600 }};
          globalThis.performance = {{ now() {{ return 0; }} }};
          globalThis.getComputedStyle = () => ({{
            display: 'block', visibility: 'visible', opacity: '1', pointerEvents: 'auto', cursor: 'pointer',
          }});
          const script = buildLegacyExactTextScript({{
            text: '财务报表', scopeSelector: 'main', markerId: 'marker-abc', nonce: 'abc',
            hmacKeyHex: '11'.repeat(32),
          }});
          await eval(script);
          const envelope = JSON.parse(decodeURIComponent(attributes.get('data-aris-result')));
          const payload = envelope.payload;
          console.log(JSON.stringify({{ payload, hasProgrammaticClick: script.includes('target.click()') }}));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["payload"]["status"], "target_disabled")
        self.assertFalse(payload["hasProgrammaticClick"])

    def test_exact_text_script_rejects_multiple_scopes(self) -> None:
        javascript = f"""
          import {{ buildLegacyExactTextScript }} from {json.dumps(CLIENT.as_uri())};
          const attributes = new Map();
          const marker = {{
            id: '', setAttribute(name, value) {{ attributes.set(name, value); }}, remove() {{}},
          }};
          globalThis.document = {{
            head: {{ appendChild() {{}} }}, documentElement: {{ appendChild() {{}} }},
            getElementById() {{ return null; }}, createElement() {{ return marker; }},
            querySelectorAll() {{ return [{{}}, {{}}]; }},
          }};
          const script = buildLegacyExactTextScript({{
            text: 'target', scopeSelector: 'main', markerId: 'marker-abc', nonce: 'abc',
            hmacKeyHex: '22'.repeat(32),
          }});
          await eval(script);
          const envelope = JSON.parse(decodeURIComponent(attributes.get('data-aris-result')));
          console.log(JSON.stringify(envelope.payload));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", javascript],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ambiguous_scope")
        self.assertEqual(payload["scope_count"], 2)


if __name__ == "__main__":
    unittest.main()
