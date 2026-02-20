# RALPH — Recursive Agentic Language Processing Heuristic

A neurosymbolic agent loop framework that integrates vault knowledge, graph analytics,
Atom-of-Thoughts reasoning, and self-improving prompts into a unified execution cycle.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RALPH Loop Engine                         │
│                                                             │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│   │  SENSE   │→ │  PLAN    │→ │  ACT     │→ │ OBSERVE  │  │
│   │          │  │  (AoT)   │  │  (Tools) │  │          │  │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│        ↑                                          │        │
│        │            ┌──────────┐                  │        │
│        └────────────│ REFLECT  │←─────────────────┘        │
│                     │ (DSPy)   │                           │
│                     └──────────┘                           │
└─────────────────────────────────────────────────────────────┘
        │                   │                    │
   ┌────▼────┐        ┌────▼────┐          ┌────▼────┐
   │  Vault  │        │  Graph  │          │  Voice  │
   │ gkg/pkg │        │Analytics│          │pure-chat│
   └─────────┘        └─────────┘          └─────────┘
```

## Loop Phases

| Phase | Input | Output | Tools |
|-------|-------|--------|-------|
| **Sense** | Query/trigger | Context bundle | vault-graph, mdb query, obsidian search |
| **Plan** | Context | Atom decomposition | AoT MCP (decompose → contract) |
| **Act** | Plan atoms | Executed actions | turbovault, mtn, br, mdb, obsidian CLI |
| **Observe** | Action results | State diff | graph analytics, mdb validate |
| **Reflect** | Observations | Updated prompts/weights | DSPy teleprompter, pydantic-ai |

## Files

| File | Purpose |
|------|--------|
| `loop.py` | Core RALPH loop engine |
| `phases.py` | Phase implementations (sense/plan/act/observe/reflect) |
| `tools.py` | Unified tool registry (CLI + MCP + API) |
| `agents.py` | Pydantic AI agent definitions |
| `config.py` | Loop configuration and model routing |
| `bridge.py` | SDK bridge (Anthropic/OpenAI/Google) |

## Usage

```python
from ralph import RalphLoop, LoopConfig

config = LoopConfig(
    vault="gkg",
    temperature=0.5,
    max_iterations=10,
    aot_depth=5,
)

loop = RalphLoop(config)
result = await loop.run("What are the highest-priority Delta-Miss LOs in respiratory physiology?")
```
