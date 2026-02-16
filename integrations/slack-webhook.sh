#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# slack-webhook.sh — Post vault summary to Slack
#
# Set SLACK_WEBHOOK_URL environment variable, then run:
#   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/... ./slack-webhook.sh
#
# Add to cron for daily summaries:
#   0 9 * * * SLACK_WEBHOOK_URL=... DISPLAY=:99 /opt/obsidian/integrations/slack-webhook.sh
# ─────────────────────────────────────────────────────────────────────────────

WEBHOOK="${SLACK_WEBHOOK_URL:-}"
if [ -z "$WEBHOOK" ]; then
  echo "Error: SLACK_WEBHOOK_URL not set"
  exit 1
fi

export DISPLAY="${DISPLAY:-:99}"
VAULT="${OBSIDIAN_VAULT:-$HOME/obsidian-vault}"

# Gather stats
FILE_COUNT=$(DISPLAY=:99 obsidian files total 2>/dev/null || echo "?")
VERSION=$(DISPLAY=:99 obsidian version 2>/dev/null | head -1 || echo "?")
HOSTNAME=$(hostname)

# Build message
PAYLOAD=$(cat << EOF
{
  "blocks": [
    {
      "type": "header",
      "text": {"type": "plain_text", "text": "📓 Obsidian Vault — ${HOSTNAME}"}
    },
    {
      "type": "section",
      "fields": [
        {"type": "mrkdwn", "text": "*Files:*\n${FILE_COUNT}"},
        {"type": "mrkdwn", "text": "*Version:*\n${VERSION}"},
        {"type": "mrkdwn", "text": "*Vault:*\n\`${VAULT}\`"},
        {"type": "mrkdwn", "text": "*Time:*\n$(date -u +"%Y-%m-%d %H:%M UTC")"}
      ]
    }
  ]
}
EOF
)

curl -sS -X POST -H "Content-Type: application/json" -d "$PAYLOAD" "$WEBHOOK"
