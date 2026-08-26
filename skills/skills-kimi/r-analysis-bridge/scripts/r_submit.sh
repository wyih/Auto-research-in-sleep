#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
R_WRAPPER="$SCRIPT_DIR/r_wrapper.sh"

usage() {
    cat <<'EOF'
Usage:
  r_submit.sh R/filename.R
  r_submit.sh --time 04:00:00 R/file.R
  r_submit.sh --status <jobid>
  r_submit.sh --wait <jobid>
  r_submit.sh --foreground R/file.R
  r_submit.sh --dry-run R/file.R

Run --status and --wait from the same project directory, or set R_JOB_DIR.
EOF
}

job_dir_for_cwd() {
    if [[ -n "${R_JOB_DIR:-}" ]]; then
        echo "$R_JOB_DIR"
    else
        echo "$(pwd)/run_state/r_jobs"
    fi
}

job_meta() {
    local jobid="$1"
    echo "$(job_dir_for_cwd)/$jobid.meta"
}

job_field() {
    local jobid="$1" key="$2"
    awk -F= -v key="$key" '$1 == key {sub(/^[^=]*=/, "", $0); print $0; exit}' "$(job_meta "$jobid")" 2>/dev/null || true
}

job_status() {
    local jobid="$1"
    local meta
    meta="$(job_meta "$jobid")"
    [[ -f "$meta" ]] || { echo "UNKNOWN"; return 1; }

    local pid log_file exit_file
    pid="$(job_field "$jobid" pid)"
    log_file="$(job_field "$jobid" log_file)"
    exit_file="$(job_field "$jobid" exit_file)"

    if [[ -n "$pid" && "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
        echo "RUNNING"
        return 0
    fi

    if [[ -f "$exit_file" ]]; then
        local ec
        ec="$(cat "$exit_file" 2>/dev/null || echo 1)"
        if [[ "$ec" == "0" ]]; then
            echo "COMPLETED"
        else
            echo "FAILED"
        fi
        return 0
    fi

    if [[ -n "$log_file" && -f "$log_file" ]]; then
        if grep -Eqi "^(error|execution halted)|Error in|Traceback" "$log_file"; then
            echo "FAILED"
        else
            echo "EXITED"
        fi
    else
        echo "UNKNOWN"
    fi
}

TIME_OVERRIDE=""
DRY_RUN=false
FOREGROUND=false
STATUS_JOB=""
WAIT_JOB=""
SCRIPT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --time)    TIME_OVERRIDE="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        --foreground) FOREGROUND=true; shift ;;
        --status)  STATUS_JOB="$2"; shift 2 ;;
        --wait)    WAIT_JOB="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        -*)        echo "Unknown option: $1" >&2; exit 1 ;;
        *)         SCRIPT_FILE="$1"; shift ;;
    esac
done

if [[ -n "$STATUS_JOB" ]]; then
    job_status "$STATUS_JOB"
    exit 0
fi

if [[ -n "$WAIT_JOB" ]]; then
    while true; do
        state="$(job_status "$WAIT_JOB")"
        echo "$state"
        [[ "$state" == "RUNNING" ]] || break
        sleep 5
    done
    [[ "$state" != "FAILED" ]]
    exit $?
fi

if [[ -z "$SCRIPT_FILE" ]]; then
    usage >&2
    exit 1
fi

if [[ ! "$SCRIPT_FILE" = /* ]]; then
    SCRIPT_FILE="$(pwd)/$SCRIPT_FILE"
fi

if [[ ! -f "$SCRIPT_FILE" ]]; then
    echo "ERROR: R script not found: $SCRIPT_FILE" >&2
    exit 1
fi

WORKDIR="$(cd "$(dirname "$SCRIPT_FILE")" && pwd)"
case "$(basename "$WORKDIR")" in
    R|scripts) WORKDIR="$(dirname "$WORKDIR")" ;;
esac

JOB_DIR="${R_JOB_DIR:-$WORKDIR/run_state/r_jobs}"
SCRIPT_BASE="$(basename "$SCRIPT_FILE" .R)"
LOG_FILE="$WORKDIR/logs/${SCRIPT_BASE}.log"
EXIT_FILE="$JOB_DIR/${SCRIPT_BASE}_$(date +%Y%m%d%H%M%S)_$$.exit"
JOBID="local_r_$(date +%Y%m%d%H%M%S)_$$"
META_FILE="$JOB_DIR/$JOBID.meta"

CMD=( "$R_WRAPPER" "$SCRIPT_FILE" )

if $DRY_RUN; then
    printf 'TIME_OVERRIDE=%s\n' "${TIME_OVERRIDE:-none}"
    printf 'WORKDIR=%s\n' "$WORKDIR"
    printf 'JOB_DIR=%s\n' "$JOB_DIR"
    printf 'COMMAND=%q ' "${CMD[@]}"
    printf '\n'
    exit 0
fi

mkdir -p "$WORKDIR/logs" "$JOB_DIR"
if $FOREGROUND; then
    {
        echo "pid=$$"
        echo "script=$SCRIPT_FILE"
        echo "workdir=$WORKDIR"
        echo "log_file=$LOG_FILE"
        echo "exit_file=$EXIT_FILE"
        echo "requested_time=${TIME_OVERRIDE:-}"
        echo "started=$(date +%s)"
        echo "mode=foreground"
    } > "$META_FILE"
    (
        cd "$WORKDIR"
        set +e
        "${CMD[@]}" > "$LOG_FILE" 2>&1
        ec=$?
        echo "$ec" > "$EXIT_FILE"
        exit "$ec"
    )
    ec=$?
    echo "$JOBID"
    exit "$ec"
fi

(
    cd "$WORKDIR"
    nohup bash -c '
        log_file="$1"
        exit_file="$2"
        shift 2
        set +e
        "$@" > "$log_file" 2>&1
        echo "$?" > "$exit_file"
    ' bash "$LOG_FILE" "$EXIT_FILE" "${CMD[@]}" >/dev/null 2>&1 < /dev/null &
    pid=$!
    {
        echo "pid=$pid"
        echo "script=$SCRIPT_FILE"
        echo "workdir=$WORKDIR"
        echo "log_file=$LOG_FILE"
        echo "exit_file=$EXIT_FILE"
        echo "requested_time=${TIME_OVERRIDE:-}"
        echo "started=$(date +%s)"
    } > "$META_FILE"
)

echo "$JOBID"
