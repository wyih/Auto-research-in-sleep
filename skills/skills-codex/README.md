# `skills-codex`

Codex-native mirror and adaptation layer for the main ARIS `skills/` package.

## Scope

- Base mirror coverage: all `104` mainline skills under `skills/`
- Support directory: `shared-references/`, with all `39/39` mainline reference names mirrored
- The 24 business empirical-research skills are runtime-neutral canonical copies synchronized by `tools/sync_business_portable_mirror.py`; Codex and Grok consume them through `.agents/skills`, while the browser bridge selects the runtime adapter.
- Default reviewer contract for reviewer-heavy skills:
  - round 1: `spawn_agent`
  - follow-up: `send_input`
  - reasoning effort: `xhigh`
  - base Codex self-review: `review_independence: same-family`,
    `acceptance_status: provisional`
  - Claude/Gemini overlays or deterministic verification: `acceptance_status: accepted`
- Optional overlays:
  - `skills-codex-claude-review`
  - `skills-codex-gemini-review`

This package is still an appendage to the Claude mainline, not a separate Codex-first product line.

## Recommended Install

Project-local install is the default path for Codex and is also the shared discovery path for Grok Build:

```bash
git clone https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep.git ~/aris_repo
cd ~/your-project

bash ~/aris_repo/tools/install_aris_codex.sh .
```

For an isolated Grok/Codex smoke workspace that should not update the optional global helper pointer or AGENTS block:

```bash
bash ~/aris_repo/tools/install_aris_codex.sh . \
  --groups business-research --quiet --no-doc --no-global-pointer
grok inspect --json
```

This creates a flat managed layout:

```text
.agents/skills/<skill-name> -> ~/aris_repo/skills/skills-codex/<skill-name>
.aris/installed-skills-codex.txt
AGENTS.md   # managed Codex block
```

Reconcile after upstream changes:

```bash
cd ~/aris_repo && git pull
bash ~/aris_repo/tools/install_aris_codex.sh ~/your-project --reconcile
```

Uninstall only managed Codex entries:

```bash
bash ~/aris_repo/tools/install_aris_codex.sh ~/your-project --uninstall
```

## Cross-Machine And Team Install

Publish or select an immutable release tag, then clone that exact tag on every
machine. Install the `business-research` group rather than copying only the
pipeline entry point; the group is the exact 24-skill portable suite plus its
shared references.

macOS or Linux:

```bash
git clone --branch <release-tag> <repository-url> ~/aris_repo
bash ~/aris_repo/tools/install_aris_codex.sh /absolute/path/to/project \
  --groups business-research --quiet
```

Windows PowerShell 5.1 or PowerShell 7:

```powershell
git clone --branch <release-tag> <repository-url> "$HOME\aris_repo"
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "$HOME\aris_repo\tools\install_aris.ps1" `
  "C:\absolute\path\to\project" `
  -Platform codex `
  -ArisRepo "$HOME\aris_repo" `
  -Groups business-research `
  -Quiet
```

The Windows installer creates junctions; the macOS/Linux installer creates
symlinks. Both expose the same package under `.agents/skills`, which Codex and
Grok Build can discover. Do not copy an installed `.agents/skills` directory to
another machine because its links retain source-machine paths. Clone/extract the
release into a stable location and run the appropriate installer instead.

Browser profiles, cookies, saved credentials, WRDS credentials, licensed PDFs,
and commercial database extracts are deliberately outside the package. Each
recipient must create and sign in to a local authorized browser profile. Without
a compatible browser runtime, local files, model-native web search, open sources,
design, analysis, and writing remain usable; protected acquisition reports an
explicit adapter/access gap.

## Optional Overlays

Install the base first, then choose an overlay:

```bash
bash ~/aris_repo/tools/install_aris_codex.sh ~/your-project --reconcile --with-claude-review-overlay
```

```bash
bash ~/aris_repo/tools/install_aris_codex.sh ~/your-project --reconcile --with-gemini-review-overlay
```

Overlays only replace reviewer routing. They do not replace the base mirror or the executor model.

## Copy Install and Update

If you intentionally use a copied Codex install instead of managed project symlinks:

```bash
mkdir -p ~/.codex/skills
cp -a ~/aris_repo/skills/skills-codex/. ~/.codex/skills/
```

Update copied installs with:

```bash
bash ~/aris_repo/tools/smart_update_codex.sh
bash ~/aris_repo/tools/smart_update_codex.sh --apply
```

For a copied project-local Codex install:

```bash
bash ~/aris_repo/tools/smart_update_codex.sh --project ~/your-project
bash ~/aris_repo/tools/smart_update_codex.sh --project ~/your-project --apply
```

`smart_update_codex.sh` refuses symlink-managed installs and redirects them to `install_aris_codex.sh --reconcile`.

## Non-Degrading Skills

The following Codex skills must not silently degrade when their required capability is missing:

- `comm-lit-review`
- `research-lit`
- `paper-poster-html`
- `pixel-art`

If the required source, reviewer, or local preview capability is unavailable, the skill should stop and tell the user what to configure.
