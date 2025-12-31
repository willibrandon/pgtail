"""Custom Log widget with vim-style navigation and visual mode selection.

This module provides TailLog, a subclass of Textual's Log widget that adds:
- Vim-style navigation keybindings (j/k/g/G/Ctrl+D/Ctrl+U)
- Visual mode selection (v/V) with keyboard-based text selection
- Clipboard integration with OSC 52 and pyperclip fallback
- Standard shortcuts (Ctrl+A, Ctrl+C)

Classes:
    TailLog: Log widget with vim-style navigation and visual mode.
    SelectionCopied: Message emitted when text is copied to clipboard.
    VisualModeChanged: Message emitted when visual mode state changes.
"""

from __future__ import annotations

from typing import ClassVar

from rich.style import Style
from rich.text import Text
from textual import events
from textual.binding import Binding, BindingType
from textual.geometry import Offset
from textual.message import Message
from textual.selection import Selection
from textual.strip import Strip
from textual.widgets import Log


class TailLog(Log):
    """Log widget with vim-style navigation and visual mode selection.

    Extends Textual's Log widget with:
    - ALLOW_SELECT = True for mouse text selection
    - Vim-style navigation keys (j/k/g/G/Ctrl+D/Ctrl+U/Ctrl+F/Ctrl+B)
    - Visual mode (v/V) for keyboard-based selection
    - Clipboard copy with OSC 52 + pyperclip fallback
    - Standard shortcuts (Ctrl+A, Ctrl+C)

    Attributes:
        _visual_mode: True if currently in visual mode.
        _visual_line_mode: True if selecting full lines in visual mode.
        _visual_anchor_line: Line index where visual selection started.
    """

    ALLOW_SELECT: ClassVar[bool] = True

    BINDINGS: ClassVar[list[BindingType]] = [
        # Vim navigation
        Binding("j", "scroll_down", "Down", show=False),
        Binding("k", "scroll_up", "Up", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("shift+g", "scroll_end", "Bottom", show=False),
        Binding("f", "follow", "Follow", show=False),
        Binding("ctrl+d", "half_page_down", "Half page down", show=False),
        Binding("ctrl+u", "half_page_up", "Half page up", show=False),
        Binding("ctrl+f", "page_down", "Page down", show=False),
        Binding("pagedown", "page_down", "Page down", show=False),
        Binding("ctrl+b", "page_up", "Page up", show=False),
        Binding("pageup", "page_up", "Page up", show=False),
        # Visual mode
        Binding("v", "visual_mode", "Visual mode", show=False),
        Binding("shift+v", "visual_line_mode", "Visual line mode", show=False),
        Binding("y", "yank", "Yank", show=False),
        Binding("escape", "clear_selection", "Clear", show=False),
        # Standard shortcuts
        Binding("ctrl+a", "select_all", "Select all", show=False),
        Binding("ctrl+c", "copy_selection", "Copy", show=False),
    ]

    class SelectionCopied(Message):
        """Emitted when text is copied to clipboard.

        Attributes:
            text: The text that was copied.
            char_count: Number of characters copied.
        """

        def __init__(self, text: str, char_count: int) -> None:
            """Initialize SelectionCopied message.

            Args:
                text: The text that was copied.
                char_count: Number of characters copied.
            """
            self.text = text
            self.char_count = char_count
            super().__init__()

    class VisualModeChanged(Message):
        """Emitted when visual mode state changes.

        Attributes:
            active: True if entering visual mode, False if exiting.
            line_mode: True if in visual line mode (V), False for char mode (v).
        """

        def __init__(self, active: bool, line_mode: bool) -> None:
            """Initialize VisualModeChanged message.

            Args:
                active: True if entering visual mode.
                line_mode: True if in visual line mode.
            """
            self.active = active
            self.line_mode = line_mode
            super().__init__()

    def __init__(
        self,
        max_lines: int | None = 10000,
        auto_scroll: bool = True,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize TailLog widget.

        Args:
            max_lines: Maximum lines to retain (default 10,000).
            auto_scroll: Auto-scroll to new content (default True).
            name: Widget name.
            id: Widget ID for CSS/queries.
            classes: CSS classes.
        """
        super().__init__(
            max_lines=max_lines,
            auto_scroll=auto_scroll,
            name=name,
            id=id,
            classes=classes,
        )
        self._visual_mode: bool = False
        self._visual_line_mode: bool = False
        self._visual_anchor_line: int | None = None
        self._cursor_line: int = 0

    @property
    def cursor_line(self) -> int:
        """Current cursor line position."""
        return self._cursor_line

    @property
    def visual_mode(self) -> bool:
        """True if currently in visual mode."""
        return self._visual_mode

    @property
    def visual_line_mode(self) -> bool:
        """True if in visual line mode (selecting full lines)."""
        return self._visual_line_mode

    # Navigation actions

    def action_scroll_down(self) -> None:
        """Move cursor/selection down one line."""
        if self.line_count == 0:
            return
        self._cursor_line = min(self._cursor_line + 1, self.line_count - 1)
        self._select_cursor_line()
        self._scroll_cursor_visible()

    def action_scroll_up(self) -> None:
        """Move cursor/selection up one line."""
        if self.line_count == 0:
            return
        self._cursor_line = max(self._cursor_line - 1, 0)
        self._select_cursor_line()
        self._scroll_cursor_visible()

    def action_scroll_home(self) -> None:
        """Move cursor/selection to top of log."""
        if self.line_count == 0:
            return
        self._cursor_line = 0
        self._select_cursor_line()
        self.scroll_home()

    def action_scroll_end(self) -> None:
        """Move cursor/selection to bottom of log."""
        if self.line_count == 0:
            return
        self._cursor_line = self.line_count - 1
        self._select_cursor_line()
        self.scroll_end()

    def action_follow(self) -> None:
        """Enter follow mode: go to tail, clear selection, enable auto-scroll."""
        if self.line_count == 0:
            return
        # Exit visual mode
        self._visual_mode = False
        self._visual_line_mode = False
        self._visual_anchor_line = None
        # Move to end
        self._cursor_line = self.line_count - 1
        self._set_selection(None)
        self.scroll_end()

    def action_half_page_down(self) -> None:
        """Move cursor/selection down half a page."""
        if self.line_count == 0:
            return
        height = self.scrollable_content_region.height
        self._cursor_line = min(self._cursor_line + height // 2, self.line_count - 1)
        self._select_cursor_line()
        self._scroll_cursor_visible()

    def action_half_page_up(self) -> None:
        """Move cursor/selection up half a page."""
        if self.line_count == 0:
            return
        height = self.scrollable_content_region.height
        self._cursor_line = max(self._cursor_line - height // 2, 0)
        self._select_cursor_line()
        self._scroll_cursor_visible()

    def action_page_down(self) -> None:
        """Move cursor/selection down one full page."""
        if self.line_count == 0:
            return
        height = self.scrollable_content_region.height
        self._cursor_line = min(self._cursor_line + height, self.line_count - 1)
        self._select_cursor_line()
        self._scroll_cursor_visible()

    def action_page_up(self) -> None:
        """Move cursor/selection up one full page."""
        if self.line_count == 0:
            return
        height = self.scrollable_content_region.height
        self._cursor_line = max(self._cursor_line - height, 0)
        self._select_cursor_line()
        self._scroll_cursor_visible()

    # Visual mode actions

    def action_visual_mode(self) -> None:
        """Enter visual mode for single-line selection."""
        if self.line_count == 0:
            return
        self._visual_mode = True
        self._visual_line_mode = False
        self._visual_anchor_line = self._cursor_line
        self._select_cursor_line()
        self.post_message(self.VisualModeChanged(active=True, line_mode=False))

    def action_visual_line_mode(self) -> None:
        """Enter visual line mode for multi-line selection."""
        if self.line_count == 0:
            return
        self._visual_mode = True
        self._visual_line_mode = True
        self._visual_anchor_line = self._cursor_line
        self._select_cursor_line()
        self.post_message(self.VisualModeChanged(active=True, line_mode=True))

    def action_yank(self) -> None:
        """Copy selection to clipboard and exit visual mode."""
        # Get selected text - no-op if no selection
        selection = self.text_selection
        if selection is None:
            return

        # Get selected text using get_selection
        result = self.get_selection(selection)
        if result is None:
            return

        selected_text, _ = result
        if not selected_text:
            return

        # Strip Rich markup before copying
        plain_text = self._strip_markup(selected_text)

        # Copy to clipboard
        success = self._copy_with_fallback(plain_text)
        if success:
            self.post_message(self.SelectionCopied(plain_text, len(plain_text)))

        # Exit visual mode and clear selection
        self._exit_visual_mode()

    def action_clear_selection(self) -> None:
        """Clear selection and exit visual mode."""
        self._exit_visual_mode()

    def action_select_all(self) -> None:
        """Select all content in the log."""
        from textual.selection import SELECT_ALL

        self._set_selection(SELECT_ALL)

    def action_copy_selection(self) -> None:
        """Copy current selection to clipboard (Ctrl+C)."""
        selection = self.text_selection
        if selection is None:
            return  # No-op with no selection

        result = self.get_selection(selection)
        if result is None:
            return

        selected_text, _ = result
        if not selected_text:
            return

        # Strip Rich markup before copying
        plain_text = self._strip_markup(selected_text)

        success = self._copy_with_fallback(plain_text)
        if success:
            self.post_message(self.SelectionCopied(plain_text, len(plain_text)))

    # Event handlers

    def on_click(self, event: events.Click) -> None:
        """Handle mouse click to select line.

        Args:
            event: Click event with position information.
        """
        if self.line_count == 0:
            return

        # Calculate which line was clicked and set cursor
        clicked_line = self.scroll_offset.y + event.y
        self._cursor_line = max(0, min(clicked_line, self.line_count - 1))

        # Exit visual mode on click
        if self._visual_mode:
            self._visual_mode = False
            self._visual_line_mode = False
            self._visual_anchor_line = None

        # Select the clicked line
        self._select_cursor_line()

    # Helper methods

    def _select_cursor_line(self) -> None:
        """Select based on cursor position and visual mode state."""
        if self.line_count == 0:
            return

        if self._visual_mode and self._visual_line_mode and self._visual_anchor_line is not None:
            # Visual line mode: select from anchor to cursor
            start_line = min(self._visual_anchor_line, self._cursor_line)
            end_line = max(self._visual_anchor_line, self._cursor_line)
        else:
            # Single line selection
            start_line = self._cursor_line
            end_line = self._cursor_line

        start = Offset(0, start_line)
        end = Offset(10000, end_line)
        self._set_selection(Selection(start, end))

    def _scroll_cursor_visible(self) -> None:
        """Scroll to keep cursor line visible."""
        if self.line_count == 0:
            return

        viewport_top = self.scroll_offset.y
        viewport_height = self.scrollable_content_region.height
        viewport_bottom = viewport_top + viewport_height - 1

        if self._cursor_line < viewport_top:
            self.scroll_to(y=self._cursor_line, animate=False)
        elif self._cursor_line > viewport_bottom:
            self.scroll_to(y=self._cursor_line - viewport_height + 1, animate=False)

    def _exit_visual_mode(self) -> None:
        """Exit visual mode and clear selection."""
        was_active = self._visual_mode
        was_line_mode = self._visual_line_mode

        self._visual_mode = False
        self._visual_line_mode = False
        self._visual_anchor_line = None
        self._set_selection(None)

        if was_active:
            self.post_message(self.VisualModeChanged(active=False, line_mode=was_line_mode))

    def _set_selection(self, selection: Selection | None) -> None:
        """Set the selection for this widget.

        Args:
            selection: Selection to set, or None to clear.
        """
        if selection is None:
            self.screen.selections.pop(self, None)
        else:
            self.screen.selections[self] = selection
        self.selection_updated(selection)

    def _strip_markup(self, text: str) -> str:
        """Strip Rich markup tags from text.

        Converts Rich console markup (e.g., [bold red]text[/]) to plain text
        by parsing with Text.from_markup and extracting the plain string.

        Args:
            text: Text potentially containing Rich markup.

        Returns:
            Plain text with all markup tags removed.
        """
        # Parse markup and extract plain text
        parsed = Text.from_markup(text)
        return parsed.plain

    def _copy_with_fallback(self, text: str) -> bool:
        """Copy text to clipboard with fallback mechanisms.

        Primary: OSC 52 escape sequence via Textual's app.copy_to_clipboard()
        Fallback: pyperclip (pbcopy/xclip/xsel)

        Args:
            text: Text to copy to clipboard.

        Returns:
            True if copy succeeded via any mechanism, False otherwise.
        """
        if not text:
            return True  # Empty text is a no-op success

        success = False

        # Primary: OSC 52 via Textual
        try:
            self.app.copy_to_clipboard(text)
            success = True
        except Exception:
            pass

        # Fallback: pyperclip
        try:
            import pyperclip

            pyperclip.copy(text)
            success = True
        except ImportError:
            # pyperclip not installed
            pass
        except Exception:
            # pyperclip failed (no clipboard mechanism available)
            pass

        return success

    # Rendering override for Rich markup support

    def _render_line_strip(self, y: int, rich_style: Style) -> Strip:
        """Render a line with Rich markup support.

        Overrides parent to parse Rich console markup in log lines,
        enabling colored output for log levels, timestamps, etc.

        Args:
            y: Y offset of line.
            rich_style: Base Rich style for line.

        Returns:
            Strip with rendered line content.
        """
        selection = self.text_selection
        # Skip cache to ensure markup is always parsed
        # TODO: Re-enable cache after markup rendering confirmed working

        _line = self._process_line(self._lines[y])

        # Parse Rich markup instead of plain text
        line_text = Text.from_markup(_line)
        line_text.no_wrap = True
        # Note: Don't apply rich_style as base - it would override markup colors

        if selection is not None and (select_span := selection.get_span(y - self._clear_y)) is not None:
            start, end = select_span
            if end == -1:
                end = len(line_text)

            selection_style = self.screen.get_component_rich_style(
                "screen--selection"
            )
            line_text.stylize(selection_style, start, end)

        line = Strip(line_text.render(self.app.console), line_text.cell_len)
        return line
