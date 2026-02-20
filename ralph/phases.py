"""RALPH loop phase implementations.

Each phase is a standalone async function:
  sense  → Gather context from vault + graph
  plan   → Decompose via Atom-of-Thoughts
  act    → Execute tool calls from plan
  observe → Measure state changes
  reflect → Update prompts/weights (DSPy)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ralph.config import LoopConfig, LoopState
from ralph.tools import ToolRegistry

logger = logging.getLogger("ralph.phases")


async def sense(query: str, config: LoopConfig, state: LoopState, tools: ToolRegistry) -> dict[str, Any]:
    """Phase 1: Gather context from vault and graph analytics.

    Collects:
    - Graph analytics summary (node counts, clusters, orphans)
    - MCMC traversal results for the query
    - Relevant vault content via search
    - Current task/bead state
    """
    logger.info(f"SENSE: gathering context for '{query}'")
    context: dict[str, Any] = {"query": query}

    # Graph analytics summary
    try:
        summary = await tools.call("analytics_summary")
        context["graph_summary"] = summary
    except Exception as e:
        logger.warning(f"Failed to get analytics summary: {e}")
        context["graph_summary"] = None

    # MCMC traversal
    try:
        traversal = await tools.call(
            "mcmc_traverse",
            query=query,
            max_nodes=config.max_nodes,
            temperature=config.temperature_for_mode(),
        )
        context["traversal"] = traversal
    except Exception as e:
        logger.warning(f"Failed MCMC traversal: {e}")
        context["traversal"] = None

    # Vault search
    try:
        search_results = await tools.call("vault_search", q=query)
        context["search_results"] = search_results
    except Exception as e:
        logger.warning(f"Failed vault search: {e}")
        context["search_results"] = None

    state.context = context
    return context


async def plan(context: dict[str, Any], config: LoopConfig, state: LoopState, tools: ToolRegistry) -> list[dict[str, Any]]:
    """Phase 2: Decompose the task via Atom-of-Thoughts.

    Uses AoT to break the query into atomic reasoning steps:
    premise → reasoning → hypothesis → verification → conclusion

    Each atom carries: atomId, content, atomType, confidence, dependencies, depth.
    """
    logger.info("PLAN: decomposing via AoT")
    query = context.get("query", "")

    # Build context string from sense results
    context_parts = []
    if context.get("graph_summary"):
        context_parts.append(f"Graph: {json.dumps(context['graph_summary'], default=str)[:500]}")
    if context.get("traversal"):
        traversal = context["traversal"]
        if isinstance(traversal, dict) and "nodes" in traversal:
            node_names = [n.get("file", n.get("name", "?")) for n in traversal["nodes"][:5]]
            context_parts.append(f"Traversal nodes: {', '.join(node_names)}")
    if context.get("search_results"):
        sr = context["search_results"]
        if isinstance(sr, list):
            context_parts.append(f"Search hits: {len(sr)} results")

    # Build atoms for the plan
    # In production this calls the AoT MCP server; for now we build a structured plan
    atoms = []

    # Premise: what we know from sense
    atoms.append({
        "atomId": f"premise-{state.iteration}",
        "atomType": "premise",
        "content": f"Query: {query}. Context: {'; '.join(context_parts)}",
        "confidence": 0.9,
        "dependencies": [],
        "depth": 0,
    })

    # If traversal returned nodes, create reasoning atoms for each
    traversal = context.get("traversal", {})
    if isinstance(traversal, dict):
        # MCMC API returns {traversal: [{rank, path, relevance, pagerank, ...}]}
        nodes = traversal.get("traversal", []) or traversal.get("nodes", [])
        for i, node in enumerate(nodes[:config.max_nodes]):
            # Extract file basename from path (e.g. "LO/CICM/.../file.md" -> "file")
            node_path = node.get("path", node.get("file", f"node-{i}"))
            file_name = node_path.rsplit("/", 1)[-1].replace(".md", "") if "/" in node_path else node_path
            relevance = node.get("relevance", 0.5)
            atoms.append({
                "atomId": f"read-{state.iteration}-{i}",
                "atomType": "reasoning",
                "content": f"Read and analyze: {file_name} (relevance={relevance:.2f})",
                "confidence": 0.3 + (relevance * 0.3),  # Scale confidence by relevance
                "dependencies": [f"premise-{state.iteration}"],
                "depth": 1,
                "action": {"tool": "smart_read", "kwargs": {"file": file_name}},
            })

    # Hypothesis: synthesis atom
    atoms.append({
        "atomId": f"hypothesis-{state.iteration}",
        "atomType": "hypothesis",
        "content": f"Synthesize findings for: {query}",
        "confidence": 0.3,
        "dependencies": [a["atomId"] for a in atoms if a["atomType"] == "reasoning"],
        "depth": 2,
    })

    state.atoms.extend(atoms)
    return atoms


async def act(atoms: list[dict[str, Any]], config: LoopConfig, state: LoopState, tools: ToolRegistry) -> list[dict[str, Any]]:
    """Phase 3: Execute tool calls from plan atoms.

    Processes atoms that have an 'action' key, dispatching to the tool registry.
    """
    logger.info(f"ACT: executing {len(atoms)} atoms")
    results = []

    for atom in atoms:
        action = atom.get("action")
        if not action:
            continue

        tool_name = action["tool"]
        kwargs = action.get("kwargs", {})

        try:
            result = await tools.call(tool_name, **kwargs)
            results.append({
                "atomId": atom["atomId"],
                "tool": tool_name,
                "success": True,
                "result": result,
            })
            atom["confidence"] = min(atom["confidence"] + 0.2, 1.0)
        except Exception as e:
            logger.error(f"Action failed for {atom['atomId']}: {e}")
            results.append({
                "atomId": atom["atomId"],
                "tool": tool_name,
                "success": False,
                "error": str(e),
            })

    state.actions_taken.extend(results)
    return results


async def observe(action_results: list[dict[str, Any]], config: LoopConfig, state: LoopState, tools: ToolRegistry) -> list[dict[str, Any]]:
    """Phase 4: Measure state changes after actions.

    Checks:
    - How many actions succeeded vs failed
    - Updated graph metrics (if graph was modified)
    - Validation status (if vault content changed)
    - Confidence convergence across atoms
    """
    logger.info("OBSERVE: measuring state changes")
    observations = []

    # Action success rate
    successes = sum(1 for r in action_results if r.get("success"))
    total = len(action_results)
    success_rate = successes / total if total > 0 else 0.0
    observations.append({
        "metric": "action_success_rate",
        "value": success_rate,
        "detail": f"{successes}/{total} actions succeeded",
    })

    # Average confidence across atoms
    if state.atoms:
        avg_conf = sum(a.get("confidence", 0) for a in state.atoms) / len(state.atoms)
        observations.append({
            "metric": "avg_atom_confidence",
            "value": avg_conf,
        })
        state.confidence = avg_conf

    # Check convergence
    if state.confidence >= config.convergence_threshold:
        state.converged = True
        observations.append({
            "metric": "converged",
            "value": True,
            "detail": f"Confidence {state.confidence:.2f} >= threshold {config.convergence_threshold}",
        })

    state.observations.extend(observations)
    return observations


async def reflect(observations: list[dict[str, Any]], config: LoopConfig, state: LoopState, tools: ToolRegistry) -> str:
    """Phase 5: Update prompts/weights based on observations.

    Uses DSPy teleprompter (when enabled) to:
    - Evaluate which prompt templates produced best results
    - Generate improved few-shot examples
    - Update GEPA prompt weights

    For now: produces a textual reflection summarizing the iteration.
    """
    logger.info("REFLECT: analyzing iteration outcomes")

    if not config.enable_reflection:
        summary = "Reflection disabled."
        state.reflections.append(summary)
        return summary

    # Build reflection summary
    parts = [f"Iteration {state.iteration}:"]

    for obs in observations:
        metric = obs.get("metric", "unknown")
        value = obs.get("value", "?")
        detail = obs.get("detail", "")
        parts.append(f"  - {metric}: {value} {detail}")

    if state.converged:
        parts.append("  → CONVERGED — loop will terminate.")
    else:
        # Suggest adjustments
        success_obs = next((o for o in observations if o["metric"] == "action_success_rate"), None)
        if success_obs and success_obs["value"] < 0.5:
            parts.append("  → Low success rate. Consider: broader search, different traversal temperature.")

        conf_obs = next((o for o in observations if o["metric"] == "avg_atom_confidence"), None)
        if conf_obs and conf_obs["value"] < 0.3:
            parts.append("  → Low confidence. Consider: more premise atoms, deeper AoT decomposition.")

    summary = "\n".join(parts)
    state.reflections.append(summary)

    # TODO: DSPy teleprompter integration
    # When enabled, this would:
    # 1. Score the current prompt template based on observation metrics
    # 2. Use BootstrapFewShot to generate improved examples
    # 3. Update prompt cache at config.prompt_cache_dir
    # See bd-1yj.4 for DSPy module implementation

    return summary
