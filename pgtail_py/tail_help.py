"""Help overlay for pgtail tail mode.

This module provides the TailHelp screen that displays keybinding help
when the user presses '?' in tail mode. The help overlay shows all
available keyboard shortcuts organized by category.

Classes:
    HelpScreen: Modal screen displaying keybinding help.
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

# Keybinding definitions organized by category
KEYBINDINGS: dict[str, list[tuple[str, str]]] = {
    "Navigation": [
        ("j / ↓", "Scroll down one line"),
        ("k / ↑", "Scroll up one line"),
        ("g", "Go to top"),
        ("G", "Go to bottom (resume FOLLOW)"),
        ("Ctrl+d", "Half page down"),
        ("Ctrl+u", "Half page up"),
        ("Ctrl+f / PgDn", "Full page down"),
        ("Ctrl+b / PgUp", "Full page up"),
        ("p", "Pause (freeze display)"),
        ("f", "Resume FOLLOW mode"),
    ],
    "Selection": [
        ("v", "Visual mode (character)"),
        ("V", "Visual line mode"),
        ("h / l", "Move cursor left/right"),
        ("0 / $", "Line start/end"),
        ("y", "Yank (copy) selection"),
        ("Escape", "Clear selection"),
        ("Ctrl+a", "Select all"),
        ("Ctrl+c", "Copy selection"),
    ],
    "Commands": [
        ("/ or Tab", "Focus command input"),
        ("level <lvl>", "Filter by level"),
        ("filter /re/", "Filter by regex"),
        ("since <time>", "Filter by time"),
        ("pause", "Pause log updates"),
        ("follow", "Resume updates"),
        ("clear", "Reset filters"),
        ("errors", "Show error stats"),
        ("connections", "Show connection stats"),
        ("help", "Show command help"),
        ("q / stop", "Exit tail mode"),
    ],
    "Help": [
        ("?", "Show this help"),
        ("Escape / q", "Close help"),
    ],
}


def format_keybindings_text() -> str:
    """Format keybindings as plain text for CLI output.

    Returns:
        Plain text representation of all keybindings.
    """
    lines: list[str] = []
    for category, bindings in KEYBINDINGS.items():
        lines.append(f"\n{category}:")
        for key, desc in bindings:
            lines.append(f"  {key:<16} {desc}")
    return "\n".join(lines)


class HelpScreen(ModalScreen[None]):
    """Modal screen displaying keybinding help.

    Shows all available keyboard shortcuts organized by category.
    Dismiss with Escape, q, or ?.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("q", "dismiss", "Close", show=False),
        Binding("question_mark", "dismiss", "Close", show=False),
    ]

    CSS: ClassVar[str] = """
    HelpScreen {
        align: center middle;
    }

    #help-container {
        width: 70;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #help-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding-bottom: 1;
    }

    .help-category {
        color: $secondary;
        text-style: bold;
        padding-top: 1;
    }

    .help-binding {
        color: $text;
    }

    .help-key {
        color: $success;
        width: 18;
    }

    .help-desc {
        color: $text-muted;
    }

    #help-footer {
        text-align: center;
        color: $text-muted;
        padding-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the help overlay layout.

        Yields:
            Widgets in layout order.
        """
        with Container(id="help-container"):
            yield Static("pgtail Keybindings", id="help-title")

            with Vertical():
                for category, bindings in KEYBINDINGS.items():
                    yield Static(category, classes="help-category")
                    for key, desc in bindings:
                        yield Static(
                            f"[green]{key:<16}[/green] [dim]{desc}[/dim]",
                            classes="help-binding",
                        )

            yield Static("Press Escape, q, or ? to close", id="help-footer")

    async def action_dismiss(self, result: None = None) -> None:
        """Dismiss the help screen."""
        self.dismiss(result)
