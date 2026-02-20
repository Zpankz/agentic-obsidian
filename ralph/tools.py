"""Unified tool registry — binds all CLI, MCP, and API tools into a single dispatch layer."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

import httpx

from ralph.aot import get_aot_client

logger = logging.getLogger("ralph.tools")


class ToolKind(str, Enum):
    CLI = "cli"          # Shell command
    HTTP = "http"        # REST API call
    MCP = "mcp"          # JSON-RPC MCP tool
    PYTHON = "python"    # Native Python callable


@dataclass
class Tool:
    """A single callable tool in the registry."""
    name: str
    kind: ToolKind
    description: str
    # CLI tools
    command: str | None = None
    # HTTP tools
    endpoint: str | None = None
    method: str = "GET"
    # MCP tools
    mcp_server: str | None = None  # e.g. "vault-graph", "turbovault"
    mcp_method: str | None = None
    # Python tools
    callable: Callable[..., Awaitable[Any]] | None = None
    # Schema
    parameters: dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """Central registry for all vault tools."""

    def __init__(self, config: Any = None):
        self._tools: dict[str, Tool] = {}
        self._config = config
        self._http_client: httpx.AsyncClient | None = None
        self._register_defaults()

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, str]]:
        return [{"name": t.name, "kind": t.kind.value, "description": t.description}
                for t in self._tools.values()]

    async def call(self, name: str, **kwargs: Any) -> Any:
        """Dispatch a tool call by name."""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")

        logger.info(f"Calling tool: {name} ({tool.kind.value})")

        if tool.kind == ToolKind.CLI:
            return await self._call_cli(tool, **kwargs)
        elif tool.kind == ToolKind.HTTP:
            return await self._call_http(tool, **kwargs)
        elif tool.kind == ToolKind.MCP:
            if tool.mcp_server == "atom-of-thoughts":
                return await self._call_aot(tool, **kwargs)
            return await self._call_mcp(tool, **kwargs)
        elif tool.kind == ToolKind.PYTHON:
            return await tool.callable(**kwargs)  # type: ignore
        else:
            raise ValueError(f"Unknown tool kind: {tool.kind}")

    async def _call_cli(self, tool: Tool, **kwargs: Any) -> dict[str, Any]:
        """Execute a CLI command."""
        cmd = tool.command or ""
        for k, v in kwargs.items():
            cmd = cmd.replace(f"{{{k}}}", str(v))

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**__import__("os").environ, "DISPLAY": ":99"},
        )
        stdout, stderr = await proc.communicate()
        return {
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "returncode": proc.returncode,
        }

    async def _call_http(self, tool: Tool, **kwargs: Any) -> Any:
        """Make an HTTP API call."""
        url = tool.endpoint or ""
        for k, v in kwargs.items():
            url = url.replace(f"{{{k}}}", str(v))

        if tool.method.upper() == "GET":
            resp = await self.http.get(url, params=kwargs)
        else:
            resp = await self.http.request(tool.method.upper(), url, json=kwargs)

        try:
            return resp.json()
        except Exception:
            return {"text": resp.text, "status": resp.status_code}

    async def _call_mcp(self, tool: Tool, **kwargs: Any) -> Any:
        """Call an MCP server tool via JSON-RPC over HTTP."""
        servers = {
            "vault-graph": "http://localhost:3100",
            "turbovault": "http://localhost:3200",
        }
        base = servers.get(tool.mcp_server or "", "http://localhost:3100")
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool.mcp_method or tool.name,
                "arguments": kwargs,
            },
        }
        resp = await self.http.post(f"{base}/mcp", json=payload)
        return resp.json()

    def _register_defaults(self) -> None:
        """Register all known vault tools."""
        api = "http://localhost:3000"

        # --- Obsidian API (HTTP) ---
        self.register(Tool(
            name="vault_files", kind=ToolKind.HTTP,
            description="List vault files",
            endpoint=f"{api}/files", method="GET",
        ))
        self.register(Tool(
            name="vault_read", kind=ToolKind.HTTP,
            description="Read a vault file by name",
            endpoint=f"{api}/read", method="GET",
            parameters={"file": "string"},
        ))
        self.register(Tool(
            name="vault_search", kind=ToolKind.HTTP,
            description="Search vault content",
            endpoint=f"{api}/search", method="GET",
            parameters={"q": "string"},
        ))
        self.register(Tool(
            name="vault_create", kind=ToolKind.HTTP,
            description="Create a new vault file",
            endpoint=f"{api}/create", method="POST",
            parameters={"name": "string", "content": "string"},
        ))
        self.register(Tool(
            name="analytics_summary", kind=ToolKind.HTTP,
            description="Get graph analytics summary",
            endpoint=f"{api}/analytics/summary", method="GET",
        ))
        self.register(Tool(
            name="mcmc_traverse", kind=ToolKind.HTTP,
            description="MCMC graph traversal for optimal reading order",
            endpoint=f"{api}/traverse", method="POST",
            parameters={"query": "string", "max_nodes": "int", "temperature": "float"},
        ))
        self.register(Tool(
            name="smart_read", kind=ToolKind.HTTP,
            description="Read file with neighborhood analytics",
            endpoint=f"{api}/read/smart", method="GET",
            parameters={"file": "string"},
        ))
        self.register(Tool(
            name="analytics_compute", kind=ToolKind.HTTP,
            description="Trigger full graph metric recomputation",
            endpoint=f"{api}/analytics/compute", method="POST",
        ))

        # --- CLI tools ---
        self.register(Tool(
            name="mdb_validate", kind=ToolKind.CLI,
            description="Validate vault against mdbase-spec",
            command="cd /home/exedev/{vault} && mdb validate",
            parameters={"vault": "string"},
        ))
        self.register(Tool(
            name="mdb_query", kind=ToolKind.CLI,
            description="Query typed vault content",
            command="cd /home/exedev/{vault} && mdb query --types {types} --limit {limit}",
            parameters={"vault": "string", "types": "string", "limit": "int"},
        ))
        self.register(Tool(
            name="obsidian_cli", kind=ToolKind.CLI,
            description="Run arbitrary Obsidian CLI command",
            command="DISPLAY=:99 obsidian {args}",
            parameters={"args": "string"},
        ))
        self.register(Tool(
            name="mtn_list", kind=ToolKind.CLI,
            description="List TaskNotes tasks",
            command="mtn list",
        ))
        self.register(Tool(
            name="mtn_create", kind=ToolKind.CLI,
            description="Create a TaskNotes task",
            command='mtn create "{title}"',
            parameters={"title": "string"},
        ))
        self.register(Tool(
            name="br_ready", kind=ToolKind.CLI,
            description="List available beads work",
            command="cd /home/exedev/agentic-obsidian && br ready",
        ))
        self.register(Tool(
            name="treemd", kind=ToolKind.CLI,
            description="Analyze markdown heading tree",
            command="treemd {file}",
            parameters={"file": "string"},
        ))

        # --- MCP tools (vault-graph) ---
        for mcp_tool in [
            ("graph_snapshot", "Get current graph state snapshot"),
            ("graph_node_detail", "Get detailed info for a specific node"),
            ("graph_neighbors", "Get neighbors of a node"),
            ("graph_clusters", "Get cluster assignments"),
            ("bases_query", "Run an Obsidian Bases query"),
            ("pex_start", "Start a PEX interview session"),
            ("pex_respond", "Respond to PEX interview question"),
            ("context_inject", "Inject context from graph into conversation"),
        ]:
            self.register(Tool(
                name=mcp_tool[0], kind=ToolKind.MCP,
                description=mcp_tool[1],
                mcp_server="vault-graph",
                mcp_method=mcp_tool[0],
            ))

        # --- MCP tools (turbovault) ---
        for mcp_tool in [
            ("tv_search", "Full-text search across vault"),
            ("tv_read", "Read a file via TurboVault"),
            ("tv_write", "Write/update a file via TurboVault"),
            ("tv_health", "Vault health analysis"),
            ("tv_link_graph", "Get link graph for a file"),
        ]:
            self.register(Tool(
                name=mcp_tool[0], kind=ToolKind.MCP,
                description=mcp_tool[1],
                mcp_server="turbovault",
                mcp_method=mcp_tool[0],
            ))

        # --- MCP tools (atom-of-thoughts via stdio) ---
        self.register(Tool(
            name="AoT", kind=ToolKind.MCP,
            description=(
                "Atom of Thoughts — full reasoning chain (depth ≤ 5). "
                "Submit atomic units of thought (premise/reasoning/hypothesis/"
                "verification/conclusion) with dependencies and confidence scores. "
                "Supports decomposition-contraction and automatic termination."
            ),
            mcp_server="atom-of-thoughts",
            mcp_method="AoT",
            parameters={
                "atomId": "string",
                "content": "string",
                "atomType": "string (premise|reasoning|hypothesis|verification|conclusion)",
                "dependencies": "array[string]",
                "confidence": "number (0-1)",
                "isVerified": "boolean (optional)",
                "depth": "number (optional)",
            },
        ))
        self.register(Tool(
            name="AoT-light", kind=ToolKind.MCP,
            description=(
                "Atom of Thoughts — lightweight fast mode (depth ≤ 3, early conclusion). "
                "Same atom schema as AoT but with reduced depth, simplified verification, "
                "and immediate conclusion suggestion for high-confidence hypotheses."
            ),
            mcp_server="atom-of-thoughts",
            mcp_method="AoT-light",
            parameters={
                "atomId": "string",
                "content": "string",
                "atomType": "string (premise|reasoning|hypothesis|verification|conclusion)",
                "dependencies": "array[string]",
                "confidence": "number (0-1)",
                "isVerified": "boolean (optional)",
                "depth": "number (optional)",
            },
        ))
        self.register(Tool(
            name="atomcommands", kind=ToolKind.MCP,
            description=(
                "Control the AoT decomposition-contraction mechanism and termination. "
                "Commands: decompose (atomId), complete_decomposition (decompositionId), "
                "termination_status, best_conclusion, set_max_depth (maxDepth)."
            ),
            mcp_server="atom-of-thoughts",
            mcp_method="atomcommands",
            parameters={
                "command": "string (decompose|complete_decomposition|termination_status|best_conclusion|set_max_depth)",
                "atomId": "string (optional)",
                "decompositionId": "string (optional)",
                "maxDepth": "number (optional)",
            },
        ))

    async def _call_aot(self, tool: Tool, **kwargs: Any) -> Any:
        """Call an Atom-of-Thoughts MCP tool via the AoT stdio client."""
        client = await get_aot_client()
        tool_name = tool.mcp_method or tool.name
        return await client._call(tool_name, kwargs)

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
        # Shut down AoT subprocess if it was started
        from ralph.aot import shutdown_aot_client
        await shutdown_aot_client()
