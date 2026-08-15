#!/usr/bin/env bash
set -euo pipefail

TIMEOUT_SECONDS="${VISUAL_INSPECTION_STARTUP_TIMEOUT:-1200}"
DEADLINE=$((SECONDS + TIMEOUT_SECONDS))

wait_for_url() {
  local name="$1"
  local url="$2"

  printf 'Waiting for %s' "$name"
  until curl --fail --silent --show-error --max-time 5 "$url" >/dev/null 2>&1; do
    if (( SECONDS >= DEADLINE )); then
      printf '\nTimed out waiting for %s at %s\n' "$name" "$url" >&2
      exit 1
    fi
    printf '.'
    sleep 10
  done
  printf ' ready\n'
}

wait_for_url "Cosmos Reason2 2B" "http://127.0.0.1:8001/v1/health/ready"
wait_for_url "Cosmos Reason2 8B" "http://127.0.0.1:8002/v1/health/ready"
wait_for_url "Visual Inspection UI" "http://127.0.0.1:7860/"

echo "Visual inspection is ready at http://127.0.0.1:7860"
