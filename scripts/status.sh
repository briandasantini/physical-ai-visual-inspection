#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
docker compose -f "$ROOT_DIR/compose.yaml" ps

for endpoint in \
  "Reason2 2B|http://127.0.0.1:8001/v1/health/ready" \
  "Reason2 8B|http://127.0.0.1:8002/v1/health/ready" \
  "Cosmos3 Nano (optional)|http://127.0.0.1:8003/v1/health/ready" \
  "Visual Inspection UI|http://127.0.0.1:7860/"; do
  name="${endpoint%%|*}"
  url="${endpoint#*|}"
  if curl --fail --silent --max-time 5 "$url" >/dev/null; then
    echo "READY  $name"
  else
    echo "WAIT   $name"
  fi
done
