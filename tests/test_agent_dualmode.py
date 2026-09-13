"""Lock down the two distinct Agent API modes: headless and GUI-automation.

The tool exposes two categories of Agent-facing APIs:
  1. Headless (default): ``HeadlessAPI()`` / ``androguard-skills mcp`` — pure
     API calls, no GUI program, no terminal-TUI dependency at all.
  2. GUI: ``HeadlessAPI(include_ui=True)`` / ``androguard-skills mcp --with-ui``
     — same analysis tools PLUS nine ``ui.*`` tools that drive the shared
     terminal UI an operator is also looking at.

These tests pin the shape so nobody can silently blur the boundary.
"""

import subprocess
import sys

import pytest

from androguard.agent import (
    HeadlessAPI,
    UIAgentController,
    build_agent_api,
)

HEADLESS_PY = """
import sys
import androguard.agent.headless as h
from androguard.agent.headless import HeadlessAPI
api = HeadlessAPI()
bad = [
    m for m in sys.modules
    if m == "prompt_toolkit"
    or m.startswith("prompt_toolkit.")
    or m == "androguard.ui"
    or m == "androguard.ui"
]
print("PURITY_OK=" + str(not bad))
"""


class TestHeadlessPurity:
    """Headless mode must never pull the terminal-TUI dependency stack."""

    def test_subprocess_imports_no_tui_modules(self):
        # Run in a clean subprocess so our own session imports cannot leak in.
        proc = subprocess.run(
            [sys.executable, "-c", HEADLESS_PY],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert "PURITY_OK=True" in proc.stdout, proc.stdout

    def test_headless_has_no_ui_tools(self):
        api = HeadlessAPI()
        names = [t["name"] for t in api.list_tools()]
        ui_tools = [n for n in names if n.startswith("ui.")]
        assert ui_tools == []
        assert api._ui is None

    def test_build_agent_api_defaults_to_headless(self):
        api = build_agent_api()
        assert isinstance(api, HeadlessAPI)
        assert api._ui is None
        assert not [t for t in api.list_tools() if t["name"].startswith("ui.")]


class TestGuiMode:
    """GUI mode keeps the full analysis tool set and adds exactly the ui.* tools."""

    def test_gui_exposes_nine_ui_tools(self):
        api = HeadlessAPI(include_ui=True)
        ui_tools = [t["name"] for t in api.list_tools() if t["name"].startswith("ui.")]
        assert ui_tools == [
            "ui.action",
            "ui.export_transactions",
            "ui.get_transaction",
            "ui.publish",
            "ui.query",
            "ui.search",
            "ui.snapshot",
            "ui.start",
            "ui.stop",
        ]

    def test_gui_keeps_same_analysis_toolset_as_headless(self):
        headless = HeadlessAPI()
        gui = HeadlessAPI(include_ui=True)
        headless_names = {t["name"] for t in headless.list_tools()}
        gui_names = {t["name"] for t in gui.list_tools()}
        gui_analysis = {n for n in gui_names if not n.startswith("ui.")}
        assert gui_analysis == headless_names

    def test_ui_controller_is_lazy_until_tool_called(self):
        # Constructing the GUI API must not build DynamicUI (it only wires the
        # lightweight bridge); the TUI object appears only once a ui.* tool is used.
        api = HeadlessAPI(include_ui=True)
        controller = api._ui
        assert isinstance(controller, UIAgentController)
        assert controller.ui is None  # no DynamicUI yet

    def test_build_agent_api_with_ui_flag(self):
        api = build_agent_api(include_ui=True)
        ui_tools = [t["name"] for t in api.list_tools() if t["name"].startswith("ui.")]
        assert len(ui_tools) == 9


class TestModeDispatch:
    def test_call_ui_tool_routes_to_controller(self):
        api = HeadlessAPI(include_ui=True)
        snap = api.call_tool("ui.snapshot", {})
        assert isinstance(snap, dict)
        assert snap["status"] in {"running", "stopped"}
        assert "transaction_count" in snap