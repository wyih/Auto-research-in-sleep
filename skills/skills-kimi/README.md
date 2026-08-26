# `skills-kimi`

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
bash ~/aris_repo/tools/install_aris_kimi.sh ~/your-project --reconcile   --office-author "Your Name"
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
