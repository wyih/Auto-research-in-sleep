# Wiki helper resolution chain (Kimi Code mirror)

Kimi Code-side resolution chain for `research_wiki.py`. Same purpose as the
CC mirror at `../shared-references/wiki-helper-resolution.md`, adapted
for Kimi Code CLI's install layout (the helper may live under
`~/.kimi-code/skills/research-wiki/` for global installs).

## The chain

```bash
ARIS_REPO="${ARIS_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills-kimi.txt 2>/dev/null)}"
# Global pointer file written by install_aris*/smart_update* at ~/.aris/repo
# (#366) — same file the CC chain reads; covers global copy-installs with
# no project-local manifest.
if [ -z "${ARIS_REPO:-}" ] && [ -f "$HOME/.aris/repo" ]; then
    ARIS_REPO=$(cat "$HOME/.aris/repo" 2>/dev/null) || true
fi
WIKI_SCRIPT=""
[ -n "$ARIS_REPO" ] && [ -f "$ARIS_REPO/tools/research_wiki.py" ] && WIKI_SCRIPT="$ARIS_REPO/tools/research_wiki.py"
[ -z "$WIKI_SCRIPT" ] && [ -f tools/research_wiki.py ] && WIKI_SCRIPT="tools/research_wiki.py"
[ -z "$WIKI_SCRIPT" ] && [ -f ~/.kimi-code/skills/research-wiki/research_wiki.py ] && WIKI_SCRIPT="$HOME/.kimi-code/skills/research-wiki/research_wiki.py"
```

After the chain:

- `[ -n "$WIKI_SCRIPT" ]` → helper located, use as `python3 "$WIKI_SCRIPT" <subcommand>`
- `[ -z "$WIKI_SCRIPT" ]` → helper missing; pick a variant below

## Variant A — hard-fail (for `/research-wiki` itself)

```bash
[ -n "$WIKI_SCRIPT" ] || {
  echo "ERROR: research_wiki.py not found. Set ARIS_REPO, rerun install_aris_kimi.sh (refreshes ~/.aris/repo), copy to tools/, or use Kimi Code global install." >&2
  exit 1
}
```

## Variant B — warn + skip (for caller skills)

```bash
[ -n "$WIKI_SCRIPT" ] || {
  echo "WARN: research_wiki.py not found. Primary output will still be produced; wiki update is skipped." >&2
}
```

After Variant B, every helper invocation must be guarded:

```bash
[ -n "$WIKI_SCRIPT" ] && python3 "$WIKI_SCRIPT" ingest_paper research-wiki/ --arxiv-id "$id"
```

## Differences from the CC chain

| | CC | Kimi Code |
|---|---|---|
| Manifest filename | mainline default manifest | `installed-skills-kimi.txt` |
| Symlink layer (`.aris/tools/...`) | yes (PR #174 / #192) | no — Kimi Code install model is direct copy under `~/.kimi-code/skills/`, no symlink |
| Global-install layer (`~/.kimi-code/skills/<name>/...`) | no | yes |
| `cd "$(git rev-parse --show-toplevel)"` preamble | yes — guards subdir cwd | optional — Kimi Code usually invokes from project root |
| Global pointer file (`~/.aris/repo`) | yes (layer 4, #366) | yes — same file, read before the `~/.kimi-code/skills/...` global-install layer |

Outcome of both chains is the same: a populated `$WIKI_SCRIPT` env var
or an empty string + warning.

## See also

- [`integration-contract.md`](integration-contract.md) §2 — canonical-helper invariant
- `../research-wiki/SKILL.md` (Kimi Code side) — uses Variant A
- CC-side mirror: `../../shared-references/wiki-helper-resolution.md`
