#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# agent-setup.sh — One-shot Obsidian insider upgrade, account auth & sync setup
#
# Automates everything install.sh doesn't do:
#   1. Upgrades to Obsidian 1.12+ (Catalyst insider build via auto-updater)
#   2. Authenticates with an Obsidian account
#   3. Creates or connects to an Obsidian Sync remote vault
#
# Usage:
#   ./agent-setup.sh --email <email> --password <pass> [options]
#
# Options:
#   --email <email>           Obsidian account email (required)
#   --password <password>     Obsidian account password (required)
#   --vault-name <name>       Remote vault name to create or connect (default: basename of OBSIDIAN_VAULT)
#   --vault-path <path>       Local vault path (default: $OBSIDIAN_VAULT or ~/obsidian-vault)
#   --region <region>         Sync region for new vaults (default: auto)
#   --skip-insider            Skip insider upgrade (already on 1.12+)
#   --skip-sync               Skip sync setup
#   --connect-existing        Connect to existing vault instead of creating
#   --timeout <seconds>       Max wait for insider download (default: 60)
#   --json                    Output results as JSON
#   -h, --help                Show this help
#
# Environment variables:
#   OBSIDIAN_EMAIL            Alternative to --email
#   OBSIDIAN_PASSWORD         Alternative to --password
#   OBSIDIAN_VAULT            Local vault directory
#   OBSIDIAN_VAULT_NAME       Remote vault name
#   OBSIDIAN_SYNC_REGION      Sync region
#
# Examples:
#   # Full setup with new sync vault
#   ./agent-setup.sh --email me@example.com --password 's3cret' --vault-name myproject
#
#   # Connect to an existing remote vault
#   ./agent-setup.sh --email me@example.com --password 's3cret' \
#     --vault-name myproject --connect-existing
#
#   # Just upgrade to insider, skip sync
#   ./agent-setup.sh --email me@example.com --password 's3cret' --skip-sync
#
#   # Via environment variables
#   OBSIDIAN_EMAIL=me@example.com OBSIDIAN_PASSWORD=s3cret ./agent-setup.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[agent-setup]${NC} $*"; }
warn()  { echo -e "${YELLOW}[agent-setup]${NC} $*"; }
error() { echo -e "${RED}[agent-setup]${NC} $*"; exit 1; }

# ─── Parse arguments ─────────────────────────────────────────────────────────

EMAIL="${OBSIDIAN_EMAIL:-}"
PASSWORD="${OBSIDIAN_PASSWORD:-}"
VAULT_PATH="${OBSIDIAN_VAULT:-$HOME/obsidian-vault}"
VAULT_NAME="${OBSIDIAN_VAULT_NAME:-}"
REGION="${OBSIDIAN_SYNC_REGION:-}"
SKIP_INSIDER=false
SKIP_SYNC=false
CONNECT_EXISTING=false
TIMEOUT=60
JSON_OUTPUT=false

show_help() {
  sed -n '/^# Usage:/,/^# ──/p' "$0" | sed 's/^# \?//' | head -n -1
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --email)            EMAIL="$2"; shift 2 ;;
    --password)         PASSWORD="$2"; shift 2 ;;
    --vault-name)       VAULT_NAME="$2"; shift 2 ;;
    --vault-path)       VAULT_PATH="$2"; shift 2 ;;
    --region)           REGION="$2"; shift 2 ;;
    --skip-insider)     SKIP_INSIDER=true; shift ;;
    --skip-sync)        SKIP_SYNC=true; shift ;;
    --connect-existing) CONNECT_EXISTING=true; shift ;;
    --timeout)          TIMEOUT="$2"; shift 2 ;;
    --json)             JSON_OUTPUT=true; shift ;;
    -h|--help)          show_help ;;
    *) error "Unknown option: $1. Use --help for usage." ;;
  esac
done

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  error "--email and --password are required (or set OBSIDIAN_EMAIL / OBSIDIAN_PASSWORD)"
fi

[ -z "$VAULT_NAME" ] && VAULT_NAME=$(basename "$VAULT_PATH")

export DISPLAY=:99

# Headers required to bypass Cloudflare on api.obsidian.md
API_HEADERS='-H "Content-Type: application/json" -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" -H "Origin: https://obsidian.md" -H "Referer: https://obsidian.md/"'

# ─── Helper: API call ────────────────────────────────────────────────────────

api_post() {
  local endpoint="$1"
  local body="$2"
  python3 -c "
import urllib.request, json, sys

data = json.dumps($body).encode()
req = urllib.request.Request(
    'https://api.obsidian.md$endpoint',
    data=data,
    headers={
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Origin': 'https://obsidian.md',
        'Referer': 'https://obsidian.md/',
    }
)
try:
    with urllib.request.urlopen(req) as resp:
        print(resp.read().decode())
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(json.dumps({'error': body, 'status': e.code}), file=sys.stderr)
    sys.exit(1)
"
}

# ─── Helper: Obsidian eval (run JS in renderer) ─────────────────────────────

obs_eval() {
  DISPLAY=:99 obsidian eval code="$1" 2>/dev/null
}

# ─── Helper: Wait for condition ──────────────────────────────────────────────

wait_for() {
  local desc="$1"
  local cmd="$2"
  local max="$3"
  local elapsed=0
  while [ $elapsed -lt $max ]; do
    if eval "$cmd" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done
  return 1
}

echo -e "\n${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  agent-setup: Insider CLI + Sync Configuration${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}\n"

# ─── Preflight ───────────────────────────────────────────────────────────────

echo -e "${BOLD}Preflight checks${NC}"

if ! systemctl is-active --quiet obsidian 2>/dev/null; then
  error "obsidian.service is not running. Run install.sh first."
fi
info "Obsidian service: running ✓"

if ! pgrep -f "Xvfb :99" >/dev/null 2>&1; then
  error "Xvfb display :99 is not running."
fi
info "Xvfb display :99: running ✓"

CONFIG_DIR="$HOME/.config/obsidian"
CONFIG_FILE="$CONFIG_DIR/obsidian.json"
if [ ! -f "$CONFIG_FILE" ]; then
  error "$CONFIG_FILE not found. Run install.sh first."
fi
info "Config: $CONFIG_FILE ✓"
info "Vault: $VAULT_PATH"
info "Remote vault name: $VAULT_NAME"

# ─── Step 1: Authenticate ────────────────────────────────────────────────────

echo -e "\n${BOLD}Step 1: Authenticate with Obsidian account${NC}"

AUTH_RESULT=$(api_post "/user/signin" "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}" 2>/tmp/agent-setup-auth-err.json) || {
  warn "Authentication failed. Response:"
  cat /tmp/agent-setup-auth-err.json >&2
  error "Check your email and password."
}

TOKEN=$(echo "$AUTH_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['token'])")
ACCOUNT_NAME=$(echo "$AUTH_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('name',''))")
LICENSE=$(echo "$AUTH_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('license',''))")

info "Signed in as: $ACCOUNT_NAME ($EMAIL)"
info "License: $LICENSE"

if [ "$LICENSE" != "vip" ] && [ "$SKIP_INSIDER" = false ]; then
  warn "Account does not have Catalyst license. Insider upgrade may not work."
fi

# ─── Step 2: Upgrade to insider build ────────────────────────────────────────

if [ "$SKIP_INSIDER" = false ]; then
  echo -e "\n${BOLD}Step 2: Upgrade to Obsidian 1.12+ (insider build)${NC}"

  # Check if already on 1.12+
  CURRENT_VERSION=$(DISPLAY=:99 obsidian version 2>/dev/null | head -1 || echo "unknown")
  if echo "$CURRENT_VERSION" | grep -qP '^1\.1[2-9]|^1\.[2-9][0-9]|^[2-9]'; then
    info "Already on insider build: $CURRENT_VERSION ✓"
  else
    info "Current version: $CURRENT_VERSION — upgrading..."

    # Set insider: true in config
    python3 -c "
import json
with open('$CONFIG_FILE') as f:
    cfg = json.load(f)
cfg['insider'] = True
with open('$CONFIG_FILE', 'w') as f:
    json.dump(cfg, f, indent=2)
"
    info "Set insider: true in config"

    # Restart to trigger auto-updater
    sudo systemctl restart obsidian
    info "Restarted Obsidian — waiting for insider download..."

    # Wait for the insider .asar to appear
    INSIDER_DOWNLOADED=false
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ]; do
      sleep 3
      ELAPSED=$((ELAPSED + 3))

      # Check log for completion
      if tail -20 "$CONFIG_DIR/obsidian.log" 2>/dev/null | grep -q "App is up to date"; then
        # Verify an insider .asar exists
        if ls "$CONFIG_DIR"/obsidian-1.1[2-9]*.asar "$CONFIG_DIR"/obsidian-1.[2-9]*.asar 2>/dev/null | head -1 >/dev/null; then
          INSIDER_DOWNLOADED=true
          break
        fi
      fi

      # Also check for "Update complete"
      if tail -20 "$CONFIG_DIR/obsidian.log" 2>/dev/null | grep -q "Update complete"; then
        INSIDER_DOWNLOADED=true
        sleep 2
        break
      fi
    done

    if [ "$INSIDER_DOWNLOADED" = true ]; then
      # Restart to load the new .asar
      sudo systemctl restart obsidian
      sleep 8

      NEW_VERSION=$(DISPLAY=:99 obsidian version 2>/dev/null | head -1 || echo "unknown")
      info "Upgraded to: $NEW_VERSION ✓"
    else
      warn "Insider download did not complete within ${TIMEOUT}s."
      warn "Check: tail -30 $CONFIG_DIR/obsidian.log"
      warn "The account may not have a Catalyst license."
      # Don't exit — continue with whatever version we have
    fi
  fi
else
  info "Skipping insider upgrade (--skip-insider)"
fi

# ─── Step 3: Store account token ─────────────────────────────────────────────

echo -e "\n${BOLD}Step 3: Store account token${NC}"

# Inject token into the running Obsidian renderer's localStorage
obs_eval "
localStorage.setItem('obsidian-account', JSON.stringify({
  email: '$EMAIL',
  name: $(python3 -c "import json; print(json.dumps('$ACCOUNT_NAME'))"),
  token: '$TOKEN',
  license: '$LICENSE'
}));
'done'
"
info "Account token stored in localStorage ✓"

# Restart so the Vw account singleton picks up the new token
# (it's module-scoped and only reads localStorage at startup)
sudo systemctl restart obsidian
sleep 8
info "Obsidian restarted with account token ✓"

# ─── Step 4: Configure Sync ──────────────────────────────────────────────────

if [ "$SKIP_SYNC" = false ]; then
  echo -e "\n${BOLD}Step 4: Configure Obsidian Sync${NC}"

  # Enable sync core plugin (idempotent)
  DISPLAY=:99 obsidian plugin:enable id=sync 2>/dev/null || true

  # List remote vaults
  VAULTS_JSON=$(api_post "/vault/list" "{\"token\": \"$TOKEN\", \"supported_encryption_version\": 3}")

  # Check if target vault already exists
  VAULT_EXISTS=$(echo "$VAULTS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for v in data.get('vaults', []):
    if v['name'] == '$VAULT_NAME':
        print(json.dumps(v))
        sys.exit(0)
print('')
")

  if [ -n "$VAULT_EXISTS" ]; then
    info "Found existing remote vault: $VAULT_NAME"
    VAULT_INFO="$VAULT_EXISTS"
  elif [ "$CONNECT_EXISTING" = true ]; then
    error "Vault '$VAULT_NAME' not found in account. Available vaults:"
    echo "$VAULTS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for v in data.get('vaults', []):
    print(f\"  - {v['name']} (id: {v['id'][:12]}..., host: {v['host']})\")" >&2
    exit 1
  else
    # Check vault limit
    VAULT_LIMIT=$(echo "$VAULTS_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('limit', 0))")
    VAULT_COUNT=$(echo "$VAULTS_JSON" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('vaults', [])))")

    if [ "$VAULT_COUNT" -ge "$VAULT_LIMIT" ] && [ "$VAULT_LIMIT" -gt 0 ]; then
      error "Vault limit reached ($VAULT_COUNT/$VAULT_LIMIT). Delete a vault or use --connect-existing."
    fi

    # Determine region
    if [ -z "$REGION" ]; then
      REGION=$(api_post "/vault/regions" "{\"token\": \"$TOKEN\"}" 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
regions = data.get('regions', [])
if regions:
    print(regions[0])
else:
    print('North America')
" 2>/dev/null || echo "North America")
      info "Auto-selected region: $REGION"
    fi

    info "Creating remote vault: $VAULT_NAME (region: $REGION)"
    VAULT_INFO=$(api_post "/vault/create" "{\"token\": \"$TOKEN\", \"name\": \"$VAULT_NAME\", \"keyhash\": null, \"salt\": null, \"region\": \"$REGION\", \"encryption_version\": 3}")
    info "Remote vault created ✓"
  fi

  # Extract vault details
  REMOTE_VAULT_ID=$(echo "$VAULT_INFO" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
  REMOTE_HOST=$(echo "$VAULT_INFO" | python3 -c "import json,sys; print(json.load(sys.stdin)['host'])")
  REMOTE_PASSWORD=$(echo "$VAULT_INFO" | python3 -c "import json,sys; print(json.load(sys.stdin)['password'])")
  REMOTE_SALT=$(echo "$VAULT_INFO" | python3 -c "import json,sys; print(json.load(sys.stdin)['salt'])")
  REMOTE_ENC_VER=$(echo "$VAULT_INFO" | python3 -c "import json,sys; print(json.load(sys.stdin).get('encryption_version', 3))")

  info "Vault ID: ${REMOTE_VAULT_ID:0:12}..."
  info "Host: $REMOTE_HOST"

  # Connect local vault to remote via sync.setup()
  # CRITICAL: host must be bare hostname — getHost() prepends wss:// automatically
  info "Connecting local vault to sync server..."

  # Escape special characters in password/salt for JS string
  JS_PASSWORD=$(python3 -c "import json; print(json.dumps('$REMOTE_PASSWORD')[1:-1])")
  JS_SALT=$(python3 -c "import json; print(json.dumps('$REMOTE_SALT')[1:-1])")

  obs_eval "
var sync = app.internalPlugins.plugins.sync.instance;
sync.setup(
  '$REMOTE_VAULT_ID',
  '$VAULT_NAME',
  '$JS_PASSWORD',
  '$JS_SALT',
  '$REMOTE_HOST',
  $REMOTE_ENC_VER
).then(function() {
  sync.saveData();
  require('fs').writeFileSync('/tmp/agent-setup-sync.json', JSON.stringify({ok: true}));
}).catch(function(e) {
  require('fs').writeFileSync('/tmp/agent-setup-sync.json', JSON.stringify({error: e.message}));
});
'connecting...'
  "

  sleep 5

  if [ -f /tmp/agent-setup-sync.json ]; then
    SYNC_OK=$(python3 -c "import json; print(json.load(open('/tmp/agent-setup-sync.json')).get('ok', False))")
    if [ "$SYNC_OK" = "True" ]; then
      info "Sync plugin configured ✓"
    else
      SYNC_ERR=$(python3 -c "import json; print(json.load(open('/tmp/agent-setup-sync.json')).get('error', 'unknown'))")
      warn "Sync setup returned error: $SYNC_ERR"
    fi
    rm -f /tmp/agent-setup-sync.json
  fi

  # Final restart so sync connects with the authenticated account token
  info "Restarting Obsidian for final sync connection..."
  sudo systemctl restart obsidian
  sleep 10

  # Verify sync status
  SYNC_STATUS=$(DISPLAY=:99 obsidian sync:status 2>/dev/null | head -1 || echo "unknown")
  info "Sync status: $SYNC_STATUS"

  if echo "$SYNC_STATUS" | grep -q "synced\|syncing"; then
    info "Obsidian Sync connected ✓"
  else
    warn "Sync may need a moment to connect. Check: DISPLAY=:99 obsidian sync:status"
  fi
else
  info "Skipping sync setup (--skip-sync)"
fi

# ─── Step 5: Verify & report ─────────────────────────────────────────────────

echo -e "\n${BOLD}Step 5: Verification${NC}"

FINAL_VERSION=$(DISPLAY=:99 obsidian version 2>/dev/null | head -1 || echo "unknown")
FINAL_SYNC=$(DISPLAY=:99 obsidian sync:status 2>/dev/null || echo "unknown")
FINAL_FILES=$(DISPLAY=:99 obsidian files total 2>/dev/null || echo "0")

info "Obsidian version: $FINAL_VERSION"
info "Vault files: $FINAL_FILES"

if [ "$JSON_OUTPUT" = true ]; then
  python3 -c "
import json
result = {
    'version': '$FINAL_VERSION',
    'vault_path': '$VAULT_PATH',
    'vault_name': '$VAULT_NAME',
    'sync_status': '''$FINAL_SYNC'''.strip().split('\\n')[0] if '''$FINAL_SYNC''' else 'unknown',
    'account': '$EMAIL',
    'license': '$LICENSE',
}
print(json.dumps(result, indent=2))
"
fi

# ─── Cleanup ─────────────────────────────────────────────────────────────────

rm -f /tmp/agent-setup-auth-err.json /tmp/agent-setup-sync.json

# ─── Done ────────────────────────────────────────────────────────────────────

echo -e "\n${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  agent-setup complete!${NC}"
echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}\n"

echo "  Version:    $FINAL_VERSION"
echo "  Vault:      $VAULT_PATH"
echo "  Remote:     $VAULT_NAME"
echo ""
echo "  CLI:"
echo "    DISPLAY=:99 obsidian help"
echo "    DISPLAY=:99 obsidian sync:status"
echo "    DISPLAY=:99 obsidian files"
echo ""
