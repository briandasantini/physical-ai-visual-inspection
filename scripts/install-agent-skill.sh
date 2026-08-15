#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_NAME="visual-inspection-workshop"
SOURCE="$ROOT_DIR/skills/$SKILL_NAME"

if [[ ! -f "$SOURCE/SKILL.md" ]]; then
  echo "Visual inspection skill is missing: $SOURCE" >&2
  exit 1
fi

targets=(
  "${CODEX_HOME:-$HOME/.codex}/skills"
  "$HOME/.agents/skills"
  "$HOME/.claude/skills"
)

for target in "${targets[@]}"; do
  mkdir -p "$target"
  destination="$target/$SKILL_NAME"
  if [[ -e "$destination" && ! -L "$destination" ]]; then
    echo "Preserving existing skill directory: $destination"
    continue
  fi
  ln -sfn "$SOURCE" "$destination"
  echo "Installed $SKILL_NAME -> $destination"
done
