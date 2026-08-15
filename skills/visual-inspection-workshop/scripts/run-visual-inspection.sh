#!/usr/bin/env bash
set -euo pipefail

find_repository() {
  if [[ -n "${VISUAL_INSPECTION_HOME:-}" && -x "$VISUAL_INSPECTION_HOME/vision-inspect" ]]; then
    printf '%s\n' "$VISUAL_INSPECTION_HOME"
    return
  fi

  local candidate="$PWD"
  while [[ "$candidate" != "/" ]]; do
    if [[ -x "$candidate/vision-inspect" && -f "$candidate/WORKSHOP_FLOW.md" ]]; then
      printf '%s\n' "$candidate"
      return
    fi
    candidate="$(dirname "$candidate")"
  done

  candidate="$HOME/workspace/physical-ai-visual-inspection/physical-ai-visual-inspection"
  if [[ -x "$candidate/vision-inspect" ]]; then
    printf '%s\n' "$candidate"
    return
  fi

  echo "Could not locate the visual inspection launchable. Set VISUAL_INSPECTION_HOME." >&2
  exit 1
}

repository="$(find_repository)"
cd "$repository"
exec ./vision-inspect "$@"
