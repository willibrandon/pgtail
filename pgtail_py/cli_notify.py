"""Notification command handlers.

Provides the `notify` command for configuring desktop notifications
including level-based, pattern-based, and threshold-based alerts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML

from pgtail_py.config import save_config
from pgtail_py.filter import LogLevel
from pgtail_py.notify import NotificationRule

if TYPE_CHECKING:
    from pgtail_py.cli import AppState


def notify_command(state: AppState, args: list[str]) -> None:
    """Handle the notify command.

    Args:
        state: Current application state.
        args: Command arguments.
    """
    if not args:
        # notify (status)
        _show_status(state)
        return

    subcommand = args[0].lower()

    if subcommand == "on":
        _handle_notify_on(state, args[1:])
    elif subcommand == "off":
        _handle_notify_off(state)
    elif subcommand == "test":
        _handle_notify_test(state)
    elif subcommand == "clear":
        _handle_notify_clear(state)
    elif subcommand == "quiet":
        _handle_notify_quiet(state, args[1:])
    else:
        print_formatted_text(
            HTML("<ansiyellow>Usage: notify [on|off|test|clear|quiet]</ansiyellow>")
        )


def _show_status(state: AppState) -> None:
    """Show current notification settings."""
    if not state.notification_manager:
        print("Notifications: not initialized")
        return

    manager = state.notification_manager
    config = manager.config
    notifier = manager.notifier

    # Check availability
    if not notifier.is_available():
        print("Notifications: unavailable")
        print(f"Platform: {notifier.get_platform_info()}")
        _print_install_hint(notifier.get_platform_info())
        return

    # Status line
    status = "enabled" if config.enabled else "disabled"
    print(f"Notifications: {status}")

    if config.enabled:
        # Show level rules
        levels = config.get_level_rules()
        if levels:
            level_names = sorted([level.name for level in levels], key=_level_sort_key)
            print(f"  Levels: {', '.join(level_names)}")

        # Show pattern rules
        patterns = config.get_pattern_rules()
        if patterns:
            pattern_strs: list[str] = []
            for rule in patterns:
                if rule.case_sensitive:
                    pattern_strs.append(f"/{rule.pattern_str}/")
                else:
                    pattern_strs.append(f"/{rule.pattern_str}/i")
            print(f"  Patterns: {', '.join(pattern_strs)}")

        # Show error rate threshold
        error_rate = config.get_error_rate_threshold()
        if error_rate:
            print(f"  Error rate: > {error_rate}/min")

        # Show slow query threshold
        slow_query = config.get_slow_query_threshold()
        if slow_query:
            print(f"  Slow queries: > {slow_query}ms")

        # Show quiet hours
        if config.quiet_hours:
            quiet_str = str(config.quiet_hours)
            if config.quiet_hours.is_active():
                quiet_str += " (active)"
            print(f"  Quiet hours: {quiet_str}")

    # Platform info
    print(f"Platform: {notifier.get_platform_info()}")

    # Hint for disabled state
    if not config.enabled:
        print("Hint: Use 'notify on FATAL PANIC' to enable")


def _print_install_hint(platform_info: str) -> None:
    """Print installation hint based on platform."""
    if "notify-send not found" in platform_info:
        print("Hint: Install libnotify-bin package")
    elif "PowerShell" in platform_info and "not found" in platform_info:
        print("Hint: PowerShell is required for Windows notifications")


def _level_sort_key(name: str) -> int:
    """Sort levels by severity (most severe first)."""
    order = ["PANIC", "FATAL", "ERROR", "WARNING", "NOTICE", "LOG", "INFO", "DEBUG"]
    try:
        return order.index(name)
    except ValueError:
        return 100


def _handle_notify_on(state: AppState, args: list[str]) -> None:
    """Handle 'notify on' command."""
    if not state.notification_manager:
        print("Notification manager not initialized.")
        return

    if not args:
        print("Usage: notify on <levels> | /<pattern>/ | errors > N/min | slow > Nms")
        return

    first_arg = args[0]

    # Check for pattern syntax: /pattern/ or /pattern/i
    if first_arg.startswith("/"):
        _handle_pattern_rule(state, first_arg)
        return

    # Check for error rate syntax: errors > N/min
    if first_arg.lower() == "errors":
        _handle_error_rate_rule(state, args)
        return

    # Check for slow query syntax: slow > Nms
    if first_arg.lower() == "slow":
        _handle_slow_query_rule(state, args)
        return

    # Otherwise, treat as log levels
    _handle_level_rules(state, args)


def _handle_level_rules(state: AppState, args: list[str]) -> None:
    """Parse and add level-based notification rules."""
    if not state.notification_manager:
        return

    valid_levels: set[LogLevel] = set()
    invalid_names: list[str] = []

    for arg in args:
        try:
            level = LogLevel.from_string(arg)
            valid_levels.add(level)
        except ValueError:
            invalid_names.append(arg)

    if invalid_names:
        for name in invalid_names:
            print(f"Unknown log level: {name}")
        print(f"Valid levels: {', '.join(LogLevel.names())}")
        return

    if not valid_levels:
        print("Usage: notify on <levels> | /<pattern>/ | errors > N/min | slow > Nms")
        return

    # Add rule to config
    config = state.notification_manager.config
    config.add_rule(NotificationRule.level_rule(valid_levels))
    config.enabled = True

    # Persist to config file
    _persist_notification_config(state)

    # Confirm
    level_names = sorted([level.name for level in valid_levels], key=_level_sort_key)
    print(f"Notifications enabled for: {', '.join(level_names)}")


def _handle_pattern_rule(state: AppState, pattern_arg: str) -> None:
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
        print(f"Invalid pattern format: {pattern_arg}")
        print("Use: /pattern/ or /pattern/i")
        return

    if not pattern_str:
        print("Pattern cannot be empty")
        return

    # Validate regex
    try:
        rule = NotificationRule.pattern_rule(pattern_str, case_sensitive)
    except Exception as e:
        print(f"Invalid regex pattern: {e}")
        return

    # Add rule
    config = state.notification_manager.config
    config.add_rule(rule)
    config.enabled = True

    # Persist
    _persist_notification_config(state)

    # Confirm
    if case_sensitive:
        print(f"Notifications enabled for pattern: {pattern_str}")
    else:
        print(f"Notifications enabled for pattern: {pattern_str} (case-insensitive)")


def _handle_error_rate_rule(state: AppState, args: list[str]) -> None:
    """Parse and add error rate threshold rule."""
    if not state.notification_manager:
        return

    # Expected format: errors > N/min
    if len(args) < 3 or args[1] != ">":
        print("Usage: notify on errors > N/min")
        return

    rate_str = args[2]
    if not rate_str.endswith("/min"):
        print("Usage: notify on errors > N/min")
        return

    try:
        threshold = int(rate_str[:-4])
        if threshold < 1:
            print("Threshold must be at least 1")
            return
    except ValueError:
        print(f"Invalid threshold: {rate_str[:-4]}")
        return

    # Add rule
    config = state.notification_manager.config
    config.add_rule(NotificationRule.error_rate_rule(threshold))
    config.enabled = True

    # Persist
    _persist_notification_config(state)

    print(f"Notifications enabled: more than {threshold} errors per minute")


def _handle_slow_query_rule(state: AppState, args: list[str]) -> None:
    """Parse and add slow query threshold rule."""
    if not state.notification_manager:
        return

    # Expected format: slow > Nms or slow > Ns
    if len(args) < 3 or args[1] != ">":
        print("Usage: notify on slow > Nms")
        return

    duration_str = args[2].lower()

    try:
        if duration_str.endswith("ms"):
            threshold_ms = int(duration_str[:-2])
        elif duration_str.endswith("s"):
            threshold_ms = int(duration_str[:-1]) * 1000
        else:
            print("Invalid duration: use Nms or Ns format")
            return

        if threshold_ms < 1:
            print("Threshold must be at least 1ms")
            return
    except ValueError:
        print(f"Invalid duration: {args[2]}")
        return

    # Add rule
    config = state.notification_manager.config
    config.add_rule(NotificationRule.slow_query_rule(threshold_ms))
    config.enabled = True

    # Persist
    _persist_notification_config(state)

    print(f"Notifications enabled: queries slower than {threshold_ms}ms")


def _handle_notify_off(state: AppState) -> None:
    """Handle 'notify off' command - disable notifications."""
    if not state.notification_manager:
        print("Notification manager not initialized.")
        return

    state.notification_manager.config.enabled = False

    # Persist
    _persist_notification_config(state)

    print("Notifications disabled")


def _handle_notify_test(state: AppState) -> None:
    """Handle 'notify test' command - send test notification."""
    if not state.notification_manager:
        print("Notification manager not initialized.")
        return

    manager = state.notification_manager
    notifier = manager.notifier

    if not notifier.is_available():
        print("Test notification failed")
        print(f"Platform: {notifier.get_platform_info()}")
        _print_install_hint(notifier.get_platform_info())
        return

    success = manager.send_test()
    if success:
        print("Test notification sent")
        print(f"Platform: {notifier.get_platform_info()}")
    else:
        print("Test notification failed")
        print(f"Platform: {notifier.get_platform_info()}")


def _handle_notify_clear(state: AppState) -> None:
    """Handle 'notify clear' command - remove all rules."""
    if not state.notification_manager:
        print("Notification manager not initialized.")
        return

    state.notification_manager.config.clear_rules()

    # Persist
    _persist_notification_config(state)

    print("Notification rules cleared")


def _handle_notify_quiet(state: AppState, args: list[str]) -> None:
    """Handle 'notify quiet' command - set quiet hours."""
    from pgtail_py.notify import QuietHours

    if not state.notification_manager:
        print("Notification manager not initialized.")
        return

    if not args:
        print("Usage: notify quiet HH:MM-HH:MM | off")
        return

    if args[0].lower() == "off":
        state.notification_manager.config.quiet_hours = None
        _persist_notification_config(state)
        print("Quiet hours disabled")
        return

    # Parse time range
    try:
        quiet_hours = QuietHours.from_string(args[0])
        state.notification_manager.config.quiet_hours = quiet_hours
        _persist_notification_config(state)
        print(f"Notifications silenced {quiet_hours}")
    except ValueError as e:
        print(str(e))


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
