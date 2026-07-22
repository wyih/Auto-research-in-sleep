# Grok P1 WRDS dual-backend runtime acceptance

Use the installed project skills `$wrds-query-bridge` and `$wrds-sas-cloud`. Read both `SKILL.md` files and their R/Postgres and SAS handoff references before acting. This is a real, fresh Grok-runtime acceptance run of both canonical WRDS paths, not a plan, simulation, cache check, or review of the prior Codex evidence.

## Scope and runtime boundary

- Work from `${ARIS_REPO_ROOT}`.
- Run both of these independently:
  1. the canonical R/Postgres universe-first smoke;
  2. the canonical WRDS SAS Cloud smoke, with escalation reason `user_required`.
- Use local CLI processes and the existing WRDS/SSH configuration only. No browser, Chrome MCP, other MCP, web search, HTTP client, GUI automation, or credential entry is part of P1.
- Do not modify project skills, tests, the accepted Codex WRDS directory, or existing receipts.
- Do not use any file under `.aris/business-e2e/20260718T011517Z/wrds/r/` or `wrds/sas/landed/` as runtime evidence. They may be read only to understand the frozen acceptance contract; they may not be copied, renamed, rehashed as Grok output, or cited as proof of a new execution.
- A byte-identical result is acceptable only when a new query/job actually ran and produced a new file under the Grok workspace after this invocation began.

Use a new UTC run tag and an empty, collision-free root beneath:

```text
${ARIS_REPO_ROOT}/.aris/business-e2e/20260718T011517Z/grok-workspace/wrds/p1/<grok_run_tag>/
```

Keep `r/`, `sas/program/`, `sas/landed/`, `qa/`, and `receipts/` beneath that root. Never overwrite an existing run tag. Record the start time before the first connection attempt and require every accepted output's modification time to be later than that start.

## Secret boundary

- Credentials may come only from the current process environment, an already configured `WRDS_RENVIRON`, or existing SSH tooling/configuration. Do not ask the user to paste a secret and do not create a new credential file.
- Never run `env`, `printenv`, shell tracing, or commands that display variable values. Never print, log, hash, or persist usernames, passwords, keys, cookies, tokens, connection strings, host-account pairs, or auth prompts.
- The only allowed environment report is set/unset booleans from `skills/wrds-query-bridge/scripts/check_wrds_env.sh`.
- A real password, passphrase, OTP, Duo, MFA, or other interactive credential prompt is a hard stop. Do not automate it. The valid zero-prompt keyboard-interactive completion described by `$wrds-sas-cloud` is not a user prompt.
- Receipts may record only booleans such as `wrds_user_set`, `wrds_password_set`, `configured_ssh_alias_used`, and `secret_values_recorded: false`.

## Phase A — fresh R/Postgres smoke

Freeze and verify the current canonical inputs before running:

```text
skills/wrds-query-bridge/scripts/check_wrds_env.sh
expected SHA-256: f59549b2968d4cb81a3ff509e3c14eef64065318913954242727ff43f95c78ca

skills/wrds-query-bridge/scripts/wrds_universe_inline_template.R
expected SHA-256: 34e52cbbf34ddf892e65d42adbe28e04ff5f62126cfc256c7afb675adc8c30df
```

If either hash differs, stop with `canonical_input_drift`; rereading an unreviewed replacement is not this frozen acceptance run.

1. Run the environment checker and record only its redacted set/unset output. Missing `WRDS_USER` or `WRDS_PASSWORD` is `credentials_unavailable`; do not continue or reveal a value.
2. Invoke the current canonical script as a new process, with no secret on the command line:

   ```bash
   Rscript skills/wrds-query-bridge/scripts/wrds_universe_inline_template.R \
     --out-dir "<new_grok_p1_root>/r/universe_inline" \
     --fyear 2020 \
     --seed-n 10 \
     --crsp-month 2020-12
   ```

3. Preserve a redacted execution log that excludes credentials and account identifiers. The connection must use SSL mode `require`, select columns explicitly, filter before collection, use the local-universe/`copy_inline` pattern, and disconnect cleanly.
4. Require a zero exit, the terminal `status=complete`, and these new files under the Grok run root:
   - `universe_local.parquet`
   - `ccm_date_valid_all.parquet`
   - `ccm_date_valid_unique.parquet`
   - `ccm_duplicate_keys.csv`
   - `ccm_unlinked.csv`
   - `crsp_msf_202012_inline.parquet`
   - `UNIVERSE_INLINE_REPORT.md`
5. Independently inspect the new artifacts. Require exactly 10 seed rows and 5 seed columns; explicit 2020 fiscal-year filtering; no more unique links than seed rows; a nonzero, internally reconciled CCM result; the CRSP file to contain only December 2020 rows; and no zero-filling of missing values. Record row/column counts, missingness by column, and SHA-256 for every new data file.
6. Write `<new_grok_p1_root>/receipts/p1-wrds-r-grok.json` only after all R checks pass. Use a non-wrapper schema such as `aris.business-e2e.wrds-r-smoke.v1` and include:
   - `stage: P1`, `runtime: grok`, `backend: r_postgres`, `status: pass`;
   - start/end timestamps and a Grok run tag;
   - canonical skill/script path and verified script hash;
   - redacted invocation arguments, query identity, source tables, filters, SSL requirement, and disconnect result;
   - credential set/unset booleans and `secret_values_recorded: false`;
   - every new artifact's project-relative path, bytes, rows, columns, missingness, SHA-256, and post-start newness check;
   - `prior_codex_output_reused: false`.

Do not treat an existing Parquet file, an environment preflight, or a successful socket connection as completion. The query and artifact validation must both finish in this Grok invocation.

## Phase B — fresh WRDS SAS Cloud smoke

This phase is required even when Phase A passes. Record the escalation exactly as:

```text
reason: user_required
r_path_status: complete
purpose: independent dual-backend acceptance
```

The frozen SAS seed is:

```text
.aris/business-e2e/20260718T011517Z/wrds/sas/comp_funda_2020_smoke_v1_sas.sas
SHA-256: 4eed1b602309a29dd9e17a96cac1147a7b6735e04eec266957b618231b6d0dd2
```

Verify that hash. Use its query logic as the reviewed seed, but create a new Grok-owned SAS program under `<new_grok_p1_root>/sas/program/`. The only allowed semantic changes are a Grok-specific query label, a unique remote output directory derived from the run tag, and Grok-specific output basenames. Preserve exactly:

- source `comp.funda`;
- filters `INDL`, `STD`, `D`, `C`, and `fyear=2020`;
- `OUTOBS=10`;
- columns `gvkey, datadate, fyear, at, sale, ni`;
- preservation of SAS missing values, with no zero fill;
- CSV data export plus a schema export.

Record both the frozen-seed hash and the derived-program hash. Scan the derived program before upload and require that it contains no credentials or account identifiers.

1. Resolve the endpoint only from an already configured `WRDS_SAS_HOST`/tool or the existing SSH alias used by the current environment. The literal receipt label `wrds_alias` is not an endpoint to guess. If no configured endpoint can be resolved without revealing it, stop with `sas_endpoint_unavailable`.
2. Run a harmless ordinary SSH preflight equivalent to `ssh <configured-alias> true`. Do **not** force `BatchMode=yes`; the endpoint may legitimately complete a zero-prompt keyboard-interactive stage after accepting the configured public key. Stop if a real prompt appears.
3. Create a new remote work directory unique to the Grok run tag, upload only the new SAS program, and submit a new `qsas`-class job. A prior job ID, especially `34898972`, is not evidence. Capture the newly observed job ID and queue timestamps without recording the remote account or host value.
4. Wait for this new job to leave the queue and finish. Do not infer completion from successful upload or submission. Retrieve and audit its log; require zero SAS `ERROR` entries, zero uninitialized-variable notices, and zero invalid-data notices. Classify every warning; the bounded `OUTOBS=10` early-termination warning is acceptable when that is the actual warning.
5. Transfer the newly generated data CSV and schema CSV into `<new_grok_p1_root>/sas/landed/` with `rsync --checksum` or `scp` plus explicit hashes. Compute the remote and local SHA-256 independently and require equality.
6. Validate the landed data independently: exactly 10 data rows, exactly the six required columns in the intended order, every `fyear` equal to 2020, parseable dates/numerics, and missing values preserved rather than recoded. Validate the schema file against the data columns. Record bytes, rows, columns, missingness, and hashes.
7. Write a redacted log-audit file and `<new_grok_p1_root>/receipts/p1-wrds-sas-cloud-grok.json` only after all SAS checks pass. Use a non-wrapper schema such as `aris.business-e2e.wrds-sas-smoke.v1` and include:
   - `stage: P1`, `runtime: grok`, `backend: wrds_sas_cloud`, `status: pass`;
   - `user_required` escalation fields;
   - the frozen seed and derived program paths/hashes;
   - configured-SSH booleans, ordinary preflight result, `batch_mode_used: false`, and `new_password_or_mfa_required: false`;
   - a sanitized remote-workdir label/run tag, new job ID, submission/completion timestamps, and queue completion;
   - the redacted log counts/dispositions;
   - each new landed artifact's project-relative path, bytes, dimensions, hash, remote/local match, and post-start newness check;
   - `prior_job_or_landed_output_reused: false` and `secret_values_recorded: false`.

Do not copy the accepted Codex SAS CSV or schema into the Grok directory. Matching their hashes is not enough; the new job ID, new remote directory, post-start landing time, and transfer lineage must all be present.

## Cross-backend manifest and acceptance

After both phases pass, write `<new_grok_p1_root>/DATA_MANIFEST.md` with one R row and one SAS row. Include runtime, backend, query ID, source, filters, dimensions, new artifact path, SHA-256, execution time, and status. State that the two paths are independent smoke tests and are not expected to produce the same schema.

Write `<new_grok_p1_root>/P1_GROK_ACCEPTANCE.md` with the exact gates, observed counts, new R process, new SAS job ID, redacted security result, and any acceptable warnings. Do not label the stage pass if either backend is incomplete.

## Runtime-invocation wrapper

Only after both backend receipts, the manifest, and the acceptance report pass, create a uniquely named JSON under:

```text
.aris/business-e2e/20260718T011517Z/grok-workspace/receipts/
```

It must use this schema and actual observed values:

```json
{
  "schema_version": "aris.business-e2e.runtime-invocation.v1",
  "runtime": "grok",
  "stage": "P1",
  "status": "passed",
  "recorded_at": "observed_ISO_8601",
  "skill": ["wrds-query-bridge", "wrds-sas-cloud"],
  "invocation": {
    "grok_run_tag": "observed_unique_tag",
    "r_postgres_reexecuted": true,
    "sas_cloud_reexecuted": true,
    "sas_escalation_reason": "user_required",
    "shared_output_reused_as_runtime_proof": false,
    "secrets_recorded": false
  },
  "evidence": [
    {
      "path": ".aris/business-e2e/20260718T011517Z/grok-workspace/wrds/p1/<tag>/receipts/p1-wrds-r-grok.json",
      "size_bytes": 0,
      "sha256": "observed_64_hex"
    },
    {
      "path": ".aris/business-e2e/20260718T011517Z/grok-workspace/wrds/p1/<tag>/receipts/p1-wrds-sas-cloud-grok.json",
      "size_bytes": 0,
      "sha256": "observed_64_hex"
    }
  ]
}
```

Replace every placeholder and zero. Include the two new backend receipts, new manifest, acceptance report, and representative new R and SAS data artifacts in `evidence`, each with actual bytes and SHA-256. Every evidence path must be project-relative and must point only to this Grok run; do not cite a Codex receipt or shared WRDS output.

Then run:

```bash
python3 ${ARIS_REPO_ROOT}/scripts/verify_business_e2e.py \
  --run-id 20260718T011517Z --json
```

Require `runtimes.grok.stages.P1.status` to be `PASS`. Overall acceptance may still be incomplete for unrelated stages.

## Failure rule

If any required R, SAS, security, lineage, hash, or verifier check fails, preserve the last verified state in a redacted failure record using a schema other than `aris.business-e2e.runtime-invocation.v1`. Do not write a passed runtime wrapper, do not reuse prior output to fill the gap, and do not claim P1 pass. Report one concrete blocker and the exact safe retry point.
