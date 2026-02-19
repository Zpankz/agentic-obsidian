# AGENTS.md — Agentic Obsidian

This VM runs a headless Obsidian instance with full CLI access, operating a
**dual-vault neurosymbolic knowledge system** (gkg + pkg) with mdbase-spec
typing, MCMC graph traversal, and Atom-of-Thoughts decomposition.

All vault content is **typed and validated** against mdbase-spec v0.2.1.
All work is tracked via **beads** (`br`). All reasoning leverages **AoT** for
structured decomposition and **MCMC traversal** for optimal exploration order.

---

## First-Time Setup

After `install.sh`, run `agent-setup.sh` to authenticate, upgrade to the insider CLI, and connect sync:

```bash
./agent-setup.sh --email <email> --password '<password>' --vault-name <name>
```

---

## Dual-Vault Architecture

| Vault | Path | Purpose | Types |
|-------|------|---------|-------|
| **gkg** | `/home/exedev/gkg` | General Knowledge Graph — curriculum LOs, SAQs, exam evidence | lo, saq, index, concept, paper, saq-index, task |
| **pkg** | `/home/exedev/pkg` | Personal Knowledge Graph — identity, methodology, atomic notes, MOCs | knowledge, moc, layer, evidence, hub, identity |

Both vaults have `mdbase.yaml` + `_types/` (mdbase-spec v0.2.1 conformant).
All types extend `graph-node` which carries computed analytics (PageRank, eigenvector
centrality, cluster_id, delta_class, priority_score, staleness_days).

---

## Tool Chain

### Core CLI (all require appropriate working directory or `-C` flag)

| Tool | Purpose | Install |
|------|---------|---------|
| `mdb` | Rust mdbase CLI — validate, query, CRUD, backfill, migrate | `~/.local/bin/mdb` |
| `mdbase-lsp` | LSP server — diagnostics, completions, hover, go-to-def | `~/.local/bin/mdbase-lsp` |
| `mtn` | Standalone task CLI (reads/writes .md directly, no Obsidian needed) | npm global |
| `tn` | TaskNotes HTTP API client (needs Obsidian running) | npm global |
| `obaq` | Obsidian Bases query processor (.base files) | npm global |
| `treemd` | Markdown heading tree analysis + section extraction | cargo |
| `turbovault` | Rust MCP server (44 vault tools) | cargo |
| `br` | Beads issue tracker (Rust) | `~/.local/bin/br` |
| `bv` | Beads TUI viewer + triage engine | `~/.local/bin/bv` |
| `ntm` | Named Tmux Manager for multi-agent orchestration | `~/.local/bin/ntm` |
| `gh aw` | GitHub Activity Watch (cross-repo awareness) | gh extension |

### Obsidian CLI (all require `DISPLAY=:99`)

```bash
DISPLAY=:99 obsidian help
DISPLAY=:99 obsidian files
DISPLAY=:99 obsidian read file="note-name"
DISPLAY=:99 obsidian search query="search terms"
DISPLAY=:99 obsidian create name="New Note" content="# Title\nBody"
DISPLAY=:99 obsidian daily:append content="- [ ] Task" silent
DISPLAY=:99 obsidian tags all counts
DISPLAY=:99 obsidian sync:status
DISPLAY=:99 obsidian eval code="<javascript>"
```

### MCP Servers

| Server | Port | Protocol | Tools | Purpose |
|--------|------|----------|-------|---------|
| **obsidian-api** | 3000 | REST | ~15 | HTTP wrapper around Obsidian CLI + graph analytics |
| **vault-graph** | 3100 | JSON-RPC | 19 | Graph snapshots, .base queries, pex interview, context injection |
| **turbovault** | 3200 | JSON-RPC | 44 | Full vault CRUD, health analysis, link graph, search, templates |
| **atom-of-thoughts** | stdio | JSON-RPC | 3 | AoT reasoning: decompose → contract → conclude |

---

## mdbase-spec Enforcement

### Validation

```bash
# Validate entire gkg vault (2557 files)
cd /home/exedev/gkg && mdb validate

# Validate single file
mdb validate LO/ANZCA/E_respiratory-system/E2_respiratory-physiology/APE2i_different-modes.md

# Query typed content
mdb query --types lo --where 'college == "ANZCA" && complexity >= 2' --limit 10
mdb query --types saq --where 'passRate < 40 && year >= 2020' --limit 20
```

### Type Definitions (gkg)

| Type | Files | Match Rule | Key Fields |
|------|-------|------------|------------|
| `graph-node` | base | (inherited) | pagerank, eigenvector_centrality, cluster_id, delta_class, priority_score |
| `lo` | 557 | `entityType: lo` | college, action, complexity, saq.direct, lo.mapped, section hierarchy |
| `saq` | 1674 | `entityType: SAQ` | college, year, sitting, passRate, lo.direct, ec.expected, histogram |
| `index` | 316 | `entityType: index` | section codes, college |
| `concept` | 5 | `entityType: concept` | topics, related links |
| `paper` | 2 | `entityType: paper` | authors, doi, year |
| `saq-index` | 2 | `entityType: SAQ-Index` | college, year, sitting |
| `task` | — | `tags contains task` | status, priority, due, contexts, projects, timeEntries |

### Frontmatter Rules

1. **NEVER write bare `field:`** — use `field: null` or omit
2. **Quote wikilinks**: `section: "[[E_respiratory-system]]"`
3. **Do NOT manually set** computed fields (pagerank, eigenvector_centrality, etc.)
4. **Validate after any schema change**: `mdb validate`
5. **Type names are lowercase** in `_types/` filenames
6. **`match.where.entityType`** auto-associates files (no explicit `type:` key needed)

---

## MCMC Traversal & Neurosymbolic Reasoning

### Invariant Eigenbase Model

The knowledge graph has an **invariant eigenbasis** defined by:
- **LO nodes**: Fixed curriculum requirements (the eigenvalues)
- **SAQ nodes**: Empirical measurements (the observations)
- **Concept nodes**: Cross-cutting invariants (the eigenvectors)

PageRank computes the **stationary distribution** of a random walk on this graph.
Eigenvector centrality identifies nodes whose importance is amplified by their
neighbors' importance. Together they define the importance landscape.

### Exploration vs Exploitation

| Mode | Temperature | Strategy | Target |
|------|-------------|----------|---------|
| **Explore** | > 0.7 | High-PageRank, low-confidence paths | Unknown unknowns |
| **Exploit** | < 0.3 | High-priority, low-pass-rate paths | Delta-Miss gaps |
| **Balance** | 0.3–0.7 | Priority-weighted MCMC proposals | Optimal learning order |

### Traversal Protocol

```bash
# 1. Snapshot current state
curl http://localhost:3000/analytics/summary

# 2. MCMC traversal for a query
curl -X POST http://localhost:3000/traverse \
  -H 'Content-Type: application/json' \
  -d '{"query": "volatile agent pharmacology", "max_nodes": 8, "temperature": 0.5}'

# 3. Smart read with neighborhood
curl 'http://localhost:3000/read/smart?file=APE2i_different-modes'

# 4. Trigger full recomputation
curl -X POST http://localhost:3000/analytics/compute
```

---

## Atom-of-Thoughts (AoT) Integration

AoT decomposes complex reasoning into a Markov chain of atomic states:

| Atom Type | Purpose | Vault Analog |
|-----------|---------|-------------|
| `premise` | Starting facts | Known LO content, SAQ evidence |
| `reasoning` | Logical derivation | Cross-reference analysis |
| `hypothesis` | Candidate answer | Proposed knowledge claim |
| `verification` | Evidence check | Pass rates, examiner commentary |
| `conclusion` | Final synthesis | New pkg note with confidence |

**MCP Tools:**
- `AoT` — Full reasoning chain (depth up to 5)
- `AoT-light` — Fast mode (depth 3, early conclusion)
- `atomcommands` — Control decomposition/contraction/termination

Each atom carries: `confidence` (0–1), `dependencies[]`, `verified`, `depth`.
The Markov property ensures each state is self-contained — resolved history
is discarded, preventing error accumulation.

**Config** (`~/.config/claude/mcp_servers.json` or equivalent):
```json
{
  "atom-of-thoughts": {
    "command": "node",
    "args": ["/home/exedev/agentic-obsidian/ecosystem/atom-of-thoughts/build/index.js"]
  }
}
```

---

## Beads Project Tracking

This repo uses **beads** (`br`) for issue tracking:

```bash
br ready              # Find available work
br show <id>          # View issue details
br update <id> --status in_progress  # Claim work
br close <id>         # Complete work
br sync               # Sync with git
bv                    # TUI viewer
bv --robot-triage     # Machine-readable priority analysis
```

### Landing the Plane (Session Completion)

**MANDATORY WORKFLOW:**
1. File issues for remaining work: `br create`
2. Run quality gates: `mdb validate` (if vault content changed)
3. Update issue status: `br close` / `br update`
4. **PUSH TO REMOTE**:
   ```bash
   git pull --rebase
   br sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. Verify: all changes committed AND pushed

---

## gh-aw Activity Watch

```bash
gh aw                 # Cross-repo activity dashboard
gh aw --filter mdbase # Filter to ecosystem repos
```

Use gh-aw for cross-repository coordination when working across the
32 ecosystem repos in `/home/exedev/agentic-obsidian/ecosystem/`.

---

## .base File Queries

Obsidian Bases `.base` files define database views. Query them headlessly:

```bash
# Run a .base query
obaq -d /home/exedev/gkg -e '@LO/lo.base' -f json

# Inline query
obaq -d /home/exedev/gkg -e 'filters: "entityType == \"lo\" && complexity >= 2"' -f json

# Via vault-graph MCP
curl -X POST http://localhost:3100/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"bases_query","arguments":{"path":"LO/lo.base"}}}'
```

---

## TaskNotes (mtn / tn)

### mtn (standalone — preferred for headless)

```bash
mtn list                           # List all tasks
mtn create "Review Delta-Miss LOs" # Create task
mtn complete <ref>                 # Mark done
mtn timer start <ref>              # Start time tracking
mtn stats                          # Task statistics
```

`mtn` reads/writes markdown files directly via the mdbase library.
No Obsidian required. Task schema is defined in `gkg/_types/task.md`.

### tn (HTTP client — when Obsidian is running)

```bash
tn list                            # List via plugin API
tn create "Review pharmacology"    # Create via API
tn pomodoro start <id>             # Pomodoro timer
```

---

## Session Rhythm: Orient → Work → Persist

### 1. Orient

```bash
# Graph health
curl http://localhost:3000/analytics/summary

# Available work
br ready

# Priority triage
bv --robot-triage --triage-limit=10

# Recent changes (gh-aw)
gh aw --filter agentic-obsidian
```

### 2. Work

1. **Decompose** complex queries with AoT (`atomcommands: decompose`)
2. **Traverse** via MCMC (`POST /traverse`)
3. **Read** with context (`GET /read/smart?file=X`)
4. **Create/update** typed content (follow mdbase frontmatter rules)
5. **Validate**: `cd /home/exedev/gkg && mdb validate`
6. **Track**: `br update <id> --status in_progress`

### 3. Persist

1. Write insights as atomic notes to pkg (`pkg/notes/`)
2. Refresh graph: `POST /analytics/compute`
3. Close beads: `br close <id>`
4. Commit and push: `git add -A && git commit -m "..." && git push`

---

## API Server (Port 3000)

### Core Endpoints
- `GET /health` — service health check
- `GET /files` — list vault files
- `GET /read?file=X` — read a file
- `GET /search?q=X` — search vault
- `POST /create` — create file (`{name, content}`)
- `POST /append` — append to file (`{file, content}`)
- `POST /command` — run arbitrary CLI command (`{command}`)

### Graph Analytics Endpoints
- `GET /analytics/summary` — graph health: nodes, edges, clusters, orphans, weakest nodes
- `GET /analytics/graph` — full graph state (all nodes + edges + metadata)
- `GET /analytics/node?file=X` — single node analytics with neighborhood
- `POST /analytics/compute` — trigger full metric recomputation
- `POST /traverse` — MCMC traversal: optimal reading order (`{query, max_nodes, temperature}`)
- `GET /read/smart?file=X` — file content + neighborhood analytics + suggested next reads

---

## Services

```bash
sudo systemctl status obsidian       # Xvfb + Obsidian headless
sudo systemctl status obsidian-api   # HTTP API (port 3000)
sudo systemctl status vault-graph    # Graph analytics MCP (port 3100)
sudo systemctl status turbovault     # TurboVault MCP (port 3200)
sudo systemctl restart obsidian      # Restart (picks up new .asar, token, etc.)
```

---

## Ecosystem Reference

32 repos from `callumalpass` cloned to `ecosystem/`:

| Category | Repos | Key Tools |
|----------|-------|-----------|
| **mdbase core** | mdbase-spec, mdbase, mdbase-rs, mdbase-lsp, mdbase-cli, mdbase-skill | `mdb`, `mdbase-lsp`, spec docs |
| **TaskNotes** | tasknotes, mdbase-tasknotes, tasknotes-cli, tasknotes-nlp-core | `mtn`, `tn`, NLP parser |
| **Reading/Bib** | pulp, obsidian-biblib, biblib-cli, handwrite, inkwell | PDF reader, bibliography, OCR |
| **Obsidian plugins** | obsidian-pdf-view-sync, obsidian-template-filename, obsidian-notes-explorer | Vault UI |
| **AI/DevOps** | ops, clump, ai-issue-analyzer, psb | Agent tooling |

Full map: `ecosystem/ECOSYSTEM_MAP.md`

---

## Key Paths

| Path | Description |
|------|-------------|
| `$OBSIDIAN_VAULT` (default `~/obsidian-vault`) | Vault directory |
| `/opt/obsidian/squashfs-root/obsidian` | Obsidian binary |
| `~/.config/obsidian/obsidian.json` | App config |
| `/opt/obsidian/api/server.js` | HTTP API server |
| `/home/exedev/gkg/mdbase.yaml` | GKG collection config |
| `/home/exedev/gkg/_types/` | GKG type definitions |
| `/home/exedev/pkg/` | PKG vault |
| `/home/exedev/agentic-obsidian/ecosystem/` | 32 ecosystem repos |
| `/home/exedev/agentic-obsidian/.beads/` | Beads issue tracker |
| `/home/exedev/agentic-obsidian/.claude/skills/neurosymbolic-vault/SKILL.md` | Integrated skill |
