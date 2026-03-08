"""Notification command handlers.

Provides the `notify` command for configuring desktop notifications
including level-based, pattern-based, and threshold-based alerts.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML

from pgtail_py.config import save_config
from pgtail_py.filter import LogLevel, parse_levels
from pgtail_py.notify import NotificationRule

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.tail_log import TailLog

# Type alias for the output callback used throughout this module.
_WriteFn = Callable[[str], None]


def _make_write(log_widget: TailLog | None) -> _WriteFn:
    """Return an output function appropriate for the current context."""
    if log_widget is not None:
        return log_widget.write_line
    return print


def notify_command(
    state: AppState,
    args: list[str],
    log_widget: TailLog | None = None,
) -> None:
    """Handle the notify command.

    Args:
        state: Current application state.
        args: Command arguments.
        log_widget: Optional Textual log widget for tail-mode output.
    """
    out = _make_write(log_widget)

    if not args:
        # notify (status)
        _show_status(state, out)
        return

    subcommand = args[0].lower()

    if subcommand == "on":
        _handle_notify_on(state, args[1:], out)
    elif subcommand == "off":
        _handle_notify_off(state, out)
    elif subcommand == "test":
        _handle_notify_test(state, args[1:], out)
    elif subcommand == "clear":
        _handle_notify_clear(state, out)
    elif subcommand == "quiet":
        _handle_notify_quiet(state, args[1:], out)
    else:
        if log_widget is not None:
            out("[yellow]Usage: notify [on|off|test|clear|quiet][/yellow]")
        else:
            print_formatted_text(
                HTML("<ansiyellow>Usage: notify [on|off|test|clear|quiet]</ansiyellow>")
            )


def _show_status(state: AppState, out: _WriteFn) -> None:
    """Show current notification settings."""
    if not state.notification_manager:
        out("Notifications: not initialized")
        return

    manager = state.notification_manager
    config = manager.config
    notifier = manager.notifier

    # Check availability
    if not notifier.is_available():
        out("Notifications: unavailable")
        out(f"Platform: {notifier.get_platform_info()}")
        _print_install_hint(notifier.get_platform_info(), out)
        return

    # Status line
    status = "enabled" if config.enabled else "disabled"
    out(f"Notifications: {status}")

    if config.enabled:
        # Show level rules
        levels = config.get_level_rules()
        if levels:
            level_names = sorted([level.name for level in levels], key=_level_sort_key)
            out(f"  Levels: {', '.join(level_names)}")

        # Show pattern rules
        patterns = config.get_pattern_rules()
        if patterns:
            pattern_strs: list[str] = []
            for rule in patterns:
                if rule.case_sensitive:
                    pattern_strs.append(f"/{rule.pattern_str}/")
                else:
                    pattern_strs.append(f"/{rule.pattern_str}/i")
            out(f"  Patterns: {', '.join(pattern_strs)}")

        # Show error rate threshold
        error_rate = config.get_error_rate_threshold()
        if error_rate:
            out(f"  Error rate: > {error_rate}/min")

        # Show slow query threshold
        slow_query = config.get_slow_query_threshold()
        if slow_query:
            out(f"  Slow queries: > {slow_query}ms")

        # Show quiet hours
        if config.quiet_hours:
            quiet_str = str(config.quiet_hours)
            if config.quiet_hours.is_active():
                quiet_str += " (active)"
            out(f"  Quiet hours: {quiet_str}")

    # Platform info
    out(f"Platform: {notifier.get_platform_info()}")

    # Hint for disabled state
    if not config.enabled:
        out("Hint: Use 'notify on FATAL PANIC' to enable")


def _print_install_hint(platform_info: str, out: _WriteFn) -> None:
    """Print installation hint based on platform."""
    if "notify-send not found" in platform_info:
        out("Hint: Install libnotify-bin package")
    elif "PowerShell" in platform_info and "not found" in platform_info:
        out("Hint: PowerShell is required for Windows notifications")


def _level_sort_key(name: str) -> int:
    """Sort levels by severity (most severe first)."""
    order = ["PANIC", "FATAL", "ERROR", "WARNING", "NOTICE", "LOG", "INFO", "DEBUG"]
    try:
        return order.index(name)
    except ValueError:
        return 100


def _handle_notify_on(state: AppState, args: list[str], out: _WriteFn) -> None:
    """Handle 'notify on' command."""
    if not state.notification_manager:
        out("Notification manager not initialized.")
        return

    if not args:
        out("Usage: notify on <levels> | /<pattern>/ | errors > N/min | slow > Nms")
        return

    first_arg = args[0]

    # Check for pattern syntax: /pattern/ or /pattern/i
    if first_arg.startswith("/"):
        _handle_pattern_rule(state, first_arg, out)
        return

    # Check for error rate syntax: errors > N/min
    if first_arg.lower() == "errors":
        _handle_error_rate_rule(state, args, out)
        return

    # Check for slow query syntax: slow > Nms
    if first_arg.lower() == "slow":
        _handle_slow_query_rule(state, args, out)
        return

    # Otherwise, treat as log levels
    _handle_level_rules(state, args, out)


def _handle_level_rules(state: AppState, args: list[str], out: _WriteFn) -> None:
    """Parse and add level-based notification rules."""
    if not state.notification_manager:
        return

    valid_levels, invalid_names = parse_levels(args)

    if invalid_names:
        for name in invalid_names:
            out(f"Unknown log level: {name}")
        out(f"Valid levels: {', '.join(LogLevel.names())}")
        return

    if not valid_levels:
        out("Usage: notify on <levels> | /<pattern>/ | errors > N/min | slow > Nms")
        return

    # Add rule to config
    config = state.notification_manager.config
    config.add_rule(NotificationRule.level_rule(valid_levels))
    config.enabled = True

    # Persist to config file
    _persist_notification_config(state)

    # Confirm
    level_names = sorted([level.name for level in valid_levels], key=_level_sort_key)
    out(f"Notifications enabled for: {', '.join(level_names)}")


def _handle_pattern_rule(state: AppState, pattern_arg: str, out: _WriteFn) -> None:
    """Parse and add pattern-based notification rule."""
    if not state.notification_manager:
        return

    # Parse /pattern/ or /pattern/i
    case_sensitive = True
    pattern_str = pattern_arg

    if pattern_str.endswith("/i"):
        case_sensitive = False
        pattern_str = pattern_str[1:-2]
    elif pattern_str.endswith("/"):
        pattern_str = pattern_str[1:-1]
    else:
        out(f"Invalid pattern format: {pattern_arg}")
        out("Use: /pattern/ or /pattern/i")
        return

    if not pattern_str:
        out("Pattern cannot be empty")
        return

    # Validate regex
    try:
        rule = NotificationRule.pattern_rule(pattern_str, case_sensitive)
    except Exception as e:
        out(f"Invalid regex pattern: {e}")
        return

    # Add rule
    config = state.notification_manager.config
    config.add_rule(rule)
    config.enabled = True

    # Persist
    _persist_notification_config(state)

    # Confirm
    if case_sensitive:
        out(f"Notifications enabled for pattern: {pattern_str}")
    else:
        out(f"Notifications enabled for pattern: {pattern_str} (case-insensitive)")


def _handle_error_rate_rule(state: AppState, args: list[str], out: _WriteFn) -> None:
    """Parse and add error rate threshold rule."""
    if not state.notification_manager:
        return

    # Expected format: errors > N/min
    if len(args) < 3 or args[1] != ">":
        out("Usage: notify on errors > N/min")
        return

    rate_str = args[2]
    if not rate_str.endswith("/min"):
        out("Usage: notify on errors > N/min")
        return

    try:
        threshold = int(rate_str[:-4])
        if threshold < 1:
            out("Threshold must be at least 1")
            return
    except ValueError:
        out(f"Invalid threshold: {rate_str[:-4]}")
        return

    # Add rule
    config = state.notification_manager.config
    config.add_rule(NotificationRule.error_rate_rule(threshold))
    config.enabled = True

    # Persist
    _persist_notification_config(state)

    out(f"Notifications enabled: more than {threshold} errors per minute")


def _handle_slow_query_rule(state: AppState, args: list[str], out: _WriteFn) -> None:
    """Parse and add slow query threshold rule."""
    if not state.notification_manager:
        return

    # Expected format: slow > Nms or slow > Ns
    if len(args) < 3 or args[1] != ">":
        out("Usage: notify on slow > Nms")
        return

    duration_str = args[2].lower()

    try:
        if duration_str.endswith("ms"):
            threshold_ms = int(duration_str[:-2])
        elif duration_str.endswith("s"):
            threshold_ms = int(duration_str[:-1]) * 1000
        else:
            out("Invalid duration: use Nms or Ns format")
            return

        if threshold_ms < 1:
            out("Threshold must be at least 1ms")
            return
    except ValueError:
        out(f"Invalid duration: {args[2]}")
        return

    # Add rule
    config = state.notification_manager.config
    config.add_rule(NotificationRule.slow_query_rule(threshold_ms))
    config.enabled = True

    # Persist
    _persist_notification_config(state)

    out(f"Notifications enabled: queries slower than {threshold_ms}ms")


def _handle_notify_off(state: AppState, out: _WriteFn) -> None:
    """Handle 'notify off' command - disable notifications."""
    if not state.notification_manager:
        out("Notification manager not initialized.")
        return

    state.notification_manager.config.enabled = False

    # Persist
    _persist_notification_config(state)

    out("Notifications disabled")


_VALID_SEVERITIES = ("info", "warning", "error", "critical")


def _handle_notify_test(state: AppState, args: list[str], out: _WriteFn) -> None:
    """Handle 'notify test' command - send test notification.

    Args:
        state: Current application state.
        args: Optional severity argument (info, warning, error, critical).
        out: Output function.
    """
    if not state.notification_manager:
        out("Notification manager not initialized.")
        return

    manager = state.notification_manager
    notifier = manager.notifier

    if not notifier.is_available():
        out("Test notification failed")
        out(f"Platform: {notifier.get_platform_info()}")
        _print_install_hint(notifier.get_platform_info(), out)
        return

    severity = "info"
    if args:
        severity = args[0].lower()
        if severity not in _VALID_SEVERITIES:
            out(f"Unknown severity: {args[0]}")
            out(f"Valid severities: {', '.join(_VALID_SEVERITIES)}")
            return

    success = manager.send_test(severity=severity)
    if success:
        label = severity.upper()
        out(f"Test notification sent ({label})")
        out(f"Platform: {notifier.get_platform_info()}")
    else:
        out("Test notification failed")
        out(f"Platform: {notifier.get_platform_info()}")


def _handle_notify_clear(state: AppState, out: _WriteFn) -> None:
    """Handle 'notify clear' command - remove all rules."""
    if not state.notification_manager:
        out("Notification manager not initialized.")
        return

    state.notification_manager.config.clear_rules()

    # Persist
    _persist_notification_config(state)

    out("Notification rules cleared")


def _handle_notify_quiet(state: AppState, args: list[str], out: _WriteFn) -> None:
    """Handle 'notify quiet' command - set quiet hours."""
    from pgtail_py.notify import QuietHours

    if not state.notification_manager:
        out("Notification manager not initialized.")
        return

    if not args:
        out("Usage: notify quiet HH:MM-HH:MM | off")
        return

    if args[0].lower() == "off":
        state.notification_manager.config.quiet_hours = None
        _persist_notification_config(state)
        out("Quiet hours disabled")
        return

    # Parse time range
    try:
        quiet_hours = QuietHours.from_string(args[0])
        state.notification_manager.config.quiet_hours = quiet_hours
        _persist_notification_config(state)
        out(f"Notifications silenced {quiet_hours}")
    except ValueError as e:
        out(str(e))


def _persist_notification_config(state: AppState) -> None:
    """Persist notification configuration to config file."""
    if not state.notification_manager:
        return

    config = state.notification_manager.config

    # Save enabled state
    save_config("notifications.enabled", config.enabled)

    # Save level rules
    levels = config.get_level_rules()
    level_names = [level.name for level in levels] if levels else []
    save_config("notifications.levels", level_names)

    # Save pattern rules
    patterns = config.get_pattern_rules()
    pattern_strs: list[str] = []
    for rule in patterns:
        if rule.case_sensitive:
            pattern_strs.append(f"/{rule.pattern_str}/")
        else:
            pattern_strs.append(f"/{rule.pattern_str}/i")
    save_config("notifications.patterns", pattern_strs)

    # Save error rate threshold
    error_rate = config.get_error_rate_threshold()
    if error_rate:
        save_config("notifications.error_rate", error_rate)

    # Save slow query threshold
    slow_query = config.get_slow_query_threshold()
    if slow_query:
        save_config("notifications.slow_query_ms", slow_query)

    # Save quiet hours
    if config.quiet_hours:
        save_config("notifications.quiet_hours", str(config.quiet_hours))
