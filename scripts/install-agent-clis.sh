#!/usr/bin/env bash
set -euo pipefail

CODEX_INSTALL_URL="${VISUAL_INSPECTION_CODEX_INSTALL_URL:-https://chatgpt.com/codex/install.sh}"
CLAUDE_INSTALL_URL="${VISUAL_INSPECTION_CLAUDE_INSTALL_URL:-https://claude.ai/install.sh}"
CLAUDE_CHANNEL="${VISUAL_INSPECTION_CLAUDE_CHANNEL:-stable}"
FORCE_INSTALL="${VISUAL_INSPECTION_FORCE_AGENT_CLI_INSTALL:-false}"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to install Codex and Claude Code." >&2
  exit 1
fi

export PATH="$HOME/.local/bin:$PATH"

command_is_usable() {
  local command_name="$1"
  command -v "$command_name" >/dev/null 2>&1 \
    && "$command_name" --version >/dev/null 2>&1
}

command_version() {
  "$1" --version 2>/dev/null | head -n 1
}

download_installer() {
  local url="$1"
  local destination="$2"
  curl --proto '=https' --tlsv1.2 -fsSL "$url" -o "$destination"
}

install_codex() {
  if [[ "$FORCE_INSTALL" != "true" ]] && command_is_usable codex; then
    echo "Codex already available: $(command_version codex)"
    return
  fi

  echo "Installing Codex CLI with the official OpenAI installer..."
  download_installer "$CODEX_INSTALL_URL" "$INSTALLER_DIR/codex-install.sh"
  sh "$INSTALLER_DIR/codex-install.sh"
  command_is_usable codex || {
    echo "Codex installation completed but the codex command is unavailable." >&2
    exit 1
  }
  echo "Installed $(command_version codex)"
}

install_claude() {
  if [[ "$FORCE_INSTALL" != "true" ]] && command_is_usable claude; then
    echo "Claude Code already available: $(command_version claude)"
    return
  fi

  echo "Installing Claude Code channel '$CLAUDE_CHANNEL' with the official Anthropic installer..."
  download_installer "$CLAUDE_INSTALL_URL" "$INSTALLER_DIR/claude-install.sh"
  bash "$INSTALLER_DIR/claude-install.sh" "$CLAUDE_CHANNEL"
  command_is_usable claude || {
    echo "Claude Code installation completed but the claude command is unavailable." >&2
    exit 1
  }
  echo "Installed $(command_version claude)"
}

INSTALLER_DIR="$(mktemp -d)"
trap 'rm -rf "$INSTALLER_DIR"' EXIT

install_codex
install_claude

echo "Agent CLIs are ready. Authentication is intentionally left to each participant."
echo "From the repository, run 'codex' or 'claude' and follow the sign-in prompt."
