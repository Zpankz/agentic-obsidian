# callumalpass Ecosystem Map

Comprehensive inventory of all public repositories by [github.com/callumalpass](https://github.com/callumalpass).  
Generated from live GitHub API data. 32 public repos total.

---

## Architecture Overview

The ecosystem is built around **mdbase** — a specification for treating folders of markdown files with YAML frontmatter as typed, queryable data collections. Everything radiates outward from this core:

```
                        mdbase-spec (the specification)
                             │
              ┌──────────────┼──────────────┐
              │              │              │
          mdbase (TS)    mdbase-rs (Rust)  mdbase-lsp (Rust)
              │              │              │
         mdbase-cli     mdb binary      LSP for editors
              │
    ┌─────────┼──────────┐
    │         │          │
mdbase-    mdbase-     mdbase-
tasknotes  workouts    skill
(mtn CLI)  (workout    (Agent Skill
    │       app)        for AI IDEs)
    │
tasknotes-nlp-core (NLP parser library)
    │
    ├── tasknotes (Obsidian plugin)
    ├── tasknotes-cli (tn CLI, talks to plugin HTTP API)
    ├── tasknotes-browser-extension (Chrome)
    └── TaskNotesforAndroid (Kotlin)

ops (agent-assisted DevOps, built on mdbase)
clump (web UI for AI coding sessions)
ai-issue-analyzer (auto-analyze GitHub issues with AI)
psb (personal service bus via GitHub Gist)

obsidian-biblib + biblib-cli (bibliography management)
pulp (self-hosted PDF/EPUB reader, syncs with biblib)
handwrite + handwrite-obsidian (handwriting OCR via Gemini)
inkwell (self-hosted handwriting canvas app)

obsidian-pdf-view-sync, obsidian-template-filename,
obsidian-notes-explorer (utility Obsidian plugins)

diary-tui (terminal diary/task TUI)
study-program (CS self-study platform)
```

---

## Tier 1 — mdbase Core (The Specification & Implementations)

### 1. mdbase-spec
- **URL:** https://github.com/callumalpass/mdbase-spec
- **Purpose:** The specification for typed markdown collections — defines schemas in `_types/`, validation, query language, link resolution, CRUD operations, caching, and watch mode.
- **Language:** Markdown/HTML (spec document + YAML conformance tests)
- **Install:** Reference document; read at [mdbase.dev](https://mdbase.dev)
- **Ecosystem role:** **The foundational spec.** Everything else implements or consumes it. 15 sections covering config, types, matching, field types, links, validation, querying, expressions, operations, caching, watching. 6 conformance levels. Test suite in `tests/`.
- **Key concepts:** `mdbase.yaml` config file, `_types/` folder with type definitions as .md files, 12 field types, expression language compatible with Obsidian Bases syntax.

### 2. mdbase
- **URL:** https://github.com/callumalpass/mdbase
- **Purpose:** TypeScript reference implementation of the mdbase spec.
- **Language:** TypeScript / `npm install`
- **Ecosystem role:** The library that `mdbase-cli`, `mdbase-tasknotes`, and `mdbase-workouts` depend on. Runs the conformance test suite.
- **Key API:** `Collection.open()`, then `.read()`, `.create()`, `.update()`, `.delete()`, `.query()`, `.rename()`, `.batchUpdate()`, `.backfill()`, `.migrate()`, `.cacheRebuild()`, `.close()`

### 3. mdbase-rs
- **URL:** https://github.com/callumalpass/mdbase-rs
- **Purpose:** Rust implementation of the mdbase spec.
- **Language:** Rust / `cargo build`
- **Ecosystem role:** High-performance alternative to TS implementation. Provides the `mdb` CLI binary. Also the engine behind `mdbase-lsp`.
- **CLI binary:** `mdb` — supports `init`, CRUD, query, validate, backfill, migrate, cache commands.

### 4. mdbase-lsp
- **URL:** https://github.com/callumalpass/mdbase-lsp
- **Purpose:** Language Server Protocol server for mdbase collections.
- **Language:** Rust / `cargo build` (prebuilt binaries for Linux/macOS/Windows)
- **Ecosystem role:** Brings mdbase intelligence to any editor. Uses `mdbase-rs` internally.
- **Features:** Diagnostics (validation errors), completions (field names, enum values, link targets, tags), hover (field/type info, link preview), go-to-definition (link targets, type defs), commands (`mdbase.createFile`, `mdbase.validateCollection`).
- **Editor support:** VS Code extension in `editors/vscode/`, Neovim 0.11+ via lazy.nvim with auto-download.

### 5. mdbase-cli
- **URL:** https://github.com/callumalpass/mdbase-cli
- **Purpose:** CLI tool for mdbase collections — validate, query, CRUD, and execute Obsidian `.base` files from the terminal.
- **Language:** TypeScript / `npm ci && npm run build` (depends on local `mdbase` clone)
- **Binary name:** `mdbase`
- **Ecosystem role:** The command-line interface to any mdbase collection.
- **Key commands:** `mdbase validate .`, `mdbase query "status = published" --types note`, `mdbase base run my-view.base`, `mdbase export . --type note --format csv`, `mdbase init`, `mdbase lint`, `mdbase fmt`, `mdbase graph`, `mdbase stats`, `mdbase watch`, `mdbase diff`, `mdbase schema`

### 6. mdbase-skill
- **URL:** https://github.com/callumalpass/mdbase-skill
- **Purpose:** Agent Skill that teaches AI coding assistants (Claude Code, Copilot, Codex, Cursor, Gemini CLI) to work with mdbase collections.
- **Language:** Markdown (instruction files)
- **Install:** Clone into `.claude/skills/mdbase/` (or equivalent for other tools). Adapters for Windsurf, Amazon Q, Aider, Gemini Code Assist.
- **Ecosystem role:** Bridges mdbase spec knowledge into AI coding workflows. Contains full spec reference in `references/spec.md`.

---

## Tier 2 — TaskNotes (Task Management on mdbase)

### 7. tasknotes
- **URL:** https://github.com/callumalpass/tasknotes
- **Purpose:** Obsidian plugin — each task is a separate markdown note; all views powered by Obsidian Bases.
- **Language:** TypeScript (Obsidian plugin)
- **Install:** Obsidian Community Plugins
- **Ecosystem role:** The flagship application of the mdbase philosophy. Tasks are `.md` files with YAML frontmatter; views are `.base` files.
- **Features:** Natural language task creation, calendar sync (Google/Microsoft/ICS), time tracking with Pomodoro, recurring tasks (RRULE), dependencies, custom statuses/priorities, formula properties (urgencyScore, isOverdue, etc.), HTTP API for external integrations, webhooks, 9 UI languages, 12 NLP languages.
- **Docs:** [tasknotes.dev](https://tasknotes.dev/)
- **View types:** `tasknotesTaskList`, `tasknotesKanban`, `tasknotesCalendar`, `tasknotesAgenda`, `tasknotesMinicalendar`

### 8. mdbase-tasknotes
- **URL:** https://github.com/callumalpass/mdbase-tasknotes
- **Purpose:** Standalone CLI for managing tasks via mdbase — works on the same vault as the TaskNotes plugin OR standalone.
- **Language:** TypeScript / `npm install -g mdbase-tasknotes`
- **Binary name:** **`mtn`**
- **Ecosystem role:** The "native" task CLI that operates directly on markdown files via mdbase (no HTTP API needed, unlike `tn`).
- **Key commands:** `mtn init ~/notes`, `mtn create "Buy groceries tomorrow #shopping @errands"`, `mtn list --overdue`, `mtn complete "Buy groceries"`, `mtn timer start/stop/status/log`, `mtn search`, `mtn projects`, `mtn stats`, `mtn interactive` (REPL with live NLP preview), `mtn skip/unskip` (recurring instances)
- **Collection path resolution:** `--path` flag → `MDBASE_TASKNOTES_PATH` env → `~/.config/mdbase-tasknotes/config.json` → cwd

### 9. tasknotes-cli
- **URL:** https://github.com/callumalpass/tasknotes-cli
- **Purpose:** CLI that talks to the TaskNotes Obsidian plugin's HTTP API.
- **Language:** JavaScript / `npm link` (creates global `tn` command)
- **Binary name:** **`tn`**
- **Ecosystem role:** Remote control for the running TaskNotes plugin. Requires Obsidian to be running with API enabled.
- **Key commands:** `tn "Review PR tomorrow high priority @work"` (NLP create), `tn list --today/--overdue/--filter`, `tn complete/toggle/archive/delete`, `tn timer start/stop/status/log`, `tn pomodoro start/status/pause/stop/stats`, `tn projects list/show/create/stats`, `tn calendars list/events`, `tn recurring create/list/show`, `tn stats`, `tn-fzf` (fzf integration)
- **Config:** `~/.tasknotes-cli/config.json` with host, port, authToken

### 10. tasknotes-nlp-core
- **URL:** https://github.com/callumalpass/tasknotes-nlp-core
- **Purpose:** Framework-agnostic NLP parser for task text — extracts dates, tags, contexts, projects, priority, recurrence, estimates.
- **Language:** TypeScript / `npm install tasknotes-nlp-core`
- **Ecosystem role:** Shared parsing engine used by both `tasknotes` (plugin), `mdbase-tasknotes` (mtn), and `tasknotes-cli` (tn).
- **Key export:** `NaturalLanguageParserCore` class. Reads status/priority values from `_types/task.md` so customizations flow through.

### 11. tasknotes-browser-extension
- **URL:** https://github.com/callumalpass/tasknotes-browser-extension
- **Purpose:** Chrome extension — create tasks from Gmail, Outlook, and any webpage.
- **Language:** JavaScript (Chrome Extension)
- **Install:** [Chrome Web Store](https://chromewebstore.google.com/detail/obsidian-tasknotes-web-ex/kcbplgbcleppckifepdciipecjhdmchh)
- **Ecosystem role:** Browser-to-vault bridge via TaskNotes HTTP API.

### 12. TaskNotesforAndroid
- **URL:** https://github.com/callumalpass/TaskNotesforAndroid
- **Purpose:** Android companion app — displays today's tasks, sends notifications, creates/edits tasks.
- **Language:** Kotlin (Android)
- **Ecosystem role:** Mobile access to TaskNotes vault (reads same markdown files + plugin config).

---

## Tier 3 — mdbase Applications

### 13. mdbase-workouts
- **URL:** https://github.com/callumalpass/mdbase-workouts
- **Purpose:** Full workout tracking app (React + Hono server) storing all data as mdbase markdown files.
- **Language:** TypeScript / `npm install && npm run dev`
- **Ecosystem role:** Proof-of-concept that mdbase can power a real application. Has a Claude Agent SDK chat endpoint that reads/writes the same markdown files.
- **Architecture:** React frontend (Vite + Tailwind) → Hono API server → mdbase library → `data/**/*.md` files. 5 record types: exercise, plan, plan-template, session, quick-log.

### 14. ops
- **URL:** https://github.com/callumalpass/ops
- **Purpose:** Markdown-native operations CLI for AI-assisted delivery workflows. Keeps sidecar state in `.ops/` alongside code.
- **Language:** TypeScript / `npm install && npm run build && npm link`
- **Binary name:** `ops`
- **Ecosystem role:** Applies mdbase to DevOps. `.ops/` is an mdbase collection with types for commands, item sidecars, and handoffs.
- **Key commands:** `ops init`, `ops run triage-issue --issue 123`, `ops run address-issue --issue 123`, `ops run review-pr --pr 456`, `ops triage`, `ops issue address`, `ops handoff create/list/show/close`, `ops item ensure/list/show/set`, `ops command list/show/new/validate/render`, `ops doctor`
- **Providers:** GitHub, GitLab, Jira, Azure DevOps
- **Agent CLIs:** claude, codex (shells out to them)
- **FZF integration:** `./scripts/ops-fzf.sh`

---

## Tier 4 — AI/Agent Tooling

### 15. clump
- **URL:** https://github.com/callumalpass/clump
- **Purpose:** Web UI for running AI coding assistants (Claude Code, Gemini CLI, Codex, Copilot) against GitHub issues/PRs.
- **Language:** Python (FastAPI backend) + React frontend / `./run.sh`
- **Ecosystem role:** Agent session management. Embeds terminal sessions, saves transcripts, schedules recurring analyses.
- **Key features:** Multi-CLI adapter system, embedded xterm.js terminals, transcript search, AI-generated issue metadata (priority/difficulty/risk/type), cron scheduler, token cost tracking.
- **Data:** `~/.clump/projects/{hash}/` with SQLite + JSONL transcripts.

### 16. ai-issue-analyzer
- **URL:** https://github.com/callumalpass/ai-issue-analyzer
- **Purpose:** Auto-analyzes GitHub issues using AI CLIs, stores analyses for review.
- **Language:** JavaScript / `npm install -g .`
- **Binary name:** `ai-analyzer`
- **Ecosystem role:** Automated issue triage pipeline.
- **Key commands:** `ai-analyzer start`, `ai-analyzer ui` (web UI at :3030), `ai-analyzer analyze 123`, `ai-analyzer fix 123` (creates branch with ANALYSIS.md), `ai-analyzer config add/list/set-default/remove`

### 17. psb (Personal Service Bus)
- **URL:** https://github.com/callumalpass/psb
- **Purpose:** Lightweight personal inbox bridging phone and computer via GitHub Gists.
- **Language:** TypeScript (PWA + CLI)
- **Ecosystem role:** Cross-device message passing. Item types: note, link, prompt (question/answer).

---

## Tier 5 — Reading, Bibliography & Handwriting

### 18. pulp
- **URL:** https://github.com/callumalpass/pulp
- **Purpose:** Self-hosted PDF/EPUB reader — syncs reading progress, highlights, and bookmarks into markdown frontmatter.
- **Language:** TypeScript (Fastify + React monorepo) / `npm install && npm run dev:server`
- **Ecosystem role:** Reading companion. Stores state in frontmatter of literature notes. Works best with obsidian-biblib.
- **Config:** `~/.config/pulp/pulp.yaml` with `library_path` and `source_key`.

### 19. obsidian-biblib
- **URL:** https://github.com/callumalpass/obsidian-biblib
- **Purpose:** Obsidian plugin for managing bibliographic references as markdown notes with CSL-JSON frontmatter.
- **Language:** TypeScript (Obsidian plugin)
- **Install:** Obsidian Community Plugins (search "BibLib")
- **Ecosystem role:** Reference management. Each reference = markdown file with CSL-JSON YAML. Zotero browser connector support. Exports bibliography.json / .bib for Pandoc.
- **Docs:** [callumalpass.github.io/obsidian-biblib](https://callumalpass.github.io/obsidian-biblib)

### 20. biblib-cli
- **URL:** https://github.com/callumalpass/biblib-cli
- **Purpose:** CLI for fetching bibliographic metadata (DOI/ISBN/PMID/arXiv/URL) and writing CSL-JSON into markdown frontmatter.
- **Language:** TypeScript / `npm install && npm run build && npm link`
- **Binary name:** `biblib`
- **Ecosystem role:** Command-line companion to obsidian-biblib.
- **Key commands:** `biblib fetch "10.1038/..." --format json`, `biblib write "10.1038/..." notes/example.md`, `biblib server start/stop/status`, `biblib init-config`, `biblib from-json`
- **Config:** `~/.config/biblib/config.yaml`

### 21. handwrite
- **URL:** https://github.com/callumalpass/handwrite
- **Purpose:** CLI to convert handwritten PDFs into organized markdown using Gemini AI OCR.
- **Language:** Go / `go install github.com/callumalpass/handwrite@latest`
- **Binary name:** `handwrite`
- **Ecosystem role:** Handwriting-to-vault pipeline. Generates Obsidian-compatible markdown with YAML frontmatter.
- **Key commands:** `handwrite process /path/to/note.pdf /output/`, `handwrite config setup`

### 22. handwrite-obsidian
- **URL:** https://github.com/callumalpass/handwrite-obsidian
- **Purpose:** Obsidian plugin for OCR of handwritten notes (images + PDFs) using Gemini AI.
- **Language:** TypeScript (Obsidian plugin)
- **Ecosystem role:** In-vault version of handwrite. Supports extractable variables (custom fields Gemini identifies in handwriting).

### 23. inkwell
- **URL:** https://github.com/callumalpass/inkwell
- **Purpose:** Self-hosted handwriting app for e-ink devices (Boox). Infinite canvas, auto-transcription via Gemini, markdown sync.
- **Language:** TypeScript (client + server) / `npm install && npm run dev`
- **Ecosystem role:** Handwriting capture tool. Can sync pages as markdown to Obsidian vault.

---

## Tier 6 — Obsidian Utility Plugins

### 24. obsidian-pdf-view-sync
- **URL:** https://github.com/callumalpass/obsidian-pdf-view-sync
- **Purpose:** Auto-saves and restores PDF page position in frontmatter.
- **Language:** TypeScript (Obsidian plugin)
- **Install:** Obsidian Community Plugins

### 25. obsidian-template-filename
- **URL:** https://github.com/callumalpass/obsidian-template-filename
- **Purpose:** Create notes with templatable filenames (dates, random strings, counters, base-N timestamps).
- **Language:** TypeScript (Obsidian plugin)

### 26. obsidian-notes-explorer
- **URL:** https://github.com/callumalpass/obsidian-notes-explorer
- **Purpose:** Card-based gallery/masonry view for exploring vault notes.
- **Language:** TypeScript (Obsidian plugin)
- **Install:** Obsidian Community Plugins (search "Notes Explorer")
- **Note:** Fork of Cards View plugin, originally by tu2-atmanand.

---

## Tier 7 — Legacy / Standalone

### 27. diary-tui
- **URL:** https://github.com/callumalpass/diary-tui
- **Purpose:** Terminal TUI for diary entries, tasks, and daily timeblocking.
- **Language:** Python / `pip install .`
- **Binary names:** `diary-tui`, `task-creator`
- **Ecosystem role:** Predecessor to TaskNotes. Works with markdown diary files + YAML frontmatter.

### 28. study-program
- **URL:** https://github.com/callumalpass/study-program
- **Purpose:** CS self-study platform with AI-generated readings, exercises, quizzes, and exams.
- **Language:** TypeScript (React) / hosted at [callumalpass.github.io/study-program](https://callumalpass.github.io/study-program/)
- **Ecosystem role:** Standalone learning tool. Progress syncs to GitHub Gist.

### 29. biblio-note
- **URL:** https://github.com/callumalpass/biblio-note
- **Purpose:** Shell scripts for managing markdown literature notes (predecessor to biblib).
- **Language:** Shell

### 30. bibliography
- **URL:** https://github.com/callumalpass/bibliography
- **Purpose:** Public bibliography file.
- **Language:** Data only

### 31. academic-paper-workflow
- **URL:** https://github.com/callumalpass/academic-paper-workflow
- **Purpose:** GitHub Actions workflow for building academic papers from Markdown.
- **Language:** CSS / GitHub Actions

### 32. zk_scripts
- **URL:** https://github.com/callumalpass/zk_scripts
- **Purpose:** Zettelkasten management scripts (early predecessor to mdbase concepts).
- **Language:** Python

### 33. obsidian-releases (fork)
- **URL:** https://github.com/callumalpass/obsidian-releases
- **Purpose:** Fork of the official Obsidian community plugins/themes list (for plugin submissions).

---

## Key CLI Commands Summary

| Binary | Package | Install | What it does |
|--------|---------|---------|-------------|
| `mdbase` | mdbase-cli | `npm link` | Validate, query, CRUD, run .base files on any mdbase collection |
| `mdb` | mdbase-rs | `cargo build` | Rust CLI for mdbase operations |
| `mtn` | mdbase-tasknotes | `npm install -g mdbase-tasknotes` | Task management directly on markdown files |
| `tn` | tasknotes-cli | `npm link` | Task management via TaskNotes HTTP API |
| `ops` | ops | `npm link` | AI-assisted DevOps with markdown sidecars |
| `biblib` | biblib-cli | `npm link` | Fetch & write bibliographic metadata |
| `handwrite` | handwrite | `go install` | Handwriting PDF → markdown OCR |
| `ai-analyzer` | ai-issue-analyzer | `npm install -g .` | Auto-analyze GitHub issues with AI |
| `diary-tui` | diary-tui | `pip install .` | Terminal diary/task management |

## Key Distinction: `tn` vs `mtn`

- **`tn`** (tasknotes-cli): Talks to the running TaskNotes Obsidian plugin via HTTP API. Requires Obsidian open.
- **`mtn`** (mdbase-tasknotes): Operates directly on markdown files via mdbase library. Works standalone, no Obsidian needed. Both can work on the same vault.

## Repos NOT Found

The following were asked about but **do not exist** as public repos under callumalpass:
- `beads`, `beads_viewer`, `bv`, `br` (issue tracking)
- `gh-aw` (GitHub extension)
- `ntm` (Named Tmux Manager)
- `atom-of-thoughts` (reasoning tool)
- Any MCP (Model Context Protocol) server/tools

These may be private, under a different user, or not yet created.
