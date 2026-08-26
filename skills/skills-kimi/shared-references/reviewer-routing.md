# Reviewer Routing

> Kimi Code mirror adaptation (normative). This file is the reviewer-routing
> contract for `skills/skills-kimi/` only. The main
> `skills/shared-references/reviewer-routing.md` documents the equivalent
> contracts for the other ARIS release lines.

## Default Reviewer Contract

All reviewer-heavy Kimi Code base skills use the same default contract:

- executor: current Kimi Code main agent
- reviewer: a fresh Kimi Code subagent, spawned through the host's `Agent` tool
- reasoning depth: the host's strongest reasoning configuration. Kimi Code's
  `Agent` tool exposes no reasoning-effort or model parameter to the caller, so
  there is no tier table and no effort flag to pin — do not invent one.
- round 1: spawn a fresh subagent (`kimi_subagent`)
- follow-up rounds: resume the saved subagent (`kimi_subagent_continue` with
  `resume: <saved agent id>`)

This is the base default for `skills/skills-kimi/`. No ARIS `— effort:` level
changes the reviewer route (ARIS `— effort:` is pipeline workload, not reviewer
reasoning depth — different axes).

**Capability fallback:** there is no model/effort fallback chain under Kimi
Code — the reviewer model is whatever the host is configured to run. If the
`Agent` tool is unavailable or the spawn fails, emit `BLOCKED` /
`REVIEW_UNAVAILABLE`; never substitute the executor's own judgment and never
fabricate a provisional PASS.

> ⚠️ **Same-family by default — provisional, never accepted.** The executor
> here is Kimi Code and the reviewer is a fresh Kimi Code subagent from the
> same model family. Its substantive PASS/WARN/FAIL may drive revisions,
> terminate a loop, and advance a resumable phase, but every positive result
> records:
>
> ```yaml
> review_independence: same-family
> acceptance_status: provisional
> ```
>
> It must never be described as cross-model acceptance. For
> `review_independence: cross-family` and `acceptance_status: accepted`,
> register the **`llm-chat`** MCP reviewer (see below). A deterministic
> verifier may also record accepted. `oracle-pro` is GPT family, so for a Kimi
> Code (Moonshot/Kimi family) executor it is cross-family — record accepted
> only when the trace binds the actual reviewer model.

## Default Pattern

Single-round review:

```text
kimi_subagent:
  # Kimi Code Agent tool — fresh reviewer subagent at the host's strongest
  # reasoning configuration
  prompt: |
    [role + task]
    Read the listed files directly.
```

Multi-round review — round 1 uses the same spawn block; save the returned
agent id, then continue with:

```text
kimi_subagent_continue:
  # Kimi Code Agent tool — resume the saved reviewer subagent
  resume: [saved reviewer agent id]
  prompt: |
    [follow-up materials only]
```

## Cross-Family Upgrade: llm-chat

The base subagent reviewer is same-family. To upgrade a verdict-bearing review
to cross-family accepted, register the neutral `llm-chat` MCP server
(`mcp-servers/llm-chat/`) in your Kimi Code configuration — see the MCP
registry in `SETUP_GUIDE.md` and the review-channel section of
`docs/KIMI_ADAPTATION.md`. Then route the review through
`mcp__llm-chat__review` (round 1) and `mcp__llm-chat__review_reply`
(follow-ups, with the saved `threadId`).

The route fails closed: it may record `acceptance_status: accepted` only when
the response reports known, different families for executor and reviewer
(`independence_verified`). Missing, unknown, or same-family identity stays
provisional / `REVIEW_UNAVAILABLE`.

## Oracle Pro Override

When the user explicitly passes `--reviewer: oracle-pro`, switch only the
reviewer route: check Oracle MCP availability, call `mcp__oracle__consult` with
model `gpt-5.5-pro` if available, otherwise warn and fall back to the default
Kimi Code subagent reviewer. `oracle-pro` is optional, never the base default,
and is GPT family (cross-family for a Kimi Code executor — see the accepted
rule above).

## Invariants

- Base skills do not use any external MCP reviewer as the default route.
- Reviewer independence still applies: pass file paths and task framing, not
  executor summaries.
- Every trace and audit artifact records `review_independence` and
  `acceptance_status`; missing metadata is treated as provisional.
- If the `Agent` tool is unavailable or fails, emit `BLOCKED` /
  `REVIEW_UNAVAILABLE`; never fabricate a provisional PASS.
- Do not wrap verdict-bearing skills in `/loop`, cron, or wall-clock retries.
  Schedule only external-world waits, then invoke the reviewer once after the
  artifact changes. See `external-cadence.md`.
- Browser-based Oracle review is acceptable for one-shot stress tests, not
  ideal for tight multi-round loops.

## Skills That Commonly Benefit From a Cross-Family Upgrade

- `research-review`
- `auto-review-loop`
- `experiment-audit`
- `proof-checker`
- `rebuttal`
- `idea-creator`
- `research-lit`
