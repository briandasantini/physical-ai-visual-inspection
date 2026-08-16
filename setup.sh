#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/compose.yaml"

if [[ -z "${NGC_API_KEY:-}" ]]; then
  echo "NGC_API_KEY is required." >&2
  exit 1
fi

SECRET_DIR="${VISUAL_INSPECTION_SECRET_DIR:-$HOME/.secrets}"
SECRET_FILE="$SECRET_DIR/visual-inspection-ngc-key"
mkdir -p "$SECRET_DIR"
chmod 700 "$SECRET_DIR"
umask 077
printf '%s' "$NGC_API_KEY" > "$SECRET_FILE"
chmod 600 "$SECRET_FILE"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Use a Brev VM or Docker Compose environment." >&2
  exit 1
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi is unavailable; this launchable requires NVIDIA GPUs." >&2
  exit 1
fi

GPU_COUNT="$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l | tr -d ' ')"
if (( GPU_COUNT < 2 )); then
  echo "Visual inspection full mode requires two GPUs; found $GPU_COUNT." >&2
  exit 1
fi

configure_data() {
  if [[ -n "${VISUAL_INSPECTION_DATA_DIR:-}" ]]; then
    if [[ ! -d "$VISUAL_INSPECTION_DATA_DIR" ]]; then
      echo "VISUAL_INSPECTION_DATA_DIR does not exist: $VISUAL_INSPECTION_DATA_DIR" >&2
      exit 1
    fi
    return
  fi

  local profile="${VISUAL_INSPECTION_DATA_PROFILE:-workshop}"
  if [[ "$profile" == "none" ]]; then
    export VISUAL_INSPECTION_DATA_DIR="$ROOT_DIR/data"
    return
  fi

  python3 "$ROOT_DIR/scripts/fetch-data.py" --profile "$profile"
  export VISUAL_INSPECTION_DATA_DIR="${VISUAL_INSPECTION_DATA_HOME:-$HOME/workspace/visual-inspection-data}/current"
}

configure_data
mkdir -p "$ROOT_DIR/evidence"

if [[ "${VISUAL_INSPECTION_INSTALL_AGENT_CLIS:-true}" == "true" ]]; then
  "$ROOT_DIR/scripts/install-agent-clis.sh"
fi

if [[ "${VISUAL_INSPECTION_INSTALL_AGENT_SKILL:-true}" == "true" ]]; then
  "$ROOT_DIR/scripts/install-agent-skill.sh"
fi

echo "Authenticating Docker with NGC..."
printf '%s' "$NGC_API_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin >/dev/null
trap 'docker logout nvcr.io >/dev/null 2>&1 || true' EXIT

if [[ "${VISUAL_INSPECTION_INSTALL_NANO:-true}" == "true" ]]; then
  echo "Installing the optional Cosmos3 Nano container image (it will remain stopped)..."
  docker compose -f "$COMPOSE_FILE" --profile nano pull nim-cosmos3-nano
fi

echo "Starting the visual inspection stack..."
docker compose -f "$COMPOSE_FILE" up --detach --build

"$ROOT_DIR/scripts/wait-for-ready.sh"

echo "Visual inspection is ready. Open the website; its Jupyter links open a terminal for Codex or Claude."
