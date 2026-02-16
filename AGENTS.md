# AGENTS.md — Agentic Obsidian

This VM runs a headless Obsidian instance with full CLI access.

## Quick Reference

All CLI commands require `DISPLAY=:99` prefix:
```
DISPLAY=:99 obsidian help
DISPLAY=:99 obsidian files
DISPLAY=:99 obsidian read file="note-name"
DISPLAY=:99 obsidian search query="search terms"
DISPLAY=:99 obsidian create name="New Note" content="# Title\nBody"
DISPLAY=:99 obsidian daily:append content="- [ ] Task" silent
DISPLAY=:99 obsidian tags all counts
```

## API Server

The HTTP API runs on port 3000. Endpoints:
- `GET /health` — service health check
- `GET /files` — list vault files
- `GET /read?file=X` — read a file
- `GET /search?q=X` — search vault
- `POST /create` — create file (JSON body: `{name, content}`)
- `POST /append` — append to file (JSON body: `{file, content}`)
- `POST /command` — run arbitrary CLI command (JSON body: `{command}`)

## Key Paths

- Vault: `~/obsidian-vault/`
- Obsidian binary: `/opt/obsidian/squashfs-root/obsidian`
- Config: `~/.config/obsidian/obsidian.json`
- API server: `/opt/obsidian/api/server.js`
- Heartbeat: `~/obsidian-vault/heartbeat.md`

## Services

```
sudo systemctl status obsidian       # Xvfb + Obsidian
sudo systemctl status obsidian-api   # HTTP API
```

## Important Notes

- The Obsidian app must be running for CLI commands to work.
- `heartbeat.md` is updated every 5 minutes via cron.
- Vault backups run daily at 3am to `/opt/obsidian/backups/`.
