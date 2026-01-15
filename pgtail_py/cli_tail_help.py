"""Help command handlers for tail mode.

This module provides handlers for help commands (help, help keys, help <cmd>)
executed within the tail mode interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import FormattedText

if TYPE_CHECKING:
    from pgtail_py.tail_buffer import TailBuffer
    from pgtail_py.tail_log import TailLog


# Detailed help for each command (displayed via 'help <cmd>' or '<cmd> help')
COMMAND_HELP: dict[str, dict[str, str | list[str]]] = {
    "level": {
        "usage": "level <level>[+|-] [level2...]",
        "short": "Filter log entries by severity level",
        "description": "Show only entries matching the specified log level(s).",
        "examples": [
            "level error        Show only ERROR entries",
            "level error+       Show ERROR and more severe (FATAL, PANIC)",
            "level warning-     Show WARNING and less severe (NOTICE, LOG, etc.)",
            "level error,warn   Show ERROR and WARNING only",
            "level e+           Same as 'level error+' (abbreviation)",
            "level all          Show all levels (clear level filter)",
        ],
        "aliases": "e=error, w=warning, f=fatal, p=panic, n=notice, i=info, l=log, d=debug",
    },
    "filter": {
        "usage": "filter /pattern/[i]",
        "short": "Filter log entries by regex pattern",
        "description": "Show only entries matching the regular expression pattern.",
        "examples": [
            "filter /error/      Match lines containing 'error' (case-sensitive)",
            "filter /error/i     Match 'error' case-insensitively",
            "filter /user_\\d+/   Match 'user_' followed by digits",
            "filter clear        Remove regex filter",
        ],
    },
    "since": {
        "usage": "since <time>",
        "short": "Show entries from a specific time onward",
        "description": "Filter to show only log entries from the specified time.",
        "examples": [
            "since 5m           Entries from last 5 minutes",
            "since 2h           Entries from last 2 hours",
            "since 14:30        Entries since 2:30 PM today",
            "since 14:30:00     Entries since 2:30:00 PM today",
            "since clear        Remove time filter",
        ],
    },
    "until": {
        "usage": "until <time>",
        "short": "Show entries up to a specific time",
        "description": "Filter to show only log entries up to the specified time.",
        "examples": [
            "until 5m           Entries up to 5 minutes ago",
            "until 14:30        Entries until 2:30 PM today",
            "until clear        Remove time filter",
        ],
    },
    "between": {
        "usage": "between <start> <end>",
        "short": "Show entries in a time range",
        "description": "Filter to show only log entries between start and end times.",
        "examples": [
            "between 14:00 15:00    Entries between 2 PM and 3 PM",
            "between 1h 30m         Entries from 1 hour ago to 30 min ago",
        ],
    },
    "slow": {
        "usage": "slow <milliseconds>",
        "short": "Highlight slow queries above threshold",
        "description": "Set a threshold to highlight queries exceeding the duration.",
        "examples": [
            "slow 100           Highlight queries over 100ms",
            "slow 1000          Highlight queries over 1 second",
            "slow clear         Remove slow query threshold",
        ],
    },
    "clear": {
        "usage": "clear [force]",
        "short": "Reset filters to initial state",
        "description": "Clear all filters and return to the state when tail mode started.",
        "examples": [
            "clear              Reset to initial filters",
            "clear force        Clear ALL filters (ignore initial state)",
        ],
    },
    "errors": {
        "usage": "errors [--trend|--code CODE|--since TIME]",
        "short": "Show error statistics",
        "description": "Display error/warning counts, trends, and SQLSTATE codes.",
        "examples": [
            "errors             Summary with counts by SQLSTATE",
            "errors --trend     Sparkline of error rate (last 60 min)",
            "errors --code 23505  Filter by SQLSTATE code",
            "errors --since 30m   Time-scoped statistics",
            "errors clear       Reset all statistics",
        ],
    },
    "connections": {
        "usage": "connections [--history|--watch|--db=X|--user=X]",
        "short": "Show connection statistics",
        "description": "Display connection/disconnection counts and active sessions.",
        "examples": [
            "connections            Summary with breakdowns",
            "connections --history  Connect/disconnect rate history",
            "connections --watch    Live stream of connection events",
            "connections --db=mydb  Filter by database name",
            "connections clear      Reset statistics",
        ],
    },
    "highlight": {
        "usage": "highlight [list|on|off|enable|disable|add|remove]",
        "short": "Manage semantic highlighters",
        "description": "Enable, disable, or add custom semantic highlighters for log output.",
        "examples": [
            "highlight              Show all highlighters with status",
            "highlight list         Same as above",
            "highlight on           Enable all highlighting globally",
            "highlight off          Disable all highlighting globally",
            "highlight enable timestamp   Enable timestamp highlighting",
            "highlight disable duration   Disable duration highlighting",
            "highlight add req_id 'REQ-\\d+' --style yellow --priority 500  Add custom",
            "highlight remove req_id    Remove custom highlighter",
        ],
    },
    "set": {
        "usage": "set <key> [value]",
        "short": "Configure settings",
        "description": "View or change configuration settings. Changes are persisted immediately.",
        "examples": [
            "set highlighting.duration.slow        Show current value",
            "set highlighting.duration.slow 50     Set slow threshold to 50ms",
            "set highlighting.duration.very_slow 200  Set very_slow to 200ms",
            "set highlighting.duration.critical 1000  Set critical to 1000ms",
        ],
        "see_also": "highlight",
    },
    "pause": {
        "usage": "pause",
        "short": "Pause log updates (freeze display)",
        "description": "Stop auto-scrolling and freeze the display. New entries are buffered.",
        "examples": [
            "pause              Freeze display",
        ],
        "see_also": "follow, p key",
    },
    "follow": {
        "usage": "follow",
        "short": "Resume following new entries",
        "description": "Resume auto-scrolling and show any entries that arrived while paused.",
        "examples": [
            "follow             Resume following",
        ],
        "see_also": "pause, f key",
    },
    "help": {
        "usage": "help [command|keys]",
        "short": "Show help information",
        "description": "Display general help or detailed help for a specific command.",
        "examples": [
            "help               Show all commands",
            "help keys          Show keybinding reference",
            "help level         Show level command help",
            "help filter        Show filter command help",
        ],
    },
}


def show_command_help(
    cmd_name: str,
    buffer: TailBuffer | None,
    log_widget: TailLog | None = None,
) -> bool:
    """Display detailed help for a specific command.

    Args:
        cmd_name: Command name to show help for
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if help was displayed, False if command not found
    """
    cmd_lower = cmd_name.lower()
    if cmd_lower not in COMMAND_HELP:
        return False

    help_info = COMMAND_HELP[cmd_lower]
    usage = help_info.get("usage", cmd_lower)
    short = help_info.get("short", "")
    description = help_info.get("description", "")
    examples = help_info.get("examples", [])
    aliases = help_info.get("aliases", "")
    see_also = help_info.get("see_also", "")

    if log_widget is not None:
        # Textual mode
        log_widget.write_line(f"[bold cyan]{cmd_lower.upper()}[/bold cyan]")
        log_widget.write_line(f"  [dim]{short}[/dim]")
        log_widget.write_line("")
        log_widget.write_line(f"[bold]Usage:[/bold] [green]{usage}[/green]")
        log_widget.write_line("")
        if description:
            log_widget.write_line(f"  {description}")
            log_widget.write_line("")
        if examples:
            log_widget.write_line("[bold]Examples:[/bold]")
            for ex in examples:
                log_widget.write_line(f"  [yellow]{ex}[/yellow]")
            log_widget.write_line("")
        if aliases:
            log_widget.write_line(f"[bold]Aliases:[/bold] [dim]{aliases}[/dim]")
        if see_also:
            log_widget.write_line(f"[bold]See also:[/bold] [dim]{see_also}[/dim]")
    elif buffer is not None:
        # prompt_toolkit mode
        lines: list[tuple[str, str]] = []
        lines.append(("bold fg:ansicyan", f"{cmd_lower.upper()}\n"))
        lines.append(("fg:ansigray", f"  {short}\n\n"))
        lines.append(("bold", "Usage: "))
        lines.append(("fg:ansigreen", f"{usage}\n\n"))
        if description:
            lines.append(("", f"  {description}\n\n"))
        if examples:
            lines.append(("bold", "Examples:\n"))
            for ex in examples:
                lines.append(("fg:ansiyellow", f"  {ex}\n"))
            lines.append(("", "\n"))
        if aliases:
            lines.append(("bold", "Aliases: "))
            lines.append(("fg:ansigray", f"{aliases}\n"))
        if see_also:
            lines.append(("bold", "See also: "))
            lines.append(("fg:ansigray", f"{see_also}\n"))
        buffer.insert_command_output(FormattedText(lines))

    return True


def handle_help_command(
    args: list[str],
    buffer: TailBuffer | None,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'help' command to show available commands and shortcuts.

    Subcommands:
        help keys - Show keybinding reference
        help <cmd> - Show detailed help for a specific command

    Args:
        args: Command arguments (e.g., ['keys', 'level'])
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    # Handle 'help keys' subcommand
    if args and args[0].lower() == "keys":
        return handle_help_keys_command(buffer, log_widget)

    # Handle 'help <command>' - show command-specific help
    if args and args[0].lower() in COMMAND_HELP:
        return show_command_help(args[0], buffer, log_widget)

    # Build styled help text
    lines: list[tuple[str, str]] = []

    # Navigation section
    lines.append(("bold fg:ansicyan", "Navigation\n"))
    nav_keys = [
        ("Up/Down", "Scroll 1 line"),
        ("PgUp/PgDn", "Scroll full page"),
        ("Ctrl+u/d", "Scroll half page"),
        ("Ctrl+b/f", "Scroll full page"),
        ("Home", "Go to top"),
        ("End", "Go to bottom (resume FOLLOW mode)"),
    ]
    for key, desc in nav_keys:
        lines.append(("fg:ansigreen", f"  {key:<12} "))
        lines.append(("", f"{desc}\n"))

    lines.append(("", "\n"))
    lines.append(("bold fg:ansicyan", "Utility Keys\n"))
    utility_keys = [
        ("Ctrl+L", "Redraw screen"),
        ("F12", "Toggle debug overlay"),
        ("Ctrl+C", "Exit tail mode"),
    ]
    for key, desc in utility_keys:
        lines.append(("fg:ansigreen", f"  {key:<12} "))
        lines.append(("", f"{desc}\n"))

    # Commands section
    lines.append(("", "\n"))
    lines.append(("bold fg:ansicyan", "Commands\n"))
    commands = [
        ("help", "Show this help"),
        ("help keys", "Show keybinding reference"),
        ("pause", "Enter PAUSED mode"),
        ("follow", "Resume FOLLOW mode"),
        ("level <lvl>", "Filter by level (e.g., 'level error,warning')"),
        ("filter /re/", "Filter by regex pattern"),
        ("since <time>", "Show entries since time (e.g., '5m', '14:30')"),
        ("until <time>", "Show entries until time"),
        ("between s e", "Show entries in time range"),
        ("slow <ms>", "Set slow query threshold"),
        ("clear", "Clear all filters"),
        ("errors", "Show error statistics"),
        ("connections", "Show connection statistics"),
        ("highlight", "Manage semantic highlighters"),
        ("set <key>", "Configure settings"),
        ("stop/exit/q", "Exit tail mode"),
    ]
    for cmd, desc in commands:
        lines.append(("fg:ansiyellow", f"  {cmd:<12} "))
        lines.append(("", f"{desc}\n"))

    if buffer is not None:
        buffer.insert_command_output(FormattedText(lines))
    elif log_widget is not None:
        # Textual mode: write styled help to log
        log_widget.write_line("[bold cyan]Navigation[/bold cyan]")
        for key, desc in nav_keys:
            log_widget.write_line(f"  [green]{key:<12}[/green] [dim]{desc}[/dim]")
        log_widget.write_line("")
        log_widget.write_line("[bold cyan]Utility Keys[/bold cyan]")
        for key, desc in utility_keys:
            log_widget.write_line(f"  [green]{key:<12}[/green] [dim]{desc}[/dim]")
        log_widget.write_line("")
        log_widget.write_line("[bold cyan]Commands[/bold cyan]")
        for cmd, desc in commands:
            log_widget.write_line(f"  [yellow]{cmd:<12}[/yellow] [dim]{desc}[/dim]")
    return True


def handle_help_keys_command(buffer: TailBuffer | None, log_widget: TailLog | None = None) -> bool:
    """Handle 'help keys' command to show keybinding reference.

    Args:
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    from pgtail_py.tail_help import KEYBINDINGS, format_keybindings_text

    if buffer is not None:
        # Format for prompt_toolkit
        keybindings_text = format_keybindings_text()
        lines: list[tuple[str, str]] = []
        for line in keybindings_text.split("\n"):
            lines.append(("", f"{line}\n"))
        buffer.insert_command_output(FormattedText(lines))
    elif log_widget is not None:
        # Textual mode: write styled keybindings to log
        for category, bindings in KEYBINDINGS.items():
            log_widget.write_line(f"[bold cyan]{category}[/bold cyan]")
            for key, desc in bindings:
                log_widget.write_line(f"  [green]{key:<16}[/green] [dim]{desc}[/dim]")
    return True
