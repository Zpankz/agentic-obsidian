"""DSPy modules for self-improving GEPA prompts.

GEPA = Generate → Evaluate → Propose → Apply

Uses DSPy teleprompters to automatically optimize prompt templates
based on graph analytics feedback signals.
"""

from __future__ import annotations

import logging
import json
import os
from typing import Any

logger = logging.getLogger("ralph.dspy")

try:
    import dspy
    HAS_DSPY = True
except ImportError:
    HAS_DSPY = False


# --- Signatures ---

if HAS_DSPY:

    class VaultQuery(dspy.Signature):
        """Query the neurosymbolic vault for relevant knowledge."""
        question: str = dspy.InputField(desc="User's question about the knowledge graph")
        context: str = dspy.InputField(desc="Graph analytics context (PageRank, clusters, traversal)")
        answer: str = dspy.OutputField(desc="Structured answer with vault references")
        confidence: float = dspy.OutputField(desc="Confidence score 0-1")
        evidence_paths: list[str] = dspy.OutputField(desc="Vault file paths supporting the answer")

    class DeltaMissAnalysis(dspy.Signature):
        """Identify curriculum gaps (Delta-Miss) from graph analytics."""
        graph_summary: str = dspy.InputField(desc="Graph analytics summary JSON")
        lo_data: str = dspy.InputField(desc="Learning objective data")
        saq_data: str = dspy.InputField(desc="SAQ exam data with pass rates")
        gaps: list[str] = dspy.OutputField(desc="Identified knowledge gaps")
        priority_scores: list[float] = dspy.OutputField(desc="Priority score for each gap")
        recommended_actions: list[str] = dspy.OutputField(desc="Suggested study actions")

    class PromptEvolution(dspy.Signature):
        """Evolve a GEPA prompt based on performance metrics."""
        current_prompt: str = dspy.InputField(desc="Current prompt template")
        performance_metrics: str = dspy.InputField(desc="JSON metrics from recent iterations")
        failure_modes: str = dspy.InputField(desc="Common failure patterns")
        improved_prompt: str = dspy.OutputField(desc="Improved prompt template")
        changes_rationale: str = dspy.OutputField(desc="Why these changes were made")

    class AtomDecomposition(dspy.Signature):
        """Decompose a complex query into AoT atoms."""
        query: str = dspy.InputField(desc="Complex query to decompose")
        context: str = dspy.InputField(desc="Available context and constraints")
        atoms: list[str] = dspy.OutputField(desc="Ordered list of atomic reasoning steps")
        atom_types: list[str] = dspy.OutputField(desc="Type for each atom: premise/reasoning/hypothesis/verification/conclusion")
        dependencies: list[str] = dspy.OutputField(desc="Dependency graph as JSON")


# --- Modules ---

    class VaultQueryModule(dspy.Module):
        """DSPy module for vault queries with chain-of-thought."""

        def __init__(self):
            super().__init__()
            self.query = dspy.ChainOfThought(VaultQuery)

        def forward(self, question: str, context: str) -> Any:
            return self.query(question=question, context=context)

    class DeltaMissModule(dspy.Module):
        """DSPy module for Delta-Miss gap analysis."""

        def __init__(self):
            super().__init__()
            self.analyze = dspy.ChainOfThought(DeltaMissAnalysis)

        def forward(self, graph_summary: str, lo_data: str, saq_data: str) -> Any:
            return self.analyze(
                graph_summary=graph_summary,
                lo_data=lo_data,
                saq_data=saq_data,
            )

    class GEPAEvolver(dspy.Module):
        """GEPA prompt evolution via DSPy optimization.

        Generate → Evaluate → Propose → Apply cycle.
        """

        def __init__(self):
            super().__init__()
            self.evolve = dspy.ChainOfThought(PromptEvolution)

        def forward(self, current_prompt: str, performance_metrics: str, failure_modes: str) -> Any:
            return self.evolve(
                current_prompt=current_prompt,
                performance_metrics=performance_metrics,
                failure_modes=failure_modes,
            )


# --- Teleprompter Integration ---


def optimize_module(
    module: Any,
    trainset: list[dict[str, Any]],
    teleprompter: str = "BootstrapFewShot",
    metric: Any = None,
    cache_dir: str = "~/.cache/ralph/prompts",
) -> Any:
    """Optimize a DSPy module using the specified teleprompter.

    Args:
        module: DSPy module to optimize
        trainset: Training examples as dspy.Example objects
        teleprompter: "BootstrapFewShot", "MIPROv2", "COPRO", etc.
        metric: Scoring function(example, prediction) -> float
        cache_dir: Directory to cache optimized prompts

    Returns:
        Optimized module
    """
    if not HAS_DSPY:
        raise RuntimeError("dspy not installed. Run: pip install dspy-ai")

    cache_dir = os.path.expanduser(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

    # Convert dicts to dspy.Example
    examples = [dspy.Example(**d).with_inputs(*[k for k in d.keys() if k != "answer"]) for d in trainset]

    # Select teleprompter
    if teleprompter == "BootstrapFewShot":
        tp = dspy.BootstrapFewShot(metric=metric, max_bootstrapped_demos=4)
    elif teleprompter == "MIPROv2":
        tp = dspy.MIPROv2(metric=metric, num_candidates=5)
    else:
        raise ValueError(f"Unknown teleprompter: {teleprompter}")

    # Compile
    optimized = tp.compile(module, trainset=examples)

    # Cache the optimized module
    cache_path = os.path.join(cache_dir, f"{module.__class__.__name__}_optimized.json")
    try:
        optimized.save(cache_path)
        logger.info(f"Cached optimized module to {cache_path}")
    except Exception as e:
        logger.warning(f"Failed to cache module: {e}")

    return optimized


def configure_dspy_lm(
    model: str = "claude-sonnet-4-20250514",
    api_key: str | None = None,
    proxy_url: str = "http://localhost:8317",
) -> None:
    """Configure DSPy's language model, routing through cli-proxy when available."""
    if not HAS_DSPY:
        raise RuntimeError("dspy not installed")

    # Try cli-proxy first (OpenAI-compatible endpoint)
    try:
        lm = dspy.LM(
            model=f"openai/{model}",
            api_base=f"{proxy_url}/v1",
            api_key=api_key or "proxy",
        )
        dspy.configure(lm=lm)
        logger.info(f"DSPy configured with cli-proxy: {model}")
        return
    except Exception as e:
        logger.warning(f"cli-proxy failed for DSPy: {e}")

    # Fall back to direct Anthropic
    if "claude" in model:
        lm = dspy.LM(
            model=f"anthropic/{model}",
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", ""),
        )
    elif "gpt" in model:
        lm = dspy.LM(
            model=f"openai/{model}",
            api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
        )
    else:
        lm = dspy.LM(model=model)

    dspy.configure(lm=lm)
    logger.info(f"DSPy configured with direct SDK: {model}")
