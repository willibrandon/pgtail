"""Error trend visualization.

Provides sparkline visualization and bucketing for error rate trends.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pgtail_py.error_stats import ErrorEvent

# Unicode block characters for sparkline (increasing height)
SPARK_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[int]) -> str:
    """Generate sparkline from values.

    Args:
        values: List of integer values to visualize.

    Returns:
        Unicode sparkline string, one character per value.
    """
    if not values:
        return ""
    max_val = max(values) or 1
    return "".join(SPARK_CHARS[min(int(v / max_val * 7), 7)] for v in values)


def bucket_events(events: list[ErrorEvent], minutes: int = 60) -> list[int]:
    """Bucket events into per-minute counts.

    Args:
        events: List of ErrorEvent objects with timestamps.
        minutes: Number of minutes to bucket (default 60).

    Returns:
        List of counts per minute, oldest first.
    """
    now = datetime.now()
    buckets = [0] * minutes
    cutoff = now - timedelta(minutes=minutes)

    for event in events:
        if event.timestamp < cutoff:
            continue
        age_minutes = int((now - event.timestamp).total_seconds() / 60)
        if 0 <= age_minutes < minutes:
            buckets[minutes - 1 - age_minutes] += 1

    return buckets
