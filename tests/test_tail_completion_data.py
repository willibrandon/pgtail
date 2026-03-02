"""Validation tests for TAIL_COMPLETION_DATA (T011).

Verifies the structural correctness, completeness, and internal consistency
of the completion specification data defined in tail_completion_data.py.
These tests guard against accidental regressions when commands or flags are
added or modified.
"""

from __future__ import annotations

from pgtail_py.cli_tail import TAIL_MODE_COMMANDS
from pgtail_py.tail_completion_data import (
    BUILTIN_THEME_NAMES,
    FORMAT_VALUES,
    LEVEL_VALUES,
    SQLSTATE_CODES,
    TAIL_COMPLETION_DATA,
    THRESHOLD_PRESETS,
    TIME_PRESETS,
    CompletionSpec,
)

# ---------------------------------------------------------------------------
# Helper: walk all CompletionSpec nodes recursively and collect values
# ---------------------------------------------------------------------------

_KNOWN_DYNAMIC_KEYS = {"highlighter_names", "setting_keys", "help_topics"}


def _collect_dynamic_sources(spec: CompletionSpec) -> set[str]:
    """Recursively collect all dynamic_source values in a spec tree."""
    found: set[str] = set()
    if spec.dynamic_source is not None:
        found.add(spec.dynamic_source)
    if spec.subcommands:
        for sub in spec.subcommands.values():
            found |= _collect_dynamic_sources(sub)
    if spec.flags:
        for flag_spec in spec.flags.values():
            if flag_spec is not None:
                found |= _collect_dynamic_sources(flag_spec)
    if spec.positionals:
        for pos in spec.positionals:
            if pos is not None:
                found |= _collect_dynamic_sources(pos)
    return found


# ---------------------------------------------------------------------------
# 1. Inventory completeness
# ---------------------------------------------------------------------------


class TestInventoryCompleteness:
    """Every command from TAIL_MODE_COMMANDS plus 'theme' has a spec entry."""

    def test_all_tail_mode_commands_have_spec(self) -> None:
        """Each name in TAIL_MODE_COMMANDS is a key in TAIL_COMPLETION_DATA."""
        missing = [cmd for cmd in TAIL_MODE_COMMANDS if cmd not in TAIL_COMPLETION_DATA]
        assert missing == [], f"Commands missing from TAIL_COMPLETION_DATA: {missing}"

    def test_theme_command_has_spec(self) -> None:
        """'theme' must have a spec entry (not in TAIL_MODE_COMMANDS but required)."""
        assert "theme" in TAIL_COMPLETION_DATA, "'theme' is missing from TAIL_COMPLETION_DATA"

    def test_no_extra_unknown_commands(self) -> None:
        """All keys in TAIL_COMPLETION_DATA are either in TAIL_MODE_COMMANDS or 'theme'."""
        expected_keys = set(TAIL_MODE_COMMANDS) | {"theme"}
        actual_keys = set(TAIL_COMPLETION_DATA.keys())
        extra = actual_keys - expected_keys
        assert extra == set(), f"Unexpected extra keys in TAIL_COMPLETION_DATA: {extra}"


# ---------------------------------------------------------------------------
# 2. Boolean flags map to None
# ---------------------------------------------------------------------------


class TestBooleanFlags:
    """Boolean (no-value) flags must map to None in their command specs."""

    def test_errors_trend_flag_is_none(self) -> None:
        """errors --trend is a boolean flag (None)."""
        assert TAIL_COMPLETION_DATA["errors"].flags["--trend"] is None

    def test_errors_live_flag_is_none(self) -> None:
        """errors --live is a boolean flag (None)."""
        assert TAIL_COMPLETION_DATA["errors"].flags["--live"] is None

    def test_connections_history_flag_is_none(self) -> None:
        """connections --history is a boolean flag (None)."""
        assert TAIL_COMPLETION_DATA["connections"].flags["--history"] is None

    def test_connections_watch_flag_is_none(self) -> None:
        """connections --watch is a boolean flag (None)."""
        assert TAIL_COMPLETION_DATA["connections"].flags["--watch"] is None

    def test_export_highlighted_flag_is_none(self) -> None:
        """export --highlighted is a boolean flag (None)."""
        assert TAIL_COMPLETION_DATA["export"].flags["--highlighted"] is None



# ---------------------------------------------------------------------------
# 3. Value-taking flags map to CompletionSpec instances
# ---------------------------------------------------------------------------


class TestValueTakingFlags:
    """Flags that take a value must map to a CompletionSpec (not None)."""

    def test_errors_code_flag_is_completion_spec(self) -> None:
        """errors --code takes a SQLSTATE value, must be CompletionSpec."""
        flag_spec = TAIL_COMPLETION_DATA["errors"].flags["--code"]
        assert isinstance(flag_spec, CompletionSpec)

    def test_errors_since_flag_is_completion_spec(self) -> None:
        """errors --since takes a time value, must be CompletionSpec."""
        flag_spec = TAIL_COMPLETION_DATA["errors"].flags["--since"]
        assert isinstance(flag_spec, CompletionSpec)

    def test_connections_db_flag_is_completion_spec(self) -> None:
        """connections --db takes a value, must be CompletionSpec."""
        flag_spec = TAIL_COMPLETION_DATA["connections"].flags["--db"]
        assert isinstance(flag_spec, CompletionSpec)

    def test_connections_user_flag_is_completion_spec(self) -> None:
        """connections --user takes a value, must be CompletionSpec."""
        flag_spec = TAIL_COMPLETION_DATA["connections"].flags["--user"]
        assert isinstance(flag_spec, CompletionSpec)

    def test_connections_app_flag_is_completion_spec(self) -> None:
        """connections --app takes a value, must be CompletionSpec."""
        flag_spec = TAIL_COMPLETION_DATA["connections"].flags["--app"]
        assert isinstance(flag_spec, CompletionSpec)

    def test_export_format_flag_is_completion_spec(self) -> None:
        """export --format takes a format name, must be CompletionSpec."""
        flag_spec = TAIL_COMPLETION_DATA["export"].flags["--format"]
        assert isinstance(flag_spec, CompletionSpec)

    def test_highlight_export_file_flag_is_completion_spec(self) -> None:
        """highlight export --file takes a path, must be CompletionSpec."""
        highlight_export_spec = TAIL_COMPLETION_DATA["highlight"].subcommands["export"]
        flag_spec = highlight_export_spec.flags["--file"]
        assert isinstance(flag_spec, CompletionSpec)


# ---------------------------------------------------------------------------
# 4. Positional counts
# ---------------------------------------------------------------------------


class TestPositionalCounts:
    """Each command has the expected number of positional argument slots."""

    def test_level_has_one_positional(self) -> None:
        assert len(TAIL_COMPLETION_DATA["level"].positionals) == 1

    def test_filter_has_one_positional(self) -> None:
        assert len(TAIL_COMPLETION_DATA["filter"].positionals) == 1

    def test_since_has_one_positional(self) -> None:
        assert len(TAIL_COMPLETION_DATA["since"].positionals) == 1

    def test_until_has_one_positional(self) -> None:
        assert len(TAIL_COMPLETION_DATA["until"].positionals) == 1

    def test_between_has_two_positionals(self) -> None:
        assert len(TAIL_COMPLETION_DATA["between"].positionals) == 2

    def test_slow_has_one_positional(self) -> None:
        assert len(TAIL_COMPLETION_DATA["slow"].positionals) == 1

    def test_clear_has_one_positional(self) -> None:
        assert len(TAIL_COMPLETION_DATA["clear"].positionals) == 1

    def test_set_has_two_positionals(self) -> None:
        assert len(TAIL_COMPLETION_DATA["set"].positionals) == 2

    def test_export_has_one_positional(self) -> None:
        assert len(TAIL_COMPLETION_DATA["export"].positionals) == 1

    def test_theme_has_one_positional(self) -> None:
        assert len(TAIL_COMPLETION_DATA["theme"].positionals) == 1

    def test_help_has_one_positional(self) -> None:
        assert len(TAIL_COMPLETION_DATA["help"].positionals) == 1


# ---------------------------------------------------------------------------
# 5. Free-form positions (None slots)
# ---------------------------------------------------------------------------


class TestFreeFormPositions:
    """Positional slots that are free-form (no completions) must be None."""

    def test_filter_positional_0_is_none(self) -> None:
        """filter positional[0] is a free-form regex — must be None."""
        assert TAIL_COMPLETION_DATA["filter"].positionals[0] is None

    def test_export_positional_0_is_none(self) -> None:
        """export positional[0] is a free-form path — must be None."""
        assert TAIL_COMPLETION_DATA["export"].positionals[0] is None

    def test_highlight_add_positional_0_is_none(self) -> None:
        """highlight add positional[0] is a free-form name — must be None."""
        add_spec = TAIL_COMPLETION_DATA["highlight"].subcommands["add"]
        assert add_spec.positionals[0] is None

    def test_highlight_add_positional_1_is_none(self) -> None:
        """highlight add positional[1] is a free-form regex pattern — must be None."""
        add_spec = TAIL_COMPLETION_DATA["highlight"].subcommands["add"]
        assert add_spec.positionals[1] is None

    def test_highlight_import_positional_0_is_none(self) -> None:
        """highlight import positional[0] is a free-form file path — must be None."""
        import_spec = TAIL_COMPLETION_DATA["highlight"].subcommands["import"]
        assert import_spec.positionals[0] is None

    def test_set_positional_1_is_none(self) -> None:
        """set positional[1] is a free-form value — must be None."""
        assert TAIL_COMPLETION_DATA["set"].positionals[1] is None


# ---------------------------------------------------------------------------
# 6. No-argument commands
# ---------------------------------------------------------------------------


class TestNoArgumentCommands:
    """Commands that accept no arguments must have no_args=True."""

    def test_pause_no_args(self) -> None:
        assert TAIL_COMPLETION_DATA["pause"].no_args is True

    def test_p_no_args(self) -> None:
        assert TAIL_COMPLETION_DATA["p"].no_args is True

    def test_follow_no_args(self) -> None:
        assert TAIL_COMPLETION_DATA["follow"].no_args is True

    def test_f_no_args(self) -> None:
        assert TAIL_COMPLETION_DATA["f"].no_args is True

    def test_stop_no_args(self) -> None:
        assert TAIL_COMPLETION_DATA["stop"].no_args is True

    def test_exit_no_args(self) -> None:
        assert TAIL_COMPLETION_DATA["exit"].no_args is True

    def test_q_no_args(self) -> None:
        assert TAIL_COMPLETION_DATA["q"].no_args is True


# ---------------------------------------------------------------------------
# 7. Dynamic source keys
# ---------------------------------------------------------------------------


class TestDynamicSourceKeys:
    """Only the three approved dynamic source keys appear anywhere in the spec tree."""

    def test_only_known_dynamic_source_keys_used(self) -> None:
        """Walk all specs and verify every dynamic_source is in the approved set."""
        all_dynamic_sources: set[str] = set()
        for spec in TAIL_COMPLETION_DATA.values():
            all_dynamic_sources |= _collect_dynamic_sources(spec)
        unknown = all_dynamic_sources - _KNOWN_DYNAMIC_KEYS
        assert unknown == set(), f"Unknown dynamic source keys found: {unknown}"

    def test_all_three_dynamic_keys_are_used(self) -> None:
        """All three known dynamic source keys must actually be referenced."""
        all_dynamic_sources: set[str] = set()
        for spec in TAIL_COMPLETION_DATA.values():
            all_dynamic_sources |= _collect_dynamic_sources(spec)
        missing = _KNOWN_DYNAMIC_KEYS - all_dynamic_sources
        assert missing == set(), f"Expected dynamic source keys never used: {missing}"

    def test_highlighter_names_used_in_highlight_enable(self) -> None:
        """'highlighter_names' is used in highlight→enable positional[0]."""
        enable_spec = TAIL_COMPLETION_DATA["highlight"].subcommands["enable"]
        assert enable_spec.positionals[0].dynamic_source == "highlighter_names"

    def test_setting_keys_used_in_set_positional_0(self) -> None:
        """'setting_keys' is used in set positional[0]."""
        assert TAIL_COMPLETION_DATA["set"].positionals[0].dynamic_source == "setting_keys"

    def test_help_topics_used_in_help_positional_0(self) -> None:
        """'help_topics' is used in help positional[0]."""
        assert TAIL_COMPLETION_DATA["help"].positionals[0].dynamic_source == "help_topics"


# ---------------------------------------------------------------------------
# 8. SQLSTATE_CODES
# ---------------------------------------------------------------------------


class TestSQLSTATECodes:
    """SQLSTATE_CODES must be non-empty and each code must be exactly 5 chars."""

    def test_sqlstate_codes_nonempty(self) -> None:
        assert len(SQLSTATE_CODES) > 0, "SQLSTATE_CODES must not be empty"

    def test_sqlstate_codes_each_five_chars(self) -> None:
        bad = [code for code in SQLSTATE_CODES if len(code) != 5]
        assert bad == [], f"SQLSTATE codes with wrong length: {bad}"

    def test_sqlstate_codes_are_sorted(self) -> None:
        assert sorted(SQLSTATE_CODES) == SQLSTATE_CODES, "SQLSTATE_CODES must be sorted"


# ---------------------------------------------------------------------------
# 9. Static value lists are non-empty and sorted
# ---------------------------------------------------------------------------


class TestStaticValueLists:
    """Module-level constant lists must be non-empty and sorted alphabetically."""

    def test_level_values_nonempty(self) -> None:
        assert len(LEVEL_VALUES) > 0

    def test_level_values_sorted(self) -> None:
        assert sorted(LEVEL_VALUES) == LEVEL_VALUES, "LEVEL_VALUES must be sorted"

    def test_time_presets_nonempty(self) -> None:
        assert len(TIME_PRESETS) > 0

    def test_time_presets_sorted(self) -> None:
        assert sorted(TIME_PRESETS) == TIME_PRESETS, "TIME_PRESETS must be sorted"

    def test_threshold_presets_nonempty(self) -> None:
        assert len(THRESHOLD_PRESETS) > 0

    def test_threshold_presets_sorted(self) -> None:
        assert sorted(THRESHOLD_PRESETS) == THRESHOLD_PRESETS, "THRESHOLD_PRESETS must be sorted"

    def test_format_values_nonempty(self) -> None:
        assert len(FORMAT_VALUES) > 0

    def test_format_values_sorted(self) -> None:
        assert sorted(FORMAT_VALUES) == FORMAT_VALUES, "FORMAT_VALUES must be sorted"

    def test_builtin_theme_names_nonempty(self) -> None:
        assert len(BUILTIN_THEME_NAMES) > 0

    def test_builtin_theme_names_sorted(self) -> None:
        assert sorted(BUILTIN_THEME_NAMES) == BUILTIN_THEME_NAMES, (
            "BUILTIN_THEME_NAMES must be sorted"
        )


# ---------------------------------------------------------------------------
# 10. Highlight subcommands
# ---------------------------------------------------------------------------


class TestHighlightSubcommands:
    """The highlight command must have all 11 required subcommands."""

    _REQUIRED_SUBCOMMANDS = {
        "list",
        "on",
        "off",
        "enable",
        "disable",
        "add",
        "remove",
        "export",
        "import",
        "preview",
        "reset",
    }

    def test_highlight_has_subcommands(self) -> None:
        """highlight spec must have a subcommands dict (not None)."""
        assert TAIL_COMPLETION_DATA["highlight"].subcommands is not None

    def test_all_required_subcommands_present(self) -> None:
        """All 11 required highlight subcommands are present."""
        actual = set(TAIL_COMPLETION_DATA["highlight"].subcommands.keys())
        missing = self._REQUIRED_SUBCOMMANDS - actual
        assert missing == set(), f"Missing highlight subcommands: {missing}"

    def test_no_extra_subcommands(self) -> None:
        """No unexpected subcommands beyond the required 11."""
        actual = set(TAIL_COMPLETION_DATA["highlight"].subcommands.keys())
        extra = actual - self._REQUIRED_SUBCOMMANDS
        assert extra == set(), f"Unexpected extra highlight subcommands: {extra}"

    def test_highlight_subcommand_count_is_eleven(self) -> None:
        """highlight must have exactly 11 subcommands."""
        count = len(TAIL_COMPLETION_DATA["highlight"].subcommands)
        assert count == 11, f"Expected 11 highlight subcommands, got {count}"

    def test_highlight_no_args_subcommands(self) -> None:
        """list, on, off, preview, reset are no-arg subcommands."""
        no_arg_subs = {"list", "on", "off", "preview", "reset"}
        subcommands = TAIL_COMPLETION_DATA["highlight"].subcommands
        for name in no_arg_subs:
            spec = subcommands[name]
            assert spec.no_args is True, f"highlight {name!r} should have no_args=True"
