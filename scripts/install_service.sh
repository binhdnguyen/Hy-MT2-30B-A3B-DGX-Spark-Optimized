#!/usr/bin/env bash
set -euo pipefail

RECIPE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_UNIT="$RECIPE_DIR/systemd/llama-hymt2.service"
UNIT_DIR="${UNIT_DIR:-$HOME/.config/systemd/user}"
UNIT_PATH="$UNIT_DIR/llama-hymt2.service"
BACKUP_PATH="${UNIT_PATH}.backup"

[[ -f "$SOURCE_UNIT" ]] || {
  echo "ERROR: Service unit not found: $SOURCE_UNIT" >&2
  exit 1
}

mkdir -p -- "$UNIT_DIR"
if [[ -f "$UNIT_PATH" && ! -e "$BACKUP_PATH" ]]; then
  TEMP_BACKUP="$(mktemp "$UNIT_DIR/.llama-hymt2.service.backup.XXXXXX")"
  cleanup() {
    rm -f -- "$TEMP_BACKUP"
  }
  trap cleanup EXIT
  cp --preserve=mode,timestamps -- "$UNIT_PATH" "$TEMP_BACKUP"
  if ! ln -- "$TEMP_BACKUP" "$BACKUP_PATH"; then
    [[ -e "$BACKUP_PATH" ]] || {
      echo "ERROR: Could not create rollback backup: $BACKUP_PATH" >&2
      exit 1
    }
  fi
  rm -f -- "$TEMP_BACKUP"
  trap - EXIT
fi

install -m 0644 -- "$SOURCE_UNIT" "$UNIT_PATH"
systemctl --user daemon-reload
systemctl --user enable --now llama-hymt2.service
echo "Installed service unit: $UNIT_PATH"
if [[ -f "$BACKUP_PATH" ]]; then
  echo "Original rollback unit: $BACKUP_PATH"
fi
