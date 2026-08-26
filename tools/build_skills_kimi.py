#!/usr/bin/env python3
"""Build the Kimi Code CLI native ARIS skill package (``skills/skills-kimi``).

The Kimi package is the third ARIS release line, sibling of
``skills/skills-codex/``.  Sources:

- The 24 portable business skills and 9 portable shared references are copied
  byte-for-byte from the canonical ``skills/`` tree (exactly the same source
  set as ``tools/sync_business_portable_mirror.py`` — the two generators never
  write divergent content for the portable set).
- Every other skill / shared reference is converted from
  ``skills/skills-codex/`` with mechanical, idempotent text rules:

  a. fenced ``spawn_agent:`` / ``send_input:`` reviewer protocol blocks become
     Kimi Code Agent-tool subagent blocks (``kimi_subagent:`` for round 1,
     ``kimi_subagent_continue:`` with ``resume:`` for follow-ups);
  b. ``model: gpt-*`` / ``reasoning_effort: xhigh|ultra`` lines and tier prose
     become a neutral "host's strongest reasoning configuration" statement —
     Kimi Code's Agent tool has no model/effort parameter, none is invented;
  c. ``~/.codex/`` paths become ``~/.kimi-code/``; ``codex mcp add`` snippets
     become "register the MCP server in your Kimi Code configuration" (see the
     SETUP_GUIDE.md registry) — no ``kimi mcp add`` syntax is fabricated;
  d. Codex / GPT-5.x reviewer-identity wording becomes host-neutral;
  e. ``chrome:control-chrome`` / ``codex_native_chrome`` outside the portable
     set are hard errors (the portable browser skills are host-adaptive
     canonical byte copies and are excluded from this scan).

The default reviewer is a fresh Kimi Code subagent: same model family as the
executor, so every base review records ``review_independence: same-family`` /
``acceptance_status: provisional`` — the same honesty level as the Codex base
package.  The cross-family accepted upgrade path is the neutral ``llm-chat``
MCP server (``mcp-servers/llm-chat/``).

Usage:
    python3 tools/build_skills_kimi.py           # regenerate the package
    python3 tools/build_skills_kimi.py --check   # verify, write nothing
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
SRC_ROOT = SKILLS_ROOT / "skills-codex"
DEST_ROOT = SKILLS_ROOT / "skills-kimi"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_business_portable_mirror import (  # noqa: E402
    PORTABLE_REFERENCES,
    PORTABLE_SKILLS,
    included_files,
)

# ── Kimi subagent contract markers ────────────────────────────────────────
# Round-1 blocks start with `kimi_subagent:`; continuation blocks start with
# `kimi_subagent_continue:` and carry a `resume:` line.  tests/test_kimi_skill
# _mirror.py asserts these markers wherever the Codex package has spawn_agent /
# send_input blocks.

SPAWN_BLOCK_RE = re.compile(
    r"(?m)^(?P<indent>[ \t]*)```(?P<lang>yaml|text)?\n(?P=indent)spawn_agent:\n"
    r"(?P<body>[\s\S]*?)\n(?P=indent)```"
)
SEND_BLOCK_RE = re.compile(
    r"(?m)^(?P<indent>[ \t]*)```(?P<lang>yaml|text)?\n(?P=indent)send_input:\n"
    r"(?P<body>[\s\S]*?)\n(?P=indent)```"
)

# ── Hand-written package documents ────────────────────────────────────────

REVIEWER_ROUTING_MD = """# Reviewer Routing

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
"""

README_MD = """# `skills-kimi`

Kimi Code CLI native package of the ARIS skill set — the third release line,
sibling of `skills/skills-codex/`.

## Scope

- Base mirror coverage: all `106` mainline skills under `skills/`
- Support directory: `shared-references/`, with all `40/40` mainline reference
  names mirrored
- The 24 business portable skills and 9 portable shared references are
  byte-for-byte copies of the canonical `skills/` tree (the same source set as
  `tools/sync_business_portable_mirror.py`). Everything else is converted from
  `skills/skills-codex/` by `tools/build_skills_kimi.py`; regeneration is
  idempotent and `--check` verifies the package in place.
- Default reviewer contract for reviewer-heavy skills:
  - round 1: `kimi_subagent` — a fresh Kimi Code subagent via the host `Agent`
    tool, at the host's strongest reasoning configuration (Kimi Code exposes
    no model/effort parameter to the caller; none is fabricated here)
  - follow-up: `kimi_subagent_continue` with `resume: <saved agent id>`
  - base Kimi Code self-review: `review_independence: same-family`,
    `acceptance_status: provisional`
  - cross-family upgrade: register the neutral `llm-chat` MCP server
    (`mcp-servers/llm-chat/`) in your Kimi Code configuration for
    `review_independence: cross-family` / `acceptance_status: accepted`
    (fail-closed on family verification). See `docs/KIMI_ADAPTATION.md`.

## Discovery Surfaces

Kimi Code discovers skills at:

| Scope | Path |
| --- | --- |
| Project | `<project>/.agents/skills/<name>/SKILL.md` |
| User (Kimi) | `~/.kimi-code/skills/<name>/SKILL.md` |
| User (shared) | `~/.agents/skills/<name>/SKILL.md` |

## Recommended Install

```bash
git clone https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep.git ~/aris_repo

bash ~/aris_repo/tools/install_aris_kimi.sh ~/your-project --office-author "Your Name"
```

This creates a flat managed layout:

```text
.agents/skills/<skill-name> -> ~/aris_repo/skills/skills-kimi/<skill-name>
.aris/installed-skills-kimi.txt
AGENTS.md   # managed ARIS-KIMI block
```

Reconcile after upstream changes:

```bash
cd ~/aris_repo && git pull
bash ~/aris_repo/tools/install_aris_kimi.sh ~/your-project --reconcile \
  --office-author "Your Name"
```

Uninstall only managed Kimi entries:

```bash
bash ~/aris_repo/tools/install_aris_kimi.sh ~/your-project --uninstall
```

## Regenerate This Package

```bash
python3 tools/build_skills_kimi.py
python3 tools/build_skills_kimi.py --check
```

## Non-Degrading Skills

The following skills must not silently degrade when their required capability
is missing:

- `comm-lit-review`
- `research-lit`
- `paper-poster-html`
- `pixel-art`

If the required source, reviewer, or local preview capability is unavailable,
the skill should stop and tell the user what to configure.
"""

README_CN_MD = """# `skills-kimi`

ARIS skill 集合的 Kimi Code CLI 原生包 —— 第三条发行线，与
`skills/skills-codex/` 平级。完整说明见 [README.md](README.md)。

- 覆盖 `skills/` 主线全部 `106` 个 skill 与 `40/40` 个 shared-references。
- 24 个 business portable skill 与 9 个 portable reference 与 canonical
  `skills/` 字节一致；其余内容由 `tools/build_skills_kimi.py` 从
  `skills/skills-codex/` 机械转换（幂等，`--check` 校验）。
- 默认审稿契约:Kimi Code `Agent` 工具子代理（首轮 `kimi_subagent`，续轮
  `kimi_subagent_continue` + `resume`),same-family / provisional。
- 跨族升级路径：在 Kimi Code 配置中注册中性的 `llm-chat` MCP server
  (`mcp-servers/llm-chat/`)→ cross-family / accepted。详见
  `docs/KIMI_ADAPTATION.md`。

安装（详见英文 README 与 `docs/KIMI_ADAPTATION.md`):

```bash
bash tools/install_aris_kimi.sh ~/your-project --office-author "Your Name"
```

清单文件：`.aris/installed-skills-kimi.txt`。
"""

# ── Mechanical text conversion ────────────────────────────────────────────

# Protections: exact strings that must survive the model-name pass unchanged
# (factual third-party model names, not Codex reviewer identity).
PROTECTIONS = {
    "gpt-5.5-pro": "PROTECT_ORACLEMODEL",
    "GPT-5.5 Pro": "PROTECT_ORACLEMODELTITLE",
    "ultracode": "PROTECT_ULTRACODE",
    "Codex app-server": "PROTECT_CODEX_APPSERVER",
}

# Exact-string replacements, longest/most-specific first within each phase.
# Phase A runs before the fenced-block rewrite, Phase B after it.
REPLACEMENTS_A: list[tuple[str, str]] = [
    # ── host / package identity ──────────────────────────────────────────
    ("Codex mirror adaptation (normative).", "Kimi Code mirror adaptation (normative)."),
    ("Codex mirror adaptation (normative)", "Kimi Code mirror adaptation (normative)"),
    (
        "In this mirror the executor is the\n> current Codex agent and the default reviewer is a fresh `spawn_agent` Codex\n> agent.",
        "In this package the executor is\n> the current Kimi Code main agent and the default reviewer is a fresh\n> `kimi_subagent` subagent.",
    ),
    ("Codex mirror", "Kimi Code mirror"),
    ("base Codex mirror", "base Kimi Code package"),
    ("the base Codex mirror", "the base Kimi Code package"),
    ("in the base mirror", "in the base package"),
    ("in base Codex", "in base Kimi Code"),
    ("base Codex", "base Kimi Code"),
    ("> **Codex assurance:**", "> **Kimi Code assurance:**"),
    ("skills-codex-claude-review", "llm-chat MCP"),
    ("skills-codex-gemini-review", "llm-chat MCP"),
    ("skills/skills-codex/", "skills/skills-kimi/"),
    ("skills-codex", "skills-kimi"),
    ("installed-skills-codex.txt", "installed-skills-kimi.txt"),
    ("install_aris_codex.sh/smart_update_codex.sh", "install_aris_kimi.sh"),
    ("install_aris_codex.sh", "install_aris_kimi.sh"),
    ("smart_update_codex.sh", "install_aris_kimi.sh --reconcile"),
    ("~/.codex/", "~/.kimi-code/"),
    (".codex/mcp-servers", "aris-repo mcp-servers"),
    ("/.codex/", "/.kimi-code/"),
    ("codex-gpt-5.6-sol", "kimi-code"),
    # ── acquittal receipt examples ───────────────────────────────────────
    ('"backend":"codex","effort":"xhigh"', '"backend":"kimi-subagent","effort":"host-strongest"'),
    ('"backend": "codex", "effort": "xhigh"', '"backend": "kimi-subagent", "effort": "host-strongest"'),
    ('"backend":"codex"', '"backend":"kimi-subagent"'),
    # ── Codex-specific mechanics → host-neutral ──────────────────────────
    (
        "- **Codex reasoning always ultra** (deep-audit tier): never below `xhigh` — only the capability fallback in `reviewer-routing.md` may step down, and only on explicit capability errors.",
        "- **Reviewer reasoning is always host-strongest**: there is no downgrade chain — if the Agent tool is unavailable, follow `reviewer-routing.md` (BLOCKED / REVIEW_UNAVAILABLE, never a weaker review).",
    ),
    (
        "  `ultra` for this deep-audit skill (capability fallback never below `xhigh`)",
        "  at the host's strongest reasoning configuration for this deep-audit skill",
    ),
    (
        "Follow the capability fallback\n  in `reviewer-routing.md` (`gpt-5.6-sol` + `ultra` → `gpt-5.6-sol` + `xhigh`\n  → `gpt-5.5` + `xhigh`), and never downgrade on timeout, rate-limit, auth,\n  transport, server, or context errors.",
        "Fail closed per `reviewer-routing.md`: under Kimi Code there is no\n  model/effort fallback chain and nothing to downgrade — never retry a weaker\n  route on timeout, rate-limit, auth, transport, server, or context errors.",
    ),
    (
        "The skill always uses Codex `gpt-5.6-sol` + `ultra` (deep-audit tier) and runs",
        "The skill always delegates at the host's strongest reasoning configuration and runs",
    ),
    (
        "**Why MiniMax instead of a secondary Codex agent?** Codex CLI uses OpenAI's Responses API (`/v1/responses`) which is not supported by third-party providers. See: https://github.com/openai/codex/discussions/7782",
        "**Why MiniMax instead of the default subagent reviewer?** The default reviewer shares the executor's model family; this skill routes review through the MiniMax API for a cross-family second opinion without wiring another CLI.",
    ),
    (
        "- Codex MCP Server configured:\n  ```bash\n  claude mcp add codex -s user -- codex mcp-server\n  ```",
        "- A reviewer channel: the default is a fresh Kimi Code subagent (no setup); for a cross-family accepted route, register the `llm-chat` MCP server in your Kimi Code configuration (see the MCP registry in SETUP_GUIDE.md §3.2).",
    ),
    (
        "- **REVIEWER_REASONING = `xhigh`** — Hard invariant; the effort knob does **not** change this.",
        "- **REVIEWER_REASONING = host-strongest** — Hard invariant; ARIS `— effort:` does **not** change this.",
    ),
    ("runs its own 13-check codex review automatically", "runs its own 13-check review automatically"),
    (
        "| Codex reasoning = xhigh | Hardcoded in Step 3 reviewer config |",
        "| Reviewer reasoning = host's strongest configuration | Hardcoded in Step 3 reviewer delegation |",
    ),
    (
        "- **RENDERER = `codex-image2`** — Native image generation bridge exposed through local Codex app-server",
        "- **RENDERER = `image2`** — native image generation bridge (`mcp-servers/codex-image2`, drives the local Codex app-server); register it as MCP server `image2` in your Kimi Code configuration (see the MCP registry in SETUP_GUIDE.md §3.2)",
    ),
    ("bridge that uses Codex native image generation", "bridge that uses its native image generation"),
    (
        "`nightmare`: GPT reads repo directly via `codex exec` + memory + debate.",
        "`nightmare`: the reviewer reads the repo directly via a fresh subagent + memory + debate.",
    ),
    (
        "- **CODE_REVIEW = true** — GPT-5.6-Sol xhigh reviews experiment code before deployment.",
        "- **CODE_REVIEW = true** — a fresh subagent reviews experiment code at the host's strongest reasoning configuration before deployment.",
    ),
    (
        "GPT-5.6-Sol xhigh reviews the implementation in a new context",
        "a fresh subagent reviews the implementation at the host's strongest reasoning configuration",
    ),
    ("with `/codex:rescue` fallback", "with a rescue fallback"),
    ("no equivalent `codex` skill-selection probe yet", "no equivalent `kimi` skill-selection probe yet"),
    ("a `codex` thread returned", "a reviewer subagent returned"),
    ("send their verdict (codex", "send their verdict (kimi-subagent"),
    ('"codex can\'t handle long files"', '"the review CLI can\'t handle long files"'),
    ("nouns (codex / gemini / oracle", "nouns (the host CLI / gemini / oracle"),
    ("means `gpt*`/`codex*` reviewers", "means `kimi*`/`moonshot*` reviewers"),
    (
        "| Codex reasoning_effort | **≥ xhigh** (deep-audit skills run `ultra` — tier table in `reviewer-routing.md`) | Reviewer quality is non-negotiable. `effort` never moves the reviewer tier in either direction — and ARIS `— effort: max` is NOT Codex `reasoning_effort: max` (different axes: pipeline workload vs reviewer reasoning depth) |",
        "| Reviewer reasoning depth | **host's strongest configuration** (see `reviewer-routing.md`) | Reviewer quality is non-negotiable. ARIS `— effort:` never moves the reviewer route in either direction (different axes: pipeline workload vs reviewer reasoning depth) |",
    ),
    (
        "⚡ [effort: max] papers=25, ideas=16, rounds=6 | Codex: tier per reviewer-routing.md (floor xhigh)",
        "⚡ [effort: max] papers=25, ideas=16, rounds=6 | reviewer: host-strongest per reviewer-routing.md",
    ),
    ("<codex mcp thread id>", "<reviewer subagent or llm-chat thread id>"),
    ("the codex/oracle reviewer", "the subagent/oracle reviewer"),
    ("和 codex 一页一页过", "和 Kimi 一页一页过"),
    # ── MCP registration (no fabricated `kimi mcp add` syntax) ──────────
    (
        "To use qzcli as an MCP tool directly from Claude Code or Codex:\n\n"
        "```bash\n# Claude Code\nclaude mcp add qzcli -- qzcli-mcp\n\n"
        "# Codex\ncodex mcp add qzcli -- qzcli-mcp\n```",
        "To use qzcli as an MCP tool directly from Kimi Code, register the\n"
        "`qzcli-mcp` command as an MCP server named `qzcli` in your Kimi Code\n"
        "configuration (see the MCP registry in SETUP_GUIDE.md §3.2).",
    ),
    (
        "Register the Gemini bridge in Codex CLI:\n\n```bash\n"
        "codex mcp add gemini-cli -- npx -y gemini-mcp-tool\n```",
        "Register the Gemini bridge as an MCP server named `gemini-cli`\n"
        "(command: `npx -y gemini-mcp-tool`) in your Kimi Code configuration\n"
        "(see the MCP registry in SETUP_GUIDE.md §3.2).",
    ),
    (
        "Add to `~/.kimi-code/settings.json`:",
        "Register the `llm-chat` MCP server in your Kimi Code configuration\n"
        "(see the MCP registry in SETUP_GUIDE.md §3.2), with these settings:",
    ),
    # ── reviewer identity / effort prose ─────────────────────────────────
    (
        "- ALWAYS use `model: gpt-5.6-sol` + `reasoning_effort: ultra` for reviews "
        "(deep-audit tier; capability fallback per `reviewer-routing.md`, never below `xhigh`)",
        "- ALWAYS delegate reviews to a fresh Kimi Code subagent at the host's strongest "
        "reasoning configuration (see `reviewer-routing.md`)",
    ),
    (
        "- **ALWAYS use `reasoning_effort: xhigh`** for all Codex review calls.",
        "- **ALWAYS delegate review calls at the host's strongest reasoning configuration.**",
    ),
    (
        "- ALWAYS use `reasoning_effort: xhigh` for maximum reasoning depth",
        "- ALWAYS delegate reviews at the host's strongest reasoning configuration",
    ),
    (
        "Invoke `spawn_agent` with `model: gpt-5.6-sol`, `reasoning_effort: xhigh`, and a fresh thread. "
        "Do not reuse prior reviewer context.",
        "Invoke the Kimi Code Agent tool with a fresh subagent at the host's strongest reasoning "
        "configuration. Do not reuse prior reviewer context.",
    ),
    (
        "pin `model: gpt-5.6-sol` + `reasoning_effort: xhigh` per `../shared-references/reviewer-routing.md`",
        "delegate at the host's strongest reasoning configuration per `../shared-references/reviewer-routing.md`",
    ),
    (
        "reviewer via `spawn_agent` (`reasoning_effort: ultra`, read-only, paths-only per",
        "reviewer via a fresh Kimi Code subagent (host's strongest reasoning configuration, read-only, paths-only per",
    ),
    (
        "`reasoning_effort: xhigh` is invariant across all `effort` levels for any Codex call invoked by sub-skills.",
        "Delegating at the host's strongest reasoning configuration is invariant across all `effort` levels for any reviewer subagent call invoked by sub-skills.",
    ),
    ("`reasoning_effort: xhigh` is invariant.", "Host-strongest reasoning delegation is invariant."),
    (
        "`reasoning_effort: xhigh` is non-negotiable across all levels.",
        "Host-strongest reasoning delegation is non-negotiable across all levels.",
    ),
    (
        "**`reasoning_effort: xhigh`** is invariant across all `effort` levels.",
        "**Host-strongest reasoning delegation** is invariant across all `effort` levels.",
    ),
    (
        "- Always use `model_reasoning_effort: \"xhigh\"` for maximum analysis depth.",
        "- Always delegate at the host's strongest reasoning configuration for maximum analysis depth.",
    ),
    (
        "xhigh reasoning is non-negotiable (see `../shared-references/effort-contract.md`). "
        "If the account has no `gpt-5.6-sol` access, follow the capability fallback chain in "
        "`../shared-references/reviewer-routing.md` (`gpt-5.5`+`xhigh`; `gpt-5.4` only as an explicit user override).",
        "Delegating at the host's strongest reasoning configuration is non-negotiable "
        "(see `../shared-references/effort-contract.md` and `../shared-references/reviewer-routing.md`).",
    ),
    (
        "Send a detailed prompt with ultra reasoning:",
        "Send a detailed prompt to the reviewer subagent:",
    ),
    (
        "Send a detailed prompt with xhigh reasoning:",
        "Send a detailed prompt to the reviewer subagent:",
    ),
    (
        "Call REVIEWER_MODEL via `spawn_agent` (`spawn_agent`) with xhigh reasoning:\n```\nreasoning_effort: xhigh\n```",
        "Call REVIEWER_MODEL via the Kimi Code Agent tool (fresh subagent at the host's strongest reasoning configuration):\n"
        "```text\nkimi_subagent:\n  # Kimi Code Agent tool — fresh reviewer subagent\n"
        "  prompt: |\n    [Full novelty briefing + prior work list + specific novelty questions]\n```",
    ),
    (
        "Call REVIEWER_MODEL via `spawn_agent` (`spawn_agent`) with xhigh reasoning:",
        "Call REVIEWER_MODEL via the Kimi Code Agent tool (fresh subagent at the host's strongest reasoning configuration):",
    ),
    (
        "Send to `REVIEWER_MODEL` via `spawn_agent` with xhigh reasoning:",
        "Send to `REVIEWER_MODEL` via the Kimi Code Agent tool (fresh subagent):",
    ),
    (
        "Call `REVIEWER_MODEL` via a dedicated Codex reviewer agent at xhigh reasoning:",
        "Call `REVIEWER_MODEL` via a fresh Kimi Code reviewer subagent at the host's strongest reasoning configuration:",
    ),
    (
        "Use `send_input` with the returned agent id to continue the conversation:",
        "Resume the returned subagent (Agent tool `resume` with the saved agent id) to continue the conversation:",
    ),
    (
        "If this is round 2+, use `send_input` with the saved agent id to maintain continuity.",
        "If this is round 2+, resume the saved reviewer subagent (Agent tool `resume` + saved agent id) to maintain continuity.",
    ),
    (
        "Use `send_input` with the saved reviewer id from Round 1:",
        "Resume the saved reviewer subagent from Round 1 (Agent tool `resume`):",
    ),
    (
        "Send the rebuttal to the same reviewer via `send_input`:",
        "Send the rebuttal to the same reviewer subagent via Agent-tool `resume`:",
    ),
    (
        "Send the rebuttal to the same reviewer via `send_input`.",
        "Send the rebuttal to the same reviewer subagent via Agent-tool `resume`.",
    ),
    (
        "Re-submit to the same examiner via `send_input` using the saved reviewer id",
        "Re-submit to the same examiner subagent via Agent-tool `resume` using the saved agent id",
    ),
    (
        "re-submit for another round via `send_input`.",
        "re-submit for another round via Agent-tool `resume`.",
    ),
    (
        "- **Save `agent_id` from Phase 2** and use `send_input` for later rounds.",
        "- **Save `agent_id` from Phase 2** and resume that subagent for later rounds.",
    ),
    (
        "Save agent id from first call, use `send_input` for subsequent rounds",
        "Save the agent id from the first call, use Agent-tool `resume` for subsequent rounds",
    ),
    (
        "use spawn_agent / send_input with the Codex reviewer at the call's declared tier",
        "use the kimi_subagent / kimi_subagent_continue contract with the Kimi Code reviewer subagent",
    ),
    (
        "uses normal Codex xhigh review through `spawn_agent` / `send_input`",
        "uses a normal Kimi Code subagent review through the kimi_subagent / kimi_subagent_continue contract",
    ),
    (
        "Use the same `spawn_agent` / `send_input` route as medium,",
        "Use the same kimi_subagent / kimi_subagent_continue route as medium,",
    ),
    (
        "If you run the reviewer directly, use `spawn_agent` for Round 1 and `send_input` for follow-up rounds.",
        "If you run the reviewer directly, use `kimi_subagent` for Round 1 and `kimi_subagent_continue` for follow-up rounds.",
    ),
    (
        "Use `spawn_agent` and `send_input` when the user has explicitly allowed delegation or subagents.",
        "Use the Kimi Code Agent tool (`kimi_subagent` / `kimi_subagent_continue`) when the user has explicitly allowed delegation or subagents.",
    ),
    # ── REVIEWER_BACKEND constant lines ──────────────────────────────────
    (
        "- **REVIEWER_BACKEND = `codex`** — Default: Codex reviewer agent (`spawn_agent`, ultra — deep-audit tier). "
        "Override with `— reviewer: oracle-pro` for GPT-5.5 Pro via Oracle MCP. See `shared-references/reviewer-routing.md`.",
        "- **REVIEWER_BACKEND = `kimi-subagent`** — Default: fresh Kimi Code reviewer subagent via the Agent tool "
        "(host's strongest reasoning configuration). Override with `— reviewer: oracle-pro` for PROTECT_ORACLEMODELTITLE via "
        "Oracle MCP, or register `llm-chat` for a cross-family accepted route. See `shared-references/reviewer-routing.md`.",
    ),
    (
        "- **REVIEWER_BACKEND = `codex`** — Default: Codex xhigh reviewer through `spawn_agent` / `send_input`. "
        "Use `--reviewer: oracle-pro` only when explicitly requested; if Oracle is unavailable, warn and fall back to Codex xhigh.",
        "- **REVIEWER_BACKEND = `kimi-subagent`** — Default: Kimi Code reviewer subagent through the "
        "kimi_subagent / kimi_subagent_continue contract. Use `--reviewer: oracle-pro` only when explicitly "
        "requested; if Oracle is unavailable, warn and fall back to the default subagent reviewer.",
    ),
    (
        "- **REVIEWER_BACKEND = `codex`** — Default: Codex xhigh reviewer. Use `--reviewer: oracle-pro` only when explicitly requested; if Oracle is unavailable, warn and fall back to Codex xhigh.",
        "- **REVIEWER_BACKEND = `kimi-subagent`** — Default: Kimi Code reviewer subagent at the host's strongest "
        "reasoning configuration. Use `--reviewer: oracle-pro` only when explicitly requested; if Oracle is "
        "unavailable, warn and fall back to the default subagent reviewer.",
    ),
    (
        "- **REVIEWER_BACKEND = `codex`** — Default: Codex xhigh stress tester. Use `--reviewer: oracle-pro` only when explicitly requested; if Oracle is unavailable, warn and fall back to Codex xhigh. See `../shared-references/reviewer-routing.md`.",
        "- **REVIEWER_BACKEND = `kimi-subagent`** — Default: Kimi Code subagent stress tester. Use "
        "`--reviewer: oracle-pro` only when explicitly requested; if Oracle is unavailable, warn and fall back "
        "to the default subagent reviewer. See `../shared-references/reviewer-routing.md`.",
    ),
    (
        "- **REVIEWER_BACKEND = `codex`** — Default reviewer route for optional literature synthesis cross-checks. Use `--reviewer: oracle-pro` only when explicitly requested; if Oracle is unavailable, warn and continue with Codex xhigh or local synthesis.",
        "- **REVIEWER_BACKEND = `kimi-subagent`** — Default reviewer route for optional literature synthesis "
        "cross-checks. Use `--reviewer: oracle-pro` only when explicitly requested; if Oracle is unavailable, "
        "warn and continue with the default subagent reviewer or local synthesis.",
    ),
    # ── shared-reference normative notes ─────────────────────────────────
    (
        "> `mcp__codex__codex`, read them as current executor or fresh `spawn_agent`;\n"
        "> follow-up dialogue uses `send_input` only when continuity is intentional.",
        "> the Agent tool, read them as the current executor or a fresh `kimi_subagent`;\n"
        "> follow-up dialogue uses `kimi_subagent_continue` only when continuity is intentional.",
    ),
    (
        "`spawn_agent` route is same-family/provisional; a Claude/Gemini overlay or",
        "`kimi_subagent` route is same-family/provisional; the `llm-chat` cross-family route or",
    ),
    (
        "`spawn_agent` would REWRITE an upstream contract — forbidden.",
        "`kimi_subagent` would REWRITE an upstream contract — forbidden.",
    ),
    (
        "> accepted. Replace mainline Codex MCP examples with fresh `spawn_agent` calls;",
        "> accepted. Replace mainline Codex MCP examples with fresh `kimi_subagent` calls;",
    ),
    (
        "reviewer calls into `spawn_agent` would rewrite an upstream contract and is",
        "reviewer calls into `kimi_subagent` would rewrite an upstream contract and is",
    ),
    (
        "spawn_agent\n  model: gpt-5.6-sol\n  reasoning_effort: xhigh",
        "kimi_subagent\n  # Kimi Code Agent tool — fresh reviewer subagent",
    ),
    # ── trace / governance JSON examples ─────────────────────────────────
    ('"executor": "codex"', '"executor": "kimi"'),
    ('"executor_family": "openai"', '"executor_family": "moonshot"'),
    ('"reviewer_family": "openai"', '"reviewer_family": "moonshot"'),
    ('"executor_model": "gpt-5.6-sol"', '"executor_model": "kimi-code"'),
    ('"reviewer_model": "gpt-5.6-sol"', '"reviewer_model": "kimi-code"'),
    ('"reviewer_model": "gpt-5.5"', '"reviewer_model": "kimi-code"'),
    ('"model": "gpt-5.6-sol"', '"model": "kimi-code"'),
    ('"reasoning_effort": "xhigh"', '"reasoning_depth": "host-strongest"'),
    ('"reviewer_reasoning": "xhigh"', '"reviewer_reasoning": "host-strongest"'),
    ('"tool": "spawn_agent"', '"tool": "kimi_subagent"'),
    ('"event":"spawn_agent"', '"event":"kimi_subagent"'),
    ('"verdict_id": "codex_thread_abc123"', '"verdict_id": "kimi_agent_abc123"'),
    ("the codex thread id, the oracle", "the reviewer thread id, the oracle"),
    ("| `ERROR` | `codex_api_error` | `spawn_agent` call failed |", "| `ERROR` | `subagent_error` | `kimi_subagent` call failed |"),
    ("--executor codex-gpt-5.6-sol", "--executor kimi-code"),
    ("--executor codex`", "--executor kimi-code`"),
    ("--reviewer gpt-5.6-sol", "--reviewer kimi-code"),
    ("`gpt-5.5`+`codex`", "`kimi`+`kimi-code`"),
    ("`gpt-5.5`+`oracle-pro`", "`gpt*`+`oracle-pro`"),
    # ── misc host-specific mechanics ─────────────────────────────────────
    (
        "(2026-08-10, ~10 rounds of gpt-5.6-sol at xhigh/ultra)",
        "(2026-08-10, ~10 rounds of fresh-subagent review at the host's strongest reasoning configuration)",
    ),
    (
        "**Reviewer model**: gpt-5.6-sol ultra, fresh agents (no send_input)",
        "**Reviewer model**: the host's strongest model, fresh subagents (no resume)",
    ),
    (
        "2. **Critical review**: Use GPT-5.6-Sol via `send_input` (same agent):",
        "2. **Critical review**: Resume the same reviewer subagent via Agent-tool `resume`:",
    ),
    (
        "**Codex prompt (mandatory shape).** Send this as a fresh reviewer call (`spawn_agent`, NOT `send_input`):",
        "**Reviewer prompt (mandatory shape).** Send this as a fresh subagent call (`kimi_subagent`, NOT `kimi_subagent_continue`):",
    ),
    (
        "# … then the skill skips the spawn_agent review step if --no-review",
        "# … then the skill skips the kimi_subagent review step if --no-review",
    ),
    (
        "fire a fresh `spawn_agent` call (NEVER `send_input`; ",
        "fire a fresh `kimi_subagent` call (NEVER `kimi_subagent_continue`; ",
    ),
    (
        "**If `spawn_agent` is not available** (e.g., user runs `/render-html` on a Codex-CLI-only setup where Codex MCP isn't wired):",
        "**If the Agent tool is not available** (e.g., the host session does not expose subagents):",
    ),
    (
        "or re-run with Codex MCP available.",
        "or re-run in a session with the Agent tool available.",
    ),
    (
        "- **Codex MCP**: `spawn_agent` must be available (the user must be signed in to Codex MCP). The skill aborts at Phase 0 if Codex MCP cannot be reached.",
        "- **Agent tool**: subagent delegation must be available in the current Kimi Code session. The skill aborts at Phase 0 if the Agent tool cannot be reached.",
    ),
    (
        "Codex backend depends on this file for round-to-round continuity",
        "Backends without native subagent continuity depend on this file for round-to-round continuity",
    ),
    (
        "Copilot backend depends on this file for round-to-round continuity (every round is a fresh process), so",
        "Backends without native subagent continuity depend on this file for round-to-round continuity (every round is a fresh process), so",
    ),
]

REPLACEMENTS_B: list[tuple[str, str]] = [
    # Runs after the fenced-block rewrite; generic mop-up, ordered.
    ("codex-ledger.md", "proof-ledger.md"),
    ("local-codex-fallback", "local-kimi-fallback"),
    ('"reviewer_reasoning": "ultra"', '"reviewer_reasoning": "host-strongest"'),
    ("gpt-5.6-sol-ultra", "kimi-code"),
    ("`reasoning_effort: xhigh`", "host-strongest reasoning delegation"),
    ("at xhigh reasoning", "at the host's strongest reasoning configuration"),
    ("with xhigh reasoning", "at the host's strongest reasoning configuration"),
    ("(xhigh reasoning)", "(host's strongest reasoning configuration)"),
    (" (ultra reasoning)", ""),
    ("| Manifest filename | `installed-skills.txt` | `installed-skills-kimi.txt` |",
     "| Manifest filename | mainline default manifest | `installed-skills-kimi.txt` |"),
    ("files codex should read", "files the reviewer should read"),
    ("the codex judgment", "the reviewer judgment"),
    ("the codex prompt", "the reviewer prompt"),
    ("the codex thread", "the reviewer thread"),
    ("the codex call", "the reviewer call"),
    ("fresh codex", "fresh subagent"),
    ("codex traces", "reviewer traces"),
    ("codex trace", "reviewer trace"),
    ("codex CLI", "Kimi Code CLI"),
    ("`spawn_agent` shards", "`kimi_subagent` shards"),
    ("fresh `spawn_agent` Codex review", "fresh `kimi_subagent` review"),
    ("fresh Codex `spawn_agent`", "fresh Kimi Code `kimi_subagent`"),
    ("fresh `spawn_agent` Codex", "fresh `kimi_subagent`"),
    ("Codex `spawn_agent` threads", "`kimi_subagent` threads"),
    ("`spawn_agent` reviewer calls", "`kimi_subagent` reviewer calls"),
    ("`send_input` reviewer continuations", "`kimi_subagent_continue` reviewer continuations"),
    ("a fresh `spawn_agent` reviewer", "a fresh `kimi_subagent` reviewer"),
    ("fresh `spawn_agent` calls", "fresh `kimi_subagent` calls"),
    ("fresh `spawn_agent` call", "fresh `kimi_subagent` call"),
    ("fresh `spawn_agent`", "fresh `kimi_subagent`"),
    ("`spawn_agent` call", "`kimi_subagent` call"),
    ("`spawn_agent` calls", "`kimi_subagent` calls"),
    ("via `spawn_agent`", "via `kimi_subagent`"),
    ("`spawn_agent`", "`kimi_subagent`"),
    ("never `send_input`", "never `kimi_subagent_continue`"),
    ("NOT `send_input`", "NOT `kimi_subagent_continue`"),
    ("no `send_input`", "no `kimi_subagent_continue`"),
    ("`send_input`", "`kimi_subagent_continue`"),
    ('"tool":"spawn_agent"', '"tool":"kimi_subagent"'),
    ("spawn_agent", "kimi_subagent"),
    ("send_input", "kimi_subagent_continue"),
    ("codex-reply", "`resume` continuation"),
    ("mcp__codex-image2__", "mcp__image2__"),
    ("mcp__codex__codex", "the Kimi Code Agent tool"),
    # reviewer model names → host-neutral
    ("model `gpt-5.6-sol` (GPT-5.6-Sol)", "the host's strongest reviewer model"),
    ("via GPT-5.6-Sol xhigh review", "via host-strongest subagent review"),
    ("via GPT-5.6-Sol ultra review", "via host-strongest subagent review"),
    ("GPT-5.6-Sol xhigh", "host-strongest subagent"),
    ("GPT-5.6-Sol ultra", "host-strongest subagent"),
    ("iterative GPT-5.6-Sol review", "iterative subagent review"),
    ("fresh-agent Codex GPT-5.6-Sol ultra review", "fresh-subagent host-strongest review"),
    ("fresh-agent GPT-5.6-Sol review", "fresh-subagent review"),
    ("GPT-5.6-Sol", "the host reviewer model"),
    ("gpt-5.6-sol", "the host reviewer model"),
    ("via GPT-5.5 xhigh review", "via host-strongest subagent review"),
    ("GPT-5.5 xhigh", "host-strongest subagent"),
    ("Codex/GPT-5.5", "the Kimi Code reviewer"),
    ("Codex/GPT", "Kimi Code"),
    ("GPT-5.5", "the host reviewer model"),
    ("gpt-5.5", "the host reviewer model"),
    ("gpt-5.4", "the host reviewer model"),
    # host identity
    ("secondary Codex agent", "secondary Kimi Code subagent"),
    ("a second Codex agent", "a fresh Kimi Code subagent"),
    ("Fresh Codex reviewer", "Fresh Kimi Code subagent reviewer"),
    ("fresh Codex reviewer", "fresh Kimi Code subagent reviewer"),
    ("fresh Codex agent", "fresh Kimi Code subagent"),
    ("fresh Codex", "fresh Kimi Code"),
    ("Codex reviewer agent", "Kimi Code reviewer subagent"),
    ("Codex reviewer", "Kimi Code reviewer"),
    ("Codex xhigh review", "Kimi Code subagent review"),
    ("Codex Review", "Kimi Code Review"),
    ("— Codex Review", "— Kimi Code Review"),
    ("Codex agent", "Kimi Code subagent"),
    ("via Codex MCP", "via a Kimi Code subagent"),
    ("instead of Codex MCP", "instead of the default same-family subagent"),
    ("Codex MCP", "the Kimi Code Agent tool"),
    ("A Claude/Gemini overlay", "An `llm-chat` cross-family route"),
    ("Claude/Gemini overlays", "`llm-chat` cross-family routes"),
    ("Claude/Gemini overlay", "`llm-chat` cross-family route"),
    ("Codex CLI", "Kimi Code CLI"),
    ("for Codex CLI", "for Kimi Code CLI"),
    ("for Codex", "for Kimi Code CLI"),
    ("Codex", "Kimi Code"),
]

# Line-level regex rules, applied after REPLACEMENTS_A and block rewrites.
REVIEWER_MODEL_LINE_RE = re.compile(r"^\s*-?\s*\**REVIEWER_MODEL\**\s*=[^\n]*$", re.MULTILINE)
REVIEWER_BACKEND_LINE_RE = re.compile(
    r"^\s*-?\s*\**REVIEWER_BACKEND\**\s*=\s*`codex`[^\n]*$", re.MULTILINE
)
ALLOWED_TOOLS_RE = re.compile(r"^allowed-tools:\s*(.+)$", re.MULTILINE)


def _reviewer_model_line(match: re.Match[str]) -> str:
    line = match.group(0)
    if "gpt" not in line.lower() and "codex" not in line.lower():
        return line  # e.g. auto-review-loop-minimax keeps its MiniMax default
    return (
        "- **REVIEWER_MODEL = `kimi-subagent`** — the host's strongest model, "
        "used via a fresh Kimi Code subagent (Agent tool; the host exposes no "
        "model/effort override parameter, so none is pinned)."
    )


def _reviewer_backend_line(match: re.Match[str]) -> str:
    return (
        "- **REVIEWER_BACKEND = `kimi-subagent`** — Default: fresh Kimi Code "
        "reviewer subagent via the Agent tool (host's strongest reasoning "
        "configuration; same-family, provisional). Override with "
        "`--reviewer: oracle-pro` for PROTECT_ORACLEMODELTITLE via Oracle MCP, or register "
        "`llm-chat` for a cross-family accepted route (see "
        "`shared-references/reviewer-routing.md`)."
    )


def _allowed_tools_line(match: re.Match[str]) -> str:
    tools = []
    for tok in match.group(1).split(","):
        tok = tok.strip()
        if not tok:
            continue
        if tok == "spawn_agent":
            tok = "Agent"
        elif tok == "send_input":
            continue  # same Agent tool; resume is a parameter, not a tool
        tok = tok.replace("mcp__codex-image2__", "mcp__image2__")
        if tok not in tools:
            tools.append(tok)
    return "allowed-tools: " + ", ".join(tools)


def _rewrite_spawn_block(match: re.Match[str]) -> str:
    indent = match.group("indent")
    out = [
        f"{indent}```text",
        f"{indent}kimi_subagent:",
        f"{indent}  # Kimi Code Agent tool — fresh reviewer subagent at the host's",
        f"{indent}  # strongest reasoning configuration",
    ]
    for line in match.group("body").splitlines():
        stripped = line.strip()
        if stripped.startswith("model:") or stripped.startswith("reasoning_effort:"):
            continue
        if stripped.startswith("message:"):
            line = line.replace("message:", "prompt:", 1)
        out.append(line)
    out.append(f"{indent}```")
    return "\n".join(out)


def _rewrite_send_block(match: re.Match[str]) -> str:
    indent = match.group("indent")
    out = [
        f"{indent}```text",
        f"{indent}kimi_subagent_continue:",
        f"{indent}  # Kimi Code Agent tool — resume the saved reviewer subagent",
    ]
    for line in match.group("body").splitlines():
        stripped = line.strip()
        if stripped.startswith("model:") or stripped.startswith("reasoning_effort:"):
            continue
        for key in ("target:", "agent_id:", "id:"):
            if stripped.startswith(key):
                line = line.replace(key, "resume:", 1)
                break
        if stripped.startswith("message:"):
            line = line.replace("message:", "prompt:", 1)
        out.append(line)
    out.append(f"{indent}```")
    return "\n".join(out)


def transform_text(text: str) -> str:
    # REPLACEMENTS_A runs on the raw source so its patterns can name protected
    # tokens; the protection pass then shields both surviving source mentions
    # and any protected token an A-rule emitted.
    for old, new in REPLACEMENTS_A:
        text = text.replace(old, new)
    for old, new in PROTECTIONS.items():
        text = text.replace(old, new)
    text = SPAWN_BLOCK_RE.sub(_rewrite_spawn_block, text)
    text = SEND_BLOCK_RE.sub(_rewrite_send_block, text)
    text = REVIEWER_MODEL_LINE_RE.sub(_reviewer_model_line, text)
    text = REVIEWER_BACKEND_LINE_RE.sub(_reviewer_backend_line, text)
    text = ALLOWED_TOOLS_RE.sub(_allowed_tools_line, text)
    for old, new in REPLACEMENTS_B:
        text = text.replace(old, new)
    for old, new in sorted(PROTECTIONS.items(), key=lambda kv: -len(kv[1])):
        text = text.replace(new, old)
    return text


# ── Leak audit ────────────────────────────────────────────────────────────

FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    ("spawn_agent", r"spawn_agent"),
    ("send_input", r"send_input"),
    ("reasoning_effort", r"reasoning_effort"),
    ("~/.codex", r"~/\.codex"),
    (".codex/ path", r"\.codex/"),
    ("mcp__codex*", r"mcp__codex"),
    ("chrome:control-chrome", r"chrome:control-chrome"),
    ("codex_native_chrome", r"codex_native_chrome"),
    ("gpt-5.x model name", r"(?i)gpt-5"),
    ("xhigh effort", r"\bxhigh\b"),
    ("ultra effort", r"\bultra\b"),
    ("skills-codex", r"skills-codex"),
    ("installed-skills-codex.txt", r"installed-skills-codex"),
    ("installed-skills.txt", r"installed-skills\.txt"),
    ("install_aris_codex", r"install_aris_codex"),
    ("smart_update_codex", r"smart_update_codex"),
    ("codex mcp add", r"codex mcp add"),
    ("codex-reply", r"codex-reply"),
    ("Codex", r"\bCodex\b"),
    ("codex", r"\bcodex\b"),
]

# Factual external references that are allowed to remain verbatim.
AUDIT_WHITELIST = (
    "Codex app-server",  # mcp-servers/codex-image2 drives the real Codex app-server
    "codex-image2",  # factual repo path of the image-generation bridge
    "gpt-5.5-pro",  # Oracle's actual model name (opt-in override route)
    "GPT-5.5 Pro",
)


def audit_text(text: str, rel: str) -> list[str]:
    masked = text
    for allowed in AUDIT_WHITELIST:
        masked = masked.replace(allowed, "")
    hits: list[str] = []
    for label, pattern in FORBIDDEN_PATTERNS:
        for m in re.finditer(pattern, masked):
            line_no = masked.count("\n", 0, m.start()) + 1
            hits.append(f"{rel}:{line_no}: leaked {label}")
    return hits


# ── Package assembly ──────────────────────────────────────────────────────

IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc", "*.pyo")


def expected_files() -> dict[str, bytes]:
    """Return the full package as {relative_path: bytes}, built in memory."""
    out: dict[str, bytes] = {}
    problems: list[str] = []

    def put(rel: str, data: bytes) -> None:
        out[rel] = data

    # 1. Portable business skills: byte-for-byte from canonical skills/.
    for name in PORTABLE_SKILLS:
        source = SKILLS_ROOT / name
        if not (source / "SKILL.md").is_file():
            problems.append(f"missing canonical skill: skills/{name}")
            continue
        for rel, data in included_files(source).items():
            put(f"{name}/{rel}", data)

    # 2. Portable shared references: byte-for-byte from canonical skills/.
    for name in PORTABLE_REFERENCES:
        source = SKILLS_ROOT / "shared-references" / name
        if not source.is_file():
            problems.append(f"missing canonical reference: skills/shared-references/{name}")
            continue
        put(f"shared-references/{name}", source.read_bytes())

    # 3. Non-portable skills: convert from skills/skills-codex/.
    for skill_dir in sorted(p for p in SRC_ROOT.iterdir() if (p / "SKILL.md").is_file()):
        name = skill_dir.name
        if name in PORTABLE_SKILLS:
            continue
        for rel, data in included_files(skill_dir).items():
            dest_rel = f"{name}/{rel}"
            if rel.endswith(".md"):
                converted = transform_text(data.decode("utf-8"))
                problems.extend(audit_text(converted, dest_rel))
                put(dest_rel, converted.encode("utf-8"))
            else:
                put(dest_rel, data)  # scripts/templates ship byte-identical

    # 4. Non-portable shared references: convert; reviewer-routing is authored.
    src_refs = SRC_ROOT / "shared-references"
    for ref in sorted(src_refs.glob("*.md")):
        if ref.name in PORTABLE_REFERENCES:
            continue
        dest_rel = f"shared-references/{ref.name}"
        if ref.name == "reviewer-routing.md":
            converted = REVIEWER_ROUTING_MD
        else:
            converted = transform_text(ref.read_text(encoding="utf-8"))
        problems.extend(audit_text(converted, dest_rel))
        put(dest_rel, converted.encode("utf-8"))

    # 5. Package documents.
    put("README.md", README_MD.encode("utf-8"))
    put("README_CN.md", README_CN_MD.encode("utf-8"))

    if problems:
        raise SystemExit(
            "skills-kimi conversion refused — Codex residue in non-portable output:\n"
            + "\n".join(f"- {p}" for p in problems)
        )
    return out


def disk_files() -> dict[str, bytes]:
    if not DEST_ROOT.is_dir():
        return {}
    return included_files(DEST_ROOT)


def check() -> list[str]:
    expected = expected_files()
    actual = disk_files()
    problems: list[str] = []
    for rel in sorted(expected.keys() - actual.keys()):
        problems.append(f"missing packaged file: skills/skills-kimi/{rel}")
    for rel in sorted(actual.keys() - expected.keys()):
        problems.append(f"unexpected packaged file: skills/skills-kimi/{rel}")
    for rel in sorted(expected.keys() & actual.keys()):
        if expected[rel] != actual[rel]:
            problems.append(f"content drift: skills/skills-kimi/{rel}")
    return problems


def build() -> None:
    files = expected_files()
    if DEST_ROOT.exists():
        shutil.rmtree(DEST_ROOT)
    for rel, data in sorted(files.items()):
        target = DEST_ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args()

    if not args.check:
        build()

    problems = check()
    if problems:
        print("skills-kimi package drift detected:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1

    action = "verified" if args.check else "generated"
    skills = len({rel.split("/")[0] for rel in expected_files() if rel.endswith("/SKILL.md")})
    print(f"skills-kimi package {action}: {skills} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
