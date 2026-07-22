#!/usr/bin/env bash
set -euo pipefail

EXPECTED_SHA256="f1603f5515a69e4a04b5e989bc7232f71f9120fe7fb980888c0f4b524f38d86a"
EXPECTED_SIZE="31985729632"
MODEL="${MODEL:-$HOME/ai/models/hy-mt2-30b-a3b-q8/Hy-MT2-30B-A3B-Q8_0.gguf}"
FILENAME="Hy-MT2-30B-A3B-Q8_0.gguf"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

[[ $# -eq 1 ]] || fail "Usage: $0 BACKUP_ROOT"
BACKUP_ROOT="$1"
[[ "$BACKUP_ROOT" == /* ]] || fail "Backup root must be an absolute path"
[[ -d "$BACKUP_ROOT" ]] || fail "Backup root is not a directory: $BACKUP_ROOT"
[[ ! -L "$BACKUP_ROOT" ]] || fail "Backup root must not be a symlink: $BACKUP_ROOT"

CANONICAL_ROOT="$(realpath -e -- "$BACKUP_ROOT")"
[[ "$CANONICAL_ROOT" == "$BACKUP_ROOT" ]] ||
  fail "Backup root contains a symlink or unsafe path components: $BACKUP_ROOT"
mountpoint -q -- "$BACKUP_ROOT" ||
  fail "Backup root must be an actual mount point: $BACKUP_ROOT"
MOUNT_TARGET="$(findmnt -n -o TARGET --target "$BACKUP_ROOT")"
[[ "$MOUNT_TARGET" == "$BACKUP_ROOT" ]] ||
  fail "Backup root is not the mounted filesystem root: $BACKUP_ROOT"

ROOT_DEVICE="$(stat -c %d -- /)"
BACKUP_DEVICE="$(stat -c %d -- "$BACKUP_ROOT")"
[[ "$BACKUP_DEVICE" != "$ROOT_DEVICE" ]] ||
  fail "Backup root must be on a different filesystem from /"

[[ -f "$MODEL" ]] || fail "Source model is not a regular file: $MODEL"
[[ ! -L "$MODEL" ]] || fail "Source model must not be a symlink: $MODEL"

SOURCE_SIZE="$(stat -c %s -- "$MODEL")"
[[ "$SOURCE_SIZE" == "$EXPECTED_SIZE" ]] ||
  fail "Source size mismatch: expected $EXPECTED_SIZE, got $SOURCE_SIZE"
SOURCE_SHA256="$(sha256sum -- "$MODEL")"
SOURCE_SHA256="${SOURCE_SHA256%% *}"
[[ "$SOURCE_SHA256" == "$EXPECTED_SHA256" ]] ||
  fail "Source SHA256 mismatch: expected $EXPECTED_SHA256, got $SOURCE_SHA256"

DESTINATION="$BACKUP_ROOT/$FILENAME"
[[ ! -e "$DESTINATION" && ! -L "$DESTINATION" ]] ||
  fail "Destination already exists or is unsafe: $DESTINATION"

TEMP_FILE="$(mktemp "$BACKUP_ROOT/.${FILENAME}.tmp.XXXXXX")"
cleanup() {
  rm -f -- "$TEMP_FILE"
}
trap cleanup EXIT

cp --reflink=auto --sparse=always -- "$MODEL" "$TEMP_FILE"

DEST_SIZE="$(stat -c %s -- "$TEMP_FILE")"
[[ "$DEST_SIZE" == "$EXPECTED_SIZE" ]] ||
  fail "Destination size mismatch: expected $EXPECTED_SIZE, got $DEST_SIZE"
DEST_SHA256="$(sha256sum -- "$TEMP_FILE")"
DEST_SHA256="${DEST_SHA256%% *}"
[[ "$DEST_SHA256" == "$EXPECTED_SHA256" ]] ||
  fail "Destination SHA256 mismatch: expected $EXPECTED_SHA256, got $DEST_SHA256"

mv --no-clobber -- "$TEMP_FILE" "$DESTINATION"
[[ ! -e "$TEMP_FILE" ]] ||
  fail "Destination appeared during backup; refusing to overwrite: $DESTINATION"
trap - EXIT
echo "Verified backup created: $DESTINATION"
