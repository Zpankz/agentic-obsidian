#!/usr/bin/env bash
# arscontexta hook: session-orient
# Auto-injects vault graph context at session start.
# Writes to $WORKSPACE/.openclaw/session-context.xml

set -euo pipefail

WORKSPACE="${OPENCLAW_WORKSPACE:-/home/exedev/pkg}"
TOOLS_DIR="/home/exedev/agentic-obsidian/tools"
OUTPUT="$WORKSPACE/.openclaw/session-context.xml"

mkdir -p "$(dirname "$OUTPUT")"

# Inject context for both vaults
"$TOOLS_DIR/context-inject.sh" --vault gkg --diff --output "$OUTPUT.gkg" 2>/dev/null || true
"$TOOLS_DIR/context-inject.sh" --vault pkg --output "$OUTPUT.pkg" 2>/dev/null || true

# Merge
{
  echo "<session_context>"
  cat "$OUTPUT.gkg" 2>/dev/null || true
  cat "$OUTPUT.pkg" 2>/dev/null || true
  echo "</session_context>"
} > "$OUTPUT"

rm -f "$OUTPUT.gkg" "$OUTPUT.pkg"
echo "Session context injected: $OUTPUT"
