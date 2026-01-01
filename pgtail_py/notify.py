"""Desktop notification rules and management.

Provides notification rule types, rate limiting, quiet hours,
and the NotificationManager for alerting on log events.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum, auto
from typing import TYPE_CHECKING

from pgtail_py.filter import LogLevel

if TYPE_CHECKING:
    from pgtail_py.error_stats import ErrorStats
    from pgtail_py.notifier import Notifier
    from pgtail_py.parser import LogEntry


class NotificationRuleType(Enum):
    """Type of notification trigger."""

    LEVEL = auto()  # Trigger on specific log levels
    PATTERN = auto()  # Trigger on regex pattern match
    ERROR_RATE = auto()  # Trigger when errors/min exceeds threshold
    SLOW_QUERY = auto()  # Trigger when query duration exceeds threshold


@dataclass
class NotificationRule:
    """A single notification condition.

    Multiple rules can be active simultaneously. A rule matches if its
    specific condition is met (level match, pattern match, rate exceeded, etc).
    """

    rule_type: NotificationRuleType

    # LEVEL type fields
    levels: set[LogLevel] = field(default_factory=lambda: set())

    # PATTERN type fields
    pattern: re.Pattern[str] | None = None
    pattern_str: str = ""
    case_sensitive: bool = True

    # ERROR_RATE type fields
    error_threshold: int = 0  # Errors per minute

    # SLOW_QUERY type fields
    slow_threshold_ms: int = 0

    def matches_level(self, level: LogLevel) -> bool:
        """Check if a log level matches this rule.

        Args:
            level: The log level to check.

        Returns:
            True if this is a LEVEL rule and the level matches.
        """
        if self.rule_type != NotificationRuleType.LEVEL:
            return False
        return level in self.levels

    def matches_pattern(self, message: str) -> bool:
        """Check if a message matches this rule's pattern.

        Args:
            message: The log message to check.

        Returns:
            True if this is a PATTERN rule and the message matches.
        """
        if self.rule_type != NotificationRuleType.PATTERN or self.pattern is None:
            return False
        return self.pattern.search(message) is not None

    @classmethod
    def level_rule(cls, levels: set[LogLevel]) -> NotificationRule:
        """Create a level-based notification rule.

        Args:
            levels: Set of levels that trigger notifications.

        Returns:
            NotificationRule configured for level matching.
        """
        return cls(rule_type=NotificationRuleType.LEVEL, levels=levels)

    @classmethod
    def pattern_rule(cls, pattern_str: str, case_sensitive: bool = True) -> NotificationRule:
        """Create a pattern-based notification rule.

        Args:
            pattern_str: Regex pattern string.
            case_sensitive: Whether pattern is case-sensitive.

        Returns:
            NotificationRule configured for pattern matching.

        Raises:
            re.error: If the pattern is invalid.
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        compiled = re.compile(pattern_str, flags)
        return cls(
            rule_type=NotificationRuleType.PATTERN,
            pattern=compiled,
            pattern_str=pattern_str,
            case_sensitive=case_sensitive,
        )

    @classmethod
    def error_rate_rule(cls, threshold: int) -> NotificationRule:
        """Create an error-rate threshold rule.

        Args:
            threshold: Maximum errors per minute before notification.

        Returns:
            NotificationRule configured for error rate monitoring.
        """
        return cls(rule_type=NotificationRuleType.ERROR_RATE, error_threshold=threshold)

    @classmethod
    def slow_query_rule(cls, threshold_ms: int) -> NotificationRule:
        """Create a slow query threshold rule.

        Args:
            threshold_ms: Query duration threshold in milliseconds.

        Returns:
            NotificationRule configured for slow query monitoring.
        """
        return cls(rule_type=NotificationRuleType.SLOW_QUERY, slow_threshold_ms=threshold_ms)


class RateLimiter:
    """Simple time-window rate limiter for notifications.

    Prevents notification spam by ensuring a minimum time gap between
    notifications.
    """

    def __init__(self, window_seconds: float = 5.0) -> None:
        """Initialize the rate limiter.

        Args:
            window_seconds: Minimum seconds between notifications.
        """
        self._window = timedelta(seconds=window_seconds)
        self._last_allowed: datetime | None = None

    def should_allow(self) -> bool:
        """Check if notification should be allowed.

        Does NOT update internal state - call record_sent() after actually
        sending the notification.

        Returns:
            True if enough time has passed since the last notification.
        """
        if self._last_allowed is None:
            return True
        return (datetime.now() - self._last_allowed) >= self._window

    def record_sent(self) -> None:
        """Record that a notification was sent."""
        self._last_allowed = datetime.now()

    def time_until_next(self) -> float:
        """Get seconds until next notification is allowed.

        Returns:
            Seconds until rate limit allows another notification, or 0 if ready.
        """
        if self._last_allowed is None:
            return 0.0
        elapsed = (datetime.now() - self._last_allowed).total_seconds()
        remaining = self._window.total_seconds() - elapsed
        return max(0.0, remaining)

    def reset(self) -> None:
        """Reset the rate limiter state."""
        self._last_allowed = None


class QuietHours:
    """Time range during which notifications are suppressed.

    Handles overnight ranges correctly (e.g., 22:00-08:00 crosses midnight).
    """

    def __init__(self, start: time, end: time) -> None:
        """Initialize quiet hours.

        Args:
            start: Start time (HH:MM).
            end: End time (HH:MM).
        """
        self.start = start
        self.end = end

    def is_active(self, now: datetime | None = None) -> bool:
        """Check if currently within quiet hours.

        Args:
            now: Time to check (defaults to current time).

        Returns:
            True if within quiet hours, False otherwise.
        """
        if now is None:
            now = datetime.now()

        current = now.time()

        # Same-day range (e.g., 09:00-17:00)
        if self.start <= self.end:
            return self.start <= current <= self.end

        # Overnight range (e.g., 22:00-08:00)
        # Active if current time is after start OR before end
        return current >= self.start or current <= self.end

    @classmethod
    def from_string(cls, range_str: str) -> QuietHours:
        """Parse quiet hours from string format.

        Args:
            range_str: Time range like "22:00-08:00".

        Returns:
            QuietHours instance.

        Raises:
            ValueError: If format is invalid.
        """
        if "-" not in range_str:
            raise ValueError("Invalid format. Use: HH:MM-HH:MM")

        parts = range_str.split("-")
        if len(parts) != 2:
            raise ValueError("Invalid format. Use: HH:MM-HH:MM")

        start_str, end_str = parts[0].strip(), parts[1].strip()

        try:
            start_parts = start_str.split(":")
            end_parts = end_str.split(":")

            if len(start_parts) != 2 or len(end_parts) != 2:
                raise ValueError("Invalid format. Use: HH:MM-HH:MM")

            start_hour, start_min = int(start_parts[0]), int(start_parts[1])
            end_hour, end_min = int(end_parts[0]), int(end_parts[1])

            # Validate ranges
            if not (0 <= start_hour <= 23 and 0 <= start_min <= 59):
                raise ValueError(f"Invalid time: {start_str}")
            if not (0 <= end_hour <= 23 and 0 <= end_min <= 59):
                raise ValueError(f"Invalid time: {end_str}")

            return cls(
                start=time(start_hour, start_min),
                end=time(end_hour, end_min),
            )
        except (ValueError, IndexError) as e:
            if "Invalid" in str(e):
                raise
            raise ValueError("Invalid format. Use: HH:MM-HH:MM") from e

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')}"


@dataclass
class NotificationConfig:
    """Collection of active notification rules and settings."""

    enabled: bool = False
    rules: list[NotificationRule] = field(default_factory=lambda: [])
    quiet_hours: QuietHours | None = None

    def add_rule(self, rule: NotificationRule) -> None:
        """Add a notification rule.

        For LEVEL rules, merges levels into existing level rule if one exists.
        For ERROR_RATE and SLOW_QUERY, replaces existing rule of same type.

        Args:
            rule: Rule to add.
        """
        if rule.rule_type == NotificationRuleType.LEVEL:
            # Merge into existing level rule
            for existing in self.rules:
                if existing.rule_type == NotificationRuleType.LEVEL:
                    existing.levels.update(rule.levels)
                    return
            self.rules.append(rule)
        elif rule.rule_type in (NotificationRuleType.ERROR_RATE, NotificationRuleType.SLOW_QUERY):
            # Replace existing rule of same type
            self.rules = [r for r in self.rules if r.rule_type != rule.rule_type]
            self.rules.append(rule)
        else:
            # Pattern rules are additive
            self.rules.append(rule)

    def clear_rules(self) -> None:
        """Remove all notification rules."""
        self.rules.clear()

    def get_level_rules(self) -> set[LogLevel]:
        """Get all levels that trigger notifications.

        Returns:
            Combined set of all levels from LEVEL rules.
        """
        levels: set[LogLevel] = set()
        for rule in self.rules:
            if rule.rule_type == NotificationRuleType.LEVEL:
                levels.update(rule.levels)
        return levels

    def get_pattern_rules(self) -> list[NotificationRule]:
        """Get all pattern rules.

        Returns:
            List of PATTERN rules.
        """
        return [r for r in self.rules if r.rule_type == NotificationRuleType.PATTERN]

    def get_error_rate_threshold(self) -> int | None:
        """Get error rate threshold if configured.

        Returns:
            Threshold or None if not configured.
        """
        for rule in self.rules:
            if rule.rule_type == NotificationRuleType.ERROR_RATE:
                return rule.error_threshold
        return None

    def get_slow_query_threshold(self) -> int | None:
        """Get slow query threshold if configured.

        Returns:
            Threshold in ms or None if not configured.
        """
        for rule in self.rules:
            if rule.rule_type == NotificationRuleType.SLOW_QUERY:
                return rule.slow_threshold_ms
        return None


class NotificationManager:
    """Session-scoped coordinator for notification logic.

    Handles rule matching, rate limiting, quiet hours, and dispatching
    notifications to the platform-specific notifier.
    """

    def __init__(
        self,
        notifier: Notifier,
        config: NotificationConfig | None = None,
        error_stats: ErrorStats | None = None,
    ) -> None:
        """Initialize notification manager.

        Args:
            notifier: Platform-specific notification sender.
            config: Notification configuration.
            error_stats: Reference to error stats for rate checking.
        """
        self._notifier = notifier
        self._config = config or NotificationConfig()
        self._rate_limiter = RateLimiter()
        self._error_stats = error_stats
        self._last_error: str | None = None
        self._last_error_rate_notified: datetime | None = None

    @property
    def config(self) -> NotificationConfig:
        """Get notification configuration."""
        return self._config

    @config.setter
    def config(self, value: NotificationConfig) -> None:
        """Set notification configuration."""
        self._config = value

    @property
    def notifier(self) -> Notifier:
        """Get the notifier instance."""
        return self._notifier

    @property
    def is_available(self) -> bool:
        """Check if notification system is available."""
        return self._notifier.is_available()

    def check(self, entry: LogEntry) -> bool:
        """Check if entry should trigger a notification and send if so.

        Args:
            entry: Log entry to check.

        Returns:
            True if notification was sent, False otherwise.
        """
        # Must be enabled
        if not self._config.enabled:
            return False

        # Check quiet hours
        if self._config.quiet_hours and self._config.quiet_hours.is_active():
            return False

        # Check level rules
        if self._check_level_rules(entry):
            return self._maybe_send_notification(entry, "Level Alert")

        # Check pattern rules
        if self._check_pattern_rules(entry):
            return self._maybe_send_notification(entry, "Pattern Match")

        # Check error rate rules
        if self._check_error_rate_rules():
            return self._maybe_send_error_rate_notification()

        # Check slow query rules
        if self._check_slow_query_rules(entry):
            return self._maybe_send_slow_query_notification(entry)

        return False

    def _check_level_rules(self, entry: LogEntry) -> bool:
        """Check if entry matches any level rule."""
        levels = self._config.get_level_rules()
        return bool(levels) and entry.level in levels

    def _check_pattern_rules(self, entry: LogEntry) -> bool:
        """Check if entry matches any pattern rule."""
        message = entry.message or ""
        return any(rule.matches_pattern(message) for rule in self._config.get_pattern_rules())

    def _check_error_rate_rules(self) -> bool:
        """Check if error rate exceeds threshold."""
        threshold = self._config.get_error_rate_threshold()
        if threshold is None or self._error_stats is None:
            return False

        # Get errors in last minute
        buckets = self._error_stats.get_trend_buckets(minutes=1)
        if not buckets:
            return False

        current_rate = buckets[-1]  # Most recent minute
        if current_rate <= threshold:
            return False

        # Don't notify more than once per minute for rate alerts
        if self._last_error_rate_notified:
            elapsed = (datetime.now() - self._last_error_rate_notified).total_seconds()
            if elapsed < 60:
                return False

        return True

    def _check_slow_query_rules(self, entry: LogEntry) -> bool:
        """Check if entry is a slow query exceeding threshold."""
        threshold = self._config.get_slow_query_threshold()
        if threshold is None:
            return False

        # Extract duration from entry
        from pgtail_py.slow_query import extract_duration

        duration_ms = extract_duration(entry.message or "")
        return duration_ms is not None and duration_ms > threshold

    def _maybe_send_notification(self, entry: LogEntry, category: str) -> bool:
        """Send notification if not rate limited.

        Args:
            entry: Log entry that triggered notification.
            category: Notification category for title.

        Returns:
            True if notification was sent.
        """
        if not self._rate_limiter.should_allow():
            return False

        title = f"pgtail: {category}"
        body = self._format_entry_body(entry)
        subtitle = entry.level.name if entry.level else None

        if self._notifier.send(title, body, subtitle):
            self._rate_limiter.record_sent()
            return True

        return False

    def _maybe_send_error_rate_notification(self) -> bool:
        """Send error rate notification if not rate limited."""
        if not self._rate_limiter.should_allow():
            return False

        threshold = self._config.get_error_rate_threshold()
        if threshold is None or self._error_stats is None:
            return False

        buckets = self._error_stats.get_trend_buckets(minutes=1)
        rate = buckets[-1] if buckets else 0

        title = "pgtail: High Error Rate"
        body = f"Error rate: {rate}/min (threshold: {threshold}/min)"

        if self._notifier.send(title, body):
            self._rate_limiter.record_sent()
            self._last_error_rate_notified = datetime.now()
            return True

        return False

    def _maybe_send_slow_query_notification(self, entry: LogEntry) -> bool:
        """Send slow query notification if not rate limited."""
        if not self._rate_limiter.should_allow():
            return False

        from pgtail_py.slow_query import extract_duration

        duration_ms = extract_duration(entry.message or "")
        threshold = self._config.get_slow_query_threshold()

        title = "pgtail: Slow Query"
        body = f"Duration: {duration_ms}ms"
        if threshold:
            body += f" (threshold: {threshold}ms)"

        # Add truncated query if available
        message = entry.message or ""
        if len(message) > 100:
            message = message[:97] + "..."
        body += f"\n{message}"

        if self._notifier.send(title, body):
            self._rate_limiter.record_sent()
            return True

        return False

    def _format_entry_body(self, entry: LogEntry) -> str:
        """Format log entry for notification body."""
        parts: list[str] = []

        if entry.message:
            msg = entry.message
            if len(msg) > 150:
                msg = msg[:147] + "..."
            parts.append(msg)

        if entry.database_name:
            parts.append(f"Database: {entry.database_name}")

        return "\n".join(parts) if parts else "Log event occurred"

    def send_test(self) -> bool:
        """Send a test notification bypassing rate limiting and quiet hours.

        Returns:
            True if notification was sent successfully.
        """
        title = "pgtail: Test"
        body = "Notification system is working correctly"
        return self._notifier.send(title, body, "pgtail")

    def set_error_stats(self, error_stats: ErrorStats) -> None:
        """Set the error stats reference for rate checking.

        Args:
            error_stats: ErrorStats instance.
        """
        self._error_stats = error_stats
