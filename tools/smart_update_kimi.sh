#!/usr/bin/env bash
# smart_update_kimi.sh -- one-command update for the ARIS Kimi Code line.
#
# Kimi installs are symlinks into this clone, so updating = move the clone to a
# newer ref, then re-link added/removed skills via install_aris_kimi.sh
# --reconcile. This script wraps exactly that:
#
#   bash tools/smart_update_kimi.sh                  # dry-run plan (default)
#   bash tools/smart_update_kimi.sh --apply \
#       --project /path/to/project                   # apply: checkout + reconcile
#
# Options:
#   --to <ref>        checkout this tag/branch/commit instead of the newest
#                     business-research-suite-kimi-v* tag
#   --pull            fast-forward the current branch instead of checking out a tag
#   --project <path>  reconcile this project install (repeatable). Without any
#                     --project, only the global install (~/.aris manifest) is
#                     reconciled, if present.
#   --add-new         reconcile: accept all new upstream skills without prompting
#   --skip-new        reconcile: skip new upstream skills without prompting
#   --allow-dirty     proceed even with uncommitted tracked changes in this clone
#   --apply           perform the update; without it, only print the plan
#   -h, --help        show this help
#
# Safety:
#   - refuses to move the clone while it has uncommitted tracked changes
#     (unless --allow-dirty)
#   - never deletes anything itself; all link/unlink work is done by
#     install_aris_kimi.sh --reconcile under its own manifest rules
#   - never touches the Codex line (skills-codex) or its installs
#   - reconcile runs the installer with --quiet (its plan prompt auto-confirms);
#     new upstream skills are added by default — pass --skip-new to opt out

set -euo pipefail

APPLY=false
TO=""
PULL=false
ALLOW_DIRTY=false
NEW_POLICY=""   # "" (installer default: prompt on TTY, skip otherwise) | add | skip
PROJECTS=()

usage() { sed -n '2,34p' "$0" | sed 's/^# \?//'; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --apply) APPLY=true; shift ;;
        --to) TO="${2:?--to requires a ref}"; shift 2 ;;
        --pull) PULL=true; shift ;;
        --project) PROJECTS+=("${2:?--project requires a path}"); shift 2 ;;
        --add-new) NEW_POLICY="add"; shift ;;
        --skip-new) NEW_POLICY="skip"; shift ;;
        --allow-dirty) ALLOW_DIRTY=true; shift ;;
        -h|--help) usage; exit 0 ;;
        --*) echo "Unknown option: $1" >&2; exit 2 ;;
        *) echo "Unexpected positional argument: $1" >&2; exit 2 ;;
    esac
done

log() { echo "$@"; }
die() { echo "error: $*" >&2; exit 1; }
warn() { echo "warning: $*" >&2; }

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALLER="$REPO_ROOT/tools/install_aris_kimi.sh"

[[ -f "$INSTALLER" ]] || die "installer not found: $INSTALLER"
git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1 || \
    die "$REPO_ROOT is not a git clone; the Kimi line updates via git, re-clone first"

$PULL && [[ -n "$TO" ]] && die "--pull and --to are mutually exclusive"

# Fetch is read-only against the remote; do it in dry-run too so the plan
# reflects the newest tags. Non-fatal: offline runs fall back to local refs.
if ! git -C "$REPO_ROOT" fetch --tags --quiet 2>/dev/null; then
    warn "git fetch --tags failed (offline?); using local tags only"
fi

CURRENT_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
CURRENT_DESC="$(git -C "$REPO_ROOT" describe --tags --exact-match 2>/dev/null \
    || git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"

TARGET_KIND=""
TARGET_REF=""
TARGET_SHA=""
if $PULL; then
    git -C "$REPO_ROOT" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' >/dev/null 2>&1 || \
        die "current branch has no upstream; use --to <ref> instead of --pull"
    TARGET_KIND="pull"
    TARGET_REF="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD) (fast-forward)"
    TARGET_SHA="$CURRENT_SHA"
elif [[ -n "$TO" ]]; then
    TARGET_SHA="$(git -C "$REPO_ROOT" rev-parse --verify --quiet "$TO^{commit}")" || \
        die "ref not found: $TO"
    TARGET_KIND="checkout"
    TARGET_REF="$TO"
else
    TARGET_REF="$(git -C "$REPO_ROOT" tag -l 'business-research-suite-kimi-v*' --sort=-v:refname | head -1)"
    [[ -n "$TARGET_REF" ]] || die "no business-research-suite-kimi-v* tag found; use --to <ref>"
    TARGET_KIND="checkout"
    TARGET_SHA="$(git -C "$REPO_ROOT" rev-parse "$TARGET_REF^{commit}")"
fi

DIRTY="$(git -C "$REPO_ROOT" status --porcelain --untracked-files=no)"
if [[ -n "$DIRTY" && "$ALLOW_DIRTY" != true ]]; then
    die "this clone has uncommitted tracked changes; commit/stash first or pass --allow-dirty"
fi

GLOBAL_MANIFEST="$HOME/.aris/installed-skills-kimi.txt"

log "ARIS Kimi Smart Update"
log "  Repo:    $REPO_ROOT"
log "  Current: $CURRENT_DESC (${CURRENT_SHA:0:8})"
log "  Target:  $TARGET_REF via $TARGET_KIND"
if [[ "$TARGET_SHA" == "$CURRENT_SHA" && "$TARGET_KIND" == "checkout" ]]; then
    log "  Status:  already at target"
fi
if [[ -f "$GLOBAL_MANIFEST" ]]; then
    log "  Global:  $GLOBAL_MANIFEST (will reconcile)"
else
    log "  Global:  no global install found"
fi
if [[ ${#PROJECTS[@]} -gt 0 ]]; then
    for p in "${PROJECTS[@]}"; do
        if [[ -f "$p/.aris/installed-skills-kimi.txt" ]]; then
            log "  Project: $p (will reconcile)"
        else
            log "  Project: $p (WARNING: no Kimi manifest; reconcile will refuse)"
        fi
    done
else
    log "  Project: none given — pass --project <path> for each project install"
fi

if ! $APPLY; then
    log ""
    log "Dry-run only. Re-run with --apply to move the clone and reconcile installs."
    exit 0
fi

if [[ "$TARGET_KIND" == "pull" ]]; then
    git -C "$REPO_ROOT" pull --ff-only --quiet
    log "  pulled $(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD) to $(git -C "$REPO_ROOT" rev-parse --short HEAD)"
elif [[ "$TARGET_SHA" != "$CURRENT_SHA" ]]; then
    git -C "$REPO_ROOT" checkout --quiet "$TARGET_REF"
    log "  checked out $TARGET_REF"
fi

FORWARD=("--quiet")
case "$NEW_POLICY" in
    add) FORWARD+=("--add-new") ;;
    skip) FORWARD+=("--skip-new") ;;
esac

reconciled=0
if [[ -f "$GLOBAL_MANIFEST" ]]; then
    bash "$INSTALLER" --global --reconcile ${FORWARD[@]+"${FORWARD[@]}"}
    reconciled=$((reconciled + 1))
fi
for p in ${PROJECTS[@]+"${PROJECTS[@]}"}; do
    bash "$INSTALLER" "$p" --reconcile ${FORWARD[@]+"${FORWARD[@]}"}
    reconciled=$((reconciled + 1))
done

log ""
if (( reconciled == 0 )); then
    log "Clone updated; no managed installs to reconcile. Pass --project <path> per project next time."
else
    log "Update complete. Reconciled $reconciled install(s)."
fi
