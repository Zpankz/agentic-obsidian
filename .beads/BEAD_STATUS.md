# Bead Status Audit — 2026-02-20

Honest accounting of what's done, what's scaffolded, and what's blocked.

---

## Genuinely Closed (15/34)

| Bead | Title | Evidence |
|------|-------|----------|
| bd-1xl.1 | Start and verify cli-proxy service | systemd active, port 8317, responds to requests |
| bd-1yj.1 | Install AI SDKs in venv | anthropic 0.83, openai 2.21, dspy 3.1.3, pydantic-ai 1.62 all import |
| bd-1yj.2 | Anthropic SDK bridge | `ralph/bridge.py` — ModelBridge class with proxy+direct fallback |
| bd-1yj.3 | Pydantic AI agent definitions | `ralph/pydantic_agents.py` — 5 structured output models |
| bd-1yj.4 | DSPy modules for GEPA | `ralph/dspy_modules.py` — 4 signatures, 3 modules, optimize_module() |
| bd-2ns.1 | Build pure-chat-llm | Built, installed in gkg+pkg `.obsidian/plugins/`, enabled |
| bd-2ns.4 | Voice system prompt | `ralph/voice_bridge.py` — create_voice_system_prompt() |
| bd-3sp.1 | RALPH core loop | `ralph/loop.py` — tested, 2 iterations in 7.2s, 11 actions |
| bd-3sp.2 | Unified tool registry | `ralph/tools.py` — 31 tools (8 HTTP, 7 CLI, 13 MCP, 3 AoT) |
| bd-3sp.3 | AoT wired into RALPH | `ralph/aot.py` + `ralph/mcp_client.py` — stdio JSON-RPC client |
| bd-vir.1 | Graph analytics audit | Completed. Root cause identified: obsidian eval stdout limits. Fixed with file-based transfer + 30s cache |
| bd-2ma.1 | NTM recipes | `~/.config/ntm/recipes.toml` — 5 specialist agent recipes |
| bd-1yj | Epic: SDK | All 4 children closed |
| bd-1kp | GSD hooks (dup of bd-2ma.3) | Merged into bd-2ma.3 |
| bd-2bo | Agent routing (dup of bd-2ma.2) | Merged into bd-2ma.2 |

---

## Reopened — Scaffolded but Incomplete (13/34)

### PROXY Epic (bd-1xl) — BLOCKED on user credentials

**bd-1xl.2** — Authenticate all provider accounts
- ✅ Done: cli-proxy config.yaml lists 5 providers (gemini, antigravity, claude, codex, kimi)
- ❌ Not done: `auths/` directory is empty. Zero OAuth sessions. Needs interactive browser login per provider.
- 🔑 Blocked: Requires user to run `cli-proxy --login`, `--antigravity-login`, `--claude-login`, `--codex-login`, `--kimi-login`

**bd-1xl.3** — Configure intelligent model rotation
- ✅ Done: config.yaml has `strategy: round-robin`, `quota-exceeded: switch-project: true`, retry+failover config
- ❌ Not done: With 0 authenticated providers, rotation is inert. Needs bd-1xl.2 first.
- Depends on: bd-1xl.2

**bd-1xl.4** — Run configure-clients.sh
- ✅ Done: Script exists at `/home/exedev/cli-proxy/configure-clients.sh`
- ❌ Not done: Never executed. `~/.pi/agent/models.json` doesn't exist. Agent tools not wired to proxy.
- Depends on: bd-1xl.2 (needs working proxy)

### VOICE Epic (bd-2ns) — PARTIALLY BLOCKED

**bd-2ns.2** — Configure Obsidian Sync to sync plugins
- ✅ Done: pure-chat-llm in `community-plugins.json` for both vaults
- ❌ Not done: Obsidian Sync status not verified. Plugin sync settings not confirmed. Sync may not be pushing plugins to cloud.
- Needs: `DISPLAY=:99 obsidian sync:status` to work (currently errors), or manual verification via Obsidian UI

**bd-2ns.3** — OpenAI Realtime + Gemini Live voice providers
- ✅ Done: `data.json` config points to cli-proxy with 5 model aliases, realtimeSystemPromptFile set
- ❌ Not done: cli-proxy has 0 providers authenticated → voice calls will fail with auth errors
- Depends on: bd-1xl.2

### RALPH Epic (bd-3sp) — NEEDS RUNTIME WORK

**bd-3sp.4** — System 2 background agent
- ✅ Done: `ralph/voice_bridge.py` — VoiceBridge class with inject_context(), buffer_insight(), flush_insights()
- ✅ Done: `ralph/agents.py` — SYSTEM2_AGENT spec (low temp 0.3, 8192 tokens, 9 tools)
- ❌ Not done: No `_system2/` directory created in vault. No background runner/daemon. No systemd service. Never executed.
- Needs: A persistent runner that watches for voice queries and runs System 2 analysis asynchronously

**bd-3sp.5** — Bridge RALPH ↔ voice
- ✅ Done: `ralph/voice_bridge.py` — context injection via vault notes, system prompt generation
- ✅ Done: pure-chat-llm data.json configured with realtimeSystemPromptFile
- ❌ Not done: No end-to-end test. Requires cli-proxy auth (bd-1xl.2) + System 2 runner (bd-3sp.4)
- Depends on: bd-1xl.2, bd-3sp.4

### GRAPH Epic (bd-vir) — NEEDS IMPLEMENTATION

**bd-vir.2** — Align mdbase types with graph analytics
- ✅ Done: Graph analytics audit identified issues. getGraphState() fixed.
- ❌ Not done: 79 validation errors remain in gkg vault:
  - 44 empty wikilinks in `section.sub` fields (ANZCA LOs)
  - 15 object-format histograms (AP25B SAQs — should be arrays)
  - 5 boolean-as-array concept fields (C3x)
  - 3 META.md variation type mismatches
  - Various CICM CP25 missing required fields
- Needs: Targeted frontmatter fixes or mdbase type definition adjustments

**bd-vir.3** — Semantic mapping pipeline
- ✅ Done: `ralph/semantic_pipeline.py` — 511 lines, full pipeline design (fetch_graph, map_types, identify_gaps, generate_tasks, persist)
- ❌ Not done: Never executed against live data. No output tasks generated. No integration with beads.
- Needs: Run pipeline, validate output, create actual tasks

### TASK Epic (bd-1f7) — NEEDS RUNTIME + DATA

**bd-1f7.1** — Auto-generate tasks from Delta-Miss
- ✅ Done: `ralph/semantic_pipeline.py` has DeltaMiss gap analysis logic
- ✅ Done: `ralph/dspy_modules.py` has DeltaMissModule signature
- ❌ Not done: No tasks actually generated. Pipeline never run. No mdbase-typed task files created.
- Depends on: bd-vir.3 (pipeline working)

**bd-1f7.2** — Self-improving prompt evolution via DSPy
- ✅ Done: `ralph/dspy_modules.py` — GEPAEvolver module, optimize_module() with BootstrapFewShot/MIPROv2
- ✅ Done: configure_dspy_lm() routes through cli-proxy
- ❌ Not done: No training data collected. No prompt cache at `~/.cache/ralph/prompts/`. No optimization run. No evaluation metrics.
- Depends on: bd-1xl.2 (need LLM access), multiple RALPH loop runs to generate training examples

### ORCH Epic (bd-2ma) — PARTIALLY DONE

**bd-2ma.2** — Agent model routing via cli-proxy
- ✅ Done: `agents/model_routing.yaml` — detailed routing config per agent role and task type
- ✅ Done: `agents/routing.py` — routing logic
- ❌ Not done: Depends on cli-proxy having authenticated providers. Currently routes to empty pool.
- Depends on: bd-1xl.2

**bd-2ma.3** — GSD landing-the-plane protocol
- ✅ Done: AGENTS.md documents the mandatory workflow (file issues → quality gates → push)
- ❌ Not done: No automated beads hooks. No pre-commit/pre-push enforcement. Protocol is documentation-only.
- Needs: Git hooks or br plugin that enforces the protocol

---

## Dependency Graph

```
bd-1xl.2 (provider auth) ← USER ACTION REQUIRED
  ├── bd-1xl.3 (rotation)
  ├── bd-1xl.4 (wire clients)
  ├── bd-2ns.3 (voice providers)
  │   └── bd-3sp.5 (RALPH ↔ voice)
  ├── bd-2ma.2 (agent routing)
  └── bd-1f7.2 (DSPy optimization)

bd-3sp.4 (System 2 runner) ← IMPLEMENTATION NEEDED
  └── bd-3sp.5 (RALPH ↔ voice)

bd-vir.2 (fix 79 validation errors) ← IMPLEMENTATION NEEDED
  └── bd-vir.3 (semantic pipeline)
      └── bd-1f7.1 (Delta-Miss tasks)

bd-2ns.2 (sync verification) ← NEEDS INVESTIGATION
bd-2ma.3 (GSD hooks) ← IMPLEMENTATION NEEDED
```

## Summary

- **15 beads genuinely done** (code written, tested, working)
- **6 beads blocked on user action** (bd-1xl.2 and its dependents — need OAuth logins)
- **7 beads have code scaffolded but need runtime/testing** (pipelines, System 2, hooks)
- **6 epics reopened** to reflect incomplete children
