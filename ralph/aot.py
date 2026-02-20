"""Atom-of-Thoughts MCP client.

Async Python client that spawns the AoT MCP server as a subprocess
and communicates via JSON-RPC over stdio.  Exposes three tools:
  - AoT        (full reasoning chain, depth ≤ 5)
  - AoT-light  (fast mode, depth 3, early conclusion)
  - atomcommands (decompose / complete / status / conclusion / set_max_depth)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ralph.mcp_client import StdioMcpClient, McpError

logger = logging.getLogger("ralph.aot")

# Path to the compiled AoT MCP server
AOT_SERVER_PATH = "/home/exedev/agentic-obsidian/ecosystem/atom-of-thoughts/build/index.js"


class AoTClient:
    """High-level async client for the Atom-of-Thoughts MCP server.

    Lifecycle::

        client = AoTClient()
        await client.start()
        result = await client.aot(atomId="P1", content="...", ...)
        await client.stop()

    Or as an async context manager::

        async with AoTClient() as client:
            result = await client.aot(...)
    """

    def __init__(self, server_path: str = AOT_SERVER_PATH):
        self._mcp = StdioMcpClient(
            command=["node", server_path],
            name="atom-of-thoughts",
        )
        self._started = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Spawn the AoT MCP server subprocess and run the MCP handshake."""
        if self._started:
            return
        logger.info("Starting AoT MCP server…")
        await self._mcp.initialize()
        self._started = True
        logger.info("AoT MCP server ready")

    async def stop(self) -> None:
        """Terminate the AoT MCP server subprocess."""
        if not self._started:
            return
        logger.info("Stopping AoT MCP server…")
        await self._mcp.close()
        self._started = False

    async def __aenter__(self) -> "AoTClient":
        await self.start()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_started(self) -> None:
        if not self._started:
            raise RuntimeError("AoTClient not started — call .start() or use 'async with'")

    async def _call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the AoT server, return the parsed result."""
        self._ensure_started()
        resp = await self._mcp.call_tool(tool_name, arguments)
        return resp

    # ------------------------------------------------------------------
    # Tool: AoT (full reasoning, depth ≤ 5)
    # ------------------------------------------------------------------

    async def aot(
        self,
        *,
        atomId: str,
        content: str,
        atomType: str,
        dependencies: list[str],
        confidence: float,
        isVerified: bool = False,
        depth: int | None = None,
    ) -> dict[str, Any]:
        """Submit an atom to the full AoT reasoning chain.

        Parameters
        ----------
        atomId : str
            Unique identifier (e.g. ``"P1"``, ``"H2"``).
        content : str
            The atom's textual content.
        atomType : str
            One of ``premise``, ``reasoning``, ``hypothesis``,
            ``verification``, ``conclusion``.
        dependencies : list[str]
            IDs of atoms this one depends on.
        confidence : float
            Confidence score 0–1.
        isVerified : bool
            Whether this atom has been verified.
        depth : int | None
            Depth level in the decomposition-contraction process.
        """
        args: dict[str, Any] = {
            "atomId": atomId,
            "content": content,
            "atomType": atomType,
            "dependencies": dependencies,
            "confidence": confidence,
            "isVerified": isVerified,
        }
        if depth is not None:
            args["depth"] = depth
        return await self._call("AoT", args)

    # ------------------------------------------------------------------
    # Tool: AoT-light (fast mode, depth 3, early conclusion)
    # ------------------------------------------------------------------

    async def aot_light(
        self,
        *,
        atomId: str,
        content: str,
        atomType: str,
        dependencies: list[str],
        confidence: float,
        isVerified: bool = False,
        depth: int | None = None,
    ) -> dict[str, Any]:
        """Submit an atom to the lightweight AoT chain (depth ≤ 3).

        Same parameters as :meth:`aot` but uses a faster processing
        pipeline with immediate conclusion suggestion for high-confidence
        hypotheses.
        """
        args: dict[str, Any] = {
            "atomId": atomId,
            "content": content,
            "atomType": atomType,
            "dependencies": dependencies,
            "confidence": confidence,
            "isVerified": isVerified,
        }
        if depth is not None:
            args["depth"] = depth
        return await self._call("AoT-light", args)

    # ------------------------------------------------------------------
    # Tool: atomcommands (decompose / contract / terminate)
    # ------------------------------------------------------------------

    async def atomcommands(
        self,
        *,
        command: str,
        atomId: str | None = None,
        decompositionId: str | None = None,
        maxDepth: int | None = None,
    ) -> dict[str, Any]:
        """Execute a control command on the AoT server.

        Commands
        --------
        decompose
            Start decomposition of *atomId* into sub-atoms.
        complete_decomposition
            Complete the decomposition identified by *decompositionId*.
        termination_status
            Check whether reasoning should terminate.
        best_conclusion
            Get the highest-confidence verified conclusion.
        set_max_depth
            Change the maximum depth to *maxDepth*.
        """
        args: dict[str, Any] = {"command": command}
        if atomId is not None:
            args["atomId"] = atomId
        if decompositionId is not None:
            args["decompositionId"] = decompositionId
        if maxDepth is not None:
            args["maxDepth"] = maxDepth
        return await self._call("atomcommands", args)

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    async def decompose(self, atom_id: str) -> dict[str, Any]:
        """Start decomposition of the given atom."""
        return await self.atomcommands(command="decompose", atomId=atom_id)

    async def complete_decomposition(self, decomposition_id: str) -> dict[str, Any]:
        """Complete a decomposition."""
        return await self.atomcommands(command="complete_decomposition", decompositionId=decomposition_id)

    async def termination_status(self) -> dict[str, Any]:
        """Check whether the reasoning chain should terminate."""
        return await self.atomcommands(command="termination_status")

    async def best_conclusion(self) -> dict[str, Any]:
        """Get the best verified conclusion."""
        return await self.atomcommands(command="best_conclusion")

    async def set_max_depth(self, depth: int) -> dict[str, Any]:
        """Change the maximum reasoning depth."""
        return await self.atomcommands(command="set_max_depth", maxDepth=depth)


# ---------------------------------------------------------------------------
# Singleton management (for ToolRegistry integration)
# ---------------------------------------------------------------------------

_singleton: AoTClient | None = None
_singleton_lock = asyncio.Lock()


async def get_aot_client() -> AoTClient:
    """Return a lazily-started singleton AoTClient."""
    global _singleton
    async with _singleton_lock:
        if _singleton is None:
            _singleton = AoTClient()
            await _singleton.start()
        return _singleton


async def shutdown_aot_client() -> None:
    """Stop the singleton AoTClient if it's running."""
    global _singleton
    async with _singleton_lock:
        if _singleton is not None:
            await _singleton.stop()
            _singleton = None
