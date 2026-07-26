# Business Research End-to-End Acceptance

This matrix is the release gate for the Codex business empirical-research suite. The model selected inside Codex does not create a separate runtime, Skill package, or browser adapter.

## Evidence Rules

1. Use the same small representative research slice where practical.
2. Preserve redacted commands, Codex receipts, local artifact paths, sizes, SHA-256 hashes, schemas, and timestamps.
3. Keep licensed PDFs and vendor data local; commit only non-sensitive manifests and derived test fixtures.
4. Mark a gate `pass` only from current artifacts or traces. Use `blocked` for a real login, subscription, network, or human-challenge blocker.
5. Protected-site actions must use native `chrome:control-chrome`. Another browser backend or profile cannot substitute for Codex acceptance.

## Acceptance Matrix

| Gate | Codex evidence | Artifact gate |
|---|---|---|
| Browser adapter | Native Chrome execution receipt with `adapter = codex_native_chrome` | Redacted receipt and deterministic file verification |
| P3 open-access baseline | Search result, downloaded local PDF, method card | Correct PDF, size/hash, method claims grounded in fulltext |
| P3 CNKI | Search → article detail → PDF button in the authorized Chrome session | PDF not CAJ/HTML; title match; manifest; method card |
| P3 SSRN | Abstract page → passive Cloudflare wait when shown → current PDF download | Correct paper identity, local PDF, manifest, and browser receipt |
| P3 ScienceDirect | Article page and entitled PDF or an explicit current access blocker | Correct PDF and manifest; no API-only false pass |
| P3 Wiley | DOI landing page → entitled PDF route in the signed-in session | Correct DOI/title PDF, manifest, and browser receipt |
| P3 literature synthesis | Verified PDFs → page renders → method cards → evidence matrix → grounded review | Exact variable construction, design, inference, results, source locations, conflicts, and claim ceilings are traceable |
| P1 WRDS R/Postgres | Real minimal query and immutable extract | Query/filter record, schema, rows, hash, missingness |
| P1 WRDS SAS Cloud | Real SAS program submit, remote completion, transfer back | SAS log, output file, schema/rows/hash, handoff note |
| P4 CSMAR | Minimal named table/field/date export from the authorized session/network | Valid vendor file, required fields, filters, hash, manifest |
| P4 CNRDS | Minimal named dataset/indicator/date export from the signed-in session | Valid vendor file, required fields, filters, hash, manifest |
| P2 analysis-to-Word | Generator produces a current results document | Tables/figures checked and OOXML identity normalized to the configured author |
| P5 discovery/routing | Codex discovers and routes the focused business Skills | Catalog, mirror, and OS-specific installer tests pass |
| Full chain | Literature → method → data → analysis → claims → Word receipt | Passport and manifests link every accepted artifact |

## Browser Receipt

- `client_runtime = codex`
- `adapter = codex_native_chrome`
- `mcp_server = native`
- `implementation = codex_chrome`
- `profile_mode = user_chrome`
- current `chrome:control-chrome` instructions were used
- existing Chrome session or tab was reused when login state mattered
- no external browser backend produced the protected-site artifact

## Operating Systems

The release contains one Codex Skill package with separate installation paths for macOS, native Linux, native Windows PowerShell, and WSL 2. OS-specific link and path handling do not create different Skill semantics.

## Artifact Evidence Layout

Keep local acceptance evidence under an ignored directory such as:

```text
acceptance/business-e2e/<run-id>/
  ACCEPTANCE_SUMMARY.md
  receipts/
  manifests/
  logs/
  derived/
```

The summary must state `pass`, `fail`, `blocked`, or `not_run` for every row and link to the evidence. Release requires all required rows to be `pass`; access-dependent blockers remain visible until resolved.
