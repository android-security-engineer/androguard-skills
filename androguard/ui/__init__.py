import json
import os
import queue

from loguru import logger
from prompt_toolkit import Application
from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.layout import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    Layout,
    UIContent,
    UIControl,
    VSplit,
    Window,
)
from prompt_toolkit.styles import Style

from androguard.message import Message
from androguard.ui.data_types import DisplayTransaction
from androguard.ui.filter import Filter
from androguard.ui.selection import SelectionViewList
from androguard.ui.widget.details import DetailsFrame
from androguard.ui.widget.filters import FiltersPanel
from androguard.ui.widget.help import HelpPanel
from androguard.ui.widget.toolbar import StatusToolbar
from androguard.ui.widget.transactions import TransactionFrame


class DummyControl(UIControl):
    """
    A dummy control object that doesn't paint any content.

    Useful for filling a :class:`~prompt_toolkit.layout.Window`. (The
    `fragment` and `char` attributes of the `Window` class can be used to
    define the filling.)
    """

    def create_content(self, width: int, height: int) -> UIContent:
        def get_line(i: int) -> StyleAndTextTuples:
            return []

        return UIContent(
            get_line=get_line, line_count=100**100
        )  # Something very big.

    def is_focusable(self) -> bool:
        return True


class DynamicUI:
    def __init__(self, input_queue):
        logger.info("Starting the Terminal UI")
        self.filter: Filter | None = None
        self.app = None
        self._running = False
        self._stop_requested = False
        self._pending_filter_sync = (
            None  # (interface, method, types) for render-thread apply
        )

        self.input_queue = input_queue
        self.all_transactions = []

        self.transactions = SelectionViewList([], max_view_size=1)
        self.transaction_table = TransactionFrame(self.transactions)

        self.details_pane = DetailsFrame(self.transactions, 1)

        self.filter_panel = FiltersPanel()
        self.help_panel = HelpPanel()

        self.focusable = [self.transaction_table, self.details_pane]
        self.focus_index = 0
        self.focusable[self.focus_index].activated = True

        try:
            dimensions = os.get_terminal_size()
        except OSError:
            # Agent clients and tests often construct the UI without a TTY.
            dimensions = os.terminal_size((120, 40))
        self.resize_components(dimensions)

    def run(self):
        self.focusable = [self.transaction_table, self.details_pane]
        self.focus_index = 0
        self.focusable[self.focus_index].activated = True
        self._stop_requested = False

        kb1 = KeyBindings()

        @kb1.add('tab')
        def _(event):
            self.focus_index = (self.focus_index + 1) % len(self.focusable)
            for i, f in enumerate(self.focusable):
                f.activated = i == self.focus_index

        @kb1.add('s-tab')
        def _(event):
            self.focus_index = (
                len(self.focusable) - 1
                if self.focus_index == 0
                else self.focus_index - 1
            )
            for i, f in enumerate(self.focusable):
                f.activated = i == self.focus_index

        dummy_control = DummyControl()
        main_layout = HSplit(
            key_bindings=kb1,
            children=[
                self.transaction_table,
                VSplit(
                    [
                        self.details_pane,
                        #    self.structure_pane,
                    ]
                ),
                StatusToolbar(self.transactions, self.filter_panel),
                Window(content=dummy_control),
            ],
        )

        @Condition
        def modal_panel_visible():
            return show_help() or show_filters()

        @Condition
        def show_filters():
            return self.filter_panel.visible

        @Condition
        def show_help():
            return self.help_panel.visible

        layout = Layout(
            container=FloatContainer(
                content=main_layout,
                floats=[
                    Float(
                        top=10,
                        content=ConditionalContainer(
                            content=self.filter_panel, filter=show_filters
                        ),
                    ),
                    Float(
                        top=10,
                        content=ConditionalContainer(
                            content=self.help_panel, filter=show_help
                        ),
                    ),
                ],
            )
        )

        style = Style(
            [
                ('field.selected', 'ansiblack bg:ansiwhite'),
                ('field.default', 'fg:ansiwhite'),
                ('frame.label', 'fg:ansiwhite'),
                ('frame.border', 'fg:ansiwhite'),
                ('frame.border.selected', 'fg:ansibrightgreen'),
                ('transaction.heading', 'ansiblack bg:ansigray'),
                ('transaction.selected', 'ansiblack bg:ansiwhite'),
                ('transaction.default', 'fg:ansiwhite'),
                ('transaction.unsupported', 'fg:ansibrightblack'),
                ('transaction.error', 'fg:ansired'),
                ('transaction.no_aidl', 'fg:ansiwhite'),
                ('transaction.oneway', 'fg:ansimagenta'),
                ('transaction.request', 'fg:ansicyan'),
                ('transaction.response', 'fg:ansiyellow'),
                ('hexdump.default', 'fg:ansiwhite'),
                ('hexdump.selected', 'fg:ansiblack bg:ansiwhite'),
                ('toolbar', 'bg:ansigreen'),
                ('toolbar.text', 'fg:ansiblack'),
                ('dialog', 'fg:ansiblack bg:ansiwhite'),
                ('dialog frame.border', 'fg:ansiblack bg:ansiwhite'),
                ('dialog frame.label', 'fg:ansiblack bg:ansiwhite'),
                ('dialogger.textarea', 'fg:ansiwhite bg:ansiblack'),
            ]
        )

        kb = KeyBindings()

        @kb.add('q')
        def _(event):
            logger.info("Q pressed. App exiting.")
            event.app.exit(exception=KeyboardInterrupt, style='class:aborting')

        @kb.add('h', filter=~modal_panel_visible | show_help)
        @kb.add("enter", filter=show_help)
        def _(event):
            self.help_panel.visible = not self.help_panel.visible

        @kb.add('f', filter=~modal_panel_visible)
        @kb.add("enter", filter=show_filters)
        def _(event):
            self.filter_panel.visible = not self.filter_panel.visible
            if self.filter_panel.visible:
                get_app().layout.focus(self.filter_panel.interface_textarea)
            else:
                self.filter = self.filter_panel.filter()
                self.transactions.assign(
                    [t for t in self.all_transactions if self.filter.passes(t)]
                )
                get_app().layout.focus(dummy_control)

        @kb.add("c-c")
        def _(event):
            active_frame = self.focusable[self.focus_index]
            active_frame.copy_to_clipboard()

        app = Application(
            layout,
            key_bindings=merge_key_bindings(
                [
                    kb,
                    self.transaction_table.key_bindings(),
                    # self.structure_pane.key_bindings(),
                    # self.hexdump_pane.key_bindings()
                ]
            ),
            full_screen=True,
            style=style,
        )
        self.app = app
        app.before_render += self.check_resize

        self._running = True
        app.before_render += self._process_data_hook
        try:
            app.run()
        finally:
            self._running = False
            self.app = None

    def _process_data_hook(self, _):
        self.process_data()
        self._apply_filter_sync()

    def _apply_filter_sync(self):
        if self._pending_filter_sync is None:
            return
        interface, method, types = self._pending_filter_sync
        self.filter_panel.interface_textarea.text = interface
        self.filter_panel.method_textarea.text = method
        wanted_types = set(types or [])
        for value, _label in self.filter_panel.type_filter_checkboxes.values:
            if value in wanted_types:
                if (
                    value
                    not in self.filter_panel.type_filter_checkboxes.current_values
                ):
                    self.filter_panel.type_filter_checkboxes.current_values.append(
                        value
                    )
            else:
                try:
                    self.filter_panel.type_filter_checkboxes.current_values.remove(
                        value
                    )
                except ValueError:
                    pass
        self._pending_filter_sync = None

    def request_stop(self):
        """Ask a running prompt-toolkit application to exit."""
        self._stop_requested = True
        if self.app is not None:
            self.app.exit()

    def agent_snapshot(self, error=None):
        """Return a JSON-friendly snapshot for an Agent or test client."""
        selected = None
        if self.transactions.selection_valid():
            item = self.transactions.selected()
            selected = {
                "index": item.index,
                "from_method": item.from_method,
                "to_method": item.to_method,
                "params": item.params,
                "ret_value": item.ret_value,
                "type": item.type(),
            }

        status = (
            "running" if self._running or self.app is not None else "stopped"
        )
        if self._stop_requested and status == "running":
            status = "stopping"
        return {
            "status": status,
            "transaction_count": len(self.all_transactions),
            "visible_count": len(self.transactions),
            "selected_index": self.transactions.selection,
            "selected": selected,
            "view": {
                "start": self.transactions.view.start,
                "end": self.transactions.view.end,
                "max_size": self.transactions.max_view_size,
            },
            "visible_transactions": [
                {
                    "index": t.index,
                    "from_method": t.from_method,
                    "to_method": t.to_method,
                    "type": t.type(),
                }
                for t in self.transactions.view_slice()
            ],
            "focus": self._focus_name(),
            "help_visible": self.help_panel.visible,
            "filters_visible": self.filter_panel.visible,
            "filter": {
                "interface": self.filter.interface if self.filter else None,
                "method": self.filter.method if self.filter else None,
                "types": self.filter.types if self.filter else [],
            },
            "error": error,
        }

    def _focus_name(self):
        if self.focus_index == 1:
            return "details"
        return "transactions"

    def _set_focus(self, panel):
        names = {"transactions": 0, "transaction": 0, "details": 1}
        try:
            self.focus_index = names[panel]
        except KeyError as exc:
            raise ValueError(
                "Unknown panel; expected transactions or details"
            ) from exc
        for index, frame in enumerate(self.focusable):
            frame.activated = index == self.focus_index
        if self.app is not None:
            container = self.focusable[self.focus_index]
            self.app.layout.focus(container)

    def _action_select(self, **arguments):
        index = int(arguments["index"])
        if not 0 <= index < len(self.transactions):
            raise IndexError("Selection index out of range")
        self.transactions.move_selection(index - self.transactions.selection)

    def _action_move(self, **arguments):
        self.transactions.move_selection(int(arguments.get("step", 0)))

    def _action_focus(self, **arguments):
        self._set_focus(arguments["panel"])

    def _action_filter(self, **arguments):
        types = self._normalise_types(arguments.get("types"))
        self.filter = Filter(
            interface=arguments.get("interface") or None,
            method=arguments.get("method") or None,
            types=types,
        )
        self.transactions.assign(
            item for item in self.all_transactions if self.filter.passes(item)
        )
        # Defer widget synchronization to the render thread while the TUI runs.
        self._pending_filter_sync = (
            arguments.get("interface") or "",
            arguments.get("method") or "",
            set(types),
        )
        if self.app is None:
            self._apply_filter_sync()

    def _action_toggle_help(self, **arguments):
        self.help_panel.visible = not self.help_panel.visible

    def _action_toggle_filters(self, **arguments):
        self.filter_panel.visible = not self.filter_panel.visible

    def _action_close_modals(self, **arguments):
        self.help_panel.visible = False
        self.filter_panel.visible = False

    def _action_clear(self, **arguments):
        self.all_transactions.clear()
        self.transactions.clear()
        self.filter = None
        self._pending_filter_sync = ("", "", set())
        if self.app is None:
            self._apply_filter_sync()

    def agent_action(self, action, **arguments):
        """Apply a semantic action and return the resulting snapshot."""
        handlers = {
            "select": self._action_select,
            "move": self._action_move,
            "focus": self._action_focus,
            "filter": self._action_filter,
            "toggle_help": self._action_toggle_help,
            "toggle_filters": self._action_toggle_filters,
            "close_modals": self._action_close_modals,
            "clear": self._action_clear,
        }
        try:
            handler = handlers[action]
        except KeyError as exc:
            raise ValueError(f"Unknown UI action: {action}") from exc
        handler(**arguments)
        if self.app is not None:
            self.app.invalidate()
        return self.agent_snapshot()

    def agent_get_transaction(self, index: int) -> dict:
        """Return full details of a single transaction from all_transactions by index."""
        if not 0 <= index < len(self.all_transactions):
            raise IndexError(
                f"Transaction index {index} out of range (0–{len(self.all_transactions) - 1})"
            )
        t = self.all_transactions[index]
        return {
            "index": t.index,
            "from_method": t.from_method,
            "to_method": t.to_method,
            "params": t.params,
            "ret_value": t.ret_value,
            "type": t.type(),
        }

    # ------------------------------------------------------------------
    # 事务匹配 / 分页辅助 —— 供 agent_query / agent_export / agent_search
    # 三个数据方法共享，避免各自重复遍历全表与构造 Filter。
    # ------------------------------------------------------------------
    def _normalise_types(self, types):
        if types is None:
            return []
        if isinstance(types, str):
            return [types]
        return list(types)

    def _matching_rows(self, interface, method, types, full=False):
        """Return all_transactions rows matching criteria.

        ``full=True`` includes params/ret_value (export), else returns
        index/from_method/to_method/type summaries (query/search).
        """
        from androguard.ui.filter import Filter as _Filter

        types = self._normalise_types(types)
        predicate = _Filter(
            interface=interface or None, method=method or None, types=types
        )
        rows = []
        for t in self.all_transactions:
            if not predicate.passes(t):
                continue
            if full:
                rows.append(
                    {
                        "index": t.index,
                        "from_method": t.from_method,
                        "to_method": t.to_method,
                        "params": t.params,
                        "ret_value": t.ret_value,
                        "type": t.type(),
                    }
                )
            else:
                rows.append(
                    {
                        "index": t.index,
                        "from_method": t.from_method,
                        "to_method": t.to_method,
                        "type": t.type(),
                    }
                )
        return rows

    @staticmethod
    def _page(rows, limit, offset):
        """Apply optional limit/offset to a matched row list.

        Returns (slice, has_more).  No limit → all rows, has_more=False.
        This keeps big transaction streams from exploding Agent payloads while
        remaining backward compatible (no limit → full list).
        """
        if limit is None:
            return rows, False
        if limit < 0:
            raise ValueError("limit must be >= 0")
        if offset is None:
            offset = 0
        if offset < 0:
            raise ValueError("offset must be >= 0")
        end = offset + limit
        return rows[offset:end], end < len(rows)

    def agent_export_transactions(
        self,
        interface: str = None,
        method: str = None,
        types: list = None,
        limit: int = None,
        offset: int = None,
    ) -> dict:
        """Return all transactions (optionally filtered) as a structured list.

        Reads from all_transactions so the result is not affected by the
        active view filter.  Pass interface/method/types to narrow results,
        and limit/offset to page large transaction streams.
        """
        rows = self._matching_rows(interface, method, types, full=True)
        page, has_more = self._page(rows, limit, offset)
        return {"count": len(rows), "transactions": page, "has_more": has_more}

    def agent_query(
        self,
        interface: str = None,
        method: str = None,
        types: list = None,
        limit: int = None,
        offset: int = None,
    ) -> dict:
        """Count and summarise transactions matching optional criteria without changing the active filter.

        Useful when the Agent needs statistics or a quick search without
        disrupting the view the human is currently looking at.
        """
        rows = self._matching_rows(interface, method, types)
        page, has_more = self._page(rows, limit, offset)
        return {"count": len(rows), "transactions": page, "has_more": has_more}

    def agent_search(
        self,
        keyword: str,
        search_params: bool = True,
        search_ret_value: bool = True,
        search_methods: bool = False,
        limit: int = None,
        offset: int = None,
    ) -> dict:
        """Full-text search across transaction params, ret_value, and optionally method names.

        Returns matching transaction summaries without changing the active filter.
        Case-insensitive substring match.  Useful for finding sensitive strings
        like passwords, tokens, URLs, or cryptographic operations.

        When search_methods=True, also matches against from_method/to_method.
        """
        if not keyword:
            return {"count": 0, "transactions": [], "has_more": False}
        keyword_lower = keyword.lower()
        rows = []
        for t in self.all_transactions:
            hit = False
            if search_methods:
                if (
                    keyword_lower in t.from_method.lower()
                    or keyword_lower in t.to_method.lower()
                ):
                    hit = True
            if not hit and search_params:
                if (
                    isinstance(t.params, str)
                    and keyword_lower in t.params.lower()
                ):
                    hit = True
                elif isinstance(t.params, dict):
                    if (
                        keyword_lower
                        in json.dumps(t.params, ensure_ascii=False).lower()
                    ):
                        hit = True
            if not hit and search_ret_value:
                if (
                    isinstance(t.ret_value, str)
                    and keyword_lower in t.ret_value.lower()
                ):
                    hit = True
                elif isinstance(t.ret_value, dict):
                    if (
                        keyword_lower
                        in json.dumps(t.ret_value, ensure_ascii=False).lower()
                    ):
                        hit = True
            if hit:
                rows.append(
                    {
                        "index": t.index,
                        "from_method": t.from_method,
                        "to_method": t.to_method,
                        "type": t.type(),
                    }
                )
        page, has_more = self._page(rows, limit, offset)
        return {"count": len(rows), "transactions": page, "has_more": has_more}

    def check_resize(self, _):
        try:
            new_dimensions = os.get_terminal_size()
        except OSError:
            new_dimensions = os.terminal_size((120, 40))
        if self.dimensions != new_dimensions:
            self.resize_components(new_dimensions)

    def resize_components(self, dimensions):
        self.dimensions = dimensions
        _, height = dimensions

        # Allow for the borders:
        # - top and bottom of transaction frame
        # - top and bottom of lower frames
        # - status bar
        border_allowance = 5
        available_height = height - border_allowance

        # Split into two halfs horizontally. If there are an odd number of lines give the extra to transactions.
        transactions_height = available_height - (available_height // 2)
        lower_panels_height = available_height // 2

        logger.debug(f"New terminal dimension: {dimensions}")
        logger.debug(
            f"{border_allowance=}, {transactions_height=}, {lower_panels_height=}, total={border_allowance+transactions_height+lower_panels_height}"
        )

        self.transaction_table.resize(transactions_height)
        # self.structure_pane.max_height = lower_panels_height
        # self.hexdump_pane.max_lines = lower_panels_height

    def get_available_blocks(self):
        blocks: list[Message] = []
        # Drain up to 500 pending blocks per render cycle to keep the TUI
        # responsive even when thousands of trace events are queued.
        max_per_frame = 500
        try:
            for _ in range(max_per_frame):
                blocks.append(self.input_queue.get_nowait())
        except queue.Empty:
            pass
        return blocks

    def process_data(self):
        blocks = self.get_available_blocks()
        for block in blocks:
            block = DisplayTransaction(block)
            if not self.filter or self.filter.passes(block):
                self.transactions.append(block)
            self.all_transactions.append(block)
        if blocks and self.app is not None:
            self.app.invalidate()
        return bool(blocks)
