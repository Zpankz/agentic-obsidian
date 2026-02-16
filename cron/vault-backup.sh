#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# vault-backup.sh — daily vault backup
# Run via cron at 3am
# ─────────────────────────────────────────────────────────────────────────────

VAULT="${OBSIDIAN_VAULT:-$HOME/obsidian-vault}"
BACKUP_DIR="/opt/obsidian/backups"
MAX_BACKUPS=7

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BACKUP_FILE="$BACKUP_DIR/vault-${TIMESTAMP}.tar.gz"

tar -czf "$BACKUP_FILE" \
  --exclude='.obsidian/workspace*.json' \
  --exclude='node_modules' \
  -C "$(dirname "$VAULT")" "$(basename "$VAULT")"

# Rotate old backups (keep last N)
ls -1t "$BACKUP_DIR"/vault-*.tar.gz 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f 2>/dev/null || true

echo "[vault-backup] Created: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | awk '{print $1}'))"
