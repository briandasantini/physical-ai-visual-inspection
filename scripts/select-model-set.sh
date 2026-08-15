#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose -f "$ROOT_DIR/compose.yaml" --profile nano)
SELECTION="${1:-}"

if [[ -z "${NGC_API_KEY:-}" ]]; then
  echo "NGC_API_KEY is required by the Compose configuration." >&2
  exit 1
fi

wait_for_model() {
  local name="$1"
  local url="$2"
  printf 'Waiting for %s' "$name"
  until curl --fail --silent --max-time 5 "$url" >/dev/null 2>&1; do
    printf '.'
    sleep 10
  done
  printf ' ready\n'
}

case "$SELECTION" in
  reason2)
    "${COMPOSE[@]}" stop nim-cosmos3-nano
    "${COMPOSE[@]}" up --detach nim-reason2-2b
    wait_for_model "Cosmos Reason2 2B" "http://127.0.0.1:8001/v1/health/ready"
    ;;
  nano)
    "${COMPOSE[@]}" stop nim-reason2-2b
    "${COMPOSE[@]}" up --detach nim-cosmos3-nano
    wait_for_model "Cosmos3 Nano" "http://127.0.0.1:8003/v1/health/ready"
    ;;
  *)
    echo "Usage: $0 reason2|nano" >&2
    exit 2
    ;;
esac

echo "Cosmos Reason2 8B remains assigned to GPU 1."
