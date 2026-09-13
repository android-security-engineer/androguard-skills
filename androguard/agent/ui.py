"""Automation bridge for AndroGuard's existing terminal UI.

The bridge is deliberately action-oriented. An Agent never needs to synthesize
terminal escape sequences: it can inspect a structured snapshot and issue
``move``, ``select``, ``focus``, ``filter``, or modal actions.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Mapping

from androguard.message import MessageEvent, MessageSystem


class UIAgentController:
    """Own or attach to a :class:`androguard.ui.DynamicUI` instance."""

    def __init__(self, ui=None, input_queue=None):
        self.input_queue = input_queue if input_queue is not None else queue.Queue()
        self.ui = ui
        self._thread = None
        self._error = None

    def _ensure_ui(self):
        if self.ui is None:
            from androguard.ui import DynamicUI

            self.ui = DynamicUI(self.input_queue)
        return self.ui

    def start(self, background: bool = True) -> dict[str, Any]:
        """Start the interactive terminal UI, optionally in a background thread."""
        ui = self._ensure_ui()
        if self._thread and self._thread.is_alive():
            return {"status": "running"}
        self._error = None
        if not background:
            ui.run()
            return {"status": "stopped"}

        def runner():
            try:
                ui.run()
            except Exception as exc:  # surfaced through snapshot, not lost in a thread
                self._error = str(exc)

        self._thread = threading.Thread(target=runner, name="androguard-ui", daemon=True)
        self._thread.start()
        return {"status": "starting"}

    def stop(self) -> dict[str, Any]:
        """Request a running prompt-toolkit application to exit."""
        ui = self._ensure_ui()
        ui.request_stop()
        return {"status": "stopping"}

    def snapshot(self) -> dict[str, Any]:
        """Return a structured view of the current UI state."""
        ui = self._ensure_ui()
        return ui.agent_snapshot(error=self._error)

    def action(self, action: str, **arguments: Any) -> dict[str, Any]:
        """Execute one safe, semantic UI action and return the new snapshot.

        Supported actions and their extra keyword arguments:
          select      index=<int>   — jump to transaction by absolute index
          move        step=<int>    — move selection by +N / -N rows
          focus       panel=<str>   — set keyboard focus ("transactions" or "details")
          filter      interface=<str>, method=<str>, types=<list[str]>  — filter transactions;
                      also syncs the visual filter panel so the human sees the same filter
          toggle_help               — show/hide the help overlay
          toggle_filters            — show/hide the filter panel
          close_modals              — hide all overlays
          clear                     — remove all transactions and reset filter
        """
        ui = self._ensure_ui()
        return ui.agent_action(action, **arguments)

    def get_transaction(self, index: int) -> dict[str, Any]:
        """Get full details of one transaction by its position in all_transactions.

        Unlike ui.snapshot which only shows visible summaries, this returns
        the complete params and ret_value for any transaction regardless of
        the current filter or view.
        """
        ui = self._ensure_ui()
        return ui.agent_get_transaction(index)

    def export_transactions(
        self,
        interface: str = None,
        method: str = None,
        types: list = None,
        limit: int = None,
        offset: int = None,
    ) -> dict[str, Any]:
        """Return transactions, optionally filtered and paginated.

        ``limit`` bounds the returned page and ``offset`` skips matching rows;
        omitted values preserve the historical behavior of returning all rows.
        """
        ui = self._ensure_ui()
        return ui.agent_export_transactions(
            interface=interface, method=method, types=types,
            limit=limit, offset=offset,
        )

    def search(
        self,
        keyword: str,
        search_params: bool = True,
        search_ret_value: bool = True,
        search_methods: bool = False,
        limit: int = None,
        offset: int = None,
    ) -> dict[str, Any]:
        """Full-text search across params/ret_value/method names.

        ``limit``/``offset`` page large result sets; the active filter is never
        changed.  Returns {"count": N, "transactions": [...], "has_more": bool}.
        """
        ui = self._ensure_ui()
        return ui.agent_search(
            keyword,
            search_params=search_params,
            search_ret_value=search_ret_value,
            search_methods=search_methods,
            limit=limit,
            offset=offset,
        )

    def query(
        self,
        interface: str = None,
        method: str = None,
        types: list = None,
        limit: int = None,
        offset: int = None,
    ) -> dict[str, Any]:
        """Count/list matching summaries without changing the active filter.

        ``limit`` and ``offset`` page large result sets without disrupting the
        human user's current view.
        """
        ui = self._ensure_ui()
        return ui.agent_query(
            interface=interface, method=method, types=types,
            limit=limit, offset=offset,
        )

    def publish(
        self,
        index: int,
        from_method: str,
        to_method: str,
        params: Any = None,
        ret_value: Any = None,
        kind: str = "event",
    ) -> dict[str, Any]:
        """Publish a trace event for UI testing or an external trace producer."""
        if kind == "system":
            message = MessageSystem(index, to_method, from_method, params, ret_value)
        else:
            message = MessageEvent(index, to_method, from_method, params, ret_value)
        self.input_queue.put(message)
        ui = self._ensure_ui()
        ui.process_data()
        return ui.agent_snapshot()
