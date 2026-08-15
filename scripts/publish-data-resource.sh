#!/usr/bin/env bash
set -euo pipefail

if (( $# != 3 )); then
  echo "Usage: $0 <workshop|full> <data-root> <empty-staging-dir>" >&2
  exit 1
fi

if [[ -z "${VISUAL_INSPECTION_DATA_RESOURCE:-}" ]]; then
  echo "VISUAL_INSPECTION_DATA_RESOURCE must be <org>[/<team>]/<resource>." >&2
  exit 1
fi

if [[ -z "${NGC_API_KEY:-}" ]]; then
  echo "NGC_API_KEY is required." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="$1"
DATA_ROOT="$2"
STAGING_DIR="$3"
VERSION="${VISUAL_INSPECTION_DATA_VERSION:-2026.08.13}"

if ! command -v ngc >/dev/null 2>&1; then
  echo "ngc CLI is required. Run setup.sh once or install the pinned CLI." >&2
  exit 1
fi

python3 "$ROOT_DIR/scripts/prepare-data-resource.py" \
  "$PROFILE" "$DATA_ROOT" "$STAGING_DIR" --version "$VERSION"

ngc registry resource upload-version \
  "${VISUAL_INSPECTION_DATA_RESOURCE}:${VERSION}" \
  --source "$STAGING_DIR"
