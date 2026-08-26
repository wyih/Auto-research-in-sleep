---
name: wrds-sas-cloud
description: Hand off heavy or failed WRDS pulls to a SAS cloud path with generic qsas submission, rsync transfer, and hash verification. Use when R+Postgres WRDS pulls time out, OOM, hard-fail, or the user explicitly requires SAS; not for routine small extracts.
---

# WRDS SAS Cloud

Handoff context: $ARGUMENTS

## Purpose

Provide a **generic** SAS-cloud escalation path for WRDS extracts when the R + Postgres path is blocked. Produce transferred files, content hashes, and `DATA_MANIFEST` updates that analysis skills can consume.

This skill is intentionally **not** tied to any single vendor product name, university Option plan, or site-specific portal. Site commands belong in project notes or environment variables.

## When To Use

Use this skill when:

- `wrds-query-bridge` recorded timeout, OOM, hard failure, or auth blocker after retries
- the user explicitly requires SAS for a WRDS extract
- an existing project already runs WRDS SAS programs and needs a documented handoff

Do **not** escalate only because a table is large. There is **no fixed row threshold**. Prefer R chunking first. See `../shared-references/business-wrds-policy.md`.

## Inputs

Read available files in this order:

1. `data/wrds/DATA_MANIFEST.md` (or `data/DATA_MANIFEST.md`) — especially failed/`partial` R rows
2. `empirical-design/DATA_PLAN.md`
3. SQL or R pull scripts that failed (for filter parity)
4. existing SAS programs under `sas/`, `data/wrds/sas/`, or user-provided paths
5. `BUSINESS_RUN_PASSPORT.md` when present

Read:

- `../shared-references/business-wrds-policy.md`
- `references/sas-handoff.md` for qsas/rsync/hash patterns

## Project Layout

Use or create:

```text
data/
  wrds/
    DATA_MANIFEST.md
    sas/                    # .sas programs submitted remotely
    handoff/                # job cards, remote paths, transfer notes
  intermediate/wrds/        # landed extracts after rsync
  raw/wrds/                 # optional immutable remote dumps
logs/
  wrds/
sas/                        # optional top-level SAS programs
```

## Credentials And Host Access

SAS cloud and WRDS SAS credentials are **site-local**:

- never store passwords in the repo
- use existing SSH keys, site modules, or env vars already configured by the user
- common env hooks (optional, project-defined): `WRDS_SAS_HOST`, `WRDS_SAS_WORKDIR`, `WRDS_SAS_ACCOUNT`

This skill does not invent a login flow. If remote access is missing, stop with `data_access_gap`.

### SSH Preflight Caveat

Use the user's configured SSH alias and test a harmless remote command before upload.
Do not force `BatchMode=yes`; see `references/sas-handoff.md` for the zero-prompt
`keyboard-interactive` caveat. Stop for the user if a real credential or MFA prompt appears.

## Workflow

### Step 1: Confirm Escalation Reason

Before any SAS submit, write why R was insufficient:

| Field | Example |
|---|---|
| `reason` | `timeout` / `oom` / `hard_fail` / `auth_blocker` / `user_required` |
| `query_id` | stable id shared with the R attempt |
| `evidence` | path to redacted log |
| `r_path_status` | `failed` or `partial` |

If the only reason is “dataset is big,” return to `wrds-query-bridge` and chunk the pull.

### Step 2: Write Or Align SAS Program

Create or repair a `.sas` program that:

- uses the same universe filters as the intended R SQL when practical
- keeps variable lists explicit
- writes a clear remote output path (`.sas7bdat`, `.csv`, or parquet if the site supports it)
- avoids zero-filling missing values at extract time

Store under `data/wrds/sas/<query_id>.sas` or `sas/<query_id>.sas`.

### Step 3: Submit Job (Generic `qsas`)

Prefer the site’s batch entrypoint. Document the abstract sequence as **qsas-class** submit:

```bash
# Pseudocode — replace with project/site command
qsas data/wrds/sas/<query_id>.sas
# or: ssh "$WRDS_SAS_HOST" 'cd $WRDS_SAS_WORKDIR && qsas program.sas'
```

Record in `data/wrds/handoff/<query_id>.md`:

- submit command (no secrets)
- job id if any
- remote workdir and expected output path
- submit timestamp

If the site uses a different scheduler name, still document the same fields; do not invent Option-specific steps.

### Step 4: Transfer With `rsync` (Or `scp`)

After the job completes:

```bash
# Pseudocode — paths are project/site specific
rsync -avP "${WRDS_SAS_HOST}:${REMOTE_OUT}" "data/intermediate/wrds/"
```

Prefer `rsync` for resumable transfers. Use `scp` only when `rsync` is unavailable.

### Step 5: Verify Hash And Update Manifest

```bash
shasum -a 256 data/intermediate/wrds/<file>
```

Update `DATA_MANIFEST` with:

- `backend = sas_cloud`
- local path, format, n_rows/n_cols if known
- `content_hash`
- `status = complete | partial | failed`
- link to SAS program and handoff note
- escalation reason block

### Step 6: Handoff To Analysis

- Prefer converting remote SAS datasets to parquet/csv for R analysis when needed
- Route analysis to `r-analysis-bridge` or `stata-analysis-bridge`
- Update passport through `business-run-passport` when writing is allowed

## Output Contract

```markdown
# WRDS SAS Cloud Handoff

## Escalation Reason
## SAS Program
## Submit
| job_id | host_label | remote_out | submitted_at |

## Transfer
| method | local_path | bytes | content_hash |

## Manifest Rows Updated
## Issues
## Next Steps
```

## Rules

- For local tasks, complete only the requested stage and mark downstream gaps as next-stage inputs.
- Generic handoff only: **qsas-class submit → rsync/scp → hash → manifest**. No Option-specific product workflow.
- Escalate only per `business-wrds-policy.md`; always record the reason.
- No fixed row threshold for choosing SAS.
- Missing values are not zeros.
- No secrets in programs committed to git, handoff notes, or passport entries.
- Keep query filters aligned with the failed R attempt when the research design depends on them.
- Do not mark a transfer `complete` without a content hash (or explicit user waiver recorded in the handoff note).
