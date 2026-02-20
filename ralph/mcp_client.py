"""MCP JSON-RPC client for communicating with vault MCP servers.

Supports two transports:
  - HTTP (vault-graph on :3100, turbovault on :3200)
  - stdio (atom-of-thoughts subprocess)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("ralph.mcp_client")

# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------

_REQ_ID = 0


def _next_id() -> int:
    global _REQ_ID
    _REQ_ID += 1
    return _REQ_ID


def _jsonrpc_request(method: str, params: dict[str, Any] | None = None) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": _next_id(),
        "method": method,
        "params": params or {},
    }


# ---------------------------------------------------------------------------
# HTTP MCP client (vault-graph, turbovault-http)
# ---------------------------------------------------------------------------


class HttpMcpClient:
    """JSON-RPC client that talks to an MCP server over HTTP POST /mcp."""

    def __init__(self, base_url: str, name: str = "mcp", timeout: float = 120.0):
        # base_url should be the full endpoint e.g. http://localhost:3100/mcp
        self.base_url = base_url.rstrip("/")
        # Strip trailing /mcp if present so we don't double it
        if self.base_url.endswith("/mcp"):
            self.base_url = self.base_url[:-4]
        self.name = name
        self._http: httpx.AsyncClient | None = None
        self._timeout = timeout
        self._initialized = False

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self._timeout)
        return self._http

    async def initialize(self) -> dict[str, Any]:
        """Send MCP initialize handshake."""
        if self._initialized:
            return {"already": True}
        resp = await self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ralph-sdk-bridge", "version": "0.1.0"},
        })
        self._initialized = True
        # Send initialized notification (no response expected)
        try:
            await self.http.post(
                f"{self.base_url}/mcp",
                json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            )
        except Exception:
            pass
        return resp

    async def list_tools(self) -> list[dict[str, Any]]:
        """Fetch tools/list from the server."""
        resp = await self._rpc("tools/list")
        return resp.get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call tools/call and return the result."""
        resp = await self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        return resp

    async def health(self) -> dict[str, Any]:
        """GET /health endpoint."""
        try:
            r = await self.http.get(f"{self.base_url}/health")
            return r.json()
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def _rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = _jsonrpc_request(method, params)
        logger.debug(f"[{self.name}] → {method} id={payload['id']}")
        r = await self.http.post(f"{self.base_url}/mcp", json=payload)
        r.raise_for_status()
        body = r.json()
        if "error" in body:
            err = body["error"]
            raise McpError(err.get("message", str(err)), err.get("code", -1))
        return body.get("result", body)

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None


# ---------------------------------------------------------------------------
# Stdio MCP client (atom-of-thoughts)
# ---------------------------------------------------------------------------


class StdioMcpClient:
    """JSON-RPC client that talks to an MCP server over stdin/stdout."""

    def __init__(self, command: list[str], name: str = "stdio-mcp", env: dict[str, str] | None = None):
        self.command = command
        self.name = name
        self.env = {**os.environ, **(env or {})}
        self._proc: asyncio.subprocess.Process | None = None
        self._initialized = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Launch the subprocess."""
        if self._proc is not None:
            return
        self._proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env,
        )
        logger.info(f"[{self.name}] started pid={self._proc.pid}")

    async def initialize(self) -> dict[str, Any]:
        if self._initialized:
            return {"already": True}
        await self.start()
        resp = await self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ralph-sdk-bridge", "version": "0.1.0"},
        })
        # Send initialized notification
        await self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        self._initialized = True
        return resp

    async def list_tools(self) -> list[dict[str, Any]]:
        resp = await self._rpc("tools/list")
        return resp.get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._rpc("tools/call", {"name": name, "arguments": arguments or {}})

    async def _rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = _jsonrpc_request(method, params)
        async with self._lock:
            await self._send(payload)
            line = await self._readline()
        body = json.loads(line)
        if "error" in body:
            err = body["error"]
            raise McpError(err.get("message", str(err)), err.get("code", -1))
        return body.get("result", body)

    async def _send(self, obj: dict) -> None:
        assert self._proc and self._proc.stdin
        data = json.dumps(obj) + "\n"
        self._proc.stdin.write(data.encode())
        await self._proc.stdin.drain()

    async def _readline(self) -> str:
        """Read a non-empty JSON line from stdout, skipping stderr noise."""
        assert self._proc and self._proc.stdout
        while True:
            line = await asyncio.wait_for(self._proc.stdout.readline(), timeout=60.0)
            if not line:
                raise McpError("stdio EOF")
            decoded = line.decode().strip()
            if decoded and decoded.startswith("{"):
                return decoded

    async def close(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), timeout=5.0)
            except Exception:
                self._proc.kill()
            self._proc = None


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class McpError(Exception):
    def __init__(self, message: str, code: int = -1):
        self.code = code
        super().__init__(f"MCP error {code}: {message}")
