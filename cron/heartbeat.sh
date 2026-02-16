#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# heartbeat.sh — writes heartbeat.md to the Obsidian vault
# Run via cron every 5 minutes
# ─────────────────────────────────────────────────────────────────────────────

VAULT="${OBSIDIAN_VAULT:-$HOME/obsidian-vault}"
HEARTBEAT="$VAULT/heartbeat.md"
export DISPLAY="${DISPLAY:-:99}"

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NOW_HUMAN=$(date -u +"%Y-%m-%d %H:%M UTC")

# Gather metrics
OBS_STATUS="down"
OBS_VERSION="unknown"
if pgrep -f "squashfs-root/obsidian" >/dev/null 2>&1; then
  OBS_STATUS="running"
  OBS_VERSION=$(obsidian version 2>/dev/null | head -1 || echo "unknown")
fi

XVFB_STATUS="down"
if pgrep -f "Xvfb :99" >/dev/null 2>&1; then
  XVFB_STATUS="running"
fi

API_STATUS="down"
if curl -sf http://localhost:${API_PORT:-3000}/health >/dev/null 2>&1; then
  API_STATUS="running"
fi

VAULT_FILES=$(find "$VAULT" -name "*.md" -not -path "*/.obsidian/*" -not -path "*/node_modules/*" 2>/dev/null | wc -l | tr -d ' ')
VAULT_SIZE=$(du -sm "$VAULT" 2>/dev/null | awk '{print $1}')
UPTIME_SEC=$(awk '{print int($1)}' /proc/uptime 2>/dev/null || echo 0)
UPTIME_HOURS=$(echo "scale=1; $UPTIME_SEC / 3600" | bc 2>/dev/null || echo "0")

# Status symbols
obs_sym="✓"; [ "$OBS_STATUS" = "down" ] && obs_sym="✗"
xvfb_sym="✓"; [ "$XVFB_STATUS" = "down" ] && xvfb_sym="✗"
api_sym="✓"; [ "$API_STATUS" = "down" ] && api_sym="✗"

# Overall status
OVERALL="healthy"
[ "$OBS_STATUS" = "down" ] && OVERALL="degraded"
[ "$XVFB_STATUS" = "down" ] && OVERALL="critical"

# Write heartbeat.md
cat > "$HEARTBEAT" << EOF
---
last_beat: ${NOW}
status: ${OVERALL}
obsidian_version: "${OBS_VERSION}"
vault_files: ${VAULT_FILES}
vault_size_mb: ${VAULT_SIZE}
uptime_hours: ${UPTIME_HOURS}
api_status: ${API_STATUS}
---
# Heartbeat
Last checked: ${NOW_HUMAN}

## Services
| Service | Status |
|---------|--------|
| Obsidian | ${obs_sym} ${OBS_STATUS} |
| Xvfb | ${xvfb_sym} ${XVFB_STATUS} |
| API | ${api_sym} ${API_STATUS} |

## Vault
- Files: ${VAULT_FILES}
- Size: ${VAULT_SIZE} MB
- Path: \`${VAULT}\`

## System
- Uptime: ${UPTIME_HOURS} hours
- Obsidian: ${OBS_VERSION}
EOF
