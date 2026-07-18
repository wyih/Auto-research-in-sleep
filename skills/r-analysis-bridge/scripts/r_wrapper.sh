#!/usr/bin/env bash
set -euo pipefail

detect_r_bin() {
    if [[ -n "${R_BIN:-}" ]]; then
        echo "$R_BIN"
        return 0
    fi

    local candidate
    for candidate in \
        "$(command -v Rscript 2>/dev/null || true)" \
        /usr/local/bin/Rscript \
        /opt/homebrew/bin/Rscript \
        /usr/bin/Rscript \
        /Library/Frameworks/R.framework/Resources/bin/Rscript
    do
        [[ -n "$candidate" && -x "$candidate" ]] || continue
        echo "$candidate"
        return 0
    done

    return 1
}

if ! R_BIN_PATH="$(detect_r_bin)"; then
    echo "ERROR: Could not find a local Rscript binary." >&2
    echo "Set R_BIN to the full path of your Rscript executable." >&2
    exit 1
fi

exec "$R_BIN_PATH" "$@"
