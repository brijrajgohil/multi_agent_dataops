from __future__ import annotations

from contextlib import asynccontextmanager
import json
import sys
from collections.abc import AsyncIterator
from typing import Any


class LocalMCPClient:
    def __init__(self, server_module: str = "src.tools.mcp_server") -> None:
        self.server_module = server_module

    async def list_tools(self) -> list[str]:
        async with self._session() as session:
            result = await session.list_tools()
            return [tool.name for tool in result.tools]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        async with self._session() as session:
            result = await session.call_tool(name, arguments)
            return self._normalize_tool_result(result)

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[Any]:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "mcp is not installed. Run `python -m pip install -r requirements.txt`."
            ) from exc

        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", self.server_module],
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session

    def _normalize_tool_result(self, result: Any) -> dict[str, Any]:
        if getattr(result, "isError", False):
            return {"ok": False, "error": str(result.content)}

        structured_content = getattr(result, "structuredContent", None)
        if isinstance(structured_content, dict):
            return structured_content

        content = getattr(result, "content", [])
        if not content:
            return {"ok": True}

        first = content[0]
        text = getattr(first, "text", None)
        if text is None:
            return {"ok": True, "content": str(content)}

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return {"ok": True, "content": text}

        if isinstance(payload, dict):
            return payload
        return {"ok": True, "content": payload}
