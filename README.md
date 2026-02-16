# agentic-obsidian

One-click deployment of headless Obsidian with CLI on remote Linux VMs — built for AI agents.

## Why

Obsidian's CLI (Catalyst beta 1.12+) is powerful: it can read, write, search, and manage vaults programmatically. But the CLI requires the Obsidian GUI app to be running, which doesn't exist on headless servers.

**agentic-obsidian** solves this by:

1. Extracting an Obsidian AppImage on a headless Linux VM
2. Running it on a virtual framebuffer (Xvfb) so the CLI works
3. Overlaying the Catalyst `.asar` to unlock CLI 1.12+ features
4. Exposing the vault via CLI, HTTP API, and SSH

The result: any AI agent, cron job, or automation pipeline can use Obsidian as a knowledge backend.

## Quick Start

### Generic Linux (any VM/VPS)

```bash
# Set required env vars
export OBSIDIAN_ASAR_PATH=/path/to/obsidian-1.12.1.asar
export OBSIDIAN_VAULT=/home/user/obsidian-vault

# Install
curl -sSL https://raw.githubusercontent.com/Zpankz/agentic-obsidian/main/install.sh | bash
```

### exe.dev (one-click)

```bash
git clone https://github.com/Zpankz/agentic-obsidian.git
cd agentic-obsidian
./exe-install.sh my-obsidian-vm
```

This creates a new exe.dev VM, installs everything, and configures the HTTP proxy. Your vault is accessible at `https://my-obsidian-vm.exe.xyz/`.

## Prerequisites

- **Linux x86_64** (Ubuntu 22.04+ recommended)
- **Obsidian Catalyst license** — the CLI requires the insider `.asar` file (1.12+)
- **sudo access** — for apt packages and systemd services
- **Node.js 18+** — for the HTTP API server (installed automatically)

### Getting the .asar file

The `.asar` file is the Obsidian insider build that enables CLI functionality. If you have Obsidian Catalyst on macOS:

```
~/Library/Application Support/obsidian/obsidian-1.12.1.asar
```

On Linux:

```
~/.config/obsidian/obsidian-1.12.1.asar
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Headless Linux VM                                        │
│                                                           │
│  ┌─────────┐    ┌──────────────┐    ┌──────────────────┐ │
│  │  Xvfb   │───▶│   Obsidian   │◀───│  Obsidian CLI    │ │
│  │  :99    │    │  (headless)  │    │  (1.12+ .asar)   │ │
│  └─────────┘    └──────────────┘    └────────┬─────────┘ │
│                                               │           │
│                     ┌─────────────────────────┤           │
│                     │                         │           │
│              ┌──────▼──────┐          ┌───────▼────────┐ │
│              │  HTTP API   │          │   SSH / cron   │ │
│              │  :3000      │          │   direct CLI   │ │
│              └──────┬──────┘          └────────────────┘ │
│                     │                                     │
└─────────────────────┼─────────────────────────────────────┘
                      │
              ┌───────▼────────┐
              │  AI Agents /   │
              │  Automations   │
              └────────────────┘
```

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Obsidian AppImage | `/opt/obsidian/squashfs-root/` | Extracted Electron app |
| Xvfb | Display `:99` | Virtual framebuffer for headless GUI |
| CLI .asar | `~/.config/obsidian/` | Catalyst build enabling CLI |
| HTTP API | Port 3000 | REST wrapper around CLI |
| Heartbeat | `~/obsidian-vault/heartbeat.md` | 5-minute health pulse |
| Backups | `/opt/obsidian/backups/` | Daily vault tar.gz (7-day rotation) |

### systemd Services

- **`obsidian.service`** — Starts Xvfb + Obsidian headless
- **`obsidian-api.service`** — Starts the HTTP API server (depends on obsidian.service)

## Access Methods

### 1. Direct CLI (on the VM)

```bash
DISPLAY=:99 obsidian help
DISPLAY=:99 obsidian files
DISPLAY=:99 obsidian read file="my-note"
DISPLAY=:99 obsidian search query="meeting"
DISPLAY=:99 obsidian create name="New Note" content="# Hello"
DISPLAY=:99 obsidian daily:append content="- [ ] New task" silent
DISPLAY=:99 obsidian tags all counts
```

### 2. SSH (remote)

```bash
ssh myvm.exe.xyz 'DISPLAY=:99 obsidian search query="project ideas"'
```

Or source the helper functions:

```bash
source integrations/ssh-pipe.sh
export OBS_HOST=myvm.exe.xyz
obs-search "project ideas"
obs-read "my-note"
obs-daily "- [ ] Review PRs"
```

### 3. HTTP API

```bash
# Health check
curl https://myvm.exe.xyz/health

# List files
curl https://myvm.exe.xyz/files

# Read a note
curl https://myvm.exe.xyz/read?file=my-note

# Search
curl https://myvm.exe.xyz/search?q=meeting

# Create a note
curl -X POST https://myvm.exe.xyz/create \
  -H "Content-Type: application/json" \
  -d '{"name": "New Note", "content": "# Hello\nWorld"}'

# Append to daily note
curl -X POST https://myvm.exe.xyz/daily/append \
  -H "Content-Type: application/json" \
  -d '{"content": "- [ ] Ship the feature"}'

# Run any CLI command
curl -X POST https://myvm.exe.xyz/command \
  -H "Content-Type: application/json" \
  -d '{"command": "tags all counts"}'
```

## API Reference

### Authentication

The API supports three auth methods (checked in order):

1. **exe.dev proxy header** — `X-ExeDev-Email` (auto-injected by exe.dev HTTP proxy)
2. **Bearer token** — `Authorization: Bearer <token>` (set via `API_TOKEN` env var)
3. **Localhost only** — if no token is configured, only `127.0.0.1` can access

### Endpoints

#### `GET /health` (public)

Returns service health. Always accessible without auth.

```json
{"status": "healthy", "obsidian": true, "timestamp": "2025-01-01T00:00:00.000Z"}
```

#### `GET /version`

Returns Obsidian version string.

#### `GET /vault`

Returns vault metadata (path, file count, etc).

#### `GET /files`

Query params: `folder`, `ext`, `total`

#### `GET /read`

Query params: `file` (by name) or `path` (by path)

#### `GET /search`

Query params: `q` (required), `limit`, `matches`

#### `GET /tags`

Query params: `counts`, `sort`

#### `GET /tasks`

Query params: `daily`, `todo`, `done`

#### `POST /create`

Body: `{name, path, content, template, overwrite}`

#### `POST /append`

Body: `{file, path, content}` — content is required

#### `POST /daily/append`

Body: `{content}` — appends to today's daily note

#### `POST /command`

Body: `{command}` — runs any CLI command (e.g. `"tags all counts"`)

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSIDIAN_ASAR_PATH` | (required) | Path to the Catalyst `.asar` file |
| `OBSIDIAN_VAULT` | `~/obsidian-vault` | Vault directory path |
| `OBSIDIAN_VERSION` | `1.11.7` | AppImage version to download |
| `OBSIDIAN_USER` | current user | User to run services as |
| `API_PORT` | `3000` | HTTP API port |
| `API_TOKEN` | (none) | Bearer token for API auth |
| `SKIP_API` | `false` | Skip API server installation |
| `SKIP_CRON` | `false` | Skip cron job installation |

### Heartbeat

The heartbeat cron writes `heartbeat.md` to your vault every 5 minutes with:

```yaml
---
status: healthy | degraded
obsidian_version: 1.12.1 (installer 1.11.7)
files: 959
vault_size: 245M
uptime: 5 days, 3:22
services:
  obsidian: active
  obsidian-api: active
last_check: 2025-01-01T00:00:00Z
---
```

### Vault Backups

Daily at 3am, the vault is backed up to `/opt/obsidian/backups/` as a tar.gz archive. The 7 most recent backups are kept; older ones are automatically pruned.

## exe.dev Integration

[exe.dev](https://exe.dev) provides managed Linux VMs with built-in HTTP proxying and SSH access.

### How it works

1. `exe-install.sh` creates a VM via `ssh exe.dev new <name>`
2. Transfers the `.asar` file from your local machine
3. Runs `install.sh` on the VM
4. Configures the HTTP proxy to forward port 3000

### After install

- **HTTP API**: `https://<name>.exe.xyz/`
- **SSH**: `ssh <name>.exe.xyz`
- **Direct CLI**: `ssh <name>.exe.xyz 'DISPLAY=:99 obsidian help'`

### Slack notifications

Set up daily vault summaries in Slack:

```bash
ssh myvm.exe.xyz 'echo "0 9 * * * SLACK_WEBHOOK_URL=https://hooks.slack.com/... DISPLAY=:99 /opt/obsidian/integrations/slack-webhook.sh" | crontab -'
```

## Integrations

### SSH pipe helpers (`integrations/ssh-pipe.sh`)

Source this file to get shell functions for quick remote vault access:

```bash
source integrations/ssh-pipe.sh
export OBS_HOST=myvm.exe.xyz
obs-files          # list files
obs-read "note"    # read a note
obs-search "query" # search vault
obs-daily "task"   # append to daily note
obs-tags           # list all tags
obs-tasks          # list all tasks
obs-beat           # read heartbeat
```

### Slack webhook (`integrations/slack-webhook.sh`)

Posts a vault summary (file count, version, vault path) to a Slack channel.

### AGENTS.md

The repo includes an `AGENTS.md` file that provides quick-reference instructions for AI agents operating on the VM. Compatible with exe.dev's AGENTS.md convention.

## Project Structure

```
agentic-obsidian/
├── install.sh              # Generic Linux installer
├── exe-install.sh          # exe.dev one-click installer
├── api/
│   ├── server.js           # HTTP API server (Node.js, zero deps)
│   └── package.json
├── config/
│   ├── obsidian.service    # systemd: Xvfb + Obsidian
│   └── obsidian-api.service # systemd: HTTP API
├── cron/
│   ├── heartbeat.sh        # 5-min heartbeat writer
│   └── vault-backup.sh     # Daily backup with rotation
├── integrations/
│   ├── ssh-pipe.sh         # SSH helper functions
│   └── slack-webhook.sh    # Slack notifications
├── AGENTS.md               # AI agent instructions
├── llms.txt                # LLM-readable docs
├── LICENSE                 # MIT
└── README.md
```

## Troubleshooting

### CLI says "Obsidian is not running"

Ensure the systemd service is active:

```bash
sudo systemctl status obsidian
sudo journalctl -u obsidian --no-pager -n 50
```

### Xvfb display issues

Check that `:99` is available:

```bash
ls /tmp/.X99-lock  # if exists, Xvfb is running
DISPLAY=:99 xdpyinfo  # should show display info
```

### API returns 401

Either set `API_TOKEN` in the service env, use the exe.dev proxy (auto-injects auth header), or access from localhost.

### "pkill obsidian" kills SSH sessions

The process name contains "obsidian" which matches SSH session names. Use:

```bash
pkill -f "squashfs-root/obsidian"  # targets only the Obsidian binary
```

## License

MIT
