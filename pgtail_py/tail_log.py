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

import sys
from typing import ClassVar

from rich.errors import MarkupError
from rich.style import Style
from rich.text import Text
from textual import events
from textual.binding import Binding, BindingType
from textual.geometry import Offset
from textual.message import Message
from textual.selection import Selection
from textual.strip import Strip
from textual.widgets import Log

# Sentinel value for "end of line" in column positions.
# Using sys.maxsize instead of a magic number ensures correct behavior
# even for extremely long lines.
END_OF_LINE = sys.maxsize


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
        Binding("h", "cursor_left", "Left", show=False),
        Binding("l", "cursor_right", "Right", show=False),
        Binding("0", "cursor_line_start", "Line start", show=False),
        Binding("$", "cursor_line_end", "Line end", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G", "scroll_end", "Bottom", show=False),
        Binding("f", "follow", "Follow", show=False),
        Binding("p", "pause", "Pause", show=False),
        Binding("ctrl+d", "half_page_down", "Half page down", show=False),
        Binding("ctrl+u", "half_page_up", "Half page up", show=False),
        Binding("ctrl+f", "page_down", "Page down", show=False),
        Binding("pagedown", "page_down", "Page down", show=False),
        Binding("ctrl+b", "page_up", "Page up", show=False),
        Binding("pageup", "page_up", "Page up", show=False),
        # Visual mode
        Binding("v", "visual_mode", "Visual mode", show=False),
        Binding("V", "visual_line_mode", "Visual line mode", show=False),
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

    class PauseRequested(Message):
        """Emitted when user requests pause mode (p key)."""

        pass

    class FollowRequested(Message):
        """Emitted when user requests follow mode (f key)."""

        pass

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
        self._visual_anchor_col: int = 0
        self._cursor_line: int = 0
        self._cursor_col: int = 0
        # Track mouse down position to detect drag vs click
        self._mouse_down_pos: tuple[int, int] | None = None

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
        # Exit visual mode
        self._visual_mode = False
        self._visual_line_mode = False
        self._visual_anchor_line = None
        self._set_selection(None)
        # Navigate to end if we have content
        if self.line_count > 0:
            self._cursor_line = self.line_count - 1
            self.scroll_end()
        # Tell app to resume following (always, even if empty)
        self.post_message(self.FollowRequested())

    def action_pause(self) -> None:
        """Request pause mode (stop auto-scroll, freeze display)."""
        self.post_message(self.PauseRequested())

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

    # Column navigation actions (for character-wise visual mode)

    def _get_line_length(self, line_idx: int) -> int:
        """Get the plain text length of a line (without markup)."""
        if line_idx < 0 or line_idx >= len(self._lines):
            return 0
        line = self._lines[line_idx]
        plain_line = self._strip_markup(line)
        return len(plain_line)

    def action_cursor_left(self) -> None:
        """Move cursor left one character (h key), wrapping to previous line."""
        if self.line_count == 0:
            return
        wrapped = False
        if self._cursor_col > 0:
            self._cursor_col -= 1
        elif self._cursor_line > 0:
            # Wrap to end of previous line
            self._cursor_line -= 1
            self._cursor_col = self._get_line_length(self._cursor_line)
            wrapped = True
        if self._visual_mode and not self._visual_line_mode:
            self._select_cursor_line()
        if wrapped:
            self._scroll_cursor_visible()

    def action_cursor_right(self) -> None:
        """Move cursor right one character (l key), wrapping to next line."""
        if self.line_count == 0:
            return
        wrapped = False
        line_len = self._get_line_length(self._cursor_line)
        if self._cursor_col < line_len:
            self._cursor_col += 1
        elif self._cursor_line < self.line_count - 1:
            # Wrap to start of next line
            self._cursor_line += 1
            self._cursor_col = 0
            wrapped = True
        if self._visual_mode and not self._visual_line_mode:
            self._select_cursor_line()
        if wrapped:
            self._scroll_cursor_visible()

    def action_cursor_line_start(self) -> None:
        """Move cursor to start of line (0 key)."""
        self._cursor_col = 0
        if self._visual_mode and not self._visual_line_mode:
            self._select_cursor_line()

    def action_cursor_line_end(self) -> None:
        """Move cursor to end of line ($ key)."""
        if self.line_count == 0:
            return
        self._cursor_col = self._get_line_length(self._cursor_line)
        if self._visual_mode and not self._visual_line_mode:
            self._select_cursor_line()

    # Visual mode actions

    def action_visual_mode(self) -> None:
        """Enter visual mode for character-wise selection."""
        if self.line_count == 0:
            return
        self._visual_mode = True
        self._visual_line_mode = False
        self._visual_anchor_line = self._cursor_line
        self._visual_anchor_col = self._cursor_col
        self._select_cursor_line()
        self.post_message(self.VisualModeChanged(active=True, line_mode=False))

    def action_visual_line_mode(self) -> None:
        """Enter visual line mode for full-line selection."""
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

        # Get selected text directly from _lines to avoid coordinate issues
        selected_text = self._get_selected_text(selection)
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

        # Get selected text directly from _lines to avoid coordinate issues
        selected_text = self._get_selected_text(selection)
        if not selected_text:
            return

        # Strip Rich markup before copying
        plain_text = self._strip_markup(selected_text)

        success = self._copy_with_fallback(plain_text)
        if success:
            self.post_message(self.SelectionCopied(plain_text, len(plain_text)))

    # Event handlers

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Track mouse down position to detect drag vs click.

        Args:
            event: MouseDown event with position information.
        """
        self._mouse_down_pos = (event.x, event.y)

    def on_click(self, event: events.Click) -> None:
        """Handle mouse click to select line (but not after drag).

        For simple clicks, select the clicked line. For clicks that follow
        a drag (multi-line selection), don't override the selection.

        Args:
            event: Click event with position information.
        """
        if self.line_count == 0:
            return

        # Check if this was a drag (mouse moved from down position)
        was_drag = False
        if self._mouse_down_pos is not None:
            dx = abs(event.x - self._mouse_down_pos[0])
            dy = abs(event.y - self._mouse_down_pos[1])
            was_drag = dx > 1 or dy > 0  # Allow 1 char horizontal tolerance
        self._mouse_down_pos = None

        # Update cursor position for keyboard navigation
        clicked_line = self.scroll_offset.y + event.y
        self._cursor_line = max(0, min(clicked_line, self.line_count - 1))
        self._cursor_col = 0  # Reset to start of line on click

        # Exit visual mode on click
        if self._visual_mode:
            self._visual_mode = False
            self._visual_line_mode = False
            self._visual_anchor_line = None
            self.post_message(self.VisualModeChanged(active=False, line_mode=False))

        # Only select line on simple click (not after drag)
        if not was_drag:
            self._select_cursor_line()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        """Handle mouse release after drag selection.

        Auto-copies selection to clipboard when mouse is released after
        a drag selection (FR-002 requirement).

        Args:
            event: MouseUp event with position information.
        """
        # Check if there's a selection to copy
        selection = self.text_selection
        if selection is None:
            return

        # Get selected text directly from _lines to avoid coordinate issues
        selected_text = self._get_selected_text(selection)
        if not selected_text:
            return

        # Strip Rich markup before copying
        plain_text = self._strip_markup(selected_text)

        # Copy to clipboard (silent - no message for mouse-up auto-copy)
        self._copy_with_fallback(plain_text)

    # Helper methods

    def _select_cursor_line(self) -> None:
        """Select based on cursor position and visual mode state."""
        if self.line_count == 0:
            return

        if self._visual_mode and self._visual_anchor_line is not None:
            if self._visual_line_mode:
                # Visual LINE mode (V): always select full lines
                start_line = min(self._visual_anchor_line, self._cursor_line)
                end_line = max(self._visual_anchor_line, self._cursor_line)
                start = Offset(0, start_line)
                end = Offset(END_OF_LINE, end_line)
            else:
                # Visual CHAR mode (v): select from anchor position to cursor position
                # End is +1 to include character at cursor (vim behavior)
                if self._visual_anchor_line < self._cursor_line:
                    start = Offset(self._visual_anchor_col, self._visual_anchor_line)
                    end = Offset(self._cursor_col + 1, self._cursor_line)
                elif self._visual_anchor_line > self._cursor_line:
                    start = Offset(self._cursor_col, self._cursor_line)
                    end = Offset(self._visual_anchor_col + 1, self._visual_anchor_line)
                else:
                    # Same line - order by column
                    start_col = min(self._visual_anchor_col, self._cursor_col)
                    end_col = max(self._visual_anchor_col, self._cursor_col)
                    start = Offset(start_col, self._cursor_line)
                    end = Offset(end_col + 1, self._cursor_line)
        else:
            # Single line selection (no visual mode)
            start = Offset(0, self._cursor_line)
            end = Offset(END_OF_LINE, self._cursor_line)

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

    def _get_selected_text(self, selection: Selection) -> str:
        """Get selected text directly from _lines.

        Handles both character-wise selection (respects column positions)
        and line-wise selection (full lines).

        Args:
            selection: Selection with start/end coordinates.

        Returns:
            Selected text as a string, with lines joined by newlines.
        """
        if not self._lines:
            return ""

        # Get coordinates from selection
        start_line = selection.start.y if selection.start else 0
        start_col = selection.start.x if selection.start else 0
        end_line = selection.end.y if selection.end else len(self._lines) - 1
        end_col = selection.end.x if selection.end else END_OF_LINE

        # Clamp lines to valid range
        start_line = max(0, min(start_line, len(self._lines) - 1))
        end_line = max(0, min(end_line, len(self._lines) - 1))

        # Ensure start <= end (swap if needed)
        if start_line > end_line or (start_line == end_line and start_col > end_col):
            start_line, end_line = end_line, start_line
            start_col, end_col = end_col, start_col

        # Get plain text lines using Rich's parser for accurate column slicing
        # (matches how lines are rendered)
        plain_lines = []
        for i in range(start_line, end_line + 1):
            try:
                rich_text = Text.from_markup(self._lines[i])
                plain_lines.append(rich_text.plain)
            except MarkupError:
                # Fall back to raw text if markup is malformed
                plain_lines.append(self._lines[i])

        if not plain_lines:
            return ""

        if start_line == end_line:
            # Single line: slice from start_col to end_col
            line = plain_lines[0]
            return line[start_col:end_col]
        else:
            # Multi-line: first line from start_col, middle lines full, last line to end_col
            result = []
            # First line: from start_col to end
            result.append(plain_lines[0][start_col:])
            # Middle lines: full lines
            for line in plain_lines[1:-1]:
                result.append(line)
            # Last line: from start to end_col
            result.append(plain_lines[-1][:end_col])
            return "\n".join(result)

    def _strip_markup(self, text: str) -> str:
        """Strip Rich markup tags from text using regex.

        Uses regex to remove Rich console markup tags (e.g., [bold red], [/])
        since partial selections can start mid-tag and break Rich's parser.

        Args:
            text: Text potentially containing Rich markup.

        Returns:
            Plain text with all markup tags removed.
        """
        import re

        # Use regex to strip markup - handles partial/broken markup from selections
        # Remove markup tags like [bold], [/bold], [dim], [/], [bold red], etc.
        result = re.sub(r"\[/?[^\]]*\]", "", text)
        # Handle escaped brackets \\[ -> [
        result = result.replace("\\[", "[")
        return result

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

        # Apply ONLY background from rich_style to entire line for consistent bg
        # (Don't apply foreground - it would override markup colors)
        if rich_style.bgcolor:
            bg_only = Style(bgcolor=rich_style.bgcolor)
            line_text.stylize(bg_only, 0, len(line_text))

        if (
            selection is not None
            and (select_span := selection.get_span(y - self._clear_y)) is not None
        ):
            start, end = select_span
            if end == -1:
                end = len(line_text)

            selection_style = self.screen.get_component_rich_style("screen--selection")
            line_text.stylize(selection_style, start, end)

        line = Strip(line_text.render(self.app.console), line_text.cell_len)
        return line
