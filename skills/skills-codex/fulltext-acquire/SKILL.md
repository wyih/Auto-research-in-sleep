---
name: fulltext-acquire
description: Acquire and verify research-paper fulltext through local libraries, open-access sources, CNKI, ScienceDirect, Wiley, or other authorized publisher sessions. Use when a paper PDF is missing, when CNKI must be searched through an article-detail PDF flow, when publisher access depends on the user's signed-in Chrome, or before method-harvest needs a verified local file. Not for CSMAR/CNRDS microdata.
---

# Fulltext Acquire

Produce a verified local paper artifact or a precise access gap. Keep acquisition separate from method extraction.

## Inputs

Freeze one to ten targets with title, authors/year, DOI or known URL, reason needed, current fulltext status, and required artifact roles. `main_paper` is always required; add `online_appendix`, `questionnaire`, `codebook`, or `supplement` only when the review/design question needs material that is not embedded in the main PDF. Default to one protected-site download at a time.

Read only the relevant references:

- `references/channels.md` for channel selection
- `references/zotero.md` when a Zotero library item or attachment is the candidate fulltext source
- `references/ssrn.md` for SSRN browser challenge behavior
- `references/cnki.md` for CNKI
- `references/sciencedirect.md` for ScienceDirect
- `references/wiley.md` for Wiley Online Library
- `references/manifest.md` before writing provenance
- `../shared-references/business-helper-resolution.md` before invoking bundled scripts outside the ARIS repository

For a login-dependent site, invoke `browser-session-bridge` and follow its shared session contract. Site recipes must not call runtime-specific tools directly.

## Channel Ladder

1. Existing local PDF or Zotero attachment
2. Model-native web search/fetch, when available, for an identity-matched lawful open copy, repository manuscript, or working-paper version
3. Bounded OA metadata/API or direct-download helper
4. Institutional-IP or existing signed-in Chrome session when protected access remains necessary
5. Human login/challenge handoff in that same session
6. Documented gap

Stop at the first verified copy **for each required artifact role**. Do not fetch a duplicate main paper merely because a later channel is available. A verified `main_paper` does not satisfy a separately hosted required appendix, questionnaire, codebook, or supplement.

Do not acquire a browser turn merely to discover a title, DOI, repository copy, working-paper version, or public landing page that model-native web search/fetch can find. Public search does not establish the user's current entitlement or a protected download. Before invoking `browser-session-bridge`, record `browser_required_reason: authenticated_session | entitled_download | active_challenge` for the unresolved artifact role.

## Workflow

### 1. Local search

Search project `papers/`, `literature/`, `pdfs/`, prior manifests, and available Zotero attachments. For Zotero, preserve the bibliographic parent item and attachment child as distinct identities and follow `references/zotero.md`. Verify the resolved file; do not trust its extension.

### 2. Public-web and open-access search

When the runtime exposes it, use model-native web search/fetch first to locate and identity-check lawful public candidates. Prefer official repositories, author manuscripts, working-paper services, and publisher OA pages. If the model-native fetch lands the actual PDF, run the same local verifier and stop; a search result or HTML landing page alone is discovery evidence, not an artifact.

When discovery still needs a reproducible OA query or bounded direct download:

```bash
python3 "$FULLTEXT_SKILL_DIR/scripts/openalex_search_oa.py" "title or DOI" --oa-only --per-page 10
python3 "$FULLTEXT_SKILL_DIR/scripts/download_open_pdf.py" \
  --url URL --paper-id PAPER_ID --out-dir literature/fulltext/open
```

Confirm that the returned work matches the requested title/DOI before download. Optional DOI helpers may be used only through lawful configured sources and only when they return a real PDF.

### 3. Protected publisher or CNKI

1. Confirm that local, model-native public web, and bounded OA/direct routes did not satisfy this artifact role; freeze its `browser_required_reason`.
2. Load the site recipe.
3. Invoke `browser-session-bridge`.
4. Search or navigate to the exact article detail page.
5. Confirm title and publication metadata before download.
6. Check the same article record for explicitly linked required companion artifacts; do not broaden into bulk supplementary-material crawling.
7. Snapshot the landing directory, arm download handling, then activate the PDF control.
8. Land each required role under the channel directory without overwriting another role.
9. Run the bridge verifier and then confirm the paper identity **and artifact role** from the local content.

CNKI defaults to PDF only. A CAJ file does not satisfy this skill unless the user explicitly requests CAJ, and it still cannot feed PDF-only method extraction.

### 4. Record provenance

Append one row per acquired/gap artifact role to `literature/FULLTEXT_MANIFEST.md` when project writes are allowed. Keep the intellectual work's `work_id` separate from each acquisition/version/role `artifact_id`, and preserve the exact `parent_artifact_id`, version/role, identity evidence, channel, local path, SHA-256, acquisition time, browser receipt when required, status, and blocker. Never record credentials or session identifiers.

## Acceptance

| Requirement | Evidence |
|---|---|
| Discovery | Local hit, model-native public-web/OA result, or protected-site search/detail evidence |
| Identity | Requested title/DOI matches the detail page and local PDF |
| Artifact completeness | Every required role is verified or has an explicit role-specific gap; a main PDF never silently substitutes for a separate appendix/codebook |
| File integrity | `%PDF`, EOF marker, at least 10 KiB, SHA-256 |
| Provenance | Manifest row and browser receipt when a protected session was used |
| Runtime | Codex native Chrome receipt, Grok or OpenCode official DevTools-facade receipt, or explicitly selected Grok legacy receipt; identify the client host rather than the model provider |

A homepage, HTTP 200, visible PDF viewer, click notification, CAJ file, HTML login page, or unverified extension is a failure. An unauthenticated HTTP 403 is a channel result, not proof that the user's browser session lacks access.

## Output

```markdown
# Fulltext Acquisition Summary

| work_id | artifact_id | parent_artifact_id | artifact_role | version_identity | title | identity_evidence | discovery_evidence | channel | status | local_path | size_bytes | pages | sha256 | browser_receipt |
|---|---|---|---|---|---|---|---|---|---|---|---:|---:|---|---|

## Gaps
| work_id | artifact_role | last_channel | blocker | required_handoff |
```

Use statuses: `local`, `open`, `institutional_ip`, `browser_session`, `human_handoff_completed`, `abstract_only`, `gap`, or `needs_verification`.

## Rules

- Use authorized personal, institutional, or open access only.
- Never automate credential entry or hard CAPTCHA completion.
- Do not bulk crawl or build a public licensed-paper mirror.
- Do not commit licensed PDFs by default; commit redacted manifests when appropriate.
- Do not assume that “supplementary material” is irrelevant. Acquire it only when it is a required role for formulas, sample construction, questionnaires, codebooks, or robustness evidence, and preserve its distinct hash/page map.
- Route CSMAR/CNRDS microdata to `cn-data-bridge`.
- Route verified PDFs to `method-harvest` for extraction.
