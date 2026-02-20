"""RALPH loop configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Vault(str, Enum):
    GKG = "gkg"
    PKG = "pkg"


class ExplorationMode(str, Enum):
    EXPLORE = "explore"      # High-PageRank, low-confidence paths
    EXPLOIT = "exploit"      # High-priority, low-pass-rate paths
    BALANCE = "balance"      # Priority-weighted MCMC proposals


@dataclass
class LoopConfig:
    """Configuration for a RALPH loop execution."""

    # Vault targeting
    vault: Vault = Vault.GKG
    gkg_path: str = field(default_factory=lambda: os.environ.get("GKG_PATH", "/home/exedev/gkg"))
    pkg_path: str = field(default_factory=lambda: os.environ.get("PKG_PATH", "/home/exedev/pkg"))

    # MCMC traversal
    temperature: float = 0.5
    max_nodes: int = 8
    exploration_mode: ExplorationMode = ExplorationMode.BALANCE

    # AoT reasoning
    aot_depth: int = 5
    aot_light: bool = False  # Use AoT-light (depth 3, early conclusion)

    # Loop control
    max_iterations: int = 10
    convergence_threshold: float = 0.95  # Stop if confidence exceeds this
    timeout_seconds: int = 300

    # Model routing
    primary_model: str = "claude-sonnet-4-20250514"
    fallback_model: str = "gpt-4o"
    reflection_model: str = "claude-sonnet-4-20250514"  # Model for reflect phase

    # Service endpoints
    obsidian_api: str = "http://localhost:3000"
    vault_graph_api: str = "http://localhost:3100"
    turbovault_api: str = "http://localhost:3200"
    cli_proxy: str = "http://localhost:8317"

    # DSPy / self-improvement
    enable_reflection: bool = True
    dspy_teleprompter: str = "BootstrapFewShot"  # or MIPROv2, etc.
    prompt_cache_dir: str = field(default_factory=lambda: os.path.expanduser("~/.cache/ralph/prompts"))

    # Verbosity
    verbose: bool = False
    log_atoms: bool = True

    def vault_path(self) -> str:
        return self.gkg_path if self.vault == Vault.GKG else self.pkg_path

    def temperature_for_mode(self) -> float:
        """Return temperature based on exploration mode if not explicitly set."""
        mode_temps = {
            ExplorationMode.EXPLORE: 0.8,
            ExplorationMode.EXPLOIT: 0.2,
            ExplorationMode.BALANCE: 0.5,
        }
        return mode_temps.get(self.exploration_mode, self.temperature)


@dataclass
class LoopState:
    """Mutable state carried through loop iterations."""

    iteration: int = 0
    confidence: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)
    atoms: list[dict[str, Any]] = field(default_factory=list)
    actions_taken: list[dict[str, Any]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    reflections: list[str] = field(default_factory=list)
    converged: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "confidence": self.confidence,
            "converged": self.converged,
            "atoms_count": len(self.atoms),
            "actions_count": len(self.actions_taken),
            "error": self.error,
        }
