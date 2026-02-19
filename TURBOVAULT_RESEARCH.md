# TurboVault Research Report

## What It Is

TurboVault (`Epistates/turbovault`, v1.2.6) is a **production-grade MCP (Model Context Protocol) server** written in Rust that transforms Obsidian vaults into intelligent knowledge systems for AI agents. It provides **44 specialized MCP tools** for reading, writing, searching, analyzing, and managing Obsidian notes with sub-100ms performance for most operations.

It is published on crates.io and targets Rust 1.90+.

## How It Works

### Architecture

TurboVault is a **Rust workspace** with 8 crates organized in a layered dependency hierarchy:

```
turbovault (main binary)            — CLI + MCP server entry point
  └─ turbovault-tools               — 44 MCP tool implementations
       ├─ turbovault-vault           — Vault management, file I/O, atomic writes
       │    ├─ turbovault-parser     — OFM (Obsidian Flavored Markdown) parsing
       │    └─ turbovault-graph      — Link graph analysis with petgraph
       ├─ turbovault-batch           — Transactional batch operations
       └─ turbovault-export          — JSON/CSV/Markdown export
  └─ turbovault-core                 — Core types, config, multi-vault manager, errors
```

### Key Design Decisions

1. **Built on TurboMCP** (`turbomcp` v2.3.3 + `turbomcp-server` v2.3.3) — a Rust framework for building MCP servers. Provides `#[turbomcp::server]` macro for type-safe tool definitions, transport abstraction, middleware.

2. **Multi-vault management** — `MultiVaultManager` maintains a registry of vaults with an "active vault" pointer. Vaults can be added/removed at runtime. Project-aware caching persists vault configs to `~/.cache/turbovault/projects/{hash}/`.

3. **Vault-agnostic startup** — Server can start with NO vault; vaults are added dynamically via `add_vault` MCP tool.

4. **Lazy vault initialization** — `VaultManager` instances are created on-demand and cached. Initialization scans files and builds the link graph.

5. **OFM Parser** — Hybrid approach: pulldown-cmark for CommonMark foundation + regex for Obsidian-specific syntax (wikilinks, embeds, tags, callouts). Uses `ExcludedRanges` to skip code blocks. `LineIndex` for O(log n) position lookups.

6. **Link Graph** — `petgraph::DiGraph` where nodes=file paths, edges=links. Supports backlinks, forward links, hub detection, cycle detection, connected components, orphan detection via Kosaraju's SCC algorithm.

7. **Full-text search** — Tantivy (Rust Lucene-equivalent) with BM25 ranking. <500ms on 100k notes.

8. **Atomic writes** — Temp file → atomic rename pattern. Hash-based conflict detection for concurrent edits.

9. **Edit engine** — SEARCH/REPLACE block format with fuzzy matching (using `similar` and `strsim` crates). SHA-256 content hashing.

### Data Flow (MCP Request → Vault Operation)

1. AI agent sends MCP tool call (e.g., `search`, `read_note`)
2. `ObsidianMcpServer` receives request via transport (stdio/http/ws/tcp/unix)
3. `get_vault_pair()` resolves active vault name → gets/creates `VaultManager`
4. Tool-specific logic executes (FileTools, SearchEngine, GraphTools, etc.)
5. `VaultManager` coordinates with parser, graph, search index
6. Result wrapped in `StandardResponse<T>` envelope and returned

### StandardResponse Envelope

Every tool response uses this consistent format:
```rust
StandardResponse {
    vault: String,           // which vault
    operation: String,       // e.g., "read_note"
    success: bool,
    data: T,                 // actual result
    count: Option<usize>,    // item count
    took_ms: u64,            // timing
    warnings: Vec<String>,   // non-fatal issues
    next_steps: Vec<String>, // suggested follow-up tools
    meta: Map<String, Value>, // extensible metadata
}
```

## Dependencies

### Core Dependencies
| Dependency | Version | Purpose |
|---|---|---|
| **turbomcp** | 2.3.3 | MCP server framework |
| **turbomcp-server** | 2.3.3 | MCP server runner |
| **tokio** | 1.47 | Async runtime |
| **serde** / **serde_json** / **serde_yaml** | 1.0 | Serialization |
| **tantivy** | 0.22 | Full-text search (BM25) |
| **petgraph** | 0.6 | Graph data structures |
| **pulldown-cmark** | 0.13 | CommonMark parsing |
| **clap** | 4.4 | CLI argument parsing |
| **tracing** / **tracing-subscriber** | 0.1/0.3 | Observability |
| **similar** | 2.7 | Diff/fuzzy matching |
| **sha2** | 0.10 | Content hashing |
| **dashmap** | 5.5 | Concurrent hashmap |
| **notify** | 6 | File watching |
| **walkdir** | 2 | Directory traversal |
| **regex** | 1 | OFM pattern matching |
| **path_trav** | 2 | Path traversal security |
| **shellexpand** | 3.1 | Tilde/env var expansion |
| **config** | 0.14 | Configuration loading |
| **chrono** | 0.4 | Timestamps |
| **uuid** | 1.6 | Unique IDs |
| **thiserror** / **anyhow** | 1.0 | Error handling |
| **unicode-normalization** | 0.1.6 | NFC normalization |
| **strsim** | 0.11 | Levenshtein distance |

## CLI Interface

```
turbovault [OPTIONS]

Options:
  -v, --vault <PATH>          Path to Obsidian vault (or env OBSIDIAN_VAULT_PATH)
  -p, --profile <PROFILE>     Config profile [default: development]
                               Options: development, production, readonly, high-performance
  -t, --transport <TRANSPORT>  Transport mode [default: stdio]
                               Options: stdio, http, websocket, tcp, unix
      --port <PORT>            HTTP server port [default: 3000]
      --output-format <FMT>    Output format for non-STDIO [default: json]
                               Options: json, human, text
      --init                   Initialize vault on startup
  -h, --help
  -V, --version
```

### Feature Flags (Cargo)
```
default    = []           # STDIO only (~5-6 MB binary)
http       = [turbomcp/http]       # +HTTP server
websocket  = [turbomcp/websocket]  # +WebSocket
tcp        = [turbomcp/tcp]        # +TCP
unix       = [turbomcp/unix]       # +Unix sockets (Unix-only)
full       = [http, websocket, tcp] # All cross-platform transports
```

### Build Commands
```bash
cargo install turbovault                    # Minimal (STDIO only)
cargo install turbovault --features http    # With HTTP
cargo install turbovault --features full    # All transports
```

## API Surface — All 44 MCP Tools

### File Operations (5)
| Tool | Description |
|---|---|
| `read_note` | Get note content with hash for conflict detection |
| `write_note` | Create/overwrite notes (auto-creates directories) |
| `edit_note` | Surgical edits via SEARCH/REPLACE blocks with fuzzy matching |
| `delete_note` | Safe deletion with link tracking |
| `move_note` | Rename/relocate with automatic wikilink updates |

### Search & Discovery (5)
| Tool | Description |
|---|---|
| `search` | BM25-ranked full-text search (<500ms on 100k notes) |
| `advanced_search` | Search with tag/metadata filters |
| `recommend_related` | Content-similarity recommendations |
| `find_notes_from_template` | Find notes using a specific template |
| `query_metadata` | Frontmatter pattern queries |

### Link Analysis (6)
| Tool | Description |
|---|---|
| `get_backlinks` | All notes linking TO this note |
| `get_forward_links` | All notes this note links TO |
| `get_related_notes` | Multi-hop graph traversal |
| `get_hub_notes` | Top 10 most connected notes |
| `get_dead_end_notes` | Notes with incoming but no outgoing links |
| `get_isolated_clusters` | Disconnected subgraphs |

### Graph Analysis (3)
| Tool | Description |
|---|---|
| `detect_cycles` | Circular reference chains |
| `get_centrality_ranking` | Betweenness, closeness, eigenvector centrality |
| `get_link_strength` | Connection strength between notes (0.0–1.0) |

### Vault Health & Analysis (4)
| Tool | Description |
|---|---|
| `quick_health_check` | Fast 0-100 health score (<100ms) |
| `full_health_analysis` | Comprehensive vault audit with recommendations |
| `get_broken_links` | All links pointing to non-existent notes |
| `explain_vault` | Holistic overview (replaces 5+ separate calls) |

### Templates (4)
| Tool | Description |
|---|---|
| `list_templates` | Discover available templates |
| `get_template` | Template details and required fields |
| `create_from_template` | Render and write templated notes |
| `get_ofm_examples` | All OFM feature examples |

### Vault Lifecycle (7)
| Tool | Description |
|---|---|
| `create_vault` | Programmatically create a new vault |
| `add_vault` | Register and auto-initialize vault at runtime |
| `remove_vault` | Unregister vault (safe, no file deletion) |
| `list_vaults` | All registered vaults with status |
| `get_vault_config` | Inspect vault settings |
| `set_active_vault` | Switch context between vaults |
| `get_active_vault` | Current active vault |

### Batch Operations (1)
| Tool | Description |
|---|---|
| `batch_execute` | Atomic multi-file operations (all-or-nothing) |

### Export & Reporting (4)
| Tool | Description |
|---|---|
| `export_health_report` | Export vault health as JSON/CSV |
| `export_broken_links` | Export broken links with fix suggestions |
| `export_vault_stats` | Statistics and metrics export |
| `export_analysis_report` | Complete audit trail |

### Metadata & Relationships (3)
| Tool | Description |
|---|---|
| `get_metadata_value` | Extract frontmatter values (dot notation) |
| `suggest_links` | AI-powered link suggestions |
| `get_vault_context` | Meta-tool: vault status + tools + OFM guide |

### Validation/Reference (2)
| Tool | Description |
|---|---|
| `get_ofm_syntax_guide` | Complete OFM reference |
| `get_ofm_quick_ref` | Quick OFM cheat sheet |

## Rust Library API

Each crate is also usable as a library:

```rust
// Core types
use turbovault_core::{MultiVaultManager, VaultConfig, ServerConfig};

// Vault operations
use turbovault_vault::VaultManager;

// Tools
use turbovault_tools::{
    FileTools, SearchEngine, SearchQuery, GraphTools, AnalysisTools,
    BatchTools, ExportTools, MetadataTools, RelationshipTools,
    TemplateEngine, VaultLifecycleTools, ValidationTools,
};

// Parser
use turbovault_parser::OFMParser; // Obsidian Flavored Markdown

// Graph
use turbovault_graph::LinkGraph;
```

### Key Types
- `VaultFile` — parsed note with frontmatter, links, tags, headings, tasks
- `Link` — typed link (WikiLink, Embed, BlockRef, HeadingRef, Anchor, MarkdownLink, External)
- `LinkGraph` — petgraph-based directed graph of note relationships
- `SearchEngine` — Tantivy-backed full-text search
- `EditEngine` — SEARCH/REPLACE block parser with fuzzy matching
- `StandardResponse<T>` — uniform response envelope
- `BatchOperation` — enum of batch operations (WriteNote, DeleteNote, MoveNote, etc.)

## OFM Parser Details

Parses Obsidian-specific markdown features:
- **Wikilinks**: `[[note]]`, `[[note|alias]]`, `[[note#section]]`, `[[note#^block]]`
- **Embeds**: `![[image.png]]`, `![[note]]`, `![[note#section]]`
- **Tags**: `#tag`, `#parent/child/tag`
- **Tasks**: `- [ ] Task`, `- [x] Done`
- **Callouts**: `> [!type] Title`
- **Frontmatter**: YAML metadata
- **Headings**: Hierarchical structure extraction

Implementation: pulldown-cmark for CommonMark + lazy-compiled regex for OFM-specific syntax. Code blocks are tracked via `ExcludedRanges` to prevent false matches.

## Performance Targets

| Operation | Target | Notes |
|---|---|---|
| `read_note` | <10ms | With caching |
| `get_backlinks` / `get_forward_links` | <50ms | Graph lookup |
| `write_note` | <50ms | Includes graph update |
| `search` (10k notes) | <100ms | Tantivy BM25 |
| `quick_health_check` | <100ms | Heuristic score |
| `full_health_analysis` | 1–5s | Exhaustive |
| `explain_vault` | 1–5s | Aggregates 5+ analyses |
| Vault init | 100ms–5s | Depends on vault size |

**Memory**: 100MB base + ~80MB per 10k notes.

## Security Features

- Path traversal protection (`path_trav` crate)
- Type-safe deserialization (Rust type system)
- Atomic writes (temp file → rename, never corrupts)
- Hash-based conflict detection on edits
- File size limits (default 5MB)
- No shell execution (zero command injection risk)
- Security auditing in production profile

## Configuration Profiles

| Profile | Use Case |
|---|---|
| `development` | Verbose logging |
| `production` | Security auditing + optimized logging |
| `readonly` | Read-only access |
| `high-performance` | Large vaults (10k+) with aggressive caching |

## Claude Desktop Integration

```json
{
  "mcpServers": {
    "turbovault": {
      "command": "/path/to/turbovault",
      "args": ["--vault", "/path/to/vault", "--profile", "production"]
    }
  }
}
```

## Source File Map

### Main Binary
- `crates/turbovault/src/bin/main.rs` — CLI entry point, transport selection, cache recovery
- `crates/turbovault/src/lib.rs` — Re-exports, module declarations
- `crates/turbovault/src/tools.rs` — `ObsidianMcpServer` with all 44 MCP tool handlers (~1800 lines)
- `crates/turbovault/src/resources.rs` — MCP resource definitions

### Tools
- `crates/turbovault-tools/src/file_tools.rs` — FileTools (read/write/edit/delete/move/copy)
- `crates/turbovault-tools/src/search_engine.rs` — SearchEngine (Tantivy-based)
- `crates/turbovault-tools/src/search_tools.rs` — SearchTools
- `crates/turbovault-tools/src/graph_tools.rs` — GraphTools (broken links, health, hubs, cycles, clusters)
- `crates/turbovault-tools/src/analysis_tools.rs` — AnalysisTools (vault stats)
- `crates/turbovault-tools/src/batch_tools.rs` — BatchTools (atomic operations)
- `crates/turbovault-tools/src/export_tools.rs` — ExportTools
- `crates/turbovault-tools/src/metadata_tools.rs` — MetadataTools
- `crates/turbovault-tools/src/relationship_tools.rs` — RelationshipTools
- `crates/turbovault-tools/src/templates.rs` — TemplateEngine
- `crates/turbovault-tools/src/vault_lifecycle.rs` — VaultLifecycleTools
- `crates/turbovault-tools/src/validation_tools.rs` — ValidationTools
- `crates/turbovault-tools/src/output_formatter.rs` — ResponseFormatter
- `crates/turbovault-tools/src/response_utils.rs` — Response helpers

### Core
- `crates/turbovault-core/src/models.rs` — Link, Heading, Tag, Task, VaultFile, SourcePosition, LineIndex
- `crates/turbovault-core/src/config.rs` — VaultConfig, ServerConfig, VaultConfigBuilder
- `crates/turbovault-core/src/multi_vault.rs` — MultiVaultManager
- `crates/turbovault-core/src/cache.rs` — VaultCache, CacheMetadata
- `crates/turbovault-core/src/error.rs` — Error types
- `crates/turbovault-core/src/profiles.rs` — Configuration profiles
- `crates/turbovault-core/src/metrics.rs` — Performance metrics
- `crates/turbovault-core/src/resilience.rs` — Resilience patterns
- `crates/turbovault-core/src/validation.rs` — Input validation

### Vault
- `crates/turbovault-vault/src/manager.rs` — VaultManager (scan, read, write, edit, graph access)
- `crates/turbovault-vault/src/edit.rs` — EditEngine (SEARCH/REPLACE blocks, fuzzy matching)
- `crates/turbovault-vault/src/atomic.rs` — Atomic file operations
- `crates/turbovault-vault/src/watcher.rs` — File watcher (notify-based)

### Parser
- `crates/turbovault-parser/src/engine.rs` — Main parsing engine (pulldown-cmark + regex)
- `crates/turbovault-parser/src/parsers/wikilinks.rs` — Wikilink parser
- `crates/turbovault-parser/src/parsers/embeds.rs` — Embed parser
- `crates/turbovault-parser/src/parsers/tags.rs` — Tag parser
- `crates/turbovault-parser/src/parsers/frontmatter_parser.rs` — YAML frontmatter
- `crates/turbovault-parser/src/parsers/headings.rs` — Heading extraction
- `crates/turbovault-parser/src/parsers/tasks.rs` — Task extraction
- `crates/turbovault-parser/src/parsers/callouts.rs` — Callout parsing
- `crates/turbovault-parser/src/parsers/link_utils.rs` — Link classification
- `crates/turbovault-parser/src/parsers/markdown_links.rs` — Standard markdown links

### Graph
- `crates/turbovault-graph/src/graph.rs` — LinkGraph (petgraph DiGraph)
- `crates/turbovault-graph/src/health.rs` — Health analysis algorithms

## Related Projects

- **TurboMCP** (`Epistates/turbomcp`) — The underlying MCP server framework
- **Obsidian** — The note-taking app whose vaults TurboVault manages
