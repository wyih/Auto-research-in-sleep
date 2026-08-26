# Business Repro Lock

Use `repro_lock` to make a research artifact auditable. It documents the configuration and material state used to produce an output. It does not promise byte-identical LLM replay.

## Required Fields

```yaml
repro_lock:
  schema_version: 1
  generated_at: "YYYY-MM-DDTHH:MM:SSZ"
  artifact: "path/to/output.md"
  producing_skill: "business-paper-writing"
  model: "current Codex model or user-specified model"
  source_material_hash:
    BUSINESS_RUN_PASSPORT.md: "sha256:..."
    RESULTS_SUMMARY.md: "sha256:..."
  data_outputs_hash:
    table_main.csv: "sha256:..."
  analysis_backend:
    name: "R"
    version: ""
    key_packages: []
  protocol_versions:
    handoff_schema: 1
    claim_source_audit: 1
    number_audit: 1
  limitations:
    - "LLM prose is configuration-locked, not byte-replayable."
```

## Hash Scope

Hash only materials that materially affect the artifact:

- project passport
- design files
- result summaries
- source tables and logs
- cited source inventory
- author style profile when style was applied

Do not hash private credentials, tokens, cookies, or raw restricted datasets into public-facing artifacts. Store only hash values.
