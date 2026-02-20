"""RALPH core loop engine.

Executes the sense → plan → act → observe → reflect cycle
until convergence or max iterations.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from ralph.config import LoopConfig, LoopState
from ralph.phases import sense, plan, act, observe, reflect
from ralph.tools import ToolRegistry

logger = logging.getLogger("ralph")


class RalphLoop:
    """The main RALPH execution engine."""

    def __init__(self, config: LoopConfig | None = None):
        self.config = config or LoopConfig()
        self.tools = ToolRegistry(config=self.config)
        self.state = LoopState()
        self._start_time: float = 0

    async def run(self, query: str) -> LoopResult:
        """Execute the full RALPH loop for a given query.

        Returns a LoopResult with all iteration data.
        """
        self._start_time = time.monotonic()
        logger.info(f"RALPH loop starting: '{query}' (max_iter={self.config.max_iterations})")

        iterations: list[IterationRecord] = []

        try:
            while not self._should_stop():
                self.state.iteration += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"Iteration {self.state.iteration}/{self.config.max_iterations}")
                logger.info(f"{'='*60}")

                record = await self._run_iteration(query)
                iterations.append(record)

                if self.state.converged:
                    logger.info("Loop converged.")
                    break

        except asyncio.TimeoutError:
            self.state.error = "Timeout exceeded"
            logger.error(f"Loop timed out after {self.config.timeout_seconds}s")
        except Exception as e:
            self.state.error = str(e)
            logger.error(f"Loop error: {e}", exc_info=True)
        finally:
            await self.tools.close()

        elapsed = time.monotonic() - self._start_time
        return LoopResult(
            query=query,
            iterations=iterations,
            final_state=self.state,
            elapsed_seconds=elapsed,
            converged=self.state.converged,
        )

    async def _run_iteration(self, query: str) -> IterationRecord:
        """Execute one full RALPH cycle."""
        record = IterationRecord(iteration=self.state.iteration)

        # 1. SENSE
        context = await sense(query, self.config, self.state, self.tools)
        record.context_keys = list(context.keys())

        # 2. PLAN
        atoms = await plan(context, self.config, self.state, self.tools)
        record.atoms_count = len(atoms)
        record.atom_types = [a["atomType"] for a in atoms]

        # 3. ACT
        action_results = await act(atoms, self.config, self.state, self.tools)
        record.actions_count = len(action_results)
        record.actions_succeeded = sum(1 for r in action_results if r.get("success"))

        # 4. OBSERVE
        observations = await observe(action_results, self.config, self.state, self.tools)
        record.observations = observations

        # 5. REFLECT
        reflection = await reflect(observations, self.config, self.state, self.tools)
        record.reflection = reflection

        record.confidence = self.state.confidence
        record.converged = self.state.converged

        if self.config.verbose:
            logger.info(f"Iteration {self.state.iteration} summary:")
            logger.info(f"  Atoms: {record.atoms_count}, Actions: {record.actions_count}/{record.actions_succeeded}")
            logger.info(f"  Confidence: {record.confidence:.2f}, Converged: {record.converged}")
            logger.info(f"  Reflection: {reflection}")

        return record

    def _should_stop(self) -> bool:
        """Check termination conditions."""
        if self.state.converged:
            return True
        if self.state.iteration >= self.config.max_iterations:
            logger.info(f"Max iterations ({self.config.max_iterations}) reached.")
            return True
        elapsed = time.monotonic() - self._start_time
        if elapsed > self.config.timeout_seconds:
            return True
        if self.state.error:
            return True
        return False


class IterationRecord:
    """Record of a single RALPH iteration."""

    def __init__(self, iteration: int = 0):
        self.iteration = iteration
        self.context_keys: list[str] = []
        self.atoms_count: int = 0
        self.atom_types: list[str] = []
        self.actions_count: int = 0
        self.actions_succeeded: int = 0
        self.observations: list[dict[str, Any]] = []
        self.reflection: str = ""
        self.confidence: float = 0.0
        self.converged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "atoms": self.atoms_count,
            "atom_types": self.atom_types,
            "actions": f"{self.actions_succeeded}/{self.actions_count}",
            "confidence": round(self.confidence, 3),
            "converged": self.converged,
        }


class LoopResult:
    """Final result of a RALPH loop execution."""

    def __init__(
        self,
        query: str,
        iterations: list[IterationRecord],
        final_state: LoopState,
        elapsed_seconds: float,
        converged: bool,
    ):
        self.query = query
        self.iterations = iterations
        self.final_state = final_state
        self.elapsed_seconds = elapsed_seconds
        self.converged = converged

    def summary(self) -> str:
        lines = [
            f"RALPH Loop Result",
            f"  Query: {self.query}",
            f"  Iterations: {len(self.iterations)}",
            f"  Converged: {self.converged}",
            f"  Final confidence: {self.final_state.confidence:.3f}",
            f"  Total atoms: {len(self.final_state.atoms)}",
            f"  Total actions: {len(self.final_state.actions_taken)}",
            f"  Elapsed: {self.elapsed_seconds:.1f}s",
        ]
        if self.final_state.error:
            lines.append(f"  Error: {self.final_state.error}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "iterations": [it.to_dict() for it in self.iterations],
            "converged": self.converged,
            "confidence": round(self.final_state.confidence, 3),
            "atoms": len(self.final_state.atoms),
            "actions": len(self.final_state.actions_taken),
            "elapsed": round(self.elapsed_seconds, 1),
            "error": self.final_state.error,
        }
