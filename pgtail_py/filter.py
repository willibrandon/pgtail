"""Log level filtering for PostgreSQL log output."""

from enum import IntEnum

# Abbreviation mappings for level names (module-level to avoid IntEnum issues)
_LEVEL_ALIASES: dict[str, str] = {
    # Common abbreviations
    "ERR": "ERROR",
    "WARN": "WARNING",
    "INF": "INFO",
    "DBG": "DEBUG1",
    "DEBUG": "DEBUG1",
    "FAT": "FATAL",
    "PAN": "PANIC",
    "NOT": "NOTICE",
    "NTC": "NOTICE",
    # Single-letter shortcuts for most common
    "E": "ERROR",
    "W": "WARNING",
    "I": "INFO",
    "L": "LOG",
    "D": "DEBUG1",
    "F": "FATAL",
    "P": "PANIC",
    "N": "NOTICE",
}


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
        """Parse a log level from its string name or abbreviation.

        Supports full names (ERROR, WARNING) and common abbreviations
        (err, warn, e, w, etc.).

        Args:
            name: Case-insensitive level name or abbreviation.

        Returns:
            The corresponding LogLevel enum value.

        Raises:
            ValueError: If the name is not a valid log level.
        """
        upper_name = name.upper()

        # Check aliases first
        if upper_name in _LEVEL_ALIASES:
            upper_name = _LEVEL_ALIASES[upper_name]

        try:
            return cls[upper_name]
        except KeyError:
            valid = ", ".join(level.name for level in cls)
            abbrevs = ", ".join(sorted(set(_LEVEL_ALIASES.keys())))
            raise ValueError(
                f"Unknown log level '{name}'. Valid levels: {valid}. Abbreviations: {abbrevs}"
            ) from None

    @classmethod
    def all_levels(cls) -> set["LogLevel"]:
        """Return a set containing all log levels."""
        return set(cls)

    @classmethod
    def names(cls) -> list[str]:
        """Return list of all level names."""
        return [level.name for level in cls]

    @classmethod
    def at_or_above(cls, threshold: "LogLevel") -> set["LogLevel"]:
        """Return all levels at or above a severity threshold.

        Since lower enum values indicate higher severity, this returns
        all levels with values <= the threshold.

        Args:
            threshold: The minimum severity level to include.

        Returns:
            Set of LogLevel values at or above the threshold.

        Example:
            LogLevel.at_or_above(LogLevel.WARNING) returns
            {PANIC, FATAL, ERROR, WARNING}
        """
        return {level for level in cls if level.value <= threshold.value}

    @classmethod
    def at_or_below(cls, threshold: "LogLevel") -> set["LogLevel"]:
        """Return all levels at or below a severity threshold.

        Since lower enum values indicate higher severity, this returns
        all levels with values >= the threshold.

        Args:
            threshold: The maximum severity level to include.

        Returns:
            Set of LogLevel values at or below the threshold.

        Example:
            LogLevel.at_or_below(LogLevel.WARNING) returns
            {WARNING, NOTICE, LOG, INFO, DEBUG1, DEBUG2, DEBUG3, DEBUG4, DEBUG5}
        """
        return {level for level in cls if level.value >= threshold.value}


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

    Supports three syntaxes:
    - "WARNING" → exact match, only WARNING
    - "WARNING+" → WARNING and more severe (ERROR, FATAL, PANIC)
    - "WARNING-" → WARNING and less severe (NOTICE, LOG, INFO, DEBUG...)

    Multiple levels can be specified: "ERROR,WARNING" for exact matches,
    or "ERROR+,INFO" to combine ranges.

    Args:
        args: List of level names (e.g., ["ERROR+", "WARNING"]).

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
        arg_upper = arg.upper()

        # Check for + or - suffix
        if arg_upper.endswith("+"):
            level_name = arg_upper[:-1]
            try:
                level = LogLevel.from_string(level_name)
                valid_levels.update(LogLevel.at_or_above(level))
            except ValueError:
                invalid_names.append(arg)
        elif arg_upper.endswith("-"):
            level_name = arg_upper[:-1]
            try:
                level = LogLevel.from_string(level_name)
                valid_levels.update(LogLevel.at_or_below(level))
            except ValueError:
                invalid_names.append(arg)
        else:
            # Exact match
            try:
                valid_levels.add(LogLevel.from_string(arg))
            except ValueError:
                invalid_names.append(arg)

    if not valid_levels:
        return None, invalid_names

    return valid_levels, invalid_names
