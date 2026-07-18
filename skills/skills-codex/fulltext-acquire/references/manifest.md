# Fulltext Manifest

Maintain `literature/FULLTEXT_MANIFEST.md` when project writes are allowed.

```markdown
# FULLTEXT_MANIFEST

| work_id | artifact_id | parent_artifact_id | artifact_role | version_identity | title | doi_or_source_id | identity_evidence | channel | runtime | adapter | local_path_or_gap | size_bytes | pages | sha256 | acquired_at | provenance_receipt | browser_receipt | status | blocker | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---:|---:|---|---|---|---|---|---|---|
```

## Rules

- Use one stable `work_id` for the intellectual work across channels and versions; it must match the METHOD_CARD/synthesis ID. Do not rely only on a filename.
- Give every acquired or missing role/version/channel row its own stable `artifact_id`. Byte-identical NBER and SSRN deliveries may share a `work_id` and hash but still have distinct artifact IDs and provenance.
- Use `artifact_role=main_paper|online_appendix|questionnaire|codebook|supplement`. A companion row points `parent_artifact_id` to the exact main-paper artifact row; a main row uses `not_applicable`.
- Record journal/working-paper version identity or date when visible. Do not silently treat different versions as interchangeable.
- Record concrete `identity_evidence` for the work, version, and artifact role. Include DOI/source ID when available.
- Record paths relative to the project when practical.
- Record the actual acquisition timestamp and SHA-256.
- For protected sites, use `codex_native_chrome`, `grok_chrome_devtools_mcp`, or the explicitly selected legacy `grok_chrome_mcp` from the bridge receipt.
- For protected sites, `browser_receipt` is required and must point to the runtime-specific acquisition receipt; use `not_applicable` for non-browser channels.
- Never include account names, cookies, tokens, auth headers, session identifiers, or raw IP addresses.
- Keep licensed binaries out of public git by default.
- On re-download, add a new row or version; do not erase the prior accepted hash.
- The PDF-processing receipt must repeat `work_id`, `artifact_id`, `parent_artifact_id`, `artifact_role`, `version_identity`, and `doi_or_source_id`; downstream joins fail closed on disagreement.
