"""HSplit-based layout builder for tail mode.

This module provides the TailLayout class for building the three-pane
split-screen interface: log output area (top), status bar (middle),
and command input line (bottom) using prompt_toolkit's layout system.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.layout.containers import ConditionalContainer, Float, FloatContainer, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl, UIContent, UIControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType

from pgtail_py.cli_tail import TAIL_MODE_COMMANDS
from pgtail_py.filter import LogLevel

if TYPE_CHECKING:
    pass


# Layout dimensions
LAYOUT_CONFIG = {
    "status_bar_height": 1,  # Fixed 1 line
    "input_line_height": 1,  # Fixed 1 line
    "min_log_height": 5,  # Minimum lines for log area
    "min_terminal_width": 40,
    "min_terminal_height": 10,
    "scroll_lines_per_wheel": 3,  # Lines per mouse wheel tick
}


class ScrollableFormattedTextControl(UIControl):
    """A FormattedTextControl wrapper that handles mouse scroll events.

    This control wraps a FormattedTextControl and intercepts mouse scroll
    events to provide scrolling functionality. The underlying text control
    remains non-focusable while still receiving mouse scroll events.
    """

    def __init__(
        self,
        text: Callable[[], FormattedText],
        on_scroll_up: Callable[[int], None],
        on_scroll_down: Callable[[int], None],
        scroll_lines: int = 3,
    ) -> None:
        """Initialize the scrollable control.

        Args:
            text: Callback that returns FormattedText content
            on_scroll_up: Callback for scroll up events (receives line count)
            on_scroll_down: Callback for scroll down events (receives line count)
            scroll_lines: Number of lines to scroll per wheel tick
        """
        self._text = text
        self._on_scroll_up = on_scroll_up
        self._on_scroll_down = on_scroll_down
        self._scroll_lines = scroll_lines
        # Create the underlying FormattedTextControl
        self._inner = FormattedTextControl(text=text, focusable=False)

    def create_content(self, width: int, height: int) -> UIContent:
        """Delegate content creation to the inner control."""
        return self._inner.create_content(width, height)

    def is_focusable(self) -> bool:
        """This control is not focusable."""
        return False

    def mouse_handler(self, mouse_event: MouseEvent) -> object:
        """Handle mouse events, specifically scroll up/down.

        Args:
            mouse_event: The mouse event to handle

        Returns:
            None if handled, NotImplemented otherwise
        """
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            self._on_scroll_up(self._scroll_lines)
            return None  # Event handled
        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self._on_scroll_down(self._scroll_lines)
            return None  # Event handled
        return NotImplemented  # Let other handlers try


class TailModeCompleter(Completer):
    """Completer for tail mode commands.

    Provides context-aware completion for commands available within
    the status bar tail mode interface.
    """

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterator[Completion]:
        """Generate completions for the current input.

        Args:
            document: The current document being edited.
            complete_event: The completion event.

        Yields:
            Completion objects for matching completions.
        """
        text = document.text_before_cursor
        parts = text.split()

        # Empty or first word - complete command names
        if not parts or (len(parts) == 1 and not text.endswith(" ")):
            prefix = parts[0].lower() if parts else ""
            yield from self._complete_commands(prefix)
            return

        # Command followed by space - complete arguments
        cmd = parts[0].lower()
        arg_text = parts[-1] if len(parts) > 1 and not text.endswith(" ") else ""

        if cmd == "level":
            yield from self._complete_levels(
                arg_text, parts[1:] if text.endswith(" ") else parts[1:-1]
            )
        elif cmd == "filter":
            yield from self._complete_filter(arg_text)
        elif cmd in ("since", "until", "between"):
            yield from self._complete_time(arg_text)
        elif cmd == "slow":
            yield from self._complete_slow(arg_text)

    def _complete_commands(self, prefix: str) -> Iterator[Completion]:
        """Complete command names."""
        command_descriptions = {
            "level": "Filter by log level (e.g., 'level error,warning')",
            "filter": "Filter by regex pattern (e.g., 'filter /pattern/')",
            "since": "Show entries since time (e.g., 'since 5m')",
            "until": "Show entries until time",
            "between": "Show entries in time range",
            "slow": "Set slow query threshold (ms)",
            "clear": "Clear all filters",
            "errors": "Show error statistics",
            "connections": "Show connection statistics",
            "pause": "Pause log following",
            "follow": "Resume log following",
            "help": "Show commands and keyboard shortcuts",
            "stop": "Exit tail mode",
            "exit": "Exit tail mode",
            "q": "Exit tail mode",
        }
        for name in TAIL_MODE_COMMANDS:
            if name.startswith(prefix):
                description = command_descriptions.get(name, "")
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display_meta=description,
                )

    def _complete_levels(self, prefix: str, already_selected: list[str]) -> Iterator[Completion]:
        """Complete log level names."""
        prefix_upper = prefix.upper()
        selected_upper = {s.upper() for s in already_selected}

        # Special case: ALL
        if "ALL".startswith(prefix_upper) and "ALL" not in selected_upper:
            yield Completion(
                "ALL",
                start_position=-len(prefix),
                display_meta="Show all log levels",
            )

        # Log levels
        for level in LogLevel:
            if level.name not in selected_upper and level.name.startswith(prefix_upper):
                yield Completion(
                    level.name,
                    start_position=-len(prefix),
                    display_meta=f"Severity {level.value}",
                )

    def _complete_filter(self, prefix: str) -> Iterator[Completion]:
        """Complete filter patterns."""
        if "clear".startswith(prefix.lower()):
            yield Completion(
                "clear",
                start_position=-len(prefix),
                display_meta="Clear all filters",
            )

    def _complete_time(self, prefix: str) -> Iterator[Completion]:
        """Complete time values."""
        options = {
            "5m": "5 minutes",
            "30m": "30 minutes",
            "1h": "1 hour",
            "2h": "2 hours",
            "1d": "1 day",
        }
        prefix_lower = prefix.lower()
        for name, description in options.items():
            if name.startswith(prefix_lower):
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display_meta=description,
                )

    def _complete_slow(self, prefix: str) -> Iterator[Completion]:
        """Complete slow query thresholds."""
        options = {
            "100": "100ms threshold",
            "500": "500ms threshold",
            "1000": "1s threshold",
            "off": "Disable slow query highlighting",
        }
        prefix_lower = prefix.lower()
        for name, description in options.items():
            if name.startswith(prefix_lower):
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display_meta=description,
                )


# Default style classes used in the layout (keys without "class:" prefix)
# These are fallbacks if no theme is provided
DEFAULT_LAYOUT_STYLES = {
    # Log area
    "log": "",  # Base log text
    # Status bar - use reverse video for better contrast across terminals
    "status": "reverse",
    "status.follow": "fg:ansigreen bold reverse",
    "status.paused": "fg:ansiyellow bold reverse",
    "status.error": "fg:ansired bold reverse",
    "status.warning": "fg:ansiyellow reverse",
    "status.sep": "reverse",
    "status.filter": "fg:ansicyan reverse",
    "status.instance": "reverse",
    # Input line
    "input": "",
    "input.prompt": "fg:ansigreen bold",
    # Command output separators
    "separator": "fg:ansibrightblack",
    # Warning for small terminal
    "warning": "fg:ansiyellow bold",
    # Debug panel overlay
    "debug": "bg:ansiblack fg:ansiwhite",
    "debug.border": "bg:ansiblack fg:ansibrightblack",
    "debug.header": "bg:ansiblue fg:ansiwhite bold",
    "debug.label": "bg:ansiblack fg:ansicyan",
    "debug.value": "bg:ansiblack fg:ansiwhite",
    "debug.warning": "bg:ansiblack fg:ansiyellow",
}

# Backwards compatibility alias
LAYOUT_STYLES = DEFAULT_LAYOUT_STYLES


def generate_layout_styles_from_theme(theme: object) -> dict[str, str]:
    """Generate layout styles from a Theme object.

    Maps theme UI elements to prompt_toolkit style strings for the tail mode layout.

    Args:
        theme: A Theme object with ui dict containing status bar colors

    Returns:
        Dict mapping style class names to prompt_toolkit style strings
    """
    from pgtail_py.theme import Theme

    if not isinstance(theme, Theme):
        return dict(DEFAULT_LAYOUT_STYLES)

    styles = dict(DEFAULT_LAYOUT_STYLES)  # Start with defaults

    # Helper to convert ColorStyle to style string
    def style_str(key: str) -> str:
        color_style = theme.get_ui_style(key)
        return color_style.to_style_string()

    # Override with theme colors where available
    if theme.get_ui_style("status").fg or theme.get_ui_style("status").bg:
        styles["status"] = style_str("status")
        # Use status background for separators too
        styles["status.sep"] = style_str("status")

    if theme.get_ui_style("status_follow").fg:
        styles["status.follow"] = style_str("status_follow")

    if theme.get_ui_style("status_paused").fg:
        styles["status.paused"] = style_str("status_paused")

    if theme.get_ui_style("status_error").fg:
        styles["status.error"] = style_str("status_error")

    if theme.get_ui_style("status_warning").fg:
        styles["status.warning"] = style_str("status_warning")

    if theme.get_ui_style("status_filter").fg:
        styles["status.filter"] = style_str("status_filter")

    if theme.get_ui_style("status_instance").fg:
        styles["status.instance"] = style_str("status_instance")

    if theme.get_ui_style("input").fg or theme.get_ui_style("input").bg:
        styles["input"] = style_str("input")

    if theme.get_ui_style("input_prompt").fg:
        styles["input.prompt"] = style_str("input_prompt")

    if theme.get_ui_style("separator").fg:
        styles["separator"] = style_str("separator")

    return styles


class TailLayout:
    """HSplit-based layout manager for the tail interface.

    Creates a vertical split with (from top to bottom):
    - Log output area (flexible height)
    - Horizontal separator line (fixed 1 line)
    - Command input line (fixed 1 line)
    - Horizontal separator line (fixed 1 line)
    - Status bar (fixed 1 line)
    - Optional debug overlay (toggleable with F12)

    Attributes:
        _root: Top-level FloatContainer wrapping the HSplit
        _layout: prompt_toolkit Layout wrapping the root
        _log_window: Window for log display
        _status_window: Window for status bar
        _input_window: Window for command input
        _input_buffer: Editable buffer for command input
        _key_bindings: KeyBindings for navigation
        _debug_visible: Whether debug overlay is showing
    """

    def __init__(
        self,
        log_content_callback: Callable[[], FormattedText],
        status_content_callback: Callable[[], FormattedText],
        on_command_submit: Callable[[str], None],
        on_scroll_up: Callable[[int], None],
        on_scroll_down: Callable[[int], None],
        on_scroll_to_top: Callable[[], None],
        on_resume_follow: Callable[[], None],
        on_redraw: Callable[[], None],
        debug_info_callback: Callable[[], dict[str, object]] | None = None,
    ) -> None:
        """Build the complete tail mode layout.

        Args:
            log_content_callback: Returns FormattedText for log area
            status_content_callback: Returns FormattedText for status bar
            on_command_submit: Called when user presses Enter in input
            on_scroll_up: Called with line count for scroll up events
            on_scroll_down: Called with line count for scroll down events
            on_scroll_to_top: Called for Home key
            on_resume_follow: Called for End key
            on_redraw: Called for Ctrl+L to force redraw
            debug_info_callback: Returns dict of debug info for overlay
        """
        # Store callbacks
        self._log_content_callback = log_content_callback
        self._status_content_callback = status_content_callback
        self._on_command_submit = on_command_submit
        self._on_scroll_up = on_scroll_up
        self._on_scroll_down = on_scroll_down
        self._on_scroll_to_top = on_scroll_to_top
        self._on_resume_follow = on_resume_follow
        self._on_redraw = on_redraw
        self._debug_info_callback = debug_info_callback

        # Debug overlay state
        self._debug_visible = False

        # Create input buffer with completer
        self._completer = TailModeCompleter()
        self._input_buffer = Buffer(
            multiline=False,
            accept_handler=self._handle_input_accept,
            completer=self._completer,
            complete_while_typing=True,
        )

        # Create key bindings
        self._key_bindings = self._create_key_bindings()

        # Build layout components
        self._build_layout()

    def _handle_input_accept(self, buff: Buffer) -> bool:
        """Handle Enter key in input buffer.

        Args:
            buff: The input buffer

        Returns:
            True to clear buffer after accept
        """
        text = buff.text.strip()
        if text:
            self._on_command_submit(text)
        return True  # Clear buffer

    def _create_key_bindings(self) -> KeyBindings:
        """Create key bindings for tail mode navigation.

        Supports both standard keys and vim-like navigation:
        - Arrow keys, Page Up/Down, Home/End work always
        - Vim keys (j/k/g/G/Ctrl+d/u/f/b) work when input is empty

        Returns:
            KeyBindings with scroll and control handlers
        """
        kb = KeyBindings()

        # Filter: vim keys only work when input buffer is empty
        input_is_empty = Condition(lambda: len(self._input_buffer.text) == 0)

        # Calculate half-page size dynamically
        def get_half_page() -> int:
            return max(1, self.get_visible_height() // 2)

        def get_full_page() -> int:
            return max(1, self.get_visible_height())

        # === Line-by-line navigation (only when input empty) ===

        @kb.add("up", filter=input_is_empty)
        def scroll_up_line(event: object) -> None:
            """Scroll up 1 line (up arrow)."""
            self._on_scroll_up(1)

        _ = scroll_up_line  # Registered via decorator

        @kb.add("down", filter=input_is_empty)
        def scroll_down_line(event: object) -> None:
            """Scroll down 1 line (down arrow)."""
            self._on_scroll_down(1)

        _ = scroll_down_line  # Registered via decorator

        @kb.add("pageup")
        def scroll_up_page(event: object) -> None:
            """Scroll up 1 page."""
            self._on_scroll_up(get_full_page())

        _ = scroll_up_page  # Registered via decorator

        @kb.add("pagedown")
        def scroll_down_page(event: object) -> None:
            """Scroll down 1 page."""
            self._on_scroll_down(get_full_page())

        _ = scroll_down_page  # Registered via decorator

        @kb.add("home")
        def scroll_to_top(event: object) -> None:
            """Scroll to buffer start."""
            self._on_scroll_to_top()

        _ = scroll_to_top  # Registered via decorator

        @kb.add("end")
        def resume_follow(event: object) -> None:
            """Resume follow mode (clears selection)."""
            self._on_resume_follow()

        _ = resume_follow  # Registered via decorator

        # === Vim-style navigation ===

        @kb.add("c-u")
        def vim_scroll_up_half(event: object) -> None:
            """Scroll up half page (vim Ctrl+u)."""
            self._on_scroll_up(get_half_page())

        _ = vim_scroll_up_half  # Registered via decorator

        @kb.add("c-d")
        def vim_scroll_down_half(event: object) -> None:
            """Scroll down half page (vim Ctrl+d)."""
            self._on_scroll_down(get_half_page())

        _ = vim_scroll_down_half  # Registered via decorator

        @kb.add("c-b")
        def vim_scroll_up_full(event: object) -> None:
            """Scroll up full page (vim Ctrl+b)."""
            self._on_scroll_up(get_full_page())

        _ = vim_scroll_up_full  # Registered via decorator

        @kb.add("c-f")
        def vim_scroll_down_full(event: object) -> None:
            """Scroll down full page (vim Ctrl+f)."""
            self._on_scroll_down(get_full_page())

        _ = vim_scroll_down_full  # Registered via decorator

        # === Utility bindings ===

        @kb.add("c-l")
        def redraw_screen(event: object) -> None:
            """Force screen redraw."""
            self._on_redraw()

        _ = redraw_screen  # Registered via decorator

        @kb.add("enter")
        def submit_command(event: object) -> None:
            """Submit command on Enter."""
            text = self._input_buffer.text.strip()
            if text:
                self._on_command_submit(text)
            self._input_buffer.reset()

        _ = submit_command  # Registered via decorator

        @kb.add("f12")
        def toggle_debug(event: object) -> None:
            """Toggle debug overlay with F12."""
            self._debug_visible = not self._debug_visible
            from prompt_toolkit.application import get_app

            app = get_app()
            if app:
                app.invalidate()

        _ = toggle_debug  # Registered via decorator

        return kb

    def _build_layout(self) -> None:
        """Build the three-pane HSplit layout with debug overlay."""
        # Log output area - uses ScrollableFormattedTextControl for mouse scroll
        # Uses weight=1 to expand and fill available vertical space
        log_control = ScrollableFormattedTextControl(
            text=self._log_content_callback,
            on_scroll_up=self._on_scroll_up,
            on_scroll_down=self._on_scroll_down,
            scroll_lines=LAYOUT_CONFIG["scroll_lines_per_wheel"],
        )
        self._log_window = Window(
            content=log_control,
            wrap_lines=False,  # Disable wrapping to keep height calculation accurate
            style="class:log",
            height=Dimension(weight=1),  # Expand to fill available space
        )

        # Terminal size warning - shown when terminal is too small
        self._terminal_too_small = False

        def check_terminal_size() -> bool:
            """Check if terminal is below minimum size."""
            return self._terminal_too_small

        terminal_warning_control = FormattedTextControl(
            text=lambda: FormattedText(
                [
                    ("class:warning", "Terminal too small! Minimum: 40x10"),
                ]
            ),
            focusable=False,
        )
        self._warning_window = ConditionalContainer(
            content=Window(
                content=terminal_warning_control,
                height=Dimension.exact(1),
                style="class:warning",
            ),
            filter=Condition(check_terminal_size),
        )

        # Status bar - dynamic content, fixed 1 line
        status_control = FormattedTextControl(
            text=self._status_content_callback,
            focusable=False,
        )
        self._status_window = Window(
            content=status_control,
            height=Dimension.exact(1),
            style="class:status",
        )

        # Command input line - editable buffer, fixed 1 line
        input_control = BufferControl(
            buffer=self._input_buffer,
            input_processors=[BeforeInput("tail> ", style="class:input.prompt")],
            focusable=True,
        )
        self._input_window = Window(
            content=input_control,
            height=Dimension.exact(1),
            style="class:input",
        )

        # Horizontal separator lines above and below input (like Claude Code)
        input_separator_top = Window(
            height=Dimension.exact(1),
            char="─",
            style="class:separator",
        )
        input_separator_bottom = Window(
            height=Dimension.exact(1),
            char="─",
            style="class:separator",
        )

        # Build HSplit with log at top, input in middle, status at bottom
        # Layout order: warning, log, separator, input, separator, status
        main_hsplit = HSplit(
            [
                self._warning_window,  # Only shown when terminal too small
                self._log_window,
                input_separator_top,  # ──── line above input
                self._input_window,
                input_separator_bottom,  # ──── line below input
                self._status_window,
            ]
        )

        # Debug overlay panel
        debug_control = FormattedTextControl(
            text=self._get_debug_content,
            focusable=False,
        )
        debug_window = Window(
            content=debug_control,
            style="class:debug",
        )

        # Wrap main layout with FloatContainer for debug overlay and completions
        self._root = FloatContainer(
            content=main_hsplit,
            floats=[
                # Completion menu - positioned near cursor
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=8),
                ),
                # Debug overlay
                Float(
                    content=ConditionalContainer(
                        content=debug_window,
                        filter=Condition(lambda: self._debug_visible),
                    ),
                    right=1,
                    top=1,
                    width=45,
                    height=20,
                ),
            ],
        )

        # Create Layout
        self._layout = Layout(self._root, focused_element=self._input_window)

    def _get_debug_content(self) -> FormattedText:
        """Generate content for debug overlay panel.

        Returns:
            FormattedText with diagnostic information
        """
        from prompt_toolkit.application import get_app

        lines: list[tuple[str, str]] = []

        # Header
        lines.append(("class:debug.header", "═══════ DEBUG INFO (F12) ═══════\n"))

        # Get terminal size
        app = get_app()
        if app and app.output:
            size = app.output.get_size()
            lines.append(("class:debug.label", "Terminal Size: "))
            lines.append(("class:debug.value", f"{size.columns}x{size.rows}\n"))
        else:
            lines.append(("class:debug.label", "Terminal Size: "))
            lines.append(("class:debug.warning", "unknown\n"))

        # Calculated visible height with debug info
        visible_height = self.get_visible_height()
        lines.append(("class:debug.label", "Visible Height: "))
        lines.append(("class:debug.value", f"{visible_height} lines\n"))

        # Debug: check why visible height might be wrong
        lines.append(("class:debug.label", "Expected Height: "))
        if app and app.output:
            expected = app.output.get_size().rows - 2
            if expected != visible_height:
                lines.append(("class:debug.warning", f"{expected} (MISMATCH!)\n"))
            else:
                lines.append(("class:debug.value", f"{expected}\n"))
        else:
            lines.append(("class:debug.warning", "N/A (no app.output)\n"))

        # Get debug info from callback if available
        if self._debug_info_callback:
            try:
                info = self._debug_info_callback()

                lines.append(("class:debug.border", "─" * 33 + "\n"))
                lines.append(("class:debug.header", "Buffer State\n"))

                if "total_entries" in info:
                    lines.append(("class:debug.label", "Total Entries: "))
                    lines.append(("class:debug.value", f"{info['total_entries']}\n"))

                if "filtered_count" in info:
                    lines.append(("class:debug.label", "Filtered Count: "))
                    lines.append(("class:debug.value", f"{info['filtered_count']}\n"))

                if "visual_lines" in info:
                    lines.append(("class:debug.label", "Visual Lines: "))
                    lines.append(("class:debug.value", f"{info['visual_lines']}\n"))

                if "scroll_offset" in info:
                    lines.append(("class:debug.label", "Scroll Offset: "))
                    lines.append(("class:debug.value", f"{info['scroll_offset']}\n"))

                if "follow_mode" in info:
                    mode = "FOLLOW" if info["follow_mode"] else "PAUSED"
                    style = "class:debug.value" if info["follow_mode"] else "class:debug.warning"
                    lines.append(("class:debug.label", "Mode: "))
                    lines.append((style, f"{mode}\n"))

                if "new_since_pause" in info:
                    lines.append(("class:debug.label", "New Since Pause: "))
                    lines.append(("class:debug.value", f"{info['new_since_pause']}\n"))

                if "max_size" in info:
                    lines.append(("class:debug.label", "Max Buffer Size: "))
                    lines.append(("class:debug.value", f"{info['max_size']}\n"))

                if "display_height" in info:
                    lines.append(("class:debug.label", "Display Height: "))
                    lines.append(("class:debug.value", f"{info['display_height']}\n"))

                # Filters section
                lines.append(("class:debug.border", "─" * 33 + "\n"))
                lines.append(("class:debug.header", "Active Filters\n"))

                if "active_levels" in info:
                    levels = info["active_levels"]
                    if levels:
                        lines.append(("class:debug.label", "Levels: "))
                        lines.append(("class:debug.value", f"{levels}\n"))
                    else:
                        lines.append(("class:debug.label", "Levels: "))
                        lines.append(("class:debug.value", "ALL\n"))

                if "time_filter" in info and info["time_filter"]:
                    lines.append(("class:debug.label", "Time: "))
                    lines.append(("class:debug.value", f"{info['time_filter']}\n"))

                if "regex_filter" in info and info["regex_filter"]:
                    lines.append(("class:debug.label", "Regex: "))
                    lines.append(("class:debug.value", f"{info['regex_filter']}\n"))

            except Exception as e:
                lines.append(("class:debug.warning", f"Error: {e}\n"))
        else:
            lines.append(("class:debug.border", "─" * 33 + "\n"))
            lines.append(("class:debug.warning", "No debug callback configured\n"))

        # Footer with tip
        lines.append(("class:debug.border", "─" * 33 + "\n"))
        lines.append(("class:debug.label", "Press F12 to close\n"))

        return FormattedText(lines)

    @property
    def root(self) -> FloatContainer:
        """Top-level container (FloatContainer wrapping HSplit) for the layout."""
        return self._root

    @property
    def layout(self) -> Layout:
        """prompt_toolkit Layout wrapping the root container."""
        return self._layout

    @property
    def input_buffer(self) -> Buffer:
        """Editable buffer for the command input line."""
        return self._input_buffer

    def get_key_bindings(self) -> KeyBindings:
        """Return key bindings for tail mode navigation."""
        return self._key_bindings

    def get_visible_height(self) -> int:
        """Get the visible height of the log area.

        Calculates based on terminal height minus fixed UI elements:
        separator (1) + input (1) + separator (1) + status bar (1) = 4 lines.

        Returns:
            Number of visible lines in log area
        """
        try:
            from prompt_toolkit.application import get_app

            app = get_app()
            if app and app.output:
                size = app.output.get_size()
                # Terminal height minus sep (1) + input (1) + sep (1) + status (1) = 4
                return max(1, size.rows - 4)
        except Exception:
            pass
        # Fallback estimate
        return 20

    def check_terminal_size(self, width: int, height: int) -> bool:
        """Check if terminal size is adequate and update warning state.

        Args:
            width: Terminal width in columns
            height: Terminal height in rows

        Returns:
            True if terminal is large enough, False if too small
        """
        min_width = LAYOUT_CONFIG["min_terminal_width"]
        min_height = LAYOUT_CONFIG["min_terminal_height"]

        is_adequate = width >= min_width and height >= min_height
        self._terminal_too_small = not is_adequate

        return is_adequate
