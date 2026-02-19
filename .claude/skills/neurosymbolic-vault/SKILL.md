---
name: neurosymbolic-vault
description: >
  Comprehensive skill for operating the pkg-gkg dual-vault neurosymbolic knowledge system.
  Integrates mdbase typing, TaskNotes, graph analytics, MCMC traversal, beads issue tracking,
  Atom-of-Thoughts decomposition, and gh-aw activity watching. Use when working on any vault
  content, study material, curriculum analysis, or knowledge graph operations.
version: 1.0.0
source: multi-repo-analysis
analyzed_repos: 32
---

# Neurosymbolic Vault Operations

Patterns extracted from the callumalpass/mdbase ecosystem (32 repos), integrated with
the agentic-obsidian infrastructure, beads project management, and AoT reasoning.

## When to Activate

- Working with Obsidian vault files (gkg or pkg)
- Creating, querying, or validating typed markdown
- Managing study tasks or curriculum content
- Running graph analytics or MCMC traversals
- Tracking work via beads issue tracker
- Decomposing complex reasoning with Atom-of-Thoughts
- Any operation touching frontmatter, wikilinks, or .base files

---

## 1. Dual-Vault Architecture

| Vault | Path | Purpose | Entity Types |
|-------|------|---------|-------------|
| **gkg** | `/home/exedev/gkg` | General Knowledge Graph — curriculum LOs, SAQs, exam evidence | lo, saq, index, concept, paper, saq-index, task |
| **pkg** | `/home/exedev/pkg` | Personal Knowledge Graph — agent identity, methodology, atomic notes, MOCs | knowledge, moc, layer, evidence, hub, ops, identity |

Both vaults have `mdbase.yaml` + `_types/` and are mdbase-spec v0.2.1 conformant.
Both sync via Obsidian Sync. Both have TurboVault MCP registration.

## 2. Tool Chain

### Core CLI Tools

| Tool | Binary | Purpose | Key Commands |
|------|--------|---------|-------------|
| **mdb** | `~/.local/bin/mdb` | Rust mdbase CLI — validate, query, CRUD, backfill | `mdb validate`, `mdb query --types lo --where '...'`, `mdb create --type saq` |
| **mdbase-lsp** | `~/.local/bin/mdbase-lsp` | LSP server — diagnostics, completions, hover, go-to-def | Editor integration (neovim/vscode) |
| **mtn** | npm global | Standalone task CLI (reads/writes .md directly) | `mtn list`, `mtn create`, `mtn complete`, `mtn timer start` |
| **tn** | npm global | TaskNotes HTTP API client (needs Obsidian running) | `tn list`, `tn create`, `tn complete` |
| **obaq** | npm global | Obsidian Bases query processor | `obaq -d /vault -e '@file.base' -f json` |
| **treemd** | cargo | Markdown heading tree analysis | `treemd file.md`, section extraction |
| **turbovault** | cargo | Rust MCP server (44 tools) | Via HTTP on port 3200 |
| **br** | `~/.local/bin/br` | Beads issue tracker (Rust) | `br create`, `br list`, `br ready`, `br close` |
| **bv** | `~/.local/bin/bv` | Beads TUI viewer + triage | `bv`, `bv --robot-triage` |
| **ntm** | `~/.local/bin/ntm` | Named Tmux Manager for multi-agent sessions | `ntm spawn`, `ntm send`, `ntm palette` |
| **gh aw** | gh extension | GitHub Activity Watch | `gh aw` |

### MCP Servers

| Server | Port | Tools | Purpose |
|--------|------|-------|---------|
| **vault-graph** | 3100 | 19 | Graph analytics, .base queries, section extraction, pex interview |
| **turbovault** | 3200 | 44 | Full vault CRUD, health analysis, link graph, search, templates |
| **atom-of-thoughts** | stdio | 3 | AoT reasoning decomposition (premise→reasoning→hypothesis→verification→conclusion) |
| **obsidian-api** | 3000 | REST | HTTP wrapper around Obsidian CLI |

### MCP Tool Quick Reference

```bash
# Vault-graph MCP (port 3100)
curl -X POST http://localhost:3100/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"graph_snapshot","arguments":{}}}'

# TurboVault MCP (port 3200)
curl -X POST http://localhost:3200/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"full_health_analysis","arguments":{}}}'
```

## 3. mdbase-spec Compliance Rules

### Type Definitions

- Types live in `_types/*.md` — frontmatter IS the schema, body is docs
- `name` field MUST match filename (without .md)
- All types extend `graph-node` (base type with computed analytics fields)
- `match.where.entityType` auto-associates files without explicit `type:` key
- `strict: false` allows unknown fields (critical for graph-computed properties)

### Writing Frontmatter

1. **NEVER write bare `field:`** — use `field: null` or omit entirely
2. **Quote wikilinks in YAML**: `section: "[[E_respiratory-system]]"`
3. **Lists use YAML arrays**: `saq.direct: ["[[AP23B14]]", "[[AP22A06]]"]`
4. **Defaults apply only to MISSING fields**, not null fields
5. **Empty string `""` is distinct from null**
6. **Do NOT manually set** computed graph fields (pagerank, eigenvector_centrality, etc.)

### Validation

```bash
# Validate entire vault
cd /home/exedev/gkg && mdb validate

# Validate single file
mdb validate LO/ANZCA/E_respiratory-system/E2_respiratory-physiology/APE2i_different-modes.md

# Query with type filtering
mdb query --types lo --where 'college == "ANZCA" && complexity >= 2' --limit 10
```

## 4. MCMC Traversal Protocol

The knowledge graph supports Markov Chain Monte Carlo traversal for optimal
learning order. This is the core neurosymbolic reasoning loop:

### Protocol

1. **Snapshot** — `GET /analytics/summary` → graph health, cluster count, orphans
2. **Decompose** (AoT) — Break complex query into atomic sub-questions
3. **Traverse** — `POST /traverse` with `{"query": "...", "max_nodes": 8, "temperature": 0.7}`
4. **Read** — For each node: `GET /read/smart?file=X` → content + neighborhood + suggested_next
5. **Contract** (AoT) — Synthesize answers, update confidence, check termination
6. **Persist** — Write insights to pkg vault, update graph analytics

### Eigenbase Exploration vs Exploitation

- **Exploration** (high temperature): Follow low-confidence, high-PageRank paths
  → discover unknown unknowns, map new territory
- **Exploitation** (low temperature): Follow high-priority, low-pass-rate paths
  → strengthen weak nodes, fill Delta-Miss gaps
- **Invariant eigenbasis**: LO nodes are the fixed curriculum requirements;
  their PageRank + eigenvector centrality define the importance landscape
- **MCMC proposal**: Each traversal step proposes a next node weighted by
  `priority_score * (1/staleness_days) * temperature_factor`

## 5. Atom-of-Thoughts Integration

AoT decomposes complex vault queries into a DAG of atomic thought units:

| Atom Type | Role | Vault Analog |
|-----------|------|--------------|
| `premise` | Starting assumptions | Known LO content, SAQ evidence |
| `reasoning` | Logical derivation | Cross-reference analysis |
| `hypothesis` | Candidate answer | Proposed knowledge claim |
| `verification` | Evidence check | SAQ pass rates, examiner commentary |
| `conclusion` | Final synthesis | New pkg note with confidence score |

### Usage Pattern

```
User query: "How does sevoflurane affect CVS and what SAQs test this?"

AoT Decomposition:
  premise_1: Sevoflurane is a volatile agent (pharmacology domain)
  premise_2: CVS = cardiovascular system effects
  reasoning_1: Query gkg for LOs matching volatile + CVS [deps: premise_1, premise_2]
  reasoning_2: Find SAQs linked to those LOs [deps: reasoning_1]
  hypothesis_1: Sevoflurane CVS effects cluster around [nodes] [deps: reasoning_1]
  verification_1: Check pass rates and examiner commentary [deps: reasoning_2]
  conclusion_1: Synthesize with confidence score [deps: hypothesis_1, verification_1]
```

Each atom carries `confidence: 0-1`, `dependencies[]`, `verified: bool`, `depth: int`.
The Markov property ensures each state is self-contained.

## 6. Beads Workflow

All work in this repo is tracked via beads:

```bash
# Find available work
br ready

# Create an issue
br create --title "Add concept type definitions" --label mdbase --label types

# Claim and work
br update <id> --status in_progress

# Complete
br close <id>

# Triage (TUI)
bv

# Robot triage (for automation)
bv --robot-triage --triage-limit=20
```

### Landing the Plane

When ending a session:
1. File issues for remaining work: `br create`
2. Update issue status: `br close` / `br update`
3. Sync and push: `br sync && git push`
4. Verify: `git status` shows clean

## 7. gh-aw Integration

```bash
# Watch activity across all repos
gh aw

# Filter to specific patterns
gh aw --filter mdbase
```

gh-aw provides cross-repository activity awareness for coordinating
work across the ecosystem repos.

## 8. .base File Patterns

`.base` files define database views over vault content. They use the same
expression language as mdbase queries:

```yaml
# Example: High-priority Delta-Miss LOs
filters:
  and:
    - file.hasProperty("entityType")
    - 'entityType == "lo"'
    - 'delta_class == "Delta-Miss"'
formulas:
  urgency: 'priority_score * (1 / (staleness_days + 1))'
views:
  - type: table
    name: "Study Priority"
    order:
      - formula.urgency
      - note.title
      - note.complexity
      - note.passRate
    sort:
      - property: formula.urgency
        direction: DESC
```

Query .base files headlessly:
```bash
obaq -d /home/exedev/gkg -e '@LO/lo.base' -f json
```

## 9. Session Rhythm

### Orient
1. Read `pkg/self/identity.md`, `pkg/self/methodology.md`, `pkg/self/goals.md`
2. `GET /analytics/summary` — graph health
3. `br ready` — available work
4. `bv --robot-triage` — priority assessment

### Work
1. Decompose query with AoT if complex
2. MCMC traverse for relevant nodes
3. Create/update typed content following mdbase-spec
4. Validate: `mdb validate`
5. Track via beads: `br update`

### Persist
1. Write insights as atomic notes to pkg vault
2. `POST /analytics/compute` — refresh graph metrics
3. Update beads: `br close` / `br create` for follow-ups
4. Commit and push: `git add -A && git commit && git push`

## 10. Key Paths

| Path | Description |
|------|-------------|
| `/home/exedev/gkg` | GKG vault root |
| `/home/exedev/gkg/mdbase.yaml` | GKG collection config |
| `/home/exedev/gkg/_types/` | GKG type definitions (lo, saq, index, concept, paper, saq-index, graph-node, task) |
| `/home/exedev/gkg/LO/` | Learning Objectives (557 files) |
| `/home/exedev/gkg/SAQ/` | Short Answer Questions (1674 files) |
| `/home/exedev/gkg/TaskNotes/` | Task views (.base files) |
| `/home/exedev/pkg` | PKG vault root |
| `/home/exedev/pkg/self/` | Agent identity, methodology, goals |
| `/home/exedev/pkg/notes/` | Atomic knowledge notes + MOCs |
| `/home/exedev/pkg/ops/` | Operational coordination |
| `/home/exedev/agentic-obsidian/ecosystem/` | 32 cloned ecosystem repos |
| `/home/exedev/agentic-obsidian/.beads/` | Beads issue tracker DB |
