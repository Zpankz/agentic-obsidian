# AGENTS.md — Agentic Obsidian

This VM runs a headless Obsidian instance with full CLI access.

## First-Time Setup

After `install.sh`, run `agent-setup.sh` to authenticate, upgrade to the insider CLI, and connect sync:

```bash
./agent-setup.sh --email <email> --password '<password>' --vault-name <name>
```

Or via env vars:
```bash
OBSIDIAN_EMAIL=<email> OBSIDIAN_PASSWORD='<password>' ./agent-setup.sh --vault-name <name>
```

## Quick Reference

All CLI commands require `DISPLAY=:99` prefix:
```
DISPLAY=:99 obsidian help
DISPLAY=:99 obsidian version
DISPLAY=:99 obsidian files
DISPLAY=:99 obsidian read file="note-name"
DISPLAY=:99 obsidian search query="search terms"
DISPLAY=:99 obsidian create name="New Note" content="# Title\nBody"
DISPLAY=:99 obsidian daily:append content="- [ ] Task" silent
DISPLAY=:99 obsidian tags all counts
DISPLAY=:99 obsidian sync:status
DISPLAY=:99 obsidian eval code="<javascript>"
```

## API Server

The HTTP API runs on port 3000.

### Core Endpoints
- `GET /health` — service health check
- `GET /files` — list vault files
- `GET /read?file=X` — read a file
- `GET /search?q=X` — search vault
- `POST /create` — create file (JSON body: `{name, content}`)
- `POST /append` — append to file (JSON body: `{file, content}`)
- `POST /command` — run arbitrary CLI command (JSON body: `{command}`)

### Graph Analytics Endpoints
- `GET /analytics/summary` — graph health: nodes, edges, clusters, orphans, weakest nodes
- `GET /analytics/graph` — full graph state (all nodes + edges + metadata)
- `GET /analytics/node?file=X` — single node analytics with neighborhood
- `POST /analytics/compute` — trigger full metric recomputation (PageRank, centrality, communities, priorities)
- `POST /traverse` — MCMC traversal: optimal reading order for a query (JSON body: `{query, max_nodes, temperature}`)
- `GET /read/smart?file=X` — file content + neighborhood analytics + suggested next reads

## Key Paths

| Path | Description |
|------|-------------|
| `$OBSIDIAN_VAULT` (default `~/obsidian-vault`) | Vault directory |
| `/opt/obsidian/squashfs-root/obsidian` | Obsidian binary |
| `~/.config/obsidian/obsidian.json` | App config (vaults, insider flag) |
| `~/.config/obsidian/obsidian-*.asar` | Insider build package |
| `~/.config/obsidian/obsidian.log` | App log (update status, errors) |
| `/opt/obsidian/api/server.js` | HTTP API server |

## Services

```
sudo systemctl status obsidian       # Xvfb + Obsidian headless
sudo systemctl status obsidian-api   # HTTP API
sudo systemctl restart obsidian      # Restart (picks up new .asar, token, etc.)
```

## Important Notes

- The Obsidian app must be running for CLI commands to work.
- `insider: true` in obsidian.json triggers auto-download of the 1.12+ beta .asar on startup.
- The account token singleton (`Vw`) only reads localStorage at startup — restart Obsidian after changing it.
- Sync host must be a bare hostname (e.g., `sync-49.obsidian.md`), never `wss://...`.
- `heartbeat.md` is updated every 5 minutes via cron.
- Vault backups run daily at 3am to `/opt/obsidian/backups/`.

## Graph Analytics & MCP Tools

### vault-graph MCP (port 3100)
HTTP MCP server providing 14 tools for vault graph analytics:

```bash
# Health check
curl http://localhost:3100/health

# List tools
curl -X POST http://localhost:3100/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

**Tools:**
- `graph_snapshot` — Full graph snapshot (PageRank, hubs, components, orphans)
- `graph_diff` — Diff between current state and last snapshot
- `graph_context` — Query-focused context for agent injection
- `graph_profile` — Markdown vault profile report
- `bases_query` — Query via .base files (obaq)
- `bases_eval` — Inline Bases YAML query evaluation
- `md_tree` — Heading tree analysis (treemd)
- `md_section` — Section extraction
- `obsidian_search` / `obsidian_read` / `obsidian_eval` — CLI passthrough
- `cross_vault_context` — Combined gkg + pkg context
- `vault_node_detail` — Single node deep analytics
- `snapshot_list` — List stored snapshots

### TurboVault MCP (port 3200)
Production Rust MCP server with 44 Obsidian vault tools:

```bash
curl -X POST http://localhost:3200/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

**Vaults registered:** gkg (default), pkg

### CLI Tools
- `obaq` — Obsidian Bases query processor (npm)
- `treemd` — Interactive markdown TUI viewer/extractor (cargo)
- `turbovault` — Rust MCP server binary (cargo)

### Context Injection
- `tools/context-inject.sh` — Generate vault graph context for agent prompts
- `tools/hook-session-orient.sh` — arscontexta hook wrapper
- Session-orient handler auto-injects graph stats + diff into agent bootstrap

### Services
```
sudo systemctl status vault-graph    # Graph analytics MCP (port 3100)
sudo systemctl status turbovault     # TurboVault MCP (port 3200)
```
