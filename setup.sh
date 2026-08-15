#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/compose.yaml"
NGC_CLI_VERSION="${NGC_CLI_VERSION:-4.10.0}"

if [[ -z "${NGC_API_KEY:-}" ]]; then
  echo "NGC_API_KEY is required." >&2
  exit 1
fi

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

install_ngc_cli() {
  if command -v ngc >/dev/null 2>&1; then
    return
  fi

  local install_root="${VISUAL_INSPECTION_TOOL_HOME:-$HOME/.cache/visual-inspection/tools}/ngc-cli/$NGC_CLI_VERSION"
  local ngc_binary="$install_root/ngc-cli/ngc"
  if [[ ! -x "$ngc_binary" ]]; then
    echo "Installing NGC CLI $NGC_CLI_VERSION..."
    mkdir -p "$install_root"
    curl -fsSL \
      "https://api.ngc.nvidia.com/v2/resources/nvidia/ngc-apps/ngc_cli/versions/$NGC_CLI_VERSION/files/ngccli_linux.zip" \
      -o "$install_root/ngccli_linux.zip"
    unzip -q "$install_root/ngccli_linux.zip" -d "$install_root"
    chmod +x "$ngc_binary"
  fi
  export PATH="$(dirname "$ngc_binary"):$PATH"
}

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

  install_ngc_cli
  python3 "$ROOT_DIR/scripts/fetch-data.py" --profile "$profile"
  export VISUAL_INSPECTION_DATA_DIR="${VISUAL_INSPECTION_DATA_HOME:-$HOME/workspace/visual-inspection-data}/current"
}

configure_data

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

echo "Visual inspection is ready. Run 'codex' or 'claude' from $ROOT_DIR to use an agent."
