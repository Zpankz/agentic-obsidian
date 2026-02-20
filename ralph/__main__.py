"""RALPH CLI runner.

Usage:
    python -m ralph "What are the highest-priority Delta-Miss LOs?"
    python -m ralph --mode explore --max-iter 5 "volatile agent pharmacology"
    python -m ralph --verbose --vault pkg "identity and methodology notes"
"""

import argparse
import asyncio
import json
import logging
import sys

from ralph.config import LoopConfig, ExplorationMode, Vault
from ralph.loop import RalphLoop


def main():
    parser = argparse.ArgumentParser(description="RALPH — Recursive Agentic Language Processing Heuristic")
    parser.add_argument("query", help="Query to process through the RALPH loop")
    parser.add_argument("--vault", choices=["gkg", "pkg"], default="gkg", help="Target vault")
    parser.add_argument("--mode", choices=["explore", "exploit", "balance"], default="balance", help="Exploration mode")
    parser.add_argument("--temperature", type=float, default=None, help="Override temperature")
    parser.add_argument("--max-iter", type=int, default=10, help="Max loop iterations")
    parser.add_argument("--max-nodes", type=int, default=8, help="Max MCMC traversal nodes")
    parser.add_argument("--aot-depth", type=int, default=5, help="AoT max depth")
    parser.add_argument("--no-reflect", action="store_true", help="Disable reflection phase")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    config = LoopConfig(
        vault=Vault(args.vault),
        exploration_mode=ExplorationMode(args.mode),
        max_iterations=args.max_iter,
        max_nodes=args.max_nodes,
        aot_depth=args.aot_depth,
        enable_reflection=not args.no_reflect,
        verbose=args.verbose,
    )
    if args.temperature is not None:
        config.temperature = args.temperature

    loop = RalphLoop(config)
    result = asyncio.run(loop.run(args.query))

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.summary())
        if args.verbose:
            print("\nIteration details:")
            for it in result.iterations:
                print(f"  #{it.iteration}: atoms={it.atoms_count}, "
                      f"actions={it.actions_succeeded}/{it.actions_count}, "
                      f"confidence={it.confidence:.3f}")


if __name__ == "__main__":
    main()
