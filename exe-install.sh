#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# agentic-obsidian: exe.dev one-click installer
#
# Creates an exe.dev VM and deploys headless Obsidian with CLI + API.
#
# Prerequisites:
#   - exe.dev account (ssh exe.dev must work)
#   - Obsidian Catalyst license (for CLI support)
#
# Usage:
#   ./exe-install.sh <vm-name> [path-to-asar]
#
# Examples:
#   ./exe-install.sh my-obsidian
#   ./exe-install.sh my-obsidian ~/Library/Application\ Support/obsidian/obsidian-1.12.1.asar
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[exe.dev]${NC} $*"; }
warn()  { echo -e "${YELLOW}[exe.dev]${NC} $*"; }
error() { echo -e "${RED}[exe.dev]${NC} $*"; exit 1; }

VM_NAME="${1:-}"
ASAR_PATH="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$VM_NAME" ]; then
  echo "Usage: $0 <vm-name> [path-to-asar]"
  echo ""
  echo "  <vm-name>       Name for the exe.dev VM (e.g. my-obsidian)"
  echo "  [path-to-asar]  Optional path to insider .asar file"
  echo ""
  echo "Auto-detect asar from local Obsidian (macOS):"
  DETECTED_ASAR=$(ls "$HOME/Library/Application Support/obsidian"/obsidian-1.*.asar 2>/dev/null | sort -V | tail -1 || true)
  if [ -n "$DETECTED_ASAR" ]; then
    echo "  Found: $DETECTED_ASAR"
  else
    echo "  No local insider asar found"
  fi
  exit 1
fi

# Auto-detect asar if not provided
if [ -z "$ASAR_PATH" ]; then
  DETECTED_ASAR=$(ls "$HOME/Library/Application Support/obsidian"/obsidian-1.*.asar 2>/dev/null | sort -V | tail -1 || true)
  if [ -n "$DETECTED_ASAR" ]; then
    ASAR_PATH="$DETECTED_ASAR"
    info "Auto-detected insider asar: $(basename "$ASAR_PATH")"
  fi
fi

echo -e "\n${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  agentic-obsidian: exe.dev deployment${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}\n"

# ─── Step 1: Verify exe.dev access ──────────────────────────────────────────

echo -e "${BOLD}Step 1: Verify exe.dev access${NC}"

if ! ssh -o ConnectTimeout=5 exe.dev ls --json >/dev/null 2>&1; then
  error "Cannot connect to exe.dev. Run 'ssh exe.dev' to register first."
fi
info "exe.dev access verified ✓"

# Check if VM already exists
if ssh exe.dev ls --json 2>/dev/null | grep -q "\"vm_name\":\"$VM_NAME\""; then
  info "VM '$VM_NAME' already exists"
  VM_HOST="${VM_NAME}.exe.xyz"
else
  # ─── Step 2: Create VM ──────────────────────────────────────────────────────

  echo -e "\n${BOLD}Step 2: Create VM${NC}"
  info "Creating VM: $VM_NAME..."
  ssh exe.dev new --name="$VM_NAME"
  VM_HOST="${VM_NAME}.exe.xyz"
  info "VM created: $VM_HOST ✓"

  # Wait for VM to be ready
  info "Waiting for VM to boot..."
  for i in $(seq 1 30); do
    if ssh -o ConnectTimeout=3 "$VM_HOST" echo ok >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  info "VM is ready ✓"
fi

# ─── Step 3: Transfer files ─────────────────────────────────────────────────

echo -e "\n${BOLD}Step 3: Transfer files${NC}"

# Transfer the installer and all supporting files
scp -r "$SCRIPT_DIR/install.sh" \
       "$SCRIPT_DIR/config" \
       "$SCRIPT_DIR/cron" \
       "$SCRIPT_DIR/api" \
       "$SCRIPT_DIR/integrations" \
       "$SCRIPT_DIR/AGENTS.md" \
       "$VM_HOST:/tmp/agentic-obsidian/"
info "Project files transferred ✓"

# Transfer asar if available
if [ -n "$ASAR_PATH" ] && [ -f "$ASAR_PATH" ]; then
  ASAR_NAME=$(basename "$ASAR_PATH")
  scp "$ASAR_PATH" "$VM_HOST:/tmp/$ASAR_NAME"
  info "Insider asar transferred: $ASAR_NAME ✓"
  ASAR_REMOTE="/tmp/$ASAR_NAME"
else
  warn "No insider asar — Obsidian will install without CLI support"
  ASAR_REMOTE=""
fi

# ─── Step 4: Run installer on VM ────────────────────────────────────────────

echo -e "\n${BOLD}Step 4: Run installer on VM${NC}"

INSTALL_CMD="cd /tmp/agentic-obsidian && chmod +x install.sh"
if [ -n "$ASAR_REMOTE" ]; then
  INSTALL_CMD="$INSTALL_CMD && OBSIDIAN_ASAR_PATH=$ASAR_REMOTE bash install.sh"
else
  INSTALL_CMD="$INSTALL_CMD && bash install.sh"
fi

ssh "$VM_HOST" "$INSTALL_CMD"

# ─── Step 5: Configure exe.dev proxy ────────────────────────────────────────

echo -e "\n${BOLD}Step 5: Configure exe.dev proxy${NC}"

ssh exe.dev share port "$VM_NAME" 3000 2>/dev/null || true
info "HTTP proxy → port 3000 ✓"

# Copy AGENTS.md to home directory
ssh "$VM_HOST" "cp /tmp/agentic-obsidian/AGENTS.md ~/AGENTS.md" 2>/dev/null || true

# ─── Done ────────────────────────────────────────────────────────────────────

echo -e "\n${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  Deployed to exe.dev!${NC}"
echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}\n"

echo "  VM:        $VM_HOST"
echo ""
echo "  SSH:"
echo "    ssh $VM_HOST"
echo "    ssh $VM_HOST 'DISPLAY=:99 obsidian help'"
echo ""
echo "  API (private, requires exe.dev login):"
echo "    https://${VM_NAME}.exe.xyz/health"
echo "    https://${VM_NAME}.exe.xyz/files"
echo "    https://${VM_NAME}.exe.xyz/read?file=heartbeat"
echo ""
echo "  CLI over SSH:"
echo "    ssh $VM_HOST 'DISPLAY=:99 obsidian search query=\"my notes\"'"
echo "    ssh $VM_HOST 'DISPLAY=:99 obsidian daily:append content=\"- [ ] Task\"'"
echo ""
echo "  Make API public (optional):"
echo "    ssh exe.dev share set-public $VM_NAME"
echo ""
