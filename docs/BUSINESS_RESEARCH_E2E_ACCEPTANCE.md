# Business Research End-to-End Acceptance

This matrix is the release gate for the business empirical-research suite. Prose, tool availability, homepage reachability, and a pass in only one runtime do not satisfy it.

## Evidence Rules

1. Use the same small representative research slice where practical.
2. Preserve redacted commands, runtime receipts, local artifact paths, sizes, SHA-256 hashes, schemas, and timestamps.
3. Keep licensed PDFs and vendor data local; commit only non-sensitive manifests and derived test fixtures.
4. Mark a gate `pass` only from current artifacts or traces. Use `blocked` for a real login, subscription, network, or human-challenge blocker; do not relabel it as a pass.
5. Codex protected-site actions must use native `chrome:control-chrome`. Grok's primary path must use official `chrome-devtools-mcp` through the project safety facade and its dedicated persistent profile. The legacy `chrome-mcp` attached to the user's real Chrome is an explicitly recorded fallback, never an unlabeled substitution.

## Acceptance Matrix

| Gate | Codex evidence | Grok evidence | Shared artifact gate |
|---|---|---|---|
| Browser adapter | Native Chrome execution receipt; no external MCP substitution | Safe-facade `browser` trace, dedicated-profile restart persistence, and a separately identified legacy fallback smoke | Redacted receipt, strict adapter identity, and deterministic file verification |
| P3 open-access baseline | Search result, downloaded local PDF, method card | Same workflow invoked by Grok | Correct PDF, size/hash, method claims grounded in fulltext |
| P3 CNKI | Search → article detail → PDF button in existing Chrome session | Same site flow through the official DevTools facade | PDF not CAJ/HTML; title match; manifest; method card |
| P3 SSRN | Abstract page → passive Cloudflare wait when shown → current PDF download | Same through the official DevTools facade; no immediate 403 conclusion while the passive challenge is pending | Correct paper identity, local PDF, manifest, and browser receipt |
| P3 ScienceDirect | Article page and entitled PDF or an explicit current access blocker | Same through the official DevTools facade; any legacy fallback is a separate blocked-then-fallback trace | Correct PDF and manifest; no API-only false pass |
| P3 Wiley | DOI landing page → entitled PDF route in the signed-in session | Same through the official DevTools facade | Correct DOI/title PDF, manifest, and browser receipt; HTML challenge is not a PDF pass |
| P3 fulltext literature synthesis | Verified PDFs → inspector-native page renders → method cards → evidence matrix → grounded review | Grok generates a frozen candidate from an isolated skill/PDF snapshot; external tests run only after generation | Manifest/processing/card/synthesis artifact identity joins; Exact variable construction, design/inference, main and null results, source locations, conflicts, and claim ceilings are traceable |
| P1 WRDS R/Postgres | Real minimal query and immutable extract | Grok can route/execute the same canonical skill | Query/filter record, schema, rows, hash, missingness |
| P1 WRDS SAS Cloud | Real SAS program submit, remote completion, transfer back | Grok can route/execute the same canonical skill | SAS log, output file, schema/rows/hash, handoff note |
| P4 CSMAR | Minimal named table/field/date export from authorized session/network | Same recipe through the official DevTools facade | Valid vendor file, required fields, filters, hash, manifest |
| P4 CNRDS | Minimal named dataset/indicator/date export from signed-in session; a user-authorized Chrome-autofilled login may be submitted once without reading fields | Same recipe through the official DevTools facade | Valid vendor file, required fields, filters, hash, manifest |
| P2 analysis-to-Word | Generator produces a current results document | Grok invokes the same generator/contract | Tables/figures checked, rendered pages inspected, OOXML author metadata normalized to the explicitly configured Office author |
| P5 discovery/routing | Codex discovers and routes focused business skills | `grok inspect --json` discovers and routes the same suite | Catalog/mirror checks and selective install tests pass |
| Full chain | Literature → method → data → analysis → claims → Word receipt | Same representative request completes in Grok | Passport and manifests link every accepted artifact |

## Runtime Receipt Tests

### Codex

- `adapter = codex_native_chrome`
- current `chrome:control-chrome` instructions were used
- existing Chrome session/tab was reused when login state mattered
- no external browser MCP produced the protected-site artifact

### Grok official DevTools primary

- `adapter = grok_chrome_devtools_mcp`
- `mcp_server = browser`
- `implementation = chrome-devtools-mcp`
- `profile_mode = dedicated_persistent`
- `grok mcp doctor` exposes only the project facade's bounded `aris_*` surface
- trace contains successful facade navigation/inspection/action/download-evidence calls
- raw official JavaScript, network, console, heap, emulation, drag, bulk-form,
  raw upload, cookie, storage, and history tools were not exposed; any file
  upload used only workspace-scoped `aris_upload_file`

### Grok legacy fallback

- `adapter = grok_chrome_mcp`
- `grok mcp doctor` reports `chrome-mcp` healthy for the run
- trace contains successful `chrome-mcp` navigation/inspection/download calls
- the receipt names the primary-path blocker or the frozen need for existing real-Chrome state
- no action from the official profile is spliced into the fallback success receipt

## Artifact Evidence Layout

Keep local acceptance evidence under an ignored run directory such as:

```text
acceptance/business-e2e/<run-id>/
  ACCEPTANCE_SUMMARY.md
  receipts/
  manifests/
  logs/
  derived/
```

The summary must state `pass`, `fail`, `blocked`, or `not_run` for every matrix row and link to the evidence. Release requires all required rows to be `pass`; access-dependent blockers remain visible until resolved.
