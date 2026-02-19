# Epistates Ecosystem — Complete Research

*Researched: 2026-02-19*

## Organization

- **GitHub**: https://github.com/Epistates
- **Name**: Epistates, Inc.
- **Contact**: nick@epistates.com
- **Created**: 2025-08-10
- **Public repos**: 15
- **Primary Language**: Rust (all 15 repos)
- **UI toolkit**: Tauri 2 + SvelteKit (for desktop apps)

---

## Complete Repository List (15 repos)

### 1. turbovault ⭐32 — MCP Server for Obsidian
- **URL**: https://github.com/Epistates/turbovault
- **Language**: Rust
- **Latest**: v1.2.5 (workspace version 1.2.6)
- **Description**: Production-grade MCP server that gives Claude/AI agents 44 specialized tools for Obsidian vaults: reading, writing, searching (BM25), link graph analysis, batch operations, multi-vault support.
- **Install**: `cargo install turbovault` (7-8.8 MB binary)
- **Workspace crates**: turbovault, turbovault-tools, turbovault-core, turbovault-vault, turbovault-parser (OFM), turbovault-graph, turbovault-batch, turbovault-export
- **Topics**: mcp, mcp-server

### 2. turbomcp ⭐67 — Rust MCP SDK
- **URL**: https://github.com/Epistates/turbomcp
- **Website**: https://turbomcp.org
- **Language**: Rust
- **Latest**: v2.3.7 stable, v3.0.0-beta.3 pre-release
- **Description**: Production-ready Rust SDK for Model Context Protocol. Zero-boilerplate development with macro-driven tool definitions, multiple transports (STDIO, HTTP, WebSocket, TCP, Unix sockets), OAuth 2.1 auth, DPoP, SIMD acceleration.
- **Install**: `cargo add turbomcp`
- **Workspace crates**: turbomcp, turbomcp-server, turbomcp-client, turbomcp-protocol, turbomcp-transport, turbomcp-macros, turbomcp-auth, turbomcp-dpop, turbomcp-proxy, turbomcp-cli
- **Topics**: mcp, mcp-client, mcp-sdk, mcp-server, mcp-servers, rust

### 3. turbomcpstudio ⭐22 — MCP Server IDE
- **URL**: https://github.com/Epistates/turbomcpstudio
- **Language**: Svelte + Rust (Tauri 2)
- **Description**: Native desktop application for developing, testing, and debugging MCP servers. Multi-transport support, tool explorer, resource browser, prompt designer, protocol inspector. Cross-platform (macOS/Windows/Linux).
- **Topics**: developer-tools, mcp, mcp-client, mcp-server, rust

### 4. turboclaude ⭐8 — Rust Claude SDK
- **URL**: https://github.com/Epistates/turboclaude
- **Language**: Rust
- **Description**: Unofficial community-maintained Rust SDK for Anthropic's Claude API. Covers same features as official Python SDK. Includes agent framework, skills/tools, MCP integration.
- **Workspace crates**: turboclaude, turboclaudeagent, turboclaude-skills, turboclaude-protocol, turboclaude-transport, turboclaude-core, turboclaude-mcp

### 5. treemd ⭐550 — Markdown TUI Navigator (MOST POPULAR)
- **URL**: https://github.com/Epistates/treemd
- **Language**: Rust
- **Latest**: v0.5.6 (source v0.5.7)
- **Homebrew**: `brew install treemd`
- **Description**: Interactive markdown viewer with dual-pane TUI (heading tree + content). Features: vim-style navigation, table editing, checkbox toggling, link following, syntax highlighting (50+ languages), search, bookmarks, 8 themes, jq-like query language for CLI extraction.
- **Topics**: markdown, md, cli, terminal, tui

### 6. pmetal ⭐2 — LLM Fine-tuning for Apple Silicon
- **URL**: https://github.com/Epistates/pmetal
- **Language**: Rust
- **Description**: "Powdered Metal" — High-performance LLM fine-tuning framework for Apple Silicon. Brings Unsloth-style optimizations to macOS via custom Metal shaders and MLX framework. Supports LoRA fine-tuning with sequence packing for models like Qwen, Llama, DeepSeek.
- **Architecture**: 15 specialized crates (pmetal-core, pmetal-metal, pmetal-mlx, pmetal-models, etc.)
- **Topics**: ai, llm-inference, llm-training, metal, mlx

### 7. gravityfile ⭐19 — Filesystem Explorer TUI
- **URL**: https://github.com/Epistates/gravityfile
- **Language**: Rust
- **Description**: Interactive file system explorer/analyzer. Miller columns (ranger-style) + treemap visualization. Features: git status integration, vim-style navigation, file operations with undo, archive support, duplicate detection (BLAKE3), age analysis, command palette.
- **Install**: `cargo install gravityfile` (also installs `grav` alias)
- **Topics**: analyzer, filesystem, tui

### 8. tauq ⭐3 — Token-Efficient Data Format
- **URL**: https://github.com/Epistates/tauq
- **Website**: https://tauq.org
- **Language**: Rust (also npm + PyPI packages)
- **Description**: Schema-driven data format that achieves 44-54% fewer tokens than JSON (verified with tiktoken). Two parts: Tauq Notation (.tqn) for data and Tauq Query (.tqq) for transformations. Built for AI where every token counts.
- **Published on**: crates.io, npm, PyPI

### 9. opensesame ⭐6 — Open Files in Editors
- **URL**: https://github.com/Epistates/opensesame
- **Language**: Rust
- **Description**: Cross-platform library for opening files in text editors with line:column positioning. Supports 25+ editors (VS Code, Vim, NeoVim, Emacs, Sublime, Zed, Helix, Cursor, Windsurf, JetBrains IDEs). Smart detection via $VISUAL/$EDITOR.
- **Install**: `cargo add opensesame`

### 10. carwash ⭐10 — Cargo Multi-Project Manager TUI
- **URL**: https://github.com/Epistates/carwash
- **Language**: Rust
- **Description**: TUI for running cargo commands across multiple Rust projects simultaneously. Features: parallel execution, fuzzy command palette, real-time output, dependency management, workspace support, vim-style navigation.
- **Install**: `cargo install carwash`

### 11. taguchi ⭐1 — Orthogonal Array Library
- **URL**: https://github.com/Epistates/taguchi
- **Language**: Rust
- **Description**: Library for constructing and analyzing orthogonal arrays (Taguchi methods for Design of Experiments). Statistical calculations: ANOVA, S/N ratios.
- **Topics**: arrays, orthogonal

### 12. taguchi-ui ⭐2 — Orthogonal Array GUI
- **URL**: https://github.com/Epistates/taguchi-ui
- **Language**: Svelte + Rust (Tauri 2)
- **Description**: Desktop GUI for designing and analyzing orthogonal arrays. Built on the taguchi core library. Uses ECharts for visualization.
- **Topics**: gui, gui-application, orthogonal-arrays, rust

### 13. standby ⭐1 — Cross-Platform Time Tool
- **URL**: https://github.com/Epistates/standby
- **Language**: Rust
- **Description**: Production-ready CLI for time management. Unified interface for sleep, timeout, wait, and delay operations. POSIX compliant, GNU coreutils compatible. Supports compound time formats (1h30m45s), infinity, signal escalation.
- **Install**: `cargo install standby`

### 14. mni ⭐1 — JS/CSS/JSON Minifier
- **URL**: https://github.com/Epistates/mni
- **Language**: Rust
- **Description**: Blazing-fast minifier for JavaScript, CSS, and JSON. Built on SWC (JS, used by Next.js/Deno) + LightningCSS (CSS, 100x faster than cssnano). 7x faster than Terser, 30-45% compression.
- **Install**: `cargo install mni`

### 15. praxio ⭐5 — AI Agent Delegation Layer
- **URL**: https://github.com/Epistates/praxio
- **Language**: Rust
- **Description**: "Your AI Assistant's AI Assistant." Smart delegation layer that lets AI agents delegate specialized tasks to other models (Claude, Gemini, or any combo). Reduces context window pollution, routes simple subtasks to cheaper models, parallel execution.

---

## npm `basemd` Package (NOT by Epistates)

- **Package**: [basemd@1.0.0](https://www.npmjs.com/package/basemd)
- **Author**: yehan-s (yehanescn@gmail.com)
- **Published**: ~2025-12-06
- **License**: MIT
- **Dependencies**: none
- **Size**: 9.5 kB
- **What it does**: Creates symlinks so AGENTS.md, CLAUDE.md, GEMINI.md all point to a single `base.md` file. Unifies AI agent rules across different AI coding assistants.
- **Keywords**: ai, agent, rules, claude, gemini, copilot, codex, symlink
- **Repo**: https://github.com/yehan/basemd
- **⚠️ NOT related to Epistates or Obsidian Bases**

---

## MCP-Related Repos Summary

| Repo | Role | Stars |
|------|------|-------|
| turbomcp | SDK/framework for building MCP servers in Rust | 67 |
| turbovault | MCP server built on turbomcp, provides 44 Obsidian vault tools | 32 |
| turbomcpstudio | Desktop IDE for testing/debugging any MCP server | 22 |
| turboclaude | Claude API SDK with MCP integration crate | 8 |
| praxio | AI delegation layer (MCP-adjacent) | 5 |

**Relationship**: turbomcp is the foundation → turbovault is built on it → turbomcpstudio tests it → turboclaude provides Claude API access → praxio orchestrates multi-model workflows.

---

## Key Observations

1. **All Rust**: Every single repo is primarily Rust. Desktop UIs use Tauri 2 + SvelteKit.
2. **No Obsidian Plugin**: TurboVault is an external MCP server, NOT an Obsidian community plugin. It accesses vaults via the filesystem.
3. **Prolific but early**: 15 repos in ~6 months (Aug 2025 → Feb 2026). Most are pre-1.0 or very new.
4. **treemd is the hit**: 550 stars, on Homebrew. The rest are niche (1-67 stars).
5. **Package registries**: Many claim crates.io badges. treemd confirmed on Homebrew. tauq on npm + PyPI too.
6. **Single developer org**: All authored by "nick@epistates.com" / "Epistates, Inc."
