"""Tests for the GUI Agent API: UIAgentController / DynamicUI agent_* methods.

Validates all improvements to the headless GUI control layer:
  - snapshot structure (visible_transactions, structured filter)
  - select action scrolls view to the selected item
  - clear action empties all transactions
  - get_transaction returns full params/ret_value
  - app.invalidate() is called after mutations (monkey-patch check)
  - ui.get_transaction is registered in HeadlessAPI
  - before_render hook processes queued data automatically
"""
from __future__ import annotations

import queue
from unittest.mock import MagicMock, patch

import pytest

from androguard.agent.ui import UIAgentController
from androguard.message import MessageEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_controller() -> UIAgentController:
    q = queue.Queue()
    ctrl = UIAgentController(input_queue=q)
    ctrl._ensure_ui()  # instantiate DynamicUI without TTY
    return ctrl


def _publish_n(ctrl: UIAgentController, n: int):
    """Publish n synthetic trace events through the controller."""
    for i in range(n):
        ctrl.publish(i, f"From.Class{i}", f"toMethod{i}", params={"arg": i}, ret_value=i)


# ---------------------------------------------------------------------------
# Snapshot structure
# ---------------------------------------------------------------------------

class TestSnapshotStructure:
    def test_snapshot_has_visible_transactions_key(self):
        ctrl = _make_controller()
        snap = ctrl.snapshot()
        assert "visible_transactions" in snap

    def test_snapshot_visible_transactions_empty_when_no_data(self):
        ctrl = _make_controller()
        snap = ctrl.snapshot()
        assert snap["visible_transactions"] == []

    def test_snapshot_visible_transactions_populated_after_publish(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        snap = ctrl.snapshot()
        assert len(snap["visible_transactions"]) == 3

    def test_snapshot_visible_transaction_fields(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 1)
        snap = ctrl.snapshot()
        row = snap["visible_transactions"][0]
        assert "index" in row
        assert "from_method" in row
        assert "to_method" in row
        assert "type" in row

    def test_snapshot_filter_is_dict(self):
        ctrl = _make_controller()
        snap = ctrl.snapshot()
        assert isinstance(snap["filter"], dict)

    def test_snapshot_filter_has_keys_when_none(self):
        ctrl = _make_controller()
        snap = ctrl.snapshot()
        f = snap["filter"]
        assert f["interface"] is None
        assert f["method"] is None
        assert f["types"] == []

    def test_snapshot_filter_reflects_active_filter(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 2)
        ctrl.action("filter", interface="From.Class0")
        snap = ctrl.snapshot()
        assert snap["filter"]["interface"] == "From.Class0"

    def test_snapshot_transaction_count(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 5)
        snap = ctrl.snapshot()
        assert snap["transaction_count"] == 5

    def test_snapshot_view_keys(self):
        ctrl = _make_controller()
        snap = ctrl.snapshot()
        v = snap["view"]
        assert "start" in v
        assert "end" in v
        assert "max_size" in v


# ---------------------------------------------------------------------------
# Select action scrolls view
# ---------------------------------------------------------------------------

class TestSelectScrollsView:
    def test_select_within_view_works(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 5)
        result = ctrl.action("select", index=2)
        assert result["selected_index"] == 2

    def test_select_beyond_view_scrolls(self):
        ctrl = _make_controller()
        # Publish 50 items; default max_view_size from resize_components(40 height)
        _publish_n(ctrl, 50)
        # Select item at end
        result = ctrl.action("select", index=49)
        assert result["selected_index"] == 49
        # The view should have scrolled so the selected item is visible
        snap = ctrl.snapshot()
        view = snap["view"]
        assert view["start"] <= 49 < view["end"], (
            f"Selected item 49 not in view {view['start']}–{view['end']}"
        )

    def test_select_first_item(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 10)
        ctrl.action("select", index=9)   # go to end
        result = ctrl.action("select", index=0)  # back to start
        assert result["selected_index"] == 0

    def test_select_out_of_range_raises(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        with pytest.raises(IndexError):
            ctrl.action("select", index=99)

    def test_select_on_empty_list_raises(self):
        ctrl = _make_controller()
        with pytest.raises((IndexError, Exception)):
            ctrl.action("select", index=0)


# ---------------------------------------------------------------------------
# Clear action
# ---------------------------------------------------------------------------

class TestClearAction:
    def test_clear_empties_all_transactions(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 5)
        assert ctrl.snapshot()["transaction_count"] == 5
        result = ctrl.action("clear")
        assert result["transaction_count"] == 0

    def test_clear_empties_visible_count(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        ctrl.action("clear")
        snap = ctrl.snapshot()
        assert snap["visible_count"] == 0
        assert snap["visible_transactions"] == []

    def test_clear_resets_filter(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        ctrl.action("filter", interface="From.Class0")
        ctrl.action("clear")
        snap = ctrl.snapshot()
        assert snap["filter"]["interface"] is None

    def test_clear_then_publish_works(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 5)
        ctrl.action("clear")
        _publish_n(ctrl, 2)
        snap = ctrl.snapshot()
        assert snap["transaction_count"] == 2


# ---------------------------------------------------------------------------
# get_transaction
# ---------------------------------------------------------------------------

class TestGetTransaction:
    def test_get_transaction_returns_full_fields(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        tx = ctrl.get_transaction(0)
        assert "index" in tx
        assert "from_method" in tx
        assert "to_method" in tx
        assert "params" in tx
        assert "ret_value" in tx
        assert "type" in tx

    def test_get_transaction_correct_params(self):
        ctrl = _make_controller()
        ctrl.publish(7, "From.X", "toY", params={"x": 42}, ret_value="ok")
        tx = ctrl.get_transaction(0)
        assert tx["params"] == {"x": 42}
        assert tx["ret_value"] == "ok"

    def test_get_transaction_out_of_range(self):
        ctrl = _make_controller()
        with pytest.raises(IndexError):
            ctrl.get_transaction(0)

    def test_get_transaction_survives_filter(self):
        """get_transaction fetches from all_transactions, ignoring current filter."""
        ctrl = _make_controller()
        _publish_n(ctrl, 5)
        # Filter to only From.Class0
        ctrl.action("filter", interface="From.Class0")
        assert ctrl.snapshot()["visible_count"] == 1
        # But we can still get any transaction by index
        tx = ctrl.get_transaction(4)
        assert tx["from_method"] == "From.Class4"

    def test_get_transaction_after_clear_raises(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        ctrl.action("clear")
        with pytest.raises(IndexError):
            ctrl.get_transaction(0)


# ---------------------------------------------------------------------------
# app.invalidate() called after mutations (thread safety / human UX)
# ---------------------------------------------------------------------------

class TestInvalidateOnMutation:
    def _ctrl_with_mock_app(self):
        ctrl = _make_controller()
        mock_app = MagicMock()
        ctrl.ui.app = mock_app
        return ctrl, mock_app

    def test_action_move_calls_invalidate(self):
        ctrl, mock_app = self._ctrl_with_mock_app()
        _publish_n(ctrl, 5)
        ctrl.action("move", step=1)
        mock_app.invalidate.assert_called()

    def test_action_toggle_help_calls_invalidate(self):
        ctrl, mock_app = self._ctrl_with_mock_app()
        ctrl.action("toggle_help")
        mock_app.invalidate.assert_called()

    def test_action_filter_calls_invalidate(self):
        ctrl, mock_app = self._ctrl_with_mock_app()
        _publish_n(ctrl, 3)
        ctrl.action("filter", interface="From.Class0")
        mock_app.invalidate.assert_called()

    def test_action_clear_calls_invalidate(self):
        ctrl, mock_app = self._ctrl_with_mock_app()
        _publish_n(ctrl, 3)
        ctrl.action("clear")
        mock_app.invalidate.assert_called()

    def test_process_data_calls_invalidate_when_new_events(self):
        ctrl, mock_app = self._ctrl_with_mock_app()
        # Put an event directly in the queue without calling publish (bypasses process_data)
        msg = MessageEvent(0, "to", "from", {}, None)
        ctrl.input_queue.put(msg)
        ctrl.ui.process_data()
        mock_app.invalidate.assert_called()

    def test_process_data_no_invalidate_when_empty(self):
        ctrl, mock_app = self._ctrl_with_mock_app()
        ctrl.ui.process_data()
        mock_app.invalidate.assert_not_called()


# ---------------------------------------------------------------------------
# HeadlessAPI registers ui.get_transaction
# ---------------------------------------------------------------------------

class TestHeadlessUITools:
    def test_ui_get_transaction_registered(self):
        from androguard.agent.headless import HeadlessAPI
        api = HeadlessAPI(include_ui=True)
        names = [t["name"] for t in api.list_tools()]
        assert "ui.get_transaction" in names

    def test_ui_get_transaction_schema(self):
        from androguard.agent.headless import HeadlessAPI
        api = HeadlessAPI(include_ui=True)
        tools = {t["name"]: t for t in api.list_tools()}
        spec = tools["ui.get_transaction"]
        assert spec["inputSchema"]["properties"]["index"]["type"] == "integer"
        assert "index" in spec["inputSchema"]["required"]

    def test_ui_tools_count_is_nine(self):
        from androguard.agent.headless import HeadlessAPI
        api = HeadlessAPI(include_ui=True)
        ui_tools = [t for t in api.list_tools() if t["name"].startswith("ui.")]
        assert len(ui_tools) == 9  # start, stop, snapshot, action, publish, get_transaction, export_transactions, query, search

    def test_ui_action_description_lists_actions(self):
        from androguard.agent.headless import HeadlessAPI
        api = HeadlessAPI(include_ui=True)
        tools = {t["name"]: t for t in api.list_tools()}
        desc = tools["ui.action"]["description"]
        for action_name in ("select", "move", "focus", "filter", "toggle_help", "toggle_filters", "close_modals", "clear"):
            assert action_name in desc, f"Action '{action_name}' missing from ui.action description"


# ---------------------------------------------------------------------------
# before_render data processing
# ---------------------------------------------------------------------------

class TestBeforeRenderHook:
    def test_process_data_hook_method_exists(self):
        ctrl = _make_controller()
        assert hasattr(ctrl.ui, "_process_data_hook")
        assert callable(ctrl.ui._process_data_hook)

    def test_process_data_hook_drains_queue(self):
        ctrl = _make_controller()
        msg = MessageEvent(0, "to", "from", {}, None)
        ctrl.input_queue.put(msg)
        assert ctrl.snapshot()["transaction_count"] == 0
        # Simulate what before_render does
        ctrl.ui._process_data_hook(None)
        assert ctrl.snapshot()["transaction_count"] == 1


# ---------------------------------------------------------------------------
# Filter panel textarea sync
# ---------------------------------------------------------------------------

class TestFilterPanelSync:
    def test_filter_action_syncs_interface_textarea(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        ctrl.action("filter", interface="From.Class1")
        assert ctrl.ui.filter_panel.interface_textarea.text == "From.Class1"

    def test_filter_action_syncs_method_textarea(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        ctrl.action("filter", method="toMethod0")
        assert ctrl.ui.filter_panel.method_textarea.text == "toMethod0"

    def test_filter_action_clears_textareas_on_empty(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        ctrl.action("filter", interface="X")
        ctrl.action("filter")  # reset to no-filter
        assert ctrl.ui.filter_panel.interface_textarea.text == ""
        assert ctrl.ui.filter_panel.method_textarea.text == ""

    def test_filter_action_syncs_type_checkboxes(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        ctrl.action("filter", types=["oneway"])
        assert "oneway" in ctrl.ui.filter_panel.type_filter_checkboxes.current_values

    def test_clear_action_resets_filter_panel(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        ctrl.action("filter", interface="X", method="Y")
        ctrl.action("clear")
        assert ctrl.ui.filter_panel.interface_textarea.text == ""
        assert ctrl.ui.filter_panel.method_textarea.text == ""
        assert ctrl.ui.filter_panel.type_filter_checkboxes.current_values == []


# ---------------------------------------------------------------------------
# export_transactions
# ---------------------------------------------------------------------------

class TestExportTransactions:
    def test_export_all(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 5)
        result = ctrl.export_transactions()
        assert result["count"] == 5
        assert len(result["transactions"]) == 5

    def test_export_has_full_fields(self):
        ctrl = _make_controller()
        ctrl.publish(0, "From.X", "toY", params={"k": "v"}, ret_value=42)
        result = ctrl.export_transactions()
        tx = result["transactions"][0]
        assert tx["params"] == {"k": "v"}
        assert tx["ret_value"] == 42

    def test_export_with_interface_filter(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 5)  # From.Class0..4
        result = ctrl.export_transactions(interface="From.Class2")
        assert result["count"] == 1
        assert result["transactions"][0]["from_method"] == "From.Class2"

    def test_export_ignores_active_view_filter(self):
        """export_transactions reads from all_transactions, not the filtered view."""
        ctrl = _make_controller()
        _publish_n(ctrl, 5)
        ctrl.action("filter", interface="From.Class0")  # only 1 visible
        assert ctrl.snapshot()["visible_count"] == 1
        result = ctrl.export_transactions()  # no filter arg → all 5
        assert result["count"] == 5

    def test_export_empty(self):
        ctrl = _make_controller()
        result = ctrl.export_transactions()
        assert result["count"] == 0
        assert result["transactions"] == []


# ---------------------------------------------------------------------------
# query (non-destructive search)
# ---------------------------------------------------------------------------

class TestQuery:
    def test_query_returns_count(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 5)
        result = ctrl.query(interface="From.Class0")
        assert result["count"] == 1

    def test_query_does_not_change_visible_filter(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 5)
        ctrl.action("filter", interface="From.Class1")
        assert ctrl.snapshot()["visible_count"] == 1
        ctrl.query(interface="From.Class3")  # search, don't filter
        # view should still show only From.Class1
        assert ctrl.snapshot()["visible_count"] == 1

    def test_query_does_not_change_self_filter(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 5)
        ctrl.action("filter", interface="From.Class1")
        snap_before = ctrl.snapshot()["filter"]
        ctrl.query(interface="From.Class3")
        snap_after = ctrl.snapshot()["filter"]
        assert snap_before == snap_after

    def test_query_summary_fields(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        result = ctrl.query()
        tx = result["transactions"][0]
        assert "index" in tx
        assert "from_method" in tx
        assert "to_method" in tx
        assert "type" in tx
        assert "params" not in tx  # summary only, not full details

    def test_query_all_no_filter(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 7)
        result = ctrl.query()
        assert result["count"] == 7

    def test_query_empty(self):
        ctrl = _make_controller()
        result = ctrl.query()
        assert result["count"] == 0


# ---------------------------------------------------------------------------
# get_available_blocks drains all (not just 10)
# ---------------------------------------------------------------------------

class TestDrainAll:
    def test_drains_more_than_ten(self):
        ctrl = _make_controller()
        for i in range(25):
            ctrl.input_queue.put(MessageEvent(i, "to", "from", {}, None))
        ctrl.ui.process_data()
        assert ctrl.snapshot()["transaction_count"] == 25

    def test_drain_is_idempotent_on_empty(self):
        ctrl = _make_controller()
        ctrl.ui.process_data()
        ctrl.ui.process_data()
        assert ctrl.snapshot()["transaction_count"] == 0


# ---------------------------------------------------------------------------
# HeadlessAPI — new ui.* tools registered
# ---------------------------------------------------------------------------

class TestNewUITools:
    def test_export_transactions_registered(self):
        from androguard.agent.headless import HeadlessAPI
        api = HeadlessAPI(include_ui=True)
        names = [t["name"] for t in api.list_tools()]
        assert "ui.export_transactions" in names

    def test_query_registered(self):
        from androguard.agent.headless import HeadlessAPI
        api = HeadlessAPI(include_ui=True)
        names = [t["name"] for t in api.list_tools()]
        assert "ui.query" in names

    def test_export_transactions_schema(self):
        from androguard.agent.headless import HeadlessAPI
        api = HeadlessAPI(include_ui=True)
        tools = {t["name"]: t for t in api.list_tools()}
        schema = tools["ui.export_transactions"]["inputSchema"]
        props = schema["properties"]
        # All params are optional
        assert "interface" in props
        assert "method" in props
        assert "types" in props
        assert schema["required"] == []

    def test_query_schema_no_required(self):
        from androguard.agent.headless import HeadlessAPI
        api = HeadlessAPI(include_ui=True)
        tools = {t["name"]: t for t in api.list_tools()}
        schema = tools["ui.query"]["inputSchema"]
        assert schema["required"] == []

    def test_focus_action_no_raw_in_description(self):
        from androguard.agent.headless import HeadlessAPI
        api = HeadlessAPI(include_ui=True)
        tools = {t["name"]: t for t in api.list_tools()}
        desc = tools["ui.action"]["description"]
        assert '"raw"' not in desc and "'raw'" not in desc, (
            "'raw' should not appear in ui.action description as it is not a valid panel"
        )


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_finds_keyword_in_params(self):
        ctrl = _make_controller()
        ctrl.publish(0, "From.X", "toY", params={"secret": "password123"}, ret_value=None)
        ctrl.publish(1, "From.Z", "toW", params={"ok": True}, ret_value=None)
        result = ctrl.search("password")
        assert result["count"] == 1
        assert result["transactions"][0]["from_method"] == "From.X"

    def test_search_finds_keyword_in_ret_value(self):
        ctrl = _make_controller()
        ctrl.publish(0, "From.X", "toY", params={}, ret_value="token=abc")
        result = ctrl.search("token")
        assert result["count"] == 1

    def test_search_case_insensitive(self):
        ctrl = _make_controller()
        ctrl.publish(0, "From.X", "toY", params={"x": "PASSWORD"}, ret_value=None)
        result = ctrl.search("password")
        assert result["count"] == 1

    def test_search_no_match(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        result = ctrl.search("nonexistent_zzz")
        assert result["count"] == 0

    def test_search_empty_keyword_returns_empty(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        result = ctrl.search("")
        assert result["count"] == 0

    def test_search_does_not_change_active_filter(self):
        ctrl = _make_controller()
        ctrl.publish(0, "From.A", "toA", params={"key": "secret"}, ret_value=None)
        ctrl.publish(1, "From.B", "toB", params={"key": "other"}, ret_value=None)
        ctrl.action("filter", interface="From.A")
        assert ctrl.snapshot()["visible_count"] == 1
        ctrl.search("other")  # search, don't filter
        assert ctrl.snapshot()["visible_count"] == 1  # still filtered to From.A

    def test_search_dict_params(self):
        ctrl = _make_controller()
        ctrl.publish(0, "X", "Y", params={"nested": {"password": "x"}}, ret_value={})
        result = ctrl.search("password")
        assert result["count"] == 1

    def test_search_skip_params_when_disabled(self):
        ctrl = _make_controller()
        ctrl.publish(0, "X", "Y", params={"secret": "x"}, ret_value="other_ret")
        result = ctrl.search("secret", search_params=False)
        assert result["count"] == 0  # params skipped, ret_value doesn't contain "secret"

    def test_search_skip_ret_value_when_disabled(self):
        ctrl = _make_controller()
        ctrl.publish(0, "X", "Y", params={"ok": 1}, ret_value="secret_ret")
        result = ctrl.search("secret", search_ret_value=False)
        assert result["count"] == 0  # ret_value skipped, params don't contain "secret"


# ---------------------------------------------------------------------------
# pagination and action dispatch
# ---------------------------------------------------------------------------

class TestPagination:
    def test_export_paginates_without_changing_total_count(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 5)
        result = ctrl.export_transactions(limit=2, offset=1)
        assert result["count"] == 5
        assert len(result["transactions"]) == 2
        assert result["transactions"][0]["index"] == 1
        assert result["has_more"] is True

    def test_query_last_page_reports_no_more(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 3)
        result = ctrl.query(limit=2, offset=2)
        assert result["count"] == 3
        assert [row["index"] for row in result["transactions"]] == [2]
        assert result["has_more"] is False

    def test_search_paginates(self):
        ctrl = _make_controller()
        _publish_n(ctrl, 4)
        result = ctrl.search("from", search_methods=True, limit=1, offset=1)
        assert result["count"] == 4
        assert len(result["transactions"]) == 1
        assert result["transactions"][0]["index"] == 1

    @pytest.mark.parametrize("method", ["export_transactions", "query", "search"])
    def test_negative_pagination_is_rejected(self, method):
        ctrl = _make_controller()
        _publish_n(ctrl, 1)
        with pytest.raises(ValueError, match="limit"):
            if method == "search":
                ctrl.search("from", search_methods=True, limit=-1)
            else:
                getattr(ctrl, method)(limit=-1)


class TestActionDispatch:
    def test_unknown_action_is_a_value_error(self):
        ctrl = _make_controller()
        with pytest.raises(ValueError, match="Unknown UI action"):
            ctrl.action("does_not_exist")

    def test_filter_normalises_string_type(self):
        ctrl = _make_controller()
        ctrl.publish(0, "X", "Y", params={}, ret_value=None)
        result = ctrl.action("filter", types="oneway")
        assert result["visible_count"] == 1

    def test_search_method_name_enabled(self):
        ctrl = _make_controller()
        ctrl.publish(0, "Lcom/example/Activity;", "onCreate", params={}, ret_value=None)
        result = ctrl.search("onCreate", search_methods=True)
        assert result["count"] == 1
        assert result["transactions"][0]["to_method"] == "onCreate"

    def test_search_method_name_disabled(self):
        ctrl = _make_controller()
        ctrl.publish(0, "Lcom/example/Activity;", "onCreate", params={}, ret_value=None)
        result = ctrl.search("onCreate", search_methods=False)
        assert result["count"] == 0

    def test_search_method_name_from_method(self):
        ctrl = _make_controller()
        ctrl.publish(0, "Lcom/example/Network;", "send", params={}, ret_value=None)
        result = ctrl.search("example", search_methods=True)
        assert result["count"] == 1

    def test_search_multiple_matches(self):
        ctrl = _make_controller()
        for i in range(3):
            ctrl.publish(i, f"From.C{i}", f"toM{i}", params={"k": "secret"}, ret_value=None)
        ctrl.publish(3, "From.D", "toN", params={"k": "other"}, ret_value=None)
        result = ctrl.search("secret")
        assert result["count"] == 3

    def test_search_registered_in_headless(self):
        from androguard.agent.headless import HeadlessAPI
        api = HeadlessAPI(include_ui=True)
        names = [t["name"] for t in api.list_tools()]
        assert "ui.search" in names

    def test_search_schema(self):
        from androguard.agent.headless import HeadlessAPI
        api = HeadlessAPI(include_ui=True)
        tools = {t["name"]: t for t in api.list_tools()}
        schema = tools["ui.search"]["inputSchema"]
        assert schema["properties"]["keyword"]["type"] == "string"
        assert "keyword" in schema["required"]
