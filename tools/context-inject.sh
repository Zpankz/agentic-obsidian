#!/usr/bin/env bash
# context-inject.sh — Auto-inject vault graph context into agent sessions.
# Called by arscontexta session-orient hook or manually.
#
# Usage:
#   ./context-inject.sh [--vault gkg|pkg] [--query <topic>] [--diff] [--output <path>]
#
# Generates a compact context block suitable for prepending to agent prompts.
# Includes: vault stats, top hubs, recent changes (diff), and query-focused nodes.

set -euo pipefail

VAULT="gkg"
QUERY=""
DIFF=false
OUTPUT=""
MCP_URL="http://localhost:3100/mcp"

while [[ $# -gt 0 ]]; do
  case $1 in
    --vault) VAULT="$2"; shift 2 ;;
    --query) QUERY="$2"; shift 2 ;;
    --diff) DIFF=true; shift ;;
    --output) OUTPUT="$2"; shift 2 ;;
    *) shift ;;
  esac
done

mcp_call() {
  local tool="$1"
  local args="$2"
  curl -s "$MCP_URL" \
    -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"$tool\",\"arguments\":$args}}" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('result',{}).get('content',[{}])[0].get('text','{}'))" 2>/dev/null
}

# ── Build context block ─────────────────────────────────────────────────
CTX="<vault_context vault=\"$VAULT\" generated=\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\">\n"

# Stats
STATS=$(mcp_call "graph_snapshot" "{\"vault\":\"$VAULT\"}")
CTX+="<graph_stats>\n$STATS\n</graph_stats>\n"

# Diff (if requested)
if [ "$DIFF" = true ]; then
  DIFF_RESULT=$(mcp_call "graph_diff" "{\"vault\":\"$VAULT\"}")
  CTX+="<graph_diff>\n$DIFF_RESULT\n</graph_diff>\n"
fi

# Query-focused context
if [ -n "$QUERY" ]; then
  Q_ESC=$(echo "$QUERY" | sed 's/"/\\"/g')
  FOCUS=$(mcp_call "graph_context" "{\"vault\":\"$VAULT\",\"query\":\"$Q_ESC\",\"max_nodes\":30}")
  CTX+="<query_focus query=\"$QUERY\">\n$FOCUS\n</query_focus>\n"
fi

CTX+="</vault_context>"

if [ -n "$OUTPUT" ]; then
  echo -e "$CTX" > "$OUTPUT"
  echo "Context written to $OUTPUT" >&2
else
  echo -e "$CTX"
fi
