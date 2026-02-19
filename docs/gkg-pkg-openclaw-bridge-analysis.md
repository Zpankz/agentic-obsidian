# GKG → PKG → OpenClaw Bridge Architecture

## Overview

Three systems form a knowledge pipeline:

1. **GKG** (`/home/exedev/gkg/`) — The **Ground-truth Knowledge Graph**. A 2,561-file Obsidian vault containing structured ANZCA/CICM Primary exam data: Learning Outcomes (LOs), SAQs with examiner comments, and cross-college mappings. Uses `mdbase-spec` `.base` files for typed collections.

2. **PKG** (`/home/exedev/pkg/`) — The **Personal Knowledge Graph**. An Ars Contexta vault operated by OpenClaw's agent ("Enty"). Contains the agent's identity, methodology, session state, and derived knowledge notes. This is OpenClaw's `workspace`.

3. **OpenClaw** (`~/.openclaw/openclaw.json`) — The **agent orchestration platform**. Runs hooks, manages sessions, connects to MCP servers, and provides the agent runtime. Its workspace is set to `/home/exedev/pkg`.

## Data Flow: GKG → PKG → OpenClaw

```
┌─────────────────────────────────────────────────────────────┐
│  GKG vault (/home/exedev/gkg)                               │
│  2,561 files: LO/ANZCA/*, LO/CICM/*, SAQ/ANZCA/*, SAQ/CICM/*│
│  Schema: lo.base, saq.base (mdbase-spec typed collections)  │
│  Obsidian running: port via Xvfb, heartbeat every 5min      │
└───────────────┬─────────────────────────────────────────────┘
                │
                │  (1) Obsidian Sync + localhost API
                │      Both vaults run in same Obsidian instance
                │      API at http://localhost:3000
                ▼
┌─────────────────────────────────────────────────────────────┐
│  agentic-obsidian (/home/exedev/agentic-obsidian)           │
│  HTTP API server (api/server.js) on port 3000               │
│  Endpoints: /health, /read, /read/smart, /analytics/*,      │
│             /traverse (MCMC), /analytics/compute, /dashboard │
│  Cron: heartbeat.sh (5min), vault-backup.sh (daily 3am)     │
│  Graph analytics engine using Obsidian's metadataCache      │
└───────────────┬─────────────────────────────────────────────┘
                │
                │  (2) MCP Server: "vault-obsidian"
                │      type: http, url: http://localhost:3000
                ▼
┌─────────────────────────────────────────────────────────────┐
│  OpenClaw (~/.openclaw/openclaw.json)                        │
│  Agent workspace: /home/exedev/pkg                          │
│  Hooks: arscontexta-openclaw (4 hooks)                      │
│  MCP: vault-obsidian + 14 other servers                     │
│  Models: gpt-5.3-codex-spark, claude-opus-4-6-thinking      │
│  Channels: Telegram bot                                     │
│  Gateway: ws://127.0.0.1:18789                              │
└───────────────┬─────────────────────────────────────────────┘
                │
                │  (3) Agent sessions operate on PKG
                ▼
┌─────────────────────────────────────────────────────────────┐
│  PKG vault (/home/exedev/pkg)                               │
│  .arscontexta marker → hooks fire here                      │
│  self/ — identity, methodology, goals                       │
│  notes/ — derived knowledge graph (MOCs, nodes, hub)        │
│  ops/ — sessions, methodology, templates, scripts           │
│  memory/ — daily logs                                       │
│  Synced via Obsidian Sync (remote: 4282ab758aa8...)         │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

---

### 1. GKG Vault Structure

**Location:** `/home/exedev/gkg/`  
**Size:** 2,561 files, 180 MB  
**Purpose:** Structured exam knowledge — the "ground truth" that PKG compares against  
**No `.arscontexta` marker** — not managed by Ars Contexta hooks  

#### Directory Layout
```
gkg/
├── AGENTS.md          # Uses `bd` (beads) issue tracking
├── distribution.md    # SAQ topical quotas per exam sitting
├── heartbeat.md       # Auto-updated every 5 min
├── LO/                # Learning Outcomes
│   ├── lo.base        # mdbase-spec schema (formulas, properties, views)
│   ├── ANZCA/         # ~800+ files, hierarchical by section
│   │   ├── E_respiratory-system/E2_respiratory-physiology/
│   │   ├── L_pain/L3_pain-pharmacology/
│   │   └── ... (sections A-V)
│   └── CICM/          # Similar structure
├── SAQ/               # Short Answer Questions  
│   ├── saq.base       # mdbase-spec schema
│   ├── ANZCA/         # ~1500+ files, by sitting (AP00A-AP24B)
│   │   ├── AP24B/AP24B01.md  # Individual SAQ with full metadata
│   │   └── ...
│   └── CICM/          # Similar (CP* prefix)
├── TaskNotes/         # Task management plugin
│   └── Views/         # .base view definitions
└── _types/            # Type definitions (task.md)
```

#### LO Schema (lo.base)
```yaml
# Key formulas:
id: if(title, title, file.name)
sectionPath: section.code + "." + section.sub.code + ...
verbCategory: Basic|Intermediate|Advanced|Other
complexityLabel: Low|Medium|High
mappingConfidence: High(≥0.7)|Medium(≥0.5)|Low(>0)|None
# Cross-referencing:
relatedLOCount, relatedSAQCount, hasCrossCollege, hasDirectRelations
```

#### SAQ Schema (saq.base)
```yaml
# Key formulas:
id: college + "-" + year + "-" + sitting + "-" + question
passRateTier: High(≥60%)|Medium(40-59%)|Low(<40%)
difficulty: Easy(≥50%)|Moderate(30-49%)|Hard(<30%)
# Examiner comments fields:
ec.expected, ec.errors, ec.extra
# Cross-references:
lo.direct, elo.indirect, saq.direct, saq.indirect
```

#### Sample SAQ File (AP24B01.md)
```yaml
title: "Explain how the transfer of oxygen between alveoli..."
entityType: SAQ
college: ANZCA
year: 2024
sitting: B
passRate: 55
lo.direct: ["[[APE2xviii]]"]
elo.indirect: ["[[CPC2ii]]", "[[CPC7iii]]", ...]
saq.direct: ["[[AP99A01]]", "[[AP22B08]]", ...]
ec.expected:
  - understanding the factors which influence diffusion
  - effect of pathology
  - effect of altitude
ec.extra:
  - more detail including numerical values
```

---

### 2. PKG Vault Structure

**Location:** `/home/exedev/pkg/`  
**Size:** 54 files, 2 MB  
**Purpose:** Agent's personal knowledge graph — derived from GKG + user interaction  
**Has `.arscontexta` marker** — all 4 Ars Contexta hooks fire here  

#### Directory Layout
```
pkg/
├── .arscontexta           # Vaultguard marker (hooks only fire if this exists)
├── .openclaw/
│   └── workspace-state.json  # {version:1, bootstrapSeeded, onboardingCompleted}
├── AGENTS.md              # Master operational guide (Obsidian + Ars Contexta + Graph Analytics)
├── SOUL.md                # Agent personality ("not a chatbot, becoming someone")
├── IDENTITY.md            # Enty = Entelogontiel, void-dove, chain of reflection
├── USER.md                # Hani Mikhail — philosophical, theological
├── TOOLS.md               # Local environment cheat sheet
├── HEARTBEAT.md           # Agent heartbeat config (currently empty)
├── heartbeat.md           # Auto-updated system health (obsidian, xvfb, api status)
├── self/
│   ├── identity.md        # ANZCA/CICM Knowledge Graph Steward, dialectical architect
│   ├── methodology.md     # Graph ontology, 6-Rs loop, fractal schema, priority scoring
│   └── goals.md           # 6-day sprint: topology completion, gap closure, daily sprints
├── notes/
│   ├── 00-hub.md          # Top-level knowledge map hub
│   ├── inbox.md           # Raw capture (SAQ data seeded)
│   └── mocs/              # Maps of Content
│       ├── anzca-primary-hub.md
│       ├── cicm-primary-hub.md
│       ├── ground-truth-topology.md
│       ├── diff-dashboard.md           # Gap & Priority Dashboard
│       ├── evidence-saq-aggregate-2026-02.md
│       ├── exam-evidence-layer.md
│       ├── examiner-threshold-layer.md
│       ├── definition-precision-layer.md
│       ├── node-*.md                   # Individual knowledge nodes (5 files)
│       └── system-documentation.md
├── ops/
│   ├── sessions/
│   │   ├── current.json               # {sessionId:null, status:"fresh-vault"}
│   │   └── 2026-02-18-sprint-01.md
│   ├── methodology/
│   │   ├── graph-workflow.md
│   │   ├── multi-agent-protocol.md    # Navigator/Evaluator/Auditor pattern
│   │   ├── priority-calibration.md
│   │   └── traversal-protocol.md      # MCMC-based graph navigation
│   ├── observations/
│   ├── tensions/
│   ├── research/                      # SAQ data, Notion imports
│   ├── scripts/                       # graph-analytics.js, generate-tree-headers.js
│   ├── templates/                     # note-node, edge, gap, saq, examiner-comment
│   └── audit-report-2026-02-19.md
├── memory/
│   ├── 2026-02-16.md
│   ├── 2026-02-18.md
│   └── 2026-02-19.md
└── .obsidian/                         # Obsidian config (sync enabled)
```

#### Key PKG Concepts

**Graph Ontology (from methodology.md):**
- **Node Types:** Domain, Principle, Application, Syntax, Meta
- **Edge Types:** requires, causes, modulates, prevents, mapped_to_exam_signal, confidence_gap
- **Delta Classes:** Delta-Miss (absent), Delta-Weak (low confidence), Delta-Salt (overlearned), Delta-Noise (bad phrasing)

**Computed Properties (auto-injected by cron every 30 min):**
```yaml
node_type: knowledge|moc|layer|evidence|hub|template|ops|identity|memory|system
domain: [hierarchical list]
confidence: 0.0-1.0
priority_score: exam_weight×0.5 + difficulty×0.2 + recency×0.15 + conf_gap×0.15
pagerank: link-flow importance
eigenvector_centrality: neighbor-importance
cluster_id: community label
delta_class: Delta-Miss|Delta-Weak|Delta-Salt|Delta-Noise
in_degree / out_degree: link counts
staleness_days: days since last edit
```

**Priority Formula:**
```
Priority = (ExamWeight × 0.50) + (DifficultyWeight × 0.20) + (RecencyWeight × 0.15) + (ConfidencePenalty × 0.15)
```

---

### 3. Ars Contexta Hook System

**Source:** `/home/exedev/arscontexta-openclaw/`  
**Version:** 0.8.0  
**Installed as:** OpenClaw hook pack via `openclaw hooks install`  

#### Hook Architecture

All hooks:
1. Check for `.arscontexta` marker file in workspace
2. Skip silently if not found (safe for non-vault workspaces)
3. Get workspace from `event.context.workspace.dir` or `event.context.workspaceDir` or `process.cwd()`
4. Push messages to `event.messages[]` to communicate with the agent

| Hook | Event | Handler |
|------|-------|---------|
| **session-orient** 🧭 | `agent:bootstrap` | Injects vault tree, identity, methodology, goals, previous session state, methodology notes, maintenance signals |
| **write-validate** ✅ | `command:*` | Scans `notes/` and `thinking/` for .md files modified in last 5 min; checks YAML frontmatter for required `description` + `topics` fields |
| **auto-commit** 💾 | `session:end` | `git add -A` → `git diff --cached --stat` → `git commit` with descriptive message including session ID and file count |
| **session-capture** 📸 | `command:new`, `session:end` | Writes/rotates `ops/sessions/current.json`; archives timestamped copies; auto-commits session artifacts |

#### Session Orient Detail (the big one)

At agent bootstrap, assembles orientation text from:
1. **Vault tree** — `collectTree(workspace, '', 0, 3)` — 3 levels deep, .md files only
2. **Identity** — `self/identity.md`
3. **Methodology** — `self/methodology.md`  
4. **Goals** — `self/goals.md` (fallback: `ops/goals.md`)
5. **Previous session** — `ops/sessions/current.json` (timestamp, summary, topics, open threads)
6. **Recent methodology** — last 5 by mtime from `ops/methodology/`
7. **Maintenance signals** — observations >20, tensions >10, sessions >15, inbox >0

All injected into `event.messages[]` as a single markdown document.

#### Write Validate Detail

Required frontmatter fields for notes:
```yaml
description: "Brief summary"
topics: [topic-a, topic-b]
```
- Recency window: 5 minutes
- Watched dirs: `notes/`, `thinking/`
- Warnings pushed to agent message stream

#### Init Script

`scripts/init-vault.sh` creates:
- `.arscontexta` marker
- `self/identity.md`, `self/methodology.md`, `self/goals.md` (with defaults)
- `ops/sessions/current.json` (fresh-vault state)
- `notes/`, `ops/inbox/`, `ops/methodology/`, `ops/observations/`, `ops/tensions/`
- `.gitignore`, `git init`, initial commit

#### Setup Skill

`skills/setup.md` is a 6-phase conversational onboarding:
1. Introduction (3 starting points: Research, Personal, Experimental)
2. Understanding (2-4 turns: domain, purpose, volume, style)
3. Derivation (8 dimensions: atomicity, link density, processing depth, schema strictness, automation, self-space, MOC granularity, temporal focus)
4. Proposal (present config in user's domain vocabulary)
5. Generation (customize identity, methodology, goals, templates, MOCs, AGENTS.md)
6. Validation (15 kernel primitives checklist)

---

### 4. OpenClaw Configuration

**Config:** `~/.openclaw/openclaw.json`  
**Version:** 2026.2.15  
**CLI:** `/home/exedev/.npm-global/bin/openclaw`

#### Key Settings

```json
{
  "agents.defaults.workspace": "/home/exedev/pkg",
  "agents.defaults.model.primary": "openai-codex/gpt-5.3-codex-spark",
  "agents.defaults.maxConcurrent": 4,
  "agents.defaults.subagents.maxConcurrent": 8,
  "agents.defaults.compaction.mode": "safeguard"
}
```

#### Hook Configuration

```json
{
  "hooks.internal.enabled": true,
  "hooks.internal.load.extraDirs": [
    "/home/exedev/arscontexta-openclaw/hooks",
    "/home/exedev/arscontexta-openclaw"
  ],
  "hooks.internal.entries": {
    "session-memory": {"enabled": true},
    "command-logger": {"enabled": true},
    "boot-md": {"enabled": true},
    "bootstrap-extra-files": {
      "enabled": true,
      "paths": ["self/identity.md", "self/methodology.md", "self/goals.md"]
    },
    "arscontexta-session-orient": {"enabled": true},
    "arscontexta-write-validate": {"enabled": true},
    "arscontexta-auto-commit": {"enabled": true},
    "arscontexta-session-capture": {"enabled": true}
  }
}
```

#### MCP Servers (15 total)

| Category | Server | URL | Purpose |
|----------|--------|-----|---------|
| **Vault** | vault-obsidian | http://localhost:3000 | Obsidian API — read, search, analytics, traverse |
| **Search** | search-ref | ref.tools | General reference search |
| | search-pageindex | pageindex.ai | Page indexing |
| | search-exa | exa.ai | Web search |
| | search-limitless | tadata.com/lifelog | Lifelog/memory search |
| | search-screenapp | tadata.com/screenapp | Screen recording search |
| **Think** | think-relate | entelecheia.cloud/infranodus | Network analysis |
| | think-distil | entelecheia.cloud/atom-of-thoughts | Thought distillation |
| | think-reason | entelecheia.cloud/thoughtbox | Reasoning |
| | think-skills | entelecheia.cloud/claude-skills | Skills |
| **Code** | code-wiki | deepwiki.com | Code documentation |
| | code-graph | entelecheia.cloud/deepgraph | Code graph analysis |
| | code-context7 | context7.com | Code context |
| | code-github | githubcopilot.com | GitHub Copilot MCP |

#### Channels
- Telegram bot enabled (DM pairing, group allowlist, partial streaming)

---

### 5. Obsidian API (agentic-obsidian)

**Source:** `/home/exedev/agentic-obsidian/api/server.js`  
**Port:** 3000  
**Auth:** localhost bypass, Bearer token, or X-ExeDev-Email header  

#### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/read` | GET | Read file content |
| `/read/smart` | GET | File content + neighborhood analytics + suggested next reads |
| `/analytics/summary` | GET | Graph health: node/edge counts, clusters, orphans, weakest nodes |
| `/analytics/graph` | GET | Full graph state (nodes + edges + metadata) |
| `/analytics/compute` | POST | Trigger full recomputation of all metrics |
| `/analytics/node` | GET | Single node analytics with neighborhood |
| `/traverse` | POST | MCMC traversal — optimal reading order for a query |
| `/dashboard` | GET | HTML dashboard |

#### Graph Analytics Engine

Uses `obsidian eval` to execute JavaScript inside the running Obsidian instance, accessing `app.metadataCache` and `app.vault` directly. This gives access to:
- All file metadata and frontmatter
- Link resolution via `cache.getFirstLinkpathDest()`
- File stats (mtime, size)

#### MCMC Traversal (from traversal-protocol.md)

```
Energy(S) = -Σ[relevance(n,Q)×0.4 + info_value(n)×0.4]
            + Σ[disconnected(nᵢ,nᵢ₊₁)×0.3]
            + |S|×0.05

Transitions: Swap, Add-neighbor, Remove, Replace
Acceptance: Metropolis-Hastings: min(1, exp(-ΔE/T))
```

#### Cron Jobs
- `heartbeat.sh` — every 5 min, writes `heartbeat.md` with system health
- `vault-backup.sh` — daily at 3am
- `graph-analytics.sh` — every 30 min, recomputes PageRank, centrality, communities, priorities

---

### 6. Multi-Agent Protocol

Three agent roles for vault operations:

| Role | Type | Function |
|------|------|---------|
| **Navigator** | System 1 (fast) | Handles queries, follows MCMC traversal path, synthesizes responses |
| **Evaluator** | System 2 (deep, subagent) | Checks alternative paths, flags skipped high-priority nodes, detects cluster traps |
| **Auditor** | Background (cron, 30min) | Recomputes all graph metrics, detects structural degradation, writes audit reports |

---

### 7. The Bridge: GKG → PKG

**Current state:** The bridge is conceptual, not automated.

#### How GKG feeds PKG today:
1. GKG data (SAQs, LOs, examiner comments) is **manually referenced** by the agent during sessions
2. The agent reads GKG data → processes through the 6-Rs pipeline → writes derived notes to PKG's `notes/`
3. PKG's `notes/mocs/evidence-saq-aggregate-2026-02.md` contains data **derived from** GKG's SAQ files
4. The `diff-dashboard` compares PKG's knowledge nodes against GKG's ground-truth topology

#### What's missing for automated bridging:
1. **No direct GKG → PKG sync pipeline** — the agent must manually read GKG files and write PKG notes
2. **The localhost:3000 API currently serves PKG** (workspace `/home/exedev/pkg`) — GKG at `/home/exedev/gkg` is a separate Obsidian vault with its own heartbeat but no exposed API endpoints
3. **No cross-vault analytics** — the graph analytics engine operates on one vault at a time
4. **Session memory (2026-02-19.md)** explicitly notes: "No observed pathway for syllabus/SAQ/examiner page-index or textbook extraction" via MCP

#### Bridge opportunities:
1. **Expose GKG as a second MCP server** (e.g., `vault-gkg` on port 3001) so the agent can query both vaults
2. **Create a sync hook** that watches GKG changes and creates inbox items in PKG
3. **Build a cross-vault traverse** that considers both GKG (ground truth) and PKG (personal knowledge) in the MCMC energy function
4. **Automate the diff** — GKG's `lo.base`/`saq.base` schemas could be parsed to auto-generate PKG's ground-truth-topology nodes
