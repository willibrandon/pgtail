"""Slow query detection and highlighting for PostgreSQL logs.

Provides duration parsing, configurable thresholds for highlighting slow queries,
and session-scoped statistics collection for query duration analysis.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from enum import Enum


class SlowQueryLevel(Enum):
    """Severity level for slow query highlighting."""

    WARNING = "warning"  # Duration > warning_ms threshold
    SLOW = "slow"  # Duration > slow_ms threshold
    CRITICAL = "critical"  # Duration > critical_ms threshold


# Default threshold values in milliseconds
DEFAULT_WARNING_MS = 100.0
DEFAULT_SLOW_MS = 500.0
DEFAULT_CRITICAL_MS = 1000.0

# Regex pattern for extracting duration from PostgreSQL log entries
# Matches: "duration: 234.567 ms" or "duration: 1.234 s"
_DURATION_PATTERN = re.compile(
    r"duration:\s*(\d+\.?\d*)\s*(ms|s)",
    re.IGNORECASE,
)


def extract_duration(text: str) -> float | None:
    """Extract query duration from a PostgreSQL log line.

    Parses duration values from log entries that contain patterns like:
    - "duration: 234.567 ms"
    - "duration: 1.234 s"

    Args:
        text: Log line text to parse.

    Returns:
        Duration in milliseconds, or None if no valid duration found.
    """
    match = _DURATION_PATTERN.search(text)
    if not match:
        return None

    try:
        value = float(match.group(1))
        unit = match.group(2).lower()

        # Convert seconds to milliseconds
        if unit == "s":
            value *= 1000

        # Reject negative values (shouldn't happen, but be safe)
        if value < 0:
            return None

        return value
    except (ValueError, IndexError):
        return None


def validate_thresholds(warning: float, slow: float, critical: float) -> str | None:
    """Validate threshold values for slow query detection.

    Args:
        warning: Warning threshold in milliseconds.
        slow: Slow threshold in milliseconds.
        critical: Critical threshold in milliseconds.

    Returns:
        Error message if invalid, None if valid.
    """
    if warning <= 0 or slow <= 0 or critical <= 0:
        return "All thresholds must be positive numbers"
    if not (warning < slow < critical):
        return "Thresholds must be in ascending order: warning < slow < critical"
    return None


@dataclass
class SlowQueryConfig:
    """Configuration for slow query detection and highlighting.

    Attributes:
        enabled: Whether slow query highlighting is active.
        warning_ms: Threshold for warning level (yellow).
        slow_ms: Threshold for slow level (bold yellow).
        critical_ms: Threshold for critical level (red bold).
    """

    enabled: bool = False
    warning_ms: float = DEFAULT_WARNING_MS
    slow_ms: float = DEFAULT_SLOW_MS
    critical_ms: float = DEFAULT_CRITICAL_MS

    def get_level(self, duration_ms: float) -> SlowQueryLevel | None:
        """Determine the severity level for a given duration.

        Args:
            duration_ms: Query duration in milliseconds.

        Returns:
            SlowQueryLevel if duration exceeds a threshold, None otherwise.
        """
        if duration_ms > self.critical_ms:
            return SlowQueryLevel.CRITICAL
        if duration_ms > self.slow_ms:
            return SlowQueryLevel.SLOW
        if duration_ms > self.warning_ms:
            return SlowQueryLevel.WARNING
        return None

    def format_thresholds(self) -> str:
        """Format thresholds for display.

        Returns:
            Human-readable threshold configuration.
        """
        return (
            f"  Warning (yellow):      > {self.warning_ms:.0f}ms\n"
            f"  Slow (yellow bold):    > {self.slow_ms:.0f}ms\n"
            f"  Critical (red bold):   > {self.critical_ms:.0f}ms"
        )


@dataclass
class DurationStats:
    """Session-scoped collection of query duration samples for statistics.

    Maintains running counters for O(1) access to basic statistics,
    while storing all samples for percentile calculations.

    Attributes:
        samples: All observed duration values in milliseconds.
    """

    samples: list[float] = field(default_factory=list)
    _sum: float = 0.0
    _min: float = field(default=float("inf"))
    _max: float = 0.0

    def add(self, duration_ms: float) -> None:
        """Add a duration sample and update running statistics.

        Args:
            duration_ms: Query duration in milliseconds.
        """
        self.samples.append(duration_ms)
        self._sum += duration_ms
        if duration_ms < self._min:
            self._min = duration_ms
        if duration_ms > self._max:
            self._max = duration_ms

    def clear(self) -> None:
        """Reset all statistics."""
        self.samples.clear()
        self._sum = 0.0
        self._min = float("inf")
        self._max = 0.0

    def is_empty(self) -> bool:
        """Check if no samples have been collected."""
        return len(self.samples) == 0

    @property
    def count(self) -> int:
        """Number of samples collected."""
        return len(self.samples)

    @property
    def average(self) -> float:
        """Mean duration in milliseconds."""
        if self.is_empty():
            return 0.0
        return self._sum / self.count

    @property
    def min(self) -> float:
        """Minimum observed duration in milliseconds."""
        if self.is_empty():
            return 0.0
        return self._min

    @property
    def max(self) -> float:
        """Maximum observed duration in milliseconds."""
        return self._max

    @property
    def p50(self) -> float:
        """50th percentile (median) duration in milliseconds."""
        if self.is_empty():
            return 0.0
        if self.count == 1:
            return self.samples[0]
        quantiles = statistics.quantiles(self.samples, n=100, method="inclusive")
        return quantiles[49]  # 50th percentile

    @property
    def p95(self) -> float:
        """95th percentile duration in milliseconds."""
        if self.is_empty():
            return 0.0
        if self.count == 1:
            return self.samples[0]
        quantiles = statistics.quantiles(self.samples, n=100, method="inclusive")
        return quantiles[94]  # 95th percentile

    @property
    def p99(self) -> float:
        """99th percentile duration in milliseconds."""
        if self.is_empty():
            return 0.0
        if self.count == 1:
            return self.samples[0]
        quantiles = statistics.quantiles(self.samples, n=100, method="inclusive")
        return quantiles[98]  # 99th percentile

    def format_summary(self) -> str:
        """Format statistics for display.

        Returns:
            Human-readable statistics summary.
        """
        return (
            "Query Duration Statistics\n"
            "─────────────────────────\n"
            f"  Queries:  {self.count:,}\n"
            f"  Average:  {self.average:.1f}ms\n"
            "\n"
            "  Percentiles:\n"
            f"    p50:    {self.p50:.1f}ms\n"
            f"    p95:    {self.p95:.1f}ms\n"
            f"    p99:    {self.p99:.1f}ms\n"
            f"    max:    {self.max:.1f}ms"
        )
