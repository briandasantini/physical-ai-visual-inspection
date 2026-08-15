#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

docker compose -f "$ROOT_DIR/compose.yaml" config --quiet
python3 -m compileall -q "$ROOT_DIR/app/src"

PYTHONPATH="$ROOT_DIR/app/src" python3 -m unittest discover \
  -s "$ROOT_DIR/app/tests" \
  -p 'test_*.py'

echo "Local launchable checks passed."
