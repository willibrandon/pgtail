"""Log level filtering for PostgreSQL log output."""

from enum import IntEnum


class LogLevel(IntEnum):
    """PostgreSQL log severity levels.

    Lower values indicate higher severity. Used for filtering log output
    to show only messages at or above a certain severity threshold.
    """

    PANIC = 0
    FATAL = 1
    ERROR = 2
    WARNING = 3
    NOTICE = 4
    LOG = 5
    INFO = 6
    DEBUG1 = 7
    DEBUG2 = 8
    DEBUG3 = 9
    DEBUG4 = 10
    DEBUG5 = 11

    @classmethod
    def from_string(cls, name: str) -> "LogLevel":
        """Parse a log level from its string name.

        Args:
            name: Case-insensitive level name (e.g., "ERROR", "warning")

        Returns:
            The corresponding LogLevel enum value.

        Raises:
            ValueError: If the name is not a valid log level.
        """
        try:
            return cls[name.upper()]
        except KeyError:
            valid = ", ".join(level.name for level in cls)
            raise ValueError(f"Unknown log level '{name}'. Valid levels: {valid}") from None

    @classmethod
    def all_levels(cls) -> set["LogLevel"]:
        """Return a set containing all log levels."""
        return set(cls)

    @classmethod
    def names(cls) -> list[str]:
        """Return list of all level names."""
        return [level.name for level in cls]


def should_show(level: LogLevel, active_levels: set[LogLevel] | None) -> bool:
    """Check if a log entry should be displayed based on active levels.

    Args:
        level: The log level of the entry.
        active_levels: Set of levels to display. None means show all.

    Returns:
        True if the entry should be shown, False otherwise.
    """
    if active_levels is None:
        return True
    return level in active_levels


def parse_levels(args: list[str]) -> tuple[set[LogLevel] | None, list[str]]:
    """Parse level arguments into a set of LogLevels.

    Args:
        args: List of level names (e.g., ["ERROR", "WARNING"]).

    Returns:
        Tuple of (set of valid levels or None for ALL, list of invalid names).
    """
    if not args:
        return None, []

    # Handle ALL special case
    if len(args) == 1 and args[0].upper() == "ALL":
        return None, []

    valid_levels: set[LogLevel] = set()
    invalid_names: list[str] = []

    for arg in args:
        try:
            valid_levels.add(LogLevel.from_string(arg))
        except ValueError:
            invalid_names.append(arg)

    return valid_levels if valid_levels else None, invalid_names
