#!/usr/bin/env bash
# install_business_codex_skills.sh -- Business-only ARIS Codex skill installation.
#
# This installer manages a focused Codex project layout:
#   <project>/.agents/skills/<skill-name> -> <aris-repo>/skills/skills-codex/<skill-name>
#
# Managed entries are tracked in:
#   <project>/.aris/installed-business-skills-codex.txt
#
# Included entries:
#   business/accounting/finance skills, R/Stata analysis bridges, passport,
#   audit gates, and shared-references support files. It does not install the
#   ML workflow skills.
#
# Usage:
#   bash tools/install_business_codex_skills.sh [project_path] [options]
#
# Actions:
#   default      install or reconcile the business-only skill set
#   --reconcile  same as default, explicit for readability
#   --uninstall  remove only entries in the business-only manifest
#
# Options:
#   --aris-repo PATH  override repo discovery
#   --dry-run         show plan, no writes
#   --quiet           no informational output
#   --no-doc          skip AGENTS.md managed block update

set -euo pipefail

MANIFEST_NAME="installed-business-skills-codex.txt"
MANIFEST_PREV_NAME="installed-business-skills-codex.txt.prev"
FULL_CODEX_MANIFEST_NAME="installed-skills-codex.txt"
ARIS_DIR_NAME=".aris"
SKILLS_REL=".agents/skills"
DOC_FILE_NAME="AGENTS.md"
BLOCK_BEGIN="<!-- ARIS-BUSINESS-CODEX:BEGIN -->"
BLOCK_END="<!-- ARIS-BUSINESS-CODEX:END -->"
PACKAGE_REL="skills/skills-codex"

BUSINESS_ENTRIES=(
    business-research-suite
    business-lit-review
    business-idea-creator
    business-novelty-check
    business-run-passport
    empirical-design-plan
    data-analysis-bridge
    r-analysis-bridge
    stata-analysis-bridge
    evidence-to-claim
    business-number-audit
    business-claim-source-audit
    business-paper-plan
    business-author-style-profile
    business-paper-writing
    business-rebuttal
    business-research-pipeline
    shared-references
)

PROJECT_PATH=""
ARIS_REPO_OVERRIDE=""
ACTION="install"
DRY_RUN=false
QUIET=false
NO_DOC=false

usage() { sed -n '2,27p' "$0" | sed 's/^# \?//'; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --reconcile) ACTION="install"; shift ;;
        --uninstall) ACTION="uninstall"; shift ;;
        --aris-repo) ARIS_REPO_OVERRIDE="${2:?--aris-repo requires path}"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        --quiet) QUIET=true; shift ;;
        --no-doc) NO_DOC=true; shift ;;
        -h|--help) usage; exit 0 ;;
        --*) echo "Unknown option: $1" >&2; exit 2 ;;
        *)
            if [[ -z "$PROJECT_PATH" ]]; then
                PROJECT_PATH="$1"
            else
                echo "Error: unexpected positional argument: $1" >&2
                exit 2
            fi
            shift
            ;;
    esac
done

log() { $QUIET && return 0; echo "$@"; }
die() { echo "error: $*" >&2; exit 1; }

script_dir() {
    cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
}

default_repo_root() {
    local dir
    dir="$(script_dir)"
    cd "$dir/.." && pwd
}

resolve_repo_root() {
    local repo
    if [[ -n "$ARIS_REPO_OVERRIDE" ]]; then
        repo="$ARIS_REPO_OVERRIDE"
    else
        repo="$(default_repo_root)"
    fi
    [[ -d "$repo/$PACKAGE_REL" ]] || die "repo missing $PACKAGE_REL: $repo"
    cd "$repo" && pwd
}

resolve_project_path() {
    local project="${PROJECT_PATH:-$(pwd)}"
    mkdir -p "$project"
    cd "$project" && pwd
}

entry_is_in_business_set() {
    local needle="$1" entry
    for entry in "${BUSINESS_ENTRIES[@]}"; do
        [[ "$entry" == "$needle" ]] && return 0
    done
    return 1
}

manifest_path() {
    echo "$PROJECT_PATH/$ARIS_DIR_NAME/$MANIFEST_NAME"
}

full_manifest_path() {
    echo "$PROJECT_PATH/$ARIS_DIR_NAME/$FULL_CODEX_MANIFEST_NAME"
}

remove_doc_block() {
    local doc="$PROJECT_PATH/$DOC_FILE_NAME"
    [[ -f "$doc" ]] || return 0
    awk -v begin="$BLOCK_BEGIN" -v end="$BLOCK_END" '
        $0 == begin {skip=1; next}
        $0 == end {skip=0; next}
        skip != 1 {print}
    ' "$doc" > "$doc.tmp"
    mv "$doc.tmp" "$doc"
}

write_doc_block() {
    $NO_DOC && return 0
    local doc="$PROJECT_PATH/$DOC_FILE_NAME"
    remove_doc_block
    {
        [[ -f "$doc" ]] && cat "$doc"
        [[ -f "$doc" ]] && printf '\n'
        printf '%s\n' "$BLOCK_BEGIN"
        printf '%s\n\n' "## ARIS Business Codex Skill Scope"
        printf 'Business-only ARIS Codex skills are installed project-locally under `%s/`.\n' "$SKILLS_REL"
        printf '%s\n\n' "This install intentionally includes business/accounting/finance workflow skills and their support files only."
        printf -- '- ARIS repo root: `%s`\n' "$ARIS_REPO"
        printf -- '- Manifest: `%s/%s`\n' "$ARIS_DIR_NAME" "$MANIFEST_NAME"
        printf '%s\n' "- Update/reconcile:"
        printf '  `bash %s/tools/install_business_codex_skills.sh "%s" --reconcile --aris-repo "%s"`\n' "$ARIS_REPO" "$PROJECT_PATH" "$ARIS_REPO"
        printf '%s\n' "- Uninstall:"
        printf '  `bash %s/tools/install_business_codex_skills.sh "%s" --uninstall`\n\n' "$ARIS_REPO" "$PROJECT_PATH"
        printf '%s\n' "Primary invocations:"
        printf '%s\n' '`/business-research-suite`, `/business-lit-review`, `/business-idea-creator`, `/business-novelty-check`, `/business-run-passport`, `/empirical-design-plan`, `/data-analysis-bridge`, `/r-analysis-bridge`, `/stata-analysis-bridge`, `/evidence-to-claim`, `/business-number-audit`, `/business-claim-source-audit`, `/business-paper-plan`, `/business-author-style-profile`, `/business-paper-writing`, `/business-rebuttal`, `/business-research-pipeline`.'
        printf '%s\n' "$BLOCK_END"
    } > "$doc.tmp"
    mv "$doc.tmp" "$doc"
}

validate_sources() {
    local entry
    for entry in "${BUSINESS_ENTRIES[@]}"; do
        [[ -d "$ARIS_REPO/$PACKAGE_REL/$entry" ]] || die "missing business entry source: $PACKAGE_REL/$entry"
    done
}

target_for_entry() {
    echo "$PROJECT_PATH/$SKILLS_REL/$1"
}

source_for_entry() {
    echo "$ARIS_REPO/$PACKAGE_REL/$1"
}

is_managed_entry() {
    local entry="$1" manifest
    manifest="$(manifest_path)"
    [[ -f "$manifest" ]] || return 1
    awk -F'\t' -v entry="$entry" '$1 == "entry" && $2 == entry {found=1} END {exit found ? 0 : 1}' "$manifest"
}

install_entry() {
    local entry="$1" source target
    source="$(source_for_entry "$entry")"
    target="$(target_for_entry "$entry")"

    if $DRY_RUN; then
        echo "link $target -> $source"
        return 0
    fi

    if [[ -L "$target" ]]; then
        if [[ "$(readlink "$target")" == "$source" ]]; then
            return 0
        fi
        if is_managed_entry "$entry"; then
            rm "$target"
        else
            die "target exists as an unmanaged symlink: $target"
        fi
    elif [[ -e "$target" ]]; then
        die "target exists and is not a managed symlink: $target"
    fi

    ln -s "$source" "$target"
}

write_manifest() {
    local manifest entry
    manifest="$(manifest_path)"
    mkdir -p "$(dirname "$manifest")"
    {
        printf 'version\t1\n'
        printf 'profile\tbusiness-codex\n'
        printf 'repo_root\t%s\n' "$ARIS_REPO"
        printf 'skills_dir\t%s\n' "$SKILLS_REL"
        for entry in "${BUSINESS_ENTRIES[@]}"; do
            printf 'entry\t%s\t%s/%s\t%s/%s\n' "$entry" "$PACKAGE_REL" "$entry" "$SKILLS_REL" "$entry"
        done
    } > "$manifest"
}

install_business_skills() {
    validate_sources
    if [[ -f "$(full_manifest_path)" ]]; then
        die "full Codex install manifest exists at $(full_manifest_path). Uninstall or use a separate project before business-only install."
    fi

    if $DRY_RUN; then
        log "Business-only Codex skill install plan"
        log "Project: $PROJECT_PATH"
        log "ARIS repo: $ARIS_REPO"
    else
        mkdir -p "$PROJECT_PATH/$SKILLS_REL" "$PROJECT_PATH/$ARIS_DIR_NAME"
    fi

    local entry
    for entry in "${BUSINESS_ENTRIES[@]}"; do
        install_entry "$entry"
    done

    if $DRY_RUN; then
        log "(dry-run) no changes made"
        return 0
    fi

    write_manifest
    write_doc_block
    log "Installed business-only ARIS Codex skills: ${#BUSINESS_ENTRIES[@]} entries"
    log "Manifest: $(manifest_path)"
}

uninstall_business_skills() {
    local manifest prev entry target
    manifest="$(manifest_path)"
    prev="$PROJECT_PATH/$ARIS_DIR_NAME/$MANIFEST_PREV_NAME"

    if [[ ! -f "$manifest" ]]; then
        log "No business-only manifest found: $manifest"
        return 0
    fi

    while IFS=$'\t' read -r kind entry _; do
        [[ "$kind" == "entry" ]] || continue
        entry_is_in_business_set "$entry" || continue
        target="$(target_for_entry "$entry")"
        if $DRY_RUN; then
            echo "remove managed link $target"
        elif [[ -L "$target" ]]; then
            rm "$target"
        fi
    done < "$manifest"

    if $DRY_RUN; then
        log "(dry-run) no changes made"
        return 0
    fi

    mv "$manifest" "$prev"
    remove_doc_block
    log "Uninstalled business-only ARIS Codex skills"
    log "Previous manifest: $prev"
}

ARIS_REPO="$(resolve_repo_root)"
PROJECT_PATH="$(resolve_project_path)"

case "$ACTION" in
    install) install_business_skills ;;
    uninstall) uninstall_business_skills ;;
    *) die "unknown action: $ACTION" ;;
esac
