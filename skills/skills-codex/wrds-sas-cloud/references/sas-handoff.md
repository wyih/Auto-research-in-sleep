# SAS Cloud Handoff Reference

Companion to `wrds-sas-cloud`. Policy: `../../shared-references/business-wrds-policy.md`.

This guide is **generic**. Replace host names, queue commands, and workdirs with the project’s site configuration. Do not treat any single commercial Option package or branded portal as required.

## When Escalation Is Valid

Valid reasons (record one):

- `timeout` — WRDS Postgres query exceeded acceptable wait after chunking attempts
- `oom` — R process or host killed for memory
- `hard_fail` — driver crash, repeated disconnect, unrecoverable server error
- `auth_blocker` — Postgres path unusable but SAS path available
- `user_required` — user explicitly mandated SAS

Invalid reasons:

- “table has many rows” without an actual R failure
- aesthetic preference alone
- fixed thresholds such as “N > 5e6 rows”

## Handoff Note Template

Write `data/wrds/handoff/<query_id>.md`:

```markdown
# Handoff: <query_id>

## Escalation
- reason:
- r_query_id:
- r_log:
- attempted_at:

## Remote
- host_label: (not necessarily a real hostname if sensitive)
- workdir:
- sas_program: data/wrds/sas/<query_id>.sas
- submit_command: (no secrets)
- job_id:
- remote_output:

## Transfer
- method: rsync | scp
- local_path:
- content_hash:
- transferred_at:

## Status
- complete | partial | failed
- notes:
```

## Abstract Submit: `qsas`

Sites differ. Document the project mapping once:

| Abstract step | Example site mapping |
|---|---|
| `qsas program.sas` | local wrapper that SSHes and submits batch SAS |
| job status | `qstat`, log tail, or site portal |
| cancel | site-specific |

Example pattern (illustrative only):

```bash
# 1) copy program
rsync -avP data/wrds/sas/query_id.sas "${WRDS_SAS_HOST}:${WRDS_SAS_WORKDIR}/"

# 2) submit
ssh "${WRDS_SAS_HOST}" "cd '${WRDS_SAS_WORKDIR}' && qsas query_id.sas"

# 3) wait for log/output (site-specific)
```

If the site has no binary named `qsas`, still record the equivalent batch entrypoint under the same handoff fields.

### SSH preflight and `BatchMode`

Prefer an existing SSH alias because it carries the user's host, account, and key
selection without putting those values into project notes. Validate it first:

```bash
ssh "$WRDS_SAS_HOST" 'true'
```

Do not force `BatchMode=yes` as a generic default. Some key-enabled endpoints perform
`publickey` authentication followed by a zero-prompt `keyboard-interactive` stage;
ordinary scripted SSH succeeds, while `BatchMode=yes` rejects the second stage and
reports an authentication failure. If the ordinary command presents an actual
password, OTP, Duo, or other MFA prompt, pause for the user instead of automating or
recording that credential.

## SAS Program Skeleton

Keep extracts explicit. Do not zero-fill missings.

```sas
/* query_id: example_v1 — align filters with R SQL when possible */
libname out "~/wrds_out";  /* site path */

proc sql;
  create table out.example_v1 as
  select gvkey, datadate, fyear, at, sale, ni
  from comp.funda
  where indfmt = 'INDL'
    and datafmt = 'STD'
    and popsrc = 'D'
    and consol = 'C'
    and fyear between 2000 and 2024;
quit;

proc export data=out.example_v1
  outfile="~/wrds_out/example_v1.csv"
  dbms=csv replace;
run;
```

Prefer CSV or a clearly documented `.sas7bdat` for transfer. Convert to parquet locally with R when the analysis backend is R:

```r
df <- data.table::fread("data/intermediate/wrds/example_v1.csv")
arrow::write_parquet(df, "data/intermediate/wrds/example_v1.parquet")
```

## Transfer: `rsync`

Preferred:

```bash
rsync -avP \
  "${WRDS_SAS_HOST}:${REMOTE_OUT}" \
  "data/intermediate/wrds/"
```

Useful flags:

- `-P` partial progress / resume
- `-a` archive mode
- dry-run first: `rsync -avPn ...` when validating paths

Fallback:

```bash
scp "${WRDS_SAS_HOST}:${REMOTE_OUT}" "data/intermediate/wrds/"
```

## Hash Verification

After landing the file:

```bash
# macOS / Linux
shasum -a 256 data/intermediate/wrds/example_v1.csv

# or
sha256sum data/intermediate/wrds/example_v1.csv
```

Record `sha256:<hex>` in `DATA_MANIFEST`. Re-hash after any reconversion (csv → parquet) and store the hash of the analysis-facing file.

Optional row count check:

```bash
# csv with header
wc -l data/intermediate/wrds/example_v1.csv
```

## Manifest Backend Value

Use `backend = sas_cloud` for SAS-produced extracts. Keep the same `query_id` family as the R attempt when filters match (for example `comp_funda_ann_1990_2024_v1_sas`).

Escalation block example:

```text
escalate_to_sas:
  reason: timeout
  query_id: comp_funda_ann_1990_2024_v1
  attempted_at: 2026-07-17T10:00:00Z
  evidence: logs/wrds/comp_funda_ann_1990_2024_v1.log
  r_path_status: failed
  sas_job_id_or_path: data/wrds/handoff/comp_funda_ann_1990_2024_v1.md
```

## Security

- Do not embed WRDS or SSH passwords in `.sas` files checked into git.
- Prefer SSH agent / keys over password prompts in automation.
- Redact account identifiers in shared write-ups when required.
- Handoff notes may store host **labels** if hostnames are sensitive.

## Failure Handling

| Stage | Action |
|---|---|
| Submit rejected | fix program or site access; keep reason in handoff |
| Job failed | pull remote log (redact secrets); fix filters; resubmit with new note section |
| Transfer incomplete | re-rsync; do not mark complete |
| Hash mismatch vs expected prior run | treat as new version; new `query_id` or version suffix |

Never promote a partial remote dump to `data/final/` without an explicit sample-build step.
