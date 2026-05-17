#!/usr/bin/env bash
# install_business_codex_skills_global.sh -- Optional global business-only Codex skill install.
#
# This installer manages global Codex skill links:
#   <CODEX_HOME>/skills/<skill-name> -> <aris-repo>/skills/skills-codex/<skill-name>
#
# Managed entries are tracked in:
#   <CODEX_HOME>/skills/.aris/installed-business-skills-codex-global.txt
#
# It installs only the business/accounting/finance skill set and shared
# references. It does not install the ML workflow skills.
#
# Usage:
#   bash tools/install_business_codex_skills_global.sh [options]
#
# Actions:
#   default      install or reconcile the global business-only skill set
#   --reconcile  same as default, explicit for readability
#   --uninstall  remove only entries in the global business-only manifest
#
# Options:
#   --aris-repo PATH   override repo discovery
#   --codex-home PATH  override CODEX_HOME, defaults to $CODEX_HOME or ~/.codex
#   --dry-run          show plan, no writes
#   --quiet            no informational output

set -euo pipefail

MANIFEST_NAME="installed-business-skills-codex-global.txt"
MANIFEST_PREV_NAME="installed-business-skills-codex-global.txt.prev"
MANIFEST_DIR_REL="skills/.aris"
SKILLS_REL="skills"
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

ARIS_REPO_OVERRIDE=""
CODEX_HOME_OVERRIDE=""
ACTION="install"
DRY_RUN=false
QUIET=false

usage() { sed -n '2,27p' "$0" | sed 's/^# \?//'; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --reconcile) ACTION="install"; shift ;;
        --uninstall) ACTION="uninstall"; shift ;;
        --aris-repo) ARIS_REPO_OVERRIDE="${2:?--aris-repo requires path}"; shift 2 ;;
        --codex-home) CODEX_HOME_OVERRIDE="${2:?--codex-home requires path}"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        --quiet) QUIET=true; shift ;;
        -h|--help) usage; exit 0 ;;
        --*) echo "Unknown option: $1" >&2; exit 2 ;;
        *) echo "Error: unexpected positional argument: $1" >&2; exit 2 ;;
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

resolve_codex_home() {
    local home_path
    if [[ -n "$CODEX_HOME_OVERRIDE" ]]; then
        home_path="$CODEX_HOME_OVERRIDE"
    elif [[ -n "${CODEX_HOME:-}" ]]; then
        home_path="$CODEX_HOME"
    else
        home_path="$HOME/.codex"
    fi
    if $DRY_RUN; then
        printf '%s\n' "$home_path"
    else
        mkdir -p "$home_path"
        cd "$home_path" && pwd
    fi
}

entry_is_in_business_set() {
    local needle="$1" entry
    for entry in "${BUSINESS_ENTRIES[@]}"; do
        [[ "$entry" == "$needle" ]] && return 0
    done
    return 1
}

manifest_path() {
    echo "$CODEX_HOME_PATH/$MANIFEST_DIR_REL/$MANIFEST_NAME"
}

validate_sources() {
    local entry
    for entry in "${BUSINESS_ENTRIES[@]}"; do
        [[ -d "$ARIS_REPO/$PACKAGE_REL/$entry" ]] || die "missing business entry source: $PACKAGE_REL/$entry"
    done
}

target_for_entry() {
    echo "$CODEX_HOME_PATH/$SKILLS_REL/$1"
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
        printf 'profile\tbusiness-codex-global\n'
        printf 'repo_root\t%s\n' "$ARIS_REPO"
        printf 'codex_home\t%s\n' "$CODEX_HOME_PATH"
        printf 'skills_dir\t%s\n' "$SKILLS_REL"
        for entry in "${BUSINESS_ENTRIES[@]}"; do
            printf 'entry\t%s\t%s/%s\t%s/%s\n' "$entry" "$PACKAGE_REL" "$entry" "$SKILLS_REL" "$entry"
        done
    } > "$manifest"
}

install_global_business_skills() {
    validate_sources

    if $DRY_RUN; then
        log "Business-only global Codex skill install plan"
        log "CODEX_HOME: $CODEX_HOME_PATH"
        log "ARIS repo: $ARIS_REPO"
    else
        mkdir -p "$CODEX_HOME_PATH/$SKILLS_REL" "$CODEX_HOME_PATH/$MANIFEST_DIR_REL"
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
    log "Installed global business-only ARIS Codex skills: ${#BUSINESS_ENTRIES[@]} entries"
    log "Manifest: $(manifest_path)"
}

uninstall_global_business_skills() {
    local manifest prev entry target
    manifest="$(manifest_path)"
    prev="$CODEX_HOME_PATH/$MANIFEST_DIR_REL/$MANIFEST_PREV_NAME"

    if [[ ! -f "$manifest" ]]; then
        log "No global business-only manifest found: $manifest"
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
    log "Uninstalled global business-only ARIS Codex skills"
    log "Previous manifest: $prev"
}

ARIS_REPO="$(resolve_repo_root)"
CODEX_HOME_PATH="$(resolve_codex_home)"

case "$ACTION" in
    install) install_global_business_skills ;;
    uninstall) uninstall_global_business_skills ;;
    *) die "unknown action: $ACTION" ;;
esac
