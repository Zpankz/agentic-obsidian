# Atom of Thoughts (AoT) — Research Report

## 1. What is Atom of Thoughts?

Atom of Thoughts (AoT) is a reasoning framework from the NeurIPS 2025 paper
**"Atom of Thoughts for Markov LLM Test-Time Scaling"** (Teng et al., 2025)
([arXiv:2502.12018](https://arxiv.org/abs/2502.12018)).

It decomposes complex questions into **atomic question states** — small,
independent, self-contained sub-problems. The reasoning process is modeled as
a **Markov chain over atomic states**, where each transition uses a two-phase
mechanism:

1. **Decomposition** — Break the current question into a dependency-based
   directed acyclic graph (DAG) of sub-questions.
2. **Contraction** — Solve the sub-questions and contract the DAG back into a
   new, simpler atomic question state.

This repeats until a final answer emerges. Unlike Chain-of-Thought (linear) or
Tree-of-Thought (branching), AoT is a **DAG-structured, Markov reasoning
process** that discards resolved history, focusing compute on what matters.

### Five Atom Types
| Type | Role |
|------|------|
| `premise` | Given information / base assumptions |
| `reasoning` | Logical inference from other atoms |
| `hypothesis` | Proposed solution or intermediate conclusion |
| `verification` | Validity check (especially of hypotheses) |
| `conclusion` | Verified final answer |

Each atom carries:
- **dependencies** — which other atoms it depends on
- **confidence** — 0–1 score
- **isVerified** — boolean
- **depth** — position in the decomposition-contraction tree

## 2. Is it an MCP Server/Tool?

**Yes.** There are two community MCP server implementations:

### a) kbsooo/MCP_Atom_of_Thoughts (⭐54, JavaScript)
- GitHub: https://github.com/kbsooo/MCP_Atom_of_Thoughts
- Listed on Smithery, Glama, MCP.so
- **Install:**
  ```bash
  npx -y @smithery/cli install @kbsooo/mcp_atom_of_thoughts --client claude
  ```
  or manual config:
  ```json
  {
    "mcpServers": {
      "atom-of-thoughts": {
        "command": "node",
        "args": ["/path/to/atom-of-thoughts/build/index.js"]
      }
    }
  }
  ```
- **Tools exposed:** `AoT` (full, depth 5), `AoT-light` (fast, depth 3), `atomcommands`

### b) dioptx/mcp-atom-of-thoughts (TypeScript, npm package)
- GitHub: https://github.com/dioptx/mcp-atom-of-thoughts
- npm: `@dioptx/mcp-atom-of-thoughts`
- 121 tests, D3 visualization, approval UI
- **Install (zero-install via npx):**
  ```json
  {
    "mcpServers": {
      "atom-of-thoughts": {
        "command": "npx",
        "args": ["-y", "@dioptx/mcp-atom-of-thoughts"]
      }
    }
  }
  ```
- **Additional tools:** `export_graph` (JSON), `generate_visualization` (D3 HTML),
  `check_approval` (human-in-the-loop)
- **CLI flags:** `--mode full|fast|both`, `--no-viz`, `--max-depth <n>`,
  `--output-dir`, `--downloads-dir`

### Official research repo (Python, not MCP)
- https://github.com/qixucen/atom (NeurIPS 2025)
- Pure Python evaluation harness; benchmarks on MATH, GSM8K, BBH, MMLU, HotpotQA, LongBench
- Can run in `atom` mode (standalone) or `plugin` mode (preprocessor for other methods)

## 3. How Does It Relate to MCMC Reasoning / Neurosymbolic Scaffolding?

AoT is directly relevant to MCMC-style reasoning:

- **Markov property**: Each atomic state is self-contained. The next state
  depends only on the current atomic question, not the full history. This is
  explicitly a Markov chain over question states.
- **State transitions via decompose→contract**: Analogous to MCMC proposal
  distributions — decomposition proposes sub-states, contraction accepts/refines.
- **Confidence tracking**: Each atom has a confidence score, enabling
  probabilistic assessment akin to posterior estimation.
- **DAG structure**: The dependency graph is a symbolic scaffold — atoms have
  typed relationships (premise→reasoning→hypothesis→verification→conclusion),
  making it a neurosymbolic approach.
- **Plugin architecture**: AoT can serve as a preprocessor for other test-time
  scaling methods (e.g., best-of-N, beam search), combining symbolic
  decomposition with stochastic sampling.
- **Auto-termination**: Stops when confidence exceeds threshold or max depth
  reached — similar to convergence criteria in MCMC.

**Key distinction from Chain-of-Thought**: CoT accumulates history linearly
(error compounds). AoT's Markov property discards resolved history, keeping
only the contracted atomic state — more computationally efficient and less
prone to error accumulation.

## 4. Installation Methods

### For MCP integration (recommended: dioptx version)
```bash
# Zero-install via npx
npx -y @dioptx/mcp-atom-of-thoughts

# Or global install
npm install -g @dioptx/mcp-atom-of-thoughts

# Or via Smithery
npx -y @smithery/cli install @dioptx/mcp-atom-of-thoughts --client claude

# Or Docker
docker build -t aot .
docker run -i --rm aot
```

### For MCP integration (kbsooo version — more stars)
```bash
npx -y @smithery/cli install @kbsooo/mcp_atom_of_thoughts --client claude
```

### For research/benchmarking (official Python)
```bash
git clone https://github.com/qixucen/atom.git
cd atom
# Create apikey.py with your OpenAI key
python main.py --dataset math --start 0 --end 10 --model gpt-4o-mini
```

## 5. How It Integrates with Vault Graph Analytics

AoT does **not** natively integrate with Obsidian vault graphs. However, the
conceptual alignment is strong and integration is straightforward:

### Natural Parallels
| AoT Concept | Vault Graph Concept |
|-------------|--------------------|
| Atom (node) | Note / block |
| Dependency edge | Wiki-link / backlink |
| Atom type (premise/reasoning/etc.) | Note tag / frontmatter type |
| Confidence score | Custom metadata field |
| DAG decomposition | Note hierarchy / MOC structure |
| Contraction | Summary note linking sub-notes |

### Integration Approaches

1. **Reasoning-over-vault**: Use AoT MCP server alongside a vault-reading MCP
   server. AoT decomposes a complex vault query into atomic sub-questions;
   each sub-question queries vault content; results contract into a conclusion.

2. **Graph export → AoT input**: Export vault link graph as JSON;
   feed as premises into AoT for structural analysis (e.g., "what are the
   key clusters?", "what's missing?").

3. **AoT visualization ↔ vault graph**: The dioptx version's D3 force-directed
   graph visualization is structurally identical to Obsidian's graph view.
   Reasoning traces could be stored as vault notes with frontmatter:
   ```yaml
   ---
   atom_type: hypothesis
   confidence: 0.85
   dependencies: ["premise-1", "reasoning-2"]
   verified: true
   ---
   ```

4. **Plugin mode for vault preprocessing**: Use AoT's `plugin` mode to
   generate contracted/simplified versions of complex vault queries before
   passing to other reasoning tools.

## Summary

| Aspect | Detail |
|--------|--------|
| **What** | Markov-chain reasoning framework decomposing problems into atomic DAG states |
| **Paper** | NeurIPS 2025, arXiv:2502.12018 |
| **MCP?** | Yes — two implementations (kbsooo/JS ⭐54, dioptx/TS with viz) |
| **MCMC relation** | Direct — Markov states, confidence tracking, auto-termination |
| **Install** | `npx -y @dioptx/mcp-atom-of-thoughts` or Smithery |
| **Vault integration** | Not native, but DAG atoms map cleanly to vault notes + links |
