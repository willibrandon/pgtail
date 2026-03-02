"""Completion specifications for tail mode commands.

Defines the CompletionSpec dataclass and the TAIL_COMPLETION_DATA dictionary
that maps every tail mode command to its argument structure. This data drives
the TailCommandSuggester's structural completion pipeline.

Static value lists are exported as module-level constants for testing.
Dynamic sources (highlighter names, setting keys, help topics) are resolved
at suggestion time via callables passed to TailCommandSuggester.
"""

from __future__ import annotations

from dataclasses import dataclass

from pgtail_py.error_stats import SQLSTATE_NAMES


@dataclass(frozen=True)
class CompletionSpec:
    """Completion specification for a command or argument position.

    Each field is optional, allowing flexible composition. A command can have
    subcommands (``highlight``), flags with or without values (``errors``),
    positional arguments with static or dynamic completions (``level``),
    or no arguments at all (``pause``).

    Attributes:
        static_values: Fixed list of completable values, sorted alphabetically.
            None means no static completions for this position.
        dynamic_source: Key into the suggester's ``dynamic_sources`` dict.
            Resolved at suggestion time by calling ``dynamic_sources[key]()``.
            None means no dynamic source.
        subcommands: Mapping of subcommand name to its own CompletionSpec.
            None means the command has no subcommand tree.
        flags: Mapping of flag name (e.g. ``--trend``) to a CompletionSpec
            for the flag's value, or None for boolean flags that take no value.
            None means the command accepts no flags.
        positionals: Ordered list of CompletionSpec for each positional slot.
            A None entry means that slot is free-form (no completions offered).
            None means the command accepts no positional arguments.
        no_args: When True, the command takes no arguments whatsoever.
    """

    static_values: list[str] | None = None
    dynamic_source: str | None = None
    subcommands: dict[str, CompletionSpec] | None = None
    flags: dict[str, CompletionSpec | None] | None = None
    positionals: list[CompletionSpec | None] | None = None
    no_args: bool = False


# ---------------------------------------------------------------------------
# Static value constants (sorted alphabetically, exported for testing)
# ---------------------------------------------------------------------------

LEVEL_VALUES: list[str] = [
    "debug",
    "error",
    "fatal",
    "info",
    "log",
    "notice",
    "panic",
    "warning",
]
"""Full log-level names accepted by the ``level`` command."""

TIME_PRESETS: list[str] = [
    "10m",
    "15m",
    "1d",
    "1h",
    "2h",
    "30m",
    "4h",
    "5m",
    "clear",
]
"""Common time-range shortcuts for ``since``, ``until``, ``between``."""

THRESHOLD_PRESETS: list[str] = [
    "100",
    "1000",
    "200",
    "50",
    "500",
]
"""Slow-query threshold presets in milliseconds."""

FORMAT_VALUES: list[str] = [
    "csv",
    "json",
    "text",
]
"""Output format values for the ``export --format`` flag."""

BUILTIN_THEME_NAMES: list[str] = [
    "dark",
    "high-contrast",
    "light",
    "monokai",
    "solarized-dark",
    "solarized-light",
]
"""Built-in color theme names for the ``theme`` command."""

SQLSTATE_CODES: list[str] = sorted(SQLSTATE_NAMES.keys())
"""Common SQLSTATE codes sourced from ``error_stats.SQLSTATE_NAMES``."""


# ---------------------------------------------------------------------------
# Per-command completion data
# ---------------------------------------------------------------------------

TAIL_COMPLETION_DATA: dict[str, CompletionSpec] = {
    # -- Filter commands ----------------------------------------------------
    "level": CompletionSpec(
        positionals=[CompletionSpec(static_values=LEVEL_VALUES)],
    ),
    "filter": CompletionSpec(
        positionals=[None],  # free-form regex
    ),
    "since": CompletionSpec(
        positionals=[CompletionSpec(static_values=TIME_PRESETS)],
    ),
    "until": CompletionSpec(
        positionals=[CompletionSpec(static_values=TIME_PRESETS)],
    ),
    "between": CompletionSpec(
        positionals=[
            CompletionSpec(static_values=TIME_PRESETS),
            CompletionSpec(static_values=TIME_PRESETS),
        ],
    ),
    "slow": CompletionSpec(
        positionals=[CompletionSpec(static_values=THRESHOLD_PRESETS)],
    ),
    "clear": CompletionSpec(
        positionals=[CompletionSpec(static_values=["force"])],
    ),
    # -- Display commands ---------------------------------------------------
    "errors": CompletionSpec(
        positionals=[CompletionSpec(static_values=["clear"])],
        flags={
            "--trend": None,
            "--live": None,
            "--code": CompletionSpec(static_values=SQLSTATE_CODES),
            "--since": CompletionSpec(static_values=TIME_PRESETS),
        },
    ),
    "connections": CompletionSpec(
        positionals=[CompletionSpec(static_values=["clear"])],
        flags={
            "--history": None,
            "--watch": None,
            "--db": CompletionSpec(),
            "--user": CompletionSpec(),
            "--app": CompletionSpec(),
        },
    ),
    "highlight": CompletionSpec(
        subcommands={
            "list": CompletionSpec(no_args=True),
            "on": CompletionSpec(no_args=True),
            "off": CompletionSpec(no_args=True),
            "enable": CompletionSpec(
                positionals=[CompletionSpec(dynamic_source="highlighter_names")],
            ),
            "disable": CompletionSpec(
                positionals=[CompletionSpec(dynamic_source="highlighter_names")],
            ),
            "add": CompletionSpec(
                positionals=[None, None],  # free-form name and pattern
            ),
            "remove": CompletionSpec(
                positionals=[CompletionSpec(dynamic_source="highlighter_names")],
            ),
            "export": CompletionSpec(
                flags={"--file": CompletionSpec()},
            ),
            "import": CompletionSpec(
                positionals=[None],  # free-form path
            ),
            "preview": CompletionSpec(no_args=True),
            "reset": CompletionSpec(no_args=True),
        },
    ),
    # -- Config commands ----------------------------------------------------
    "set": CompletionSpec(
        positionals=[
            CompletionSpec(dynamic_source="setting_keys"),
            None,  # free-form value
        ],
    ),
    # -- Export commands -----------------------------------------------------
    "export": CompletionSpec(
        positionals=[None],  # free-form path
        flags={
            "--format": CompletionSpec(static_values=FORMAT_VALUES),
            "--highlighted": None,
        },
    ),
    # -- Theme command ------------------------------------------------------
    "theme": CompletionSpec(
        positionals=[CompletionSpec(static_values=BUILTIN_THEME_NAMES)],
    ),
    # -- Help command -------------------------------------------------------
    "help": CompletionSpec(
        positionals=[CompletionSpec(dynamic_source="help_topics")],
    ),
    # -- Mode commands (no arguments) ---------------------------------------
    "pause": CompletionSpec(no_args=True),
    "p": CompletionSpec(no_args=True),
    "follow": CompletionSpec(no_args=True),
    "f": CompletionSpec(no_args=True),
    # -- Exit commands (no arguments) ---------------------------------------
    "stop": CompletionSpec(no_args=True),
    "exit": CompletionSpec(no_args=True),
    "q": CompletionSpec(no_args=True),
}
"""Canonical completion data for all tail mode commands.

Maps command name to its CompletionSpec describing the full argument structure.
Used by TailCommandSuggester to resolve structural completions.
"""
