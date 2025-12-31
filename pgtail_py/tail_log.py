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

from textual.binding import Binding, BindingType
from textual.message import Message
from textual.selection import Selection
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
        """Scroll down one line."""
        self.scroll_down()
        if self._visual_mode:
            self._update_selection()

    def action_scroll_up(self) -> None:
        """Scroll up one line."""
        self.scroll_up()
        if self._visual_mode:
            self._update_selection()

    def action_scroll_home(self) -> None:
        """Scroll to top of log."""
        self.scroll_home()
        if self._visual_mode:
            self._update_selection()

    def action_scroll_end(self) -> None:
        """Scroll to bottom of log (resumes FOLLOW mode)."""
        self.scroll_end()
        if self._visual_mode:
            self._update_selection()

    def action_half_page_down(self) -> None:
        """Scroll down half a page."""
        height = self.scrollable_content_region.height
        self.scroll_relative(y=height // 2)
        if self._visual_mode:
            self._update_selection()

    def action_half_page_up(self) -> None:
        """Scroll up half a page."""
        height = self.scrollable_content_region.height
        self.scroll_relative(y=-(height // 2))
        if self._visual_mode:
            self._update_selection()

    def action_page_down(self) -> None:
        """Scroll down one full page."""
        self.scroll_page_down()
        if self._visual_mode:
            self._update_selection()

    def action_page_up(self) -> None:
        """Scroll up one full page."""
        self.scroll_page_up()
        if self._visual_mode:
            self._update_selection()

    # Visual mode actions

    def action_visual_mode(self) -> None:
        """Enter visual mode for character-wise selection."""
        if self.line_count == 0:
            return  # No-op on empty buffer
        self._visual_mode = True
        self._visual_line_mode = False
        self._visual_anchor_line = self._get_current_line()
        self._update_selection()
        self.post_message(self.VisualModeChanged(active=True, line_mode=False))

    def action_visual_line_mode(self) -> None:
        """Enter visual line mode for full-line selection."""
        if self.line_count == 0:
            return  # No-op on empty buffer
        self._visual_mode = True
        self._visual_line_mode = True
        self._visual_anchor_line = self._get_current_line()
        self._update_selection()
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

        # Copy to clipboard
        success = self._copy_with_fallback(selected_text)
        if success:
            self.post_message(self.SelectionCopied(selected_text, len(selected_text)))

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

        success = self._copy_with_fallback(selected_text)
        if success:
            self.post_message(self.SelectionCopied(selected_text, len(selected_text)))

    # Helper methods

    def _get_current_line(self) -> int:
        """Get the current line at viewport center.

        Returns:
            Line index at viewport center (clamped to valid range).
        """
        viewport_top = self.scroll_offset.y
        viewport_height = self.scrollable_content_region.height
        center_line = viewport_top + (viewport_height // 2)
        # Clamp to valid range
        return max(0, min(center_line, self.line_count - 1))

    def _update_selection(self) -> None:
        """Update selection based on visual mode anchor and current line."""
        if not self._visual_mode or self._visual_anchor_line is None:
            return

        current = self._get_current_line()
        start_line = min(self._visual_anchor_line, current)
        end_line = max(self._visual_anchor_line, current)

        # Clamp to valid bounds
        start_line = max(0, min(start_line, self.line_count - 1))
        end_line = max(0, min(end_line, self.line_count - 1))

        from textual.geometry import Offset
        from textual.selection import Selection

        if self._visual_line_mode:
            # Full line selection: start of first line to end of last line
            start = Offset(0, start_line)
            # Use a large x value to indicate end of line
            end = Offset(10000, end_line)
        else:
            # Character selection (currently same as line mode for simplicity)
            start = Offset(0, start_line)
            end = Offset(10000, end_line)

        self._set_selection(Selection(start, end))

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
