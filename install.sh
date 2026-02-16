#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# agentic-obsidian installer
# One-click deployment of headless Obsidian with CLI on Linux VMs
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/Zpankz/agentic-obsidian/main/install.sh | bash
#
# Environment variables:
#   OBSIDIAN_ASAR_PATH  - local path to insider .asar file (for CLI support)
#   OBSIDIAN_VAULT      - vault directory (default: ~/obsidian-vault)
#   OBSIDIAN_VERSION    - AppImage version (default: 1.11.7)
#   OBSIDIAN_USER       - user to run as (default: current user)
#   API_PORT            - HTTP API port (default: 3000)
#   API_TOKEN           - bearer token for API auth (optional)
#   SKIP_API            - set to 1 to skip API server install
#   SKIP_CRON           - set to 1 to skip cron job install
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[agentic-obsidian]${NC} $*"; }
warn()  { echo -e "${YELLOW}[agentic-obsidian]${NC} $*"; }
error() { echo -e "${RED}[agentic-obsidian]${NC} $*"; exit 1; }

# ─── Configuration ───────────────────────────────────────────────────────────

OBSIDIAN_VERSION="${OBSIDIAN_VERSION:-1.11.7}"
OBSIDIAN_VAULT="${OBSIDIAN_VAULT:-$HOME/obsidian-vault}"
OBSIDIAN_USER="${OBSIDIAN_USER:-$(whoami)}"
API_PORT="${API_PORT:-3000}"
INSTALL_DIR="/opt/obsidian"
CONFIG_DIR="$HOME/.config/obsidian"
REPO_URL="https://raw.githubusercontent.com/Zpankz/agentic-obsidian/main"
APPIMAGE_URL="https://github.com/obsidianmd/obsidian-releases/releases/download/v${OBSIDIAN_VERSION}/Obsidian-${OBSIDIAN_VERSION}.AppImage"

echo -e "\n${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  agentic-obsidian installer${NC}"
echo -e "${BOLD}  Headless Obsidian CLI for AI Agents${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}\n"

# ─── Step 1: Preflight checks ───────────────────────────────────────────────

echo -e "${BOLD}Step 1: Preflight checks${NC}"

ARCH=$(uname -m)
if [ "$ARCH" != "x86_64" ]; then
  error "Unsupported architecture: $ARCH. Only x86_64 is supported."
fi
info "Architecture: $ARCH ✓"

if [ "$(uname -s)" != "Linux" ]; then
  error "This installer only supports Linux."
fi
info "Platform: Linux ✓"

# Check for sudo
if ! command -v sudo &>/dev/null; then
  error "sudo is required but not found."
fi

# ─── Step 2: Install system dependencies ─────────────────────────────────────

echo -e "\n${BOLD}Step 2: Install system dependencies${NC}"

DEPS="xvfb libgtk-3-0 libnotify4 libnss3 libxss1 libxtst6 xdg-utils \
      libatspi2.0-0 libsecret-1-0 libgbm1 libasound2t64 wget curl \
      ca-certificates fonts-liberation"

# Try libasound2t64 first, fall back to libasound2
if ! sudo apt-get install -y -qq --dry-run libasound2t64 &>/dev/null 2>&1; then
  DEPS="${DEPS//libasound2t64/libasound2}"
fi

sudo apt-get update -qq
sudo apt-get install -y -qq $DEPS
info "System dependencies installed ✓"

# Install Node.js if not present (for API server)
if [ "${SKIP_API:-0}" != "1" ] && ! command -v node &>/dev/null; then
  info "Installing Node.js..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y -qq nodejs
  info "Node.js $(node --version) installed ✓"
fi

# ─── Step 3: Download and extract Obsidian AppImage ──────────────────────────

echo -e "\n${BOLD}Step 3: Download and extract Obsidian${NC}"

sudo mkdir -p "$INSTALL_DIR"
sudo chown "$OBSIDIAN_USER:$OBSIDIAN_USER" "$INSTALL_DIR"

if [ -d "$INSTALL_DIR/squashfs-root" ]; then
  info "Obsidian already extracted, skipping download"
else
  info "Downloading Obsidian ${OBSIDIAN_VERSION} AppImage..."
  wget -q "$APPIMAGE_URL" -O "$INSTALL_DIR/Obsidian.AppImage"
  chmod +x "$INSTALL_DIR/Obsidian.AppImage"

  info "Extracting AppImage (no FUSE required)..."
  cd "$INSTALL_DIR"
  ./Obsidian.AppImage --appimage-extract >/dev/null 2>&1
  rm -f Obsidian.AppImage
  info "Obsidian extracted to $INSTALL_DIR/squashfs-root ✓"
fi

# ─── Step 4: Overlay insider asar (if provided) ─────────────────────────────

echo -e "\n${BOLD}Step 4: Configure Obsidian${NC}"

mkdir -p "$CONFIG_DIR"

if [ -n "${OBSIDIAN_ASAR_PATH:-}" ] && [ -f "$OBSIDIAN_ASAR_PATH" ]; then
  ASAR_NAME=$(basename "$OBSIDIAN_ASAR_PATH")
  cp "$OBSIDIAN_ASAR_PATH" "$CONFIG_DIR/$ASAR_NAME"
  info "Insider asar installed: $ASAR_NAME ✓"
  INSIDER=true
elif ls "$CONFIG_DIR"/obsidian-1.*.asar &>/dev/null 2>&1; then
  info "Insider asar already present ✓"
  INSIDER=true
else
  warn "No insider asar provided — CLI requires Obsidian 1.12+ (Catalyst beta)"
  warn "Set OBSIDIAN_ASAR_PATH to your local obsidian-1.12.x.asar file"
  INSIDER=false
fi

# Create vault directory
mkdir -p "$OBSIDIAN_VAULT/.obsidian"

# Generate vault ID and write config
VAULT_ID=$(echo -n "$OBSIDIAN_VAULT" | md5sum | cut -c1-16)
cat > "$CONFIG_DIR/obsidian.json" << EOF
{
  "vaults": {
    "${VAULT_ID}": {
      "path": "$OBSIDIAN_VAULT",
      "ts": $(date +%s)000,
      "open": true
    }
  },
  "insider": $INSIDER,
  "cli": true
}
EOF
info "Obsidian config written ✓"
info "Vault: $OBSIDIAN_VAULT"

# Create CLI symlink
sudo ln -sf "$INSTALL_DIR/squashfs-root/obsidian" /usr/local/bin/obsidian
info "CLI symlink created: /usr/local/bin/obsidian ✓"

# ─── Step 5: Create start/stop scripts ──────────────────────────────────────

echo -e "\n${BOLD}Step 5: Install services${NC}"

cat > "$INSTALL_DIR/start.sh" << 'STARTEOF'
#!/usr/bin/env bash
# Start Xvfb and Obsidian headlessly
export DISPLAY=:99

# Start Xvfb if not running
if ! pgrep -f "Xvfb :99" >/dev/null 2>&1; then
  Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
  sleep 1
fi

# Start Obsidian
/opt/obsidian/squashfs-root/obsidian --no-sandbox --disable-gpu &
OBSIDIAN_PID=$!
echo "$OBSIDIAN_PID" > /tmp/obsidian-headless.pid

# Wait for Obsidian to initialize
sleep 5
echo "Obsidian started (PID: $OBSIDIAN_PID)"
STARTEOF
chmod +x "$INSTALL_DIR/start.sh"

cat > "$INSTALL_DIR/stop.sh" << 'STOPEOF'
#!/usr/bin/env bash
# Stop Obsidian and Xvfb
if [ -f /tmp/obsidian-headless.pid ]; then
  kill "$(cat /tmp/obsidian-headless.pid)" 2>/dev/null
  rm -f /tmp/obsidian-headless.pid
fi
pkill -f "Xvfb :99" 2>/dev/null || true
STOPEOF
chmod +x "$INSTALL_DIR/stop.sh"

# Install systemd services
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd 2>/dev/null || echo /tmp)"

install_service() {
  local name="$1"
  local url="$REPO_URL/config/$name"
  local target="/etc/systemd/system/$name"

  if [ -f "$SCRIPT_DIR/config/$name" ]; then
    sudo cp "$SCRIPT_DIR/config/$name" "$target"
  else
    sudo curl -sSL "$url" -o "$target"
  fi

  # Patch user if not exedev
  if [ "$OBSIDIAN_USER" != "exedev" ]; then
    sudo sed -i "s/User=exedev/User=$OBSIDIAN_USER/" "$target"
    sudo sed -i "s|HOME=/home/exedev|HOME=$HOME|" "$target"
  fi
}

install_service "obsidian.service"
info "obsidian.service installed ✓"

if [ "${SKIP_API:-0}" != "1" ]; then
  install_service "obsidian-api.service"
  info "obsidian-api.service installed ✓"
fi

sudo systemctl daemon-reload

# ─── Step 6: Install API server ─────────────────────────────────────────────

if [ "${SKIP_API:-0}" != "1" ]; then
  echo -e "\n${BOLD}Step 6: Install API server${NC}"

  sudo mkdir -p "$INSTALL_DIR/api"
  sudo chown "$OBSIDIAN_USER:$OBSIDIAN_USER" "$INSTALL_DIR/api"

  if [ -f "$SCRIPT_DIR/api/server.js" ]; then
    cp "$SCRIPT_DIR/api/server.js" "$INSTALL_DIR/api/server.js"
    cp "$SCRIPT_DIR/api/package.json" "$INSTALL_DIR/api/package.json"
  else
    curl -sSL "$REPO_URL/api/server.js" -o "$INSTALL_DIR/api/server.js"
    curl -sSL "$REPO_URL/api/package.json" -o "$INSTALL_DIR/api/package.json"
  fi

  cd "$INSTALL_DIR/api"
  npm install --production --silent 2>/dev/null
  info "API server installed on port $API_PORT ✓"
fi

# ─── Step 7: Install cron jobs ───────────────────────────────────────────────

if [ "${SKIP_CRON:-0}" != "1" ]; then
  echo -e "\n${BOLD}Step 7: Install cron jobs${NC}"

  sudo mkdir -p "$INSTALL_DIR/cron"
  sudo chown "$OBSIDIAN_USER:$OBSIDIAN_USER" "$INSTALL_DIR/cron"

  for script in heartbeat.sh vault-backup.sh; do
    if [ -f "$SCRIPT_DIR/cron/$script" ]; then
      cp "$SCRIPT_DIR/cron/$script" "$INSTALL_DIR/cron/$script"
    else
      curl -sSL "$REPO_URL/cron/$script" -o "$INSTALL_DIR/cron/$script"
    fi
    chmod +x "$INSTALL_DIR/cron/$script"
  done

  # Install crontab entries (idempotent)
  CRON_TAG="# agentic-obsidian"
  (crontab -l 2>/dev/null | grep -v "$CRON_TAG" || true; cat << EOF
*/5 * * * * DISPLAY=:99 OBSIDIAN_VAULT=$OBSIDIAN_VAULT /opt/obsidian/cron/heartbeat.sh $CRON_TAG
0 3 * * * OBSIDIAN_VAULT=$OBSIDIAN_VAULT /opt/obsidian/cron/vault-backup.sh $CRON_TAG
EOF
  ) | crontab -
  info "Cron jobs installed (heartbeat every 5m, backup daily 3am) ✓"
fi

# ─── Step 8: Start services ─────────────────────────────────────────────────

echo -e "\n${BOLD}Step 8: Start services${NC}"

sudo systemctl enable --now obsidian.service
info "Obsidian service started ✓"

# Wait for Obsidian to initialize
sleep 8

if [ "${SKIP_API:-0}" != "1" ]; then
  sudo systemctl enable --now obsidian-api.service
  info "API server started on port $API_PORT ✓"
fi

# ─── Step 9: Write initial heartbeat ────────────────────────────────────────

echo -e "\n${BOLD}Step 9: Initial heartbeat${NC}"

export DISPLAY=:99
if OBSIDIAN_VAULT="$OBSIDIAN_VAULT" /opt/obsidian/cron/heartbeat.sh 2>/dev/null; then
  info "heartbeat.md written to vault ✓"
fi

# ─── Step 10: Verify ────────────────────────────────────────────────────────

echo -e "\n${BOLD}Step 10: Verification${NC}"

if DISPLAY=:99 obsidian version 2>/dev/null | grep -q "1\."; then
  OBS_VER=$(DISPLAY=:99 obsidian version 2>/dev/null | head -1)
  info "Obsidian CLI: $OBS_VER ✓"
else
  warn "Obsidian CLI not responding yet (may need more startup time)"
fi

if [ "${SKIP_API:-0}" != "1" ]; then
  sleep 2
  if curl -sf "http://localhost:$API_PORT/health" >/dev/null 2>&1; then
    info "API server: healthy ✓"
  else
    warn "API server not responding yet (check: systemctl status obsidian-api)"
  fi
fi

# ─── Done ────────────────────────────────────────────────────────────────────

echo -e "\n${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  agentic-obsidian installed successfully!${NC}"
echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}\n"

echo "  Obsidian:  $INSTALL_DIR/squashfs-root/"
echo "  Vault:     $OBSIDIAN_VAULT"
echo "  Config:    $CONFIG_DIR/obsidian.json"
echo ""
echo "  CLI usage:"
echo "    DISPLAY=:99 obsidian help"
echo "    DISPLAY=:99 obsidian search query=\"my notes\""
echo "    DISPLAY=:99 obsidian daily:append content=\"- [ ] New task\""
echo ""
if [ "${SKIP_API:-0}" != "1" ]; then
  echo "  API endpoints:"
  echo "    http://localhost:$API_PORT/health"
  echo "    http://localhost:$API_PORT/files"
  echo "    http://localhost:$API_PORT/read?file=heartbeat"
  echo ""
fi
echo "  Services:"
echo "    sudo systemctl status obsidian"
echo "    sudo systemctl status obsidian-api"
echo ""
