# Findings & Decisions

## Requirements

- Finish and genuinely accept the business empirical-research chain rather than merely writing skills.
- Acceptance must pass in both Codex and Grok.
- Codex must use its native `chrome:control-chrome` capability and the user's existing Chrome state.
- Grok and other runtimes must use an MCP-backed existing-session Chrome path.
- Complete missing smoke tests, including WRDS SAS acquisition.
- Preserve user changes and the existing Grok worktree.

## Current Verified Findings

- The latest root verifier for run `20260718T011517Z` reports shared P1/P2/P3/P5 `PASS` and the complete Codex P1–P5 runtime `PASS`.
- Codex browser acceptance is complete for CNKI, SSRN, ScienceDirect, Wiley, CNRDS, and CSMAR.
- Grok P1, P5 discovery, and the independent Grok CNKI browser receipt pass. Grok's remaining evidence is P2/P3 invocation, SSRN/ScienceDirect/Wiley acquisition, and CNRDS/CSMAR export.
- P1 is fully evidenced in the shared/Codex path: R/Postgres, inline universe, CCM/CRSP, IBES, CIK fallback, and a real SAS Cloud `qsas` job all pass.
- P2 has an executable `results-to-docx` generator, rendered/a11y QA, normalized configured-author OOXML identity, and separate real-WRDS engineering-chain outputs. Grok independently rebuilt the 10-row pack, passed 7/7 tests and three-page visual/a11y/metadata checks, and now has a root-verifier P2 `PASS`.
- P3 v2 binds three verified PDFs to inspector-generated native render evidence, three enriched method cards, a matrix, a grounded review, visual checks, and an acceptance report. The manifest/processing/card/synthesis six-field artifact identity joins are exact and shared P3 passes 56 recomputed checks; audit values such as `unknown`, `needs_verification`, and `fail` are preserved rather than repaired.
- Grok P1 independently produced a new R/Postgres 10-row inline-universe/CCM/CRSP run and a new SAS Cloud `qsas` job (`34899386`) with 10×6 data, matching schema, clean SAS error audit, and remote/local hash equality; the root Grok P1 gate passes.
- A Grok P3 success can no longer be self-certified by a hashed wrapper: candidate generation occurs in an isolated snapshot without repository tests or prior outputs, the candidate is frozen, and only a post-generation external verifier plus real-bundle JUnit run can issue the runtime wrapper.
- The Chrome MCP compatibility helper now rejects credential-bearing query and fragment parameters before navigation or legacy injection, including camel-case and percent-encoded variants. Public raw-web-content calls remain forbidden, exact-text remains inspect/scroll only, and mutating uncertainty remains machine-readable.
- CNRDS saved-login behavior is now explicit: with user authorization the agent may submit a form already populated by Chrome once, but it may never read, copy, log, or type credential values; empty fields, failure, MFA/account choice, or hard CAPTCHA require handoff.
- P4 Codex acceptance contains real minimal exports: CNRDS CIRD (`000001`, 2020, 2×10) and CSMAR `FS_Combas` (`000001`, 2020-12-31, report type `A`, 1×5). Grok needs independent portal receipts for both.
- P5's recorded acceptance verifies an exact 24-skill portable set for both isolated Codex and Grok discovery, 9 portable shared references, and zero mirror/inventory/validator failures. The local `chrome-mcp` listener later stopped and currently needs extension reconnection; that operational outage does not rewrite the historical P5 discovery receipt but blocks new protected-site runs.
- After the remaining Grok receipts, release work is limited to final mirror sync/check, the full relevant suite/root verifier, diff review, and commit. Prepared prompts or stopped sessions are not running-gate evidence.

## Research Findings and Historical Resolution

- At task start, the Grok session had implemented P1–P4 in a separate legacy business-skills worktree, but none of that work was committed; it remains preserved continuity context rather than the implementation target.
- That worktree branch is 296 commits behind current `main` and has 3 branch-only historical commits.
- At task start, `main` was clean at `c5f3d5b`; implementation now uses the dirty working branch `codex/business-research-e2e` pending final review and commit.
- Grok's `chrome-mcp` is healthy and advertises 27 tools through a bridge parented by the user's real Google Chrome process, so it can reuse the real profile/login state. The loaded legacy extension does not implement every advertised modern tool; the project helper supplies the verified compatibility layer.
- Grok's separate `browser` MCP is healthy but launches a separate headless profile under `~/.config/agent-skills/my-agent-browser/user-data`, so it is not the protected-portal path.
- Vendored CNKI/ScienceDirect skills hard-code Chrome DevTools MCP names such as `mcp__chrome-devtools__navigate_page`, while Grok uses a `chrome_*` MCP surface. The bridge advertises modern read/JavaScript/download tools, but the loaded legacy extension requires the project's old-tool compatibility mappings and CSS-only interaction path.
- The initial user-reported Grok CNKI success was converted into an independent hashed Grok CNKI receipt through the portable browser-session contract.
- The initial Grok discovery gap is resolved: isolated `grok inspect` now discovers the exact 24 project-sourced portable business skills and P5 passes.
- The initial partial P1 state is resolved: WRDS SAS Cloud, IBES, CIK fallback, CCM/CRSP, and inline-universe evidence now pass the root verifier.
- The initial ad hoc P3 state is resolved for shared/Codex evidence through P3 v2; only Grok's independent P3 invocation and three non-CNKI browser receipts remain.
- The initial prose-only P4 state is resolved in Codex with verified CNRDS/CSMAR exports; Grok still requires independent exports.
- The initial P2 smoke-only state is resolved with an executable generator and render/a11y/metadata acceptance; Grok still requires an invocation receipt.
- At task start, current `main` contained only `business-number-audit` from the prior business suite; the remaining workflow has since been integrated on `codex/business-research-e2e` but is not yet committed.
- The initial selective port deliberately omitted hand-copied `skills/skills-codex` mirrors and the 18 hard-coded CNKI/ScienceDirect top-level skills; the accepted portable mirror was later generated mechanically from canonical sources.
- The old `method-harvest` conflation was resolved by separating acquisition into `fulltext-acquire` and keeping verified-PDF extraction in `method-harvest`.
- Canonical browser workflows need an explicit adapter contract; a prose instruction to “map tool names” is insufficient.
- Codex packaging still installs generated copies from `skills/skills-codex`, but generation/catalog wiring is now present and the recorded P5 mirror/inventory checks pass; a final post-Grok sync/check remains before commit.
- Current selective installation is driven by `tools/skill-groups.tsv`; therefore dual-runtime discovery must be expressed through the existing catalog rather than by reviving the stale standalone business installers.
- Grok Build `0.2.102` discovers user skills from both `~/.grok/skills` and `~/.agents/skills`; its current inspection reports multiple skills sourced directly from `~/.agents/skills`. This gives Codex and Grok a shared project/global installation surface without changing `~/.grok/config.toml`.
- The earlier Grok inspection that lacked the business suite is superseded by isolated 24/24 project discovery; MCP health was never the discovery blocker.
- A single `browser-session-bridge` can enforce runtime selection and return a common redacted receipt while leaving selectors and business filters in site recipes. This is the concrete boundary that the previous “map tool names” prose lacked.
- Generic browser-download integrity can be tested deterministically across runtimes: reject HTML masquerading as a file, verify PDF magic/EOF, validate XLSX/ZIP structure, accept UTF-8 or GB18030 CSV, and always hash the result.
- The P3 OA path now has current real evidence: OpenAlex matched NBER Working Paper 23255; the SSRN delivery endpoint returned HTTP 403, while the official NBER PDF endpoint produced an 875,844-byte valid PDF with SHA-256 `f69be9aa4373ff67db8a98b9bcb27ff3576067ae82a1337a88e1aaed998847a2`.
- Visual and text inspection confirmed the acquired file is *Corporate Culture: Evidence from the Field* (79 pages), and a source-located method card was produced from its survey design, sample, variables, inference, data sources, and noncausal identification caveat.
- A fresh Codex-native CNKI run passed from the blank search page through an identity-matched detail page and explicit PDF control. The accepted thesis PDF is 2,086,277 bytes, 67 pages, SHA-256 `79b6a8b9f2c6f075343f1322c38ff4c6c79abedba8ed963cee5f8a6094a28117`, and its title/author/institution were confirmed from page state, extracted text, and a rendered cover.
- CNKI preloads Tencent CAPTCHA DOM at approximately `y=-1000000`. The semantic snapshot and locator `isVisible()` both exposed “拖动下方拼图完成验证”, while the screenshot showed no challenge and all operations worked. CAPTCHA detection must require viewport intersection and an actually blocked intended action.
- CNKI completed the PDF landing without emitting the Codex native download event. A narrow recent-file check of the controlled download directory found the new file; stable landing plus the standard integrity, hash, identity, and render checks is a valid recorded fallback.
- The CNKI method card extracted a 2017 questionnaire window, 370 distributed/354 valid responses, four quality-culture dimensions, perceived financial/non-financial performance, three commitment dimensions, SPSS/AMOS analysis, and a noncausal claim ceiling. It also flags an internal Table 22 `t=1.235` / `p=0.000` inconsistency.
- The SSRN HTTP 403 came from a direct unauthenticated client and does not show that Chrome access is blocked. SSRN should wait for its passive Cloudflare challenge to clear without clicking; ScienceDirect may require an interactive challenge and therefore an action-time human confirmation.
- At task start the business route referenced `business-number-audit` while the main-branch directory was empty. Its actual skill/checker was recovered read-only from the preserved worktree and added to the portable package, closing that audit break.
- The exact CNKI acceptance case now passes in Grok Build through the project-installed `chrome-mcp`: the independently landed 67-page file is byte-identical to the Codex artifact, and no viewport-blocking challenge appeared.
- SSRN's real Chrome path behaves differently from direct HTTP: its passive Cloudflare interstitial cleared automatically after a short wait and the browser emitted a successful download event for the 79-page target paper.
- ScienceDirect presented a real interactive checkbox challenge. After the authorized click, the existing session showed Tsinghua institutional access; the article's visible PDF viewer downloaded a valid 526,357-byte, 19-page PDF. Direct delivery requests were not a reliable substitute and dynamic delivery URLs must never be retained.
- The ScienceDirect paper supplies a useful P3→P4 bridge: 1,030 private Chinese listed firms for 2014, hand-collected website culture indicators, CSMAR financials, CNKI patent data, factor-based culture promotion, OLS with industry effects and robust t-statistics, and an explicit association-only claim ceiling.
- After the allowed IP was corrected, WRDS R/Postgres immediately passed both a minimal query and a real 10-firm inline-universe → CCM → CRSP workflow. The earlier host-side disconnect was environmental, not a defect in the R bridge.
- The original `business-lit-review` is usable as the discovery/positioning layer, but its former output contract stopped before fulltext synthesis. The accepted design keeps acquisition in `fulltext-acquire`, enriches per-paper evidence in `method-harvest`, then re-enters `business-lit-review` in `fulltext_synthesis` mode to produce a cross-paper evidence matrix and grounded prose.
- Real use on three culture papers exposed why formula-level extraction matters: Zhao et al. explicitly define `Ln(1 + Words)` but label several other zero-containing counts and patents with a plain natural log, without a zero-handling rule; the exact calculation is therefore `needs_verification`, not an inferred `log1p` implementation.
- Cross-paper synthesis must distinguish stated values, lived norms, formal institutions, public culture promotion, and quality culture. The apparent disagreement between positive perceived-performance associations and negative/null market/accounting results is primarily a measurement/design difference, not a clean substantive conflict.
- WRDS P1 now has complete real evidence. Official IBES linking passed; the WRDS SEC schema denied permission and correctly triggered the `farr` fallback; a real SAS Cloud `qsas` job returned a 10×6 Compustat extract with clean error checks and byte-identical remote/local outputs.
- P3 PDF handling is now an explicit stage rather than an implicit read: each paper has a `aris.method-harvest.pdf-inspection.v1` receipt with identity, hash/pages/size, text-layer classification, and source-preservation facts. All three route through native text; Duan's six sparse/empty candidates were visually cleared, so OCR was not used.
- Root P3 acceptance does not trust a prose `PASS`: it re-hashes artifacts, parses structured method-card fields/tokens, cross-checks PDF and inspector lineage, and rejects legacy or semantically weakened receipts.
- The Codex CNRDS fallback records that the authorized UI export completed while Chrome blocked the direct landing; a one-time fetch of the UI-generated URL was used without persisting it. CSMAR emitted a normal browser download event. Both artifacts were then independently verified.

## Technical Decisions

| Decision | Rationale |
|---|---|
| Define semantic browser operations and platform adapters | Canonical site workflows should express intent, not runtime-specific tool names. |
| Separate fulltext acquisition from method extraction | Browser/download concerns and PDF method extraction have different failure modes and consumers. |
| Reuse one session contract for P3 and P4 | CNKI/ScienceDirect and CSMAR/CNRDS share authenticated-browser mechanics while retaining separate site recipes and artifact contracts. |
| Verify downloads after landing | A click is not proof; validate magic bytes, size, hash, format, and provenance. |
| Treat Grok and Codex as equal acceptance targets | Neither a Codex-only nor Grok-only pass completes the Goal. |
| Require rendered challenge intersection, not DOM presence | Hidden/preloaded anti-bot markup otherwise creates false CAPTCHA handoffs. |
| Use download-event first with a narrow directory fallback | Some authenticated sites land files without surfacing a runtime event; acceptance still requires a new stable file and full verification. |

## Issues Encountered

| Issue | Resolution |
|---|---|
| Old worktree is based on a stale branch and contains 104 untracked files plus tracked modifications | Preserve it and selectively port onto a new branch from current `main`. |
| Existing site skills conflate site selectors with one MCP namespace | Refactor into site recipes plus Codex/Grok adapters. |
| Existing browser-independent prose was accepted as capability | Replace with artifact-based acceptance gates. |
| Current main installation architecture predates the old branch's business installer | Re-evaluate current `install_aris*` behavior rather than porting old installer scripts blindly. |
| Codex installation currently depends on a checked-in mirror | Preserve one authoring source and make the mirror mechanically generated/verified; do not hand-maintain two divergent skill bodies. |
| Codex and Grok can both consume `.agents/skills` | Use a common installed skill body with runtime-specific browser adapter references; keep platform choice inside the adapter, not in duplicated research workflows. |
| Runtime receipts are necessary but not sufficient | The bridge verifies transport/file integrity; each calling skill still verifies title, fields, date span, grain, and research meaning. |
| Fulltext acquisition and method extraction are separate skills | Acquisition can fail or change channels without contaminating extraction; method cards consume only verified identity-matched local PDFs. |
| Direct-client SSRN 403 is not an access verdict | Browser challenge/session behavior is a separate authorized channel and must be tested before declaring a gap. |
| Browser PDF viewers may require UI-level download control | A valid rendered PDF is not yet a landed artifact; use the viewer's own download action, then verify local magic, pages, identity, size, and hash. |
| Literature discovery and fulltext synthesis are separate passes of the same review skill | Keep abstract-level mapping lightweight, then require verified method cards and a source-located evidence matrix before detailed review claims. |

## Resources

- `<legacy-business-skills-worktree>`
- `${HOME}/.grok/sessions/<project-key>/<session-id>/`
- `${HOME}/.codex/plugins/cache/openai-bundled/chrome/26.715.31251/skills/control-chrome/SKILL.md`
- `/opt/homebrew/lib/node_modules/mcp-chrome-bridge`

## Visual/Browser Findings

- Codex-native CNKI acceptance passed for `质量文化对企业绩效的影响研究——组织承诺的中介作用` under the page's `清华大学图书馆` access label.
- Hidden CNKI CAPTCHA markup was offscreen and non-blocking; this run required no user challenge action.
- The rendered PDF cover visibly matched the target title, author 段菁菁, 西北大学, and 2018.
- Grok reproduced this exact CNKI target through `chrome-mcp`; its independent 67-page artifact is byte-identical to the accepted Codex PDF. The remaining Grok browser targets are SSRN, ScienceDirect, Wiley, CNRDS, and CSMAR.

---

Update after every two browser/search observations.

## Official DevTools profile findings

- `my-agent-browser` is a launcher around active official
  `chrome-devtools-mcp`, but its bundled academic-paper recipes are not safe to
  adopt: raw arbitrary JavaScript, challenge-DOM deletion, unfiltered URLs, and
  weak download claims conflict with ARIS acceptance.
- A dedicated profile does retain cookies/site storage across independent Grok
  and Chrome restarts. It requires one initial login/challenge per site in the
  ordinary case, but site expiry, IP/institution changes, MFA, and renewed bot
  checks remain valid future handoffs.
- On this Mac, sandboxed Grok cannot launch the visible profile through the raw
  stdio wrapper. It can connect successfully while retaining the workspace
  sandbox when the dedicated Chrome is already running and the wrapper uses a
  loopback `browserUrl`. This motivates an externally managed profile lifecycle
  plus a sandbox-compatible safe facade.
- The fresh profile initially triggered a fixed ScienceDirect Turnstile checkbox.
  After one user-completed checkbox, the same profile retained clearance across
  a full Chrome shutdown/restart and a different PII article. The normal Chrome
  session also loaded the same target without a challenge. Current evidence
  therefore favors the official MCP as primary after bootstrap, with the legacy
  bridge retained only for emergency access to existing real-Chrome state.
- The official 29-tool surface is too broad for direct Grok acceptance. Raw page
  lists/snapshots can expose query-bearing URLs or autofilled values; network,
  console, heap, and arbitrary evaluation are unnecessary; and no accepted
  download waiter exists. A facade must sanitize before model exposure, enforce
  unique page leases and fresh opaque elements, constrain challenge actions, and
  provide an opaque `~/Downloads` baseline/delta/copy gate.
- The safe execution split is: sandboxed Grok uses only the facade MCP for browser
  work and produces a frozen candidate; an external runner independently checks
  file structure/identity/hash and issues acceptance evidence. This avoids
  granting an unsandboxed browser-facing model general Bash or filesystem access.
- Switching ScienceDirect articles is not a reliable way to force a renewed
  Turnstile after the dedicated profile has been cleared. One Grok-driven and five
  facade-driven cross-journal article changes all retained title/PDF access with
  no visible challenge. Reproduction now requires an explicitly cold profile or
  natural clearance expiry; current-profile absence must not be generalized to
  all future sessions.
- The maintained facade is live-compatible with the dedicated profile: its
  transport probe, private official child handshake, 13-tool surface, unique tab
  lease, challenge observation, and bounded PDF/title inspection all passed.
  Grok's user config now points `browser` at this facade; the raw official MCP is
  no longer the exposed Grok server.
- Candidate promotion is only trustworthy if the browser-facing candidate and
  external acceptor share one exact schema. The first audit found drift in both
  top-level fields and artifact metadata, plus insufficient metadata from
  `aris_copy_download`; download success alone would therefore be unpromotable.

## Superseding Findings at the Pause Checkpoint

- The official DevTools facade has 15 public tools, not 13. It now enforces
  one-action snapshot freshness, supports a sole selected duplicate-tab match,
  provides non-echoing value continuity proof, and exposes only redacted file
  metadata required by the external acceptor.
- The earlier claim that a complete Grok P3 browser download remained pending is
  obsolete: Grok independently downloaded and externally passed CNKI, SSRN,
  ScienceDirect, and Wiley. What remains in P3 is the canonical blind synthesis
  receipt, not browser acquisition.
- CSMAR's global reset is destructive across builder state. A stable flow must
  select/verify `FS_Combas`, reset exactly once before any frozen filter, verify
  the four mandatory fields, then apply dates, code, add only `A001000000`, set
  `Typrep=A`, preview, and export. Global reset and `全选` must not be used as
  repair actions after filters are set.
- The previously reported CSMAR overlay did not recur from a clean stable entry.
  The Skill therefore observes/dismisses one visible obstruction at most once,
  but does not assume an overlay exists.
- A CNRDS authenticated module deep link is more reliable than rediscovering
  CIRD from the portal home page. When the final dataset page is already open,
  use a narrow route substring such as `/ViewName/`; a broad domain filter can
  be ambiguous because the dedicated profile retains background module tabs.
- Codex Chrome and the dedicated Grok DevTools profile are genuinely separate.
  Closing duplicate tabs through Codex's Chrome extension does not clean the
  dedicated Grok profile and must not be treated as Grok tab evidence.
- The branch checkpoint intentionally preserves reusable Grok source and frozen
  non-secret prompt/spec fixtures while excluding PDFs, datasets, credentials,
  session logs, and runtime receipts.

## 2026-07-19 Grok Goal Audit and Steer

- A fresh root-verifier run confirms that Grok P3 is genuinely `PASS`: the
  canonical P3 invocation passes 39 evidence checks, and CNKI, SSRN,
  ScienceDirect, and Wiley each pass 22 browser-evidence checks. This supersedes
  the pause-checkpoint statement that Grok P3 synthesis remained incomplete.
- The overall root and Grok statuses remain `INCOMPLETE` only because neither
  CNRDS nor CSMAR has a promoted Grok P4 receipt.
- The CNRDS retry scripts contain a control-scoping bug: after clicking the main
  download button, a generic substring search treats the permanent
  `提交/添加条件` button as a download-modal confirmation. That click creates the
  `请设置完整条件` dialog and invalidates subsequent diagnosis.
- The same retry path fails open at the wrong layer: when
  `compress_done_found=false`, it falls back to any generic `下载` control and
  attempts download capture. P4 must instead stop until a real, fresh
  `压缩完成` control is present.
- The facade error `downloads_directory_unavailable` is independent of the
  portal UI. On this host Grok keeps the normal HOME, but the strict macOS
  sandbox denies access to the host Downloads directory; synthetic tests also
  cover an unavailable HOME/Downloads boundary. The download boundary must be
  corrected without exposing an arbitrary filesystem path to the model.
- Grok began considering a raw child `evaluate_script` workaround. That turn was
  cancelled because it violates the frozen 15-tool facade and would make P4
  evidence ineligible. The Goal was compacted with these constraints and resumed.

## 2026-07-19 CNRDS Grok download findings

- Official queue download icon is a11y `StaticText` with a PUA glyph (`\uE618`); Playwright/chrome-devtools `click(uid)` fails because StaticText UIDs do not resolve to ElementHandles.
- Safe fix is facade-only: after validating the selected control is a short PUA StaticText, run a fixed non-user-programmable DOM click near `压缩完成`, then baseline/wait/copy.
- CNRDS packages CSV as a ZIP container but may name the file `上市公司专利申请情况.7z`. Acceptance still uses `format: zip` and ZIP CRC/member checks.
- Grok download wait must use a filename filter present in the real landing name (`专利申请` or `.7z`), not only `.zip`.

## 2026-07-19 Grok P4 CSMAR evidence

- Independent Grok CSMAR export promoted: receipt `.aris/business-e2e/20260718T011517Z/cn-data/receipts/p4-csmar-grok.json`.
- Artifact: `cn-data/raw/csmar/2026-07-18_grok_v1/csmar-fs-combas-000001-2020.zip` (215923 B; sha256 `a3b467bc8381a98efc22a107641bba9781c72edb8d6c2989759bd22eba440991`); member `FS_Combas.csv` exactly one data row: Stkcd=000001, Accper=2020-12-31, Typrep=A, A001000000=4468514000000.00.
- Root verifier after promote: overall `PASS` for run `20260718T011517Z` (shared + Codex + Grok, including Grok P4_CNRDS and P4_CSMAR).
- Facade note: multiple `sdownload.html` tabs share the same URL; facade now claims identical-URL matches by page id (`identical_url_matches`) so lease/inspect/download remain usable; content still verified on page before local-save. `child_hint` redaction runs through `safePublicString`.
- Constraints held: 15-tool safe facade only for portal actions; accept/promote only via project scripts; no P3 reopen; no host Downloads symlink / no sandbox relax.

## 2026-07-19 packaged Skill forward test

- Grok 0.2.102 discovers `business-research-pipeline` and all 23 supporting
  business skills from project `.agents/skills`.
- A symlink install whose targets live outside the Grok workspace is discoverable
  by name but unreadable under the strict sandbox. A self-contained copied package
  avoids that cross-root boundary; same-repository installs are unaffected.
- Fresh no-memory Grok session `e50f46c7-40d8-47ce-bd63-075a402bfdc6`
  invoked `/business-research-pipeline` from an empty copied-package workspace.
  It produced Stage 0–5 Passport, literature review, four identity-matched PDFs,
  two method cards, cross-paper synthesis, idea/novelty artifacts, and all four
  empirical-design files before the protected-data checkpoint.
- Deterministic re-verification passed for all four PDFs and hashes; method-card
  sample sizes and reported coefficients were found in the local text layers.
  Grok's independent `/check-work` verdict was `PASS`; Codex independently
  confirmed the required artifact and JSON paths.
