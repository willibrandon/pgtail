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
