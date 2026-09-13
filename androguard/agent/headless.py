"""Headless Agent API and MCP-compatible request handling."""

from __future__ import annotations

import json
from typing import Any, Mapping

from androguard.agent.protocol import AgentError, ToolRegistry, jsonable
from androguard.skills.main import AndroguardSkillsMain


class HeadlessAPI:
    """Expose AndroGuard skills as discoverable, stateful Agent tools.

    The object is safe to embed in a process or to put behind stdio/TCP/HTTP.
    State is kept in the underlying ``AndroguardSkillsMain`` instance, so an
    Agent can load once and issue multiple analysis calls without reparsing.
    """

    protocol_version = "2024-11-05"

    def __init__(self, skills: AndroguardSkillsMain | None = None, include_ui: bool = False):
        self.skills = skills or AndroguardSkillsMain()
        self.registry = ToolRegistry()
        self.registry.add_object(self.skills)
        self._ui = None
        if include_ui:
            from androguard.agent.ui import UIAgentController

            self._ui = UIAgentController()
            self.registry.add("ui.snapshot", self._ui.snapshot)
            self.registry.add("ui.action", self._ui.action)
            self.registry.add("ui.publish", self._ui.publish)
            self.registry.add("ui.get_transaction", self._ui.get_transaction)
            self.registry.add("ui.export_transactions", self._ui.export_transactions)
            self.registry.add("ui.query", self._ui.query)
            self.registry.add("ui.search", self._ui.search)
            self.registry.add("ui.start", self._ui.start)
            self.registry.add("ui.stop", self._ui.stop)

    def list_tools(self) -> list[dict[str, Any]]:
        return self.registry.list()

    def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> Any:
        return self.registry.call(name, arguments)

    def handle(self, request: Mapping[str, Any]) -> dict[str, Any] | None:
        """Handle one JSON-RPC/MCP request; notifications return ``None``."""

        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}
        if not method:
            return self._error(request_id, -32600, "Invalid request")
        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return self._result(request_id, {
                "protocolVersion": self.protocol_version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "androguard-agent", "version": "1"},
            })
        if method == "tools/list":
            return self._result(request_id, {"tools": self.list_tools()})
        if method == "tools/call":
            try:
                name = params["name"]
                arguments = params.get("arguments", {})
                result = self.call_tool(name, arguments)
                return self._result(request_id, {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                    "isError": False,
                })
            except AgentError as exc:
                return self._result(request_id, {
                    "content": [{"type": "text", "text": json.dumps({"error": exc.message}, ensure_ascii=False)}],
                    "isError": True,
                })
        # A direct method call is useful for simple SKILLS-style clients and
        # remains compatible with the existing daemon method names.
        if method in self.registry._tools:
            try:
                return self._result(request_id, self.call_tool(method, params))
            except AgentError as exc:
                return self._error(request_id, -32603, exc.message, exc.code)
        return self._error(request_id, -32601, f"Method not found: {method}")

    @staticmethod
    def _result(request_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "result": jsonable(result), "id": request_id}

    @staticmethod
    def _error(request_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {"jsonrpc": "2.0", "error": error, "id": request_id}
