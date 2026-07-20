# Fulltext Channel Selection

Use the earliest authorized channel that yields a verified, identity-matched local PDF.

| Priority | Channel | Use when | Success status |
|---:|---|---|---|
| 1 | Local/project/Zotero | A prior copy or attachment exists | `local` |
| 2 | Model-native public web | Public search/fetch finds an identity-matched lawful PDF, accepted manuscript, repository copy, or working paper | `open` |
| 3 | Bounded OA/direct helper | An OA metadata API or stable public direct URL yields a reproducible PDF | `open` |
| 4 | Institutional IP / browser session | Current network entitlement, Chrome cookies, or SSO is required after lighter routes are exhausted | `institutional_ip` or `browser_session` |
| 5 | Human handoff | Login or challenge must be completed by the user | `human_handoff_completed` |
| 6 | Gap | Authorized channels are exhausted or denied | `gap` |

## Local

Search only relevant project and reference-library locations. A filename match is not enough: verify PDF integrity and compare title/DOI inside the paper.

## Open Access

Use model-native web search/fetch before a browser to find stable lawful sources such as an author manuscript, SSRN, NBER, RePEc, arXiv, an institutional repository, or a publisher OA PDF. Then use a bounded OA API/direct helper only when needed for a reproducible landing. Record the landing and final URLs. Do not use shadow libraries as a suite default. A public search hit or HTML page is not a verified PDF. If a direct SSRN request returns a Cloudflare/403 page, retry through the real Chrome session and follow `ssrn.md`; do not infer subscription denial from the direct request.

## Institutional IP

Use the current authorized network without recording raw IP addresses. If access is denied, do not claim that reachability proves entitlement.

## Existing Browser Session

Invoke `browser-session-bridge` only after local, model-native public web, and bounded OA/direct routes are exhausted for the artifact role. Record `browser_required_reason: authenticated_session | entitled_download | active_challenge`. Reuse the authorized Chrome state and keep credentials inside the browser. Codex and Grok must each produce their own runtime receipt during matched acceptance.

## Human Handoff

Ask once for login or hard challenge completion in the same tab. Resume from fresh page state. If the user cannot complete it or the subscription lacks the item, record the blocker.

## Gap Reasons

Use a specific reason such as `not_found`, `not_logged_in`, `captcha_required`, `subscription_denied`, `no_pdf_control`, `caj_only`, `download_failed`, `artifact_invalid`, or `identity_mismatch`.
