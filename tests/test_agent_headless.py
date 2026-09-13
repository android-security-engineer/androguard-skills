"""Tests for androguard.agent.headless — HeadlessAPI / MCP protocol handling."""

from __future__ import annotations

import json
import pytest

from androguard.agent.headless import HeadlessAPI
from androguard.agent.protocol import AgentError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_api() -> HeadlessAPI:
    return HeadlessAPI()


def _req(method: str, params: dict = None, req_id=1) -> dict:
    r: dict = {"jsonrpc": "2.0", "method": method, "id": req_id}
    if params is not None:
        r["params"] = params
    return r


# ---------------------------------------------------------------------------
# MCP protocol — initialize
# ---------------------------------------------------------------------------

class TestMCPInitialize:
    def test_initialize_handshake(self):
        api = _make_api()
        resp = api.handle(_req("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}}))
        assert resp is not None
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        result = resp["result"]
        assert result["protocolVersion"] == HeadlessAPI.protocol_version
        assert "tools" in result["capabilities"]
        assert result["serverInfo"]["name"] == "androguard-agent"

    def test_initialized_notification_returns_none(self):
        api = _make_api()
        # notifications have no id
        resp = api.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
        assert resp is None

    def test_unknown_method_returns_error(self):
        api = _make_api()
        resp = api.handle(_req("no_such_method"))
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_missing_method_field_is_invalid_request(self):
        api = _make_api()
        resp = api.handle({"jsonrpc": "2.0", "id": 9})
        assert resp["error"]["code"] == -32600


# ---------------------------------------------------------------------------
# MCP protocol — tools/list
# ---------------------------------------------------------------------------

class TestMCPToolsList:
    def test_tools_list_returns_tools(self):
        api = _make_api()
        resp = api.handle(_req("tools/list"))
        assert "result" in resp
        tools = resp["result"]["tools"]
        assert isinstance(tools, list)
        assert len(tools) > 100  # we have 217+

    def test_tools_list_has_typed_schemas(self):
        api = _make_api()
        resp = api.handle(_req("tools/list"))
        tools = resp["result"]["tools"]
        untyped = []
        for t in tools:
            for pname, pschema in t["inputSchema"]["properties"].items():
                if "type" not in pschema and "anyOf" not in pschema:
                    untyped.append(f"{t['name']}.{pname}")
        assert untyped == [], f"Parameters missing type schema: {untyped}"

    def test_tools_list_includes_load_apk(self):
        api = _make_api()
        resp = api.handle(_req("tools/list"))
        tools_by_name = {t["name"]: t for t in resp["result"]["tools"]}
        assert "load_apk" in tools_by_name
        schema = tools_by_name["load_apk"]["inputSchema"]
        assert schema["properties"]["apk_path"]["type"] == "string"
        assert "apk_path" in schema["required"]

    def test_tools_list_load_dex_typed(self):
        api = _make_api()
        resp = api.handle(_req("tools/list"))
        tools_by_name = {t["name"]: t for t in resp["result"]["tools"]}
        assert "load_dex" in tools_by_name
        schema = tools_by_name["load_dex"]["inputSchema"]
        assert schema["properties"]["dex_path"]["type"] == "string"


# ---------------------------------------------------------------------------
# MCP protocol — tools/call
# ---------------------------------------------------------------------------

class TestMCPToolsCall:
    def test_tools_call_missing_apk_returns_error(self):
        """Calling an analysis method without loading APK returns isError=True."""
        api = _make_api()
        resp = api.handle(_req("tools/call", {"name": "apk_info", "arguments": {}}))
        assert "result" in resp
        result = resp["result"]
        assert result["isError"] is True
        content_text = result["content"][0]["text"]
        data = json.loads(content_text)
        assert "error" in data

    def test_tools_call_unknown_tool_returns_error(self):
        api = _make_api()
        resp = api.handle(_req("tools/call", {"name": "no_such_tool", "arguments": {}}))
        assert "result" in resp
        assert resp["result"]["isError"] is True

    def test_tools_call_bad_arguments_returns_error(self):
        api = _make_api()
        resp = api.handle(_req("tools/call", {
            "name": "load_apk",
            "arguments": {},  # missing required apk_path
        }))
        assert resp["result"]["isError"] is True


# ---------------------------------------------------------------------------
# Direct JSON-RPC method dispatch (backward compat path)
# ---------------------------------------------------------------------------

class TestDirectMethodDispatch:
    def test_direct_method_not_found(self):
        api = _make_api()
        resp = api.handle(_req("nonexistent_method", {}))
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_direct_method_returns_error_when_not_loaded(self):
        api = _make_api()
        resp = api.handle(_req("apk_info", {}))
        # Direct dispatch wraps tool failures as JSON-RPC -32603 errors
        assert "error" in resp
        assert resp["error"]["code"] == -32603


# ---------------------------------------------------------------------------
# HeadlessAPI.list_tools / call_tool (Python API surface)
# ---------------------------------------------------------------------------

class TestHeadlessAPIDirectPython:
    def test_list_tools_count(self):
        api = _make_api()
        tools = api.list_tools()
        assert len(tools) > 100

    def test_list_tools_have_input_schema(self):
        api = _make_api()
        for tool in api.list_tools():
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"

    def test_call_tool_invalid_raises_agent_error(self):
        api = _make_api()
        with pytest.raises(AgentError):
            api.call_tool("no_such_tool", {})


# ---------------------------------------------------------------------------
# server.py — stdio server (import + run with fake stdin)
# ---------------------------------------------------------------------------

class TestStdioServer:
    def test_server_module_importable(self):
        from androguard.agent import server
        assert callable(server.run_stdio)
        assert callable(server.main)

    def test_run_stdio_single_request(self, monkeypatch, capsys):
        from androguard.agent import server
        import io

        req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                          "params": {"protocolVersion": "2024-11-05", "capabilities": {}}})
        monkeypatch.setattr("sys.stdin", io.StringIO(req + "\n"))
        server.run_stdio()
        out = capsys.readouterr().out
        lines = [l for l in out.splitlines() if l.strip()]
        assert len(lines) == 1
        resp = json.loads(lines[0])
        assert resp["result"]["serverInfo"]["name"] == "androguard-agent"

    def test_run_stdio_batch_request(self, monkeypatch, capsys):
        from androguard.agent import server
        import io

        batch = json.dumps([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ])
        monkeypatch.setattr("sys.stdin", io.StringIO(batch + "\n"))
        server.run_stdio()
        out = capsys.readouterr().out
        lines = [l for l in out.splitlines() if l.strip()]
        assert len(lines) == 1
        responses = json.loads(lines[0])
        assert isinstance(responses, list)
        assert len(responses) == 2
        ids = {r["id"] for r in responses}
        assert ids == {1, 2}

    def test_run_stdio_parse_error(self, monkeypatch, capsys):
        from androguard.agent import server
        import io

        monkeypatch.setattr("sys.stdin", io.StringIO("not valid json\n"))
        server.run_stdio()
        out = capsys.readouterr().out
        lines = [l for l in out.splitlines() if l.strip()]
        assert len(lines) == 1
        resp = json.loads(lines[0])
        assert resp["error"]["code"] == -32700
