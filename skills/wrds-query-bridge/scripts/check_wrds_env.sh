#!/usr/bin/env bash
# Report whether WRDS env vars are set without printing secret values.
set -euo pipefail

ok=0

check_var() {
  local name="$1"
  local required="${2:-1}"
  if [[ -n "${!name:-}" ]]; then
    echo "${name}=set"
  else
    if [[ "$required" == "1" ]]; then
      echo "${name}=missing"
      ok=1
    else
      echo "${name}=unset (optional)"
    fi
  fi
}

check_var WRDS_USER 1
check_var WRDS_PASSWORD 1
check_var WRDS_HOST 0
check_var WRDS_PORT 0
check_var WRDS_DBNAME 0

if [[ "$ok" -eq 0 ]]; then
  echo "status=ready"
  exit 0
fi

echo "status=not_ready"
echo "Set WRDS_USER and WRDS_PASSWORD in the environment (do not paste secrets into chat or git-tracked files)."
exit 1
