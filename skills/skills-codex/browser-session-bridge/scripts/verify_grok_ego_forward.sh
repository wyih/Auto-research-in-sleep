#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf '%s\n' \
    "Usage: verify_grok_ego_forward.sh [--cwd PROJECT_DIR] [--model MODEL_ALIAS]" \
    "" \
    "Runs a fresh Grok Build forward acceptance of browser-session-bridge" \
    "through the macOS-only ego-browser adapter. When --model is omitted," \
    "Grok uses the default model and API credentials from its own config." \
    "" \
    "Environment:" \
    "  ARIS_GROK_MODEL  Optional model alias; overridden by --model."
}

project_dir=$PWD
model_alias=${ARIS_GROK_MODEL:-}

while (($#)); do
  case "$1" in
    --cwd)
      [[ $# -ge 2 ]] || {
        printf '%s\n' "missing value for --cwd" >&2
        exit 2
      }
      project_dir=$2
      shift 2
      ;;
    --model)
      [[ $# -ge 2 ]] || {
        printf '%s\n' "missing value for --model" >&2
        exit 2
      }
      model_alias=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ $(uname -s) != Darwin ]]; then
  printf '%s\n' \
    "Grok ego forward acceptance requires macOS; ego-lite must not be selected on Windows, WSL, or native Linux." >&2
  exit 2
fi

if [[ ! -d $project_dir ]]; then
  printf 'project directory does not exist: %s\n' "$project_dir" >&2
  exit 2
fi

task_space="aris-grok-forward-acceptance-$(date -u +%Y%m%dT%H%M%SZ)-$$"
scratch_dir=$(mktemp -d "${TMPDIR:-/tmp}/aris-grok-ego-acceptance.XXXXXX")
result_json="$scratch_dir/grok-result.json"
stderr_log="$scratch_dir/grok-stderr.log"
cleanup_probe="$scratch_dir/cleanup-probe.json"

cleanup() {
  rm -f "$result_json" "$stderr_log" "$cleanup_probe"
  rmdir "$scratch_dir" 2>/dev/null || true
}
trap cleanup EXIT

prompt=$(printf '%s\n' \
  "Run a fresh forward acceptance of the installed browser-session-bridge and ego-browser skills." \
  "Read both complete SKILL.md files before acting." \
  "This is an adapter-health acceptance on client_runtime grok and a Darwin host, not a research-data operation." \
  "Do not use Chrome MCP, chrome-mcp, web search, raw CDP, browser JavaScript, or edit any file." \
  "Use ego-browser exactly as its installed Skill requires:" \
  "1. Create a uniquely named agent-owned Task Space named $task_space." \
  "2. Open https://example.com/." \
  "3. Verify fresh pageInfo has title Example Domain and URL https://example.com/." \
  "4. Call completeTaskSpace with keep:false in its own dedicated final ego-browser invocation and verify done:true." \
  "Finally return one compact JSON object with exactly these keys:" \
  "status, client_runtime, adapter, platform, bridge_skill_loaded, ego_skill_loaded, title, url, cleanup_done, blocker." \
  "Set status to pass only if every assertion was observed directly; otherwise fail with blocker." \
  "Do not expose credentials, cookies, identifiers, or Task Space numeric IDs.")

grok_args=(
  --cwd "$project_dir"
  --single "$prompt"
  --always-approve
  --max-turns 14
  --no-subagents
  --disable-web-search
  --deny "MCPTool(*)"
  --output-format json
)
if [[ -n $model_alias ]]; then
  grok_args+=(--model "$model_alias")
fi

if ! grok "${grok_args[@]}" >"$result_json" 2>"$stderr_log"; then
  printf '%s\n' "Grok ego forward acceptance did not complete." >&2
  tail -80 "$stderr_log" >&2
  exit 1
fi

python3 - "$result_json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

outer_path = Path(sys.argv[1])
try:
    outer = json.loads(outer_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as error:
    raise SystemExit(f"Grok did not return valid headless JSON: {error}")

if outer.get("stopReason") != "EndTurn":
    raise SystemExit(f"Grok stopReason is not EndTurn: {outer.get('stopReason')!r}")

text = outer.get("text")
if not isinstance(text, str):
    raise SystemExit("Grok result has no response text")

decoder = json.JSONDecoder()
receipt = None
for index, char in enumerate(text):
    if char != "{":
        continue
    try:
        candidate, _ = decoder.raw_decode(text[index:])
    except json.JSONDecodeError:
        continue
    if isinstance(candidate, dict) and "status" in candidate:
        receipt = candidate
        break

if receipt is None:
    raise SystemExit("Grok response contains no acceptance receipt")

expected = {
    "status": "pass",
    "client_runtime": "grok",
    "adapter": "ego_lite_task_space",
    "platform": "Darwin",
    "bridge_skill_loaded": True,
    "ego_skill_loaded": True,
    "title": "Example Domain",
    "url": "https://example.com/",
    "cleanup_done": True,
    "blocker": None,
}
if receipt != expected:
    raise SystemExit(f"Grok acceptance receipt mismatch: {receipt!r}")
PY

ego-browser nodejs >"$cleanup_probe" 2>&1 <<EOF
const spaces = await listTaskSpaces()
const present = spaces.some(
  item => item.name === '$task_space' || item.taskId === '$task_space'
)
cliLog(JSON.stringify({ acceptanceSpacePresent: present }))
EOF

python3 - "$cleanup_probe" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

probe_path = Path(sys.argv[1])
lines = [line.strip() for line in probe_path.read_text(encoding="utf-8").splitlines() if line.strip()]
if not lines:
    raise SystemExit("ego-browser cleanup probe returned no output")
try:
    probe = json.loads(lines[-1])
except json.JSONDecodeError as error:
    raise SystemExit(f"ego-browser cleanup probe is not JSON: {error}")
if probe != {"acceptanceSpacePresent": False}:
    raise SystemExit("Grok acceptance Task Space still exists after reported cleanup")
PY

printf '%s\n' "Grok ego forward acceptance: PASS"
