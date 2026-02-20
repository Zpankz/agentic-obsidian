"""RALPH — Recursive Agentic Language Processing Heuristic.

A neurosymbolic agent loop framework integrating vault knowledge,
graph analytics, Atom-of-Thoughts reasoning, and self-improving prompts.
"""

from ralph.config import LoopConfig
from ralph.loop import RalphLoop
from ralph.tools import ToolRegistry
from ralph.bridge import ModelBridge
from ralph.aot import AoTClient
from ralph.mcp_client import StdioMcpClient

__all__ = [
    "RalphLoop", "LoopConfig", "ToolRegistry",
    "ModelBridge", "AoTClient", "StdioMcpClient",
]
__version__ = "0.1.0"
