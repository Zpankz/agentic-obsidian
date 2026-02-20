#!/usr/bin/env python3
"""Agent model routing via cli-proxy.

Loads model_routing.yaml and provides a `get_model_for_agent()` function
that maps (agent_name, task_type) -> model alias for the cli-proxy on
localhost:8317.

Bead: bd-2ma.2

Usage:
    from agents.routing import get_model_for_agent, get_proxy_headers

    model = get_model_for_agent("graph-agent", "reasoning")
    headers = get_proxy_headers()
    # POST to http://127.0.0.1:8317/v1/chat/completions with model & headers
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml

_CONFIG_PATH = Path(__file__).parent / "model_routing.yaml"
_config: Optional[dict] = None


def _load_config() -> dict:
    """Load and cache the routing config."""
    global _config
    if _config is None:
        with open(_CONFIG_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


def get_proxy_url() -> str:
    """Return the cli-proxy base URL."""
    cfg = _load_config()["proxy"]
    return f"http://{cfg['host']}:{cfg['port']}"


def get_proxy_headers() -> dict[str, str]:
    """Return auth headers for cli-proxy requests.

    Checks CLIPROXY_API_KEY env var first, falls back to config.
    """
    cfg = _load_config()
    api_key = os.environ.get("CLIPROXY_API_KEY", cfg["proxy"]["api_key"])
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def get_model_for_agent(
    agent_name: str,
    task_type: str = "general",
) -> str:
    """Resolve the optimal model for a given agent and task type.

    Args:
        agent_name: One of infra-agent, graph-agent, ralph-agent, voice-agent.
        task_type:  One of planning, reasoning, coding, realtime, general.

    Returns:
        Model alias string (e.g. "cl-opus-4-6") usable with cli-proxy.

    Raises:
        KeyError: If agent_name is unknown.
    """
    cfg = _load_config()
    agents = cfg["agents"]

    if agent_name not in agents:
        raise KeyError(
            f"Unknown agent '{agent_name}'. "
            f"Available: {', '.join(agents.keys())}"
        )

    agent_cfg = agents[agent_name]
    routing = agent_cfg.get("task_routing", {})
    return routing.get(task_type, agent_cfg["default_model"])


def get_fallback_chain() -> list[str]:
    """Return the ordered fallback model chain."""
    return _load_config().get("fallback_chain", [])


def list_agents() -> dict[str, str]:
    """Return {agent_name: description} for all configured agents."""
    return {
        name: info["description"]
        for name, info in _load_config()["agents"].items()
    }


# ---------------------------------------------------------------------------
# CLI quick-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    import sys

    print(f"Proxy URL: {get_proxy_url()}")
    print(f"Agents:")
    for name, desc in list_agents().items():
        print(f"  {name}: {desc}")
        for tt in ["coding", "planning", "reasoning", "realtime", "general"]:
            model = get_model_for_agent(name, tt)
            print(f"    {tt:>10s} -> {model}")
    print(f"\nFallback chain: {get_fallback_chain()}")
    print(f"\nHeaders (redacted key): {{", end="")
    h = get_proxy_headers()
    for k, v in h.items():
        if k == "Authorization":
            v = v[:15] + "..."
        print(f" {k}: {v}", end=",")
    print(" }")
