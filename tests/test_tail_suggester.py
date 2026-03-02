"""Tests for TailCommandSuggester command name completion (T009).

Covers input parsing, command name matching, exact-match suppression,
no-match cases, alphabetical ordering, full-line return format,
alias handling, and suggester configuration attributes.

Argument completion (T015) and history fallback (T019) are separate tasks.
"""

from __future__ import annotations

import pytest

from pgtail_py.tail_completion_data import TAIL_COMPLETION_DATA
from pgtail_py.tail_history import TailCommandHistory
from pgtail_py.tail_suggester import TailCommandSuggester


def _make_suggester() -> TailCommandSuggester:
    """Create a TailCommandSuggester with empty history and no dynamic sources."""
    history = TailCommandHistory(max_entries=100)
    return TailCommandSuggester(
        history=history,
        completion_data=TAIL_COMPLETION_DATA,
        dynamic_sources={},
    )


# ---------------------------------------------------------------------------
# 1. Input parsing (_parse_input)
# ---------------------------------------------------------------------------


class TestParseInput:
    """Tests for TailCommandSuggester._parse_input."""

    def test_empty_string(self) -> None:
        """Empty string yields (None, [], '')."""
        s = _make_suggester()
        assert s._parse_input("") == (None, [], "")

    def test_whitespace_only(self) -> None:
        """Whitespace-only string yields (None, [], '')."""
        s = _make_suggester()
        assert s._parse_input("   ") == (None, [], "")

    def test_single_partial(self) -> None:
        """Single partial word without trailing space: still typing command."""
        s = _make_suggester()
        assert s._parse_input("le") == (None, [], "le")

    def test_command_with_trailing_space(self) -> None:
        """Command followed by space: command identified, empty partial."""
        s = _make_suggester()
        assert s._parse_input("level ") == ("level", [], "")

    def test_command_with_trailing_spaces(self) -> None:
        """Command followed by multiple spaces: same as single trailing space."""
        s = _make_suggester()
        assert s._parse_input("level  ") == ("level", [], "")

    def test_command_with_partial_arg(self) -> None:
        """Command and partial argument: command identified, partial captured."""
        s = _make_suggester()
        assert s._parse_input("level e") == ("level", [], "e")

    def test_multiple_tokens_with_trailing_space(self) -> None:
        """Multiple completed tokens: all args captured, empty partial."""
        s = _make_suggester()
        assert s._parse_input("errors --since 5m ") == (
            "errors",
            ["--since", "5m"],
            "",
        )

    def test_multiple_tokens_without_trailing_space(self) -> None:
        """Multiple tokens, last is partial: last token is partial."""
        s = _make_suggester()
        assert s._parse_input("errors --since 5") == (
            "errors",
            ["--since"],
            "5",
        )

    def test_command_casefolded(self) -> None:
        """Command token is lowercased in the returned tuple."""
        s = _make_suggester()
        assert s._parse_input("LEVEL ") == ("level", [], "")
        assert s._parse_input("Level error") == ("level", [], "error")


# ---------------------------------------------------------------------------
# 2. Command name matching (get_suggestion)
# ---------------------------------------------------------------------------


class TestCommandNameMatching:
    """Tests for command name prefix matching via get_suggestion."""

    async def test_le_suggests_level(self) -> None:
        """'le' prefix-matches 'level', returned as full line."""
        s = _make_suggester()
        result = await s.get_suggestion("le")
        assert result == "level"

    async def test_hi_suggests_highlight(self) -> None:
        """'hi' prefix-matches 'highlight'."""
        s = _make_suggester()
        result = await s.get_suggestion("hi")
        assert result == "highlight"

    async def test_s_suggests_set(self) -> None:
        """'s' matches set, since, slow, stop; 'set' is first alphabetically."""
        s = _make_suggester()
        result = await s.get_suggestion("s")
        assert result == "set"

    async def test_case_insensitive_partial_preserves_user_casing(self) -> None:
        """'LEV' matches 'level' case-insensitively; suffix appended to user input."""
        s = _make_suggester()
        result = await s.get_suggestion("LEV")
        assert result == "LEVel"

    async def test_full_command_uppercase_returns_none(self) -> None:
        """'LEVEL' is 5 chars matching 'level' (5 chars) — empty suffix → None."""
        s = _make_suggester()
        result = await s.get_suggestion("LEVEL")
        assert result is None


# ---------------------------------------------------------------------------
# 3. Exact command match (empty suffix → None)
# ---------------------------------------------------------------------------


class TestExactCommandMatch:
    """When typed text exactly matches a command name, no ghost text."""

    async def test_p_exact_match_returns_none(self) -> None:
        """'p' exactly matches the 'p' command — no suggestion."""
        s = _make_suggester()
        result = await s.get_suggestion("p")
        assert result is None

    async def test_q_exact_match_returns_none(self) -> None:
        """'q' exactly matches the 'q' command — no suggestion."""
        s = _make_suggester()
        result = await s.get_suggestion("q")
        assert result is None

    async def test_level_exact_match_returns_none(self) -> None:
        """'level' (no trailing space) exactly matches — empty suffix → None."""
        s = _make_suggester()
        result = await s.get_suggestion("level")
        assert result is None

    async def test_f_exact_match_returns_none(self) -> None:
        """'f' exactly matches the 'f' command — no suggestion."""
        s = _make_suggester()
        result = await s.get_suggestion("f")
        assert result is None


# ---------------------------------------------------------------------------
# 4. No match
# ---------------------------------------------------------------------------


class TestNoMatch:
    """Unknown prefixes return None."""

    async def test_xyz_no_match(self) -> None:
        """'xyz' matches no command."""
        s = _make_suggester()
        result = await s.get_suggestion("xyz")
        assert result is None

    async def test_zz_no_match(self) -> None:
        """'zz' matches no command."""
        s = _make_suggester()
        result = await s.get_suggestion("zz")
        assert result is None

    async def test_empty_string_no_suggestion(self) -> None:
        """Empty input returns None (nothing to complete)."""
        s = _make_suggester()
        result = await s.get_suggestion("")
        assert result is None


# ---------------------------------------------------------------------------
# 5. First alphabetical ordering
# ---------------------------------------------------------------------------


class TestAlphabeticalOrdering:
    """Prefix matches return the first alphabetical command."""

    async def test_s_returns_set(self) -> None:
        """'s' → 'set' (before since, slow, stop)."""
        s = _make_suggester()
        result = await s.get_suggestion("s")
        assert result == "set"

    async def test_c_returns_clear(self) -> None:
        """'c' → 'clear' (before connections)."""
        s = _make_suggester()
        result = await s.get_suggestion("c")
        assert result == "clear"

    async def test_ex_returns_exit(self) -> None:
        """'ex' → 'exit' (exit < export alphabetically)."""
        s = _make_suggester()
        result = await s.get_suggestion("ex")
        assert result == "exit"

    async def test_st_returns_stop(self) -> None:
        """'st' → 'stop' (not 'set', since 'se' != 'st')."""
        s = _make_suggester()
        result = await s.get_suggestion("st")
        assert result == "stop"


# ---------------------------------------------------------------------------
# 6. Full-line return format
# ---------------------------------------------------------------------------


class TestFullLineReturn:
    """get_suggestion returns the full line, not just the suffix."""

    async def test_le_returns_full_word(self) -> None:
        """'le' returns 'level', not 'vel'."""
        s = _make_suggester()
        result = await s.get_suggestion("le")
        assert result == "level"
        assert result.startswith("le")

    async def test_return_starts_with_input(self) -> None:
        """Returned suggestion always starts with the original input."""
        s = _make_suggester()
        for prefix in ("le", "hi", "si", "be", "er", "co", "pa"):
            result = await s.get_suggestion(prefix)
            if result is not None:
                assert result.startswith(prefix), (
                    f"Suggestion {result!r} does not start with {prefix!r}"
                )


# ---------------------------------------------------------------------------
# 7. Alias handling
# ---------------------------------------------------------------------------


class TestAliasHandling:
    """Short command names like 'p', 'f', 'q' are real commands, not aliases.
    Test prefix matching for commands that share prefixes with shorter ones."""

    async def test_pa_suggests_pause(self) -> None:
        """'pa' prefix-matches 'pause'."""
        s = _make_suggester()
        result = await s.get_suggestion("pa")
        assert result == "pause"

    async def test_fo_suggests_follow(self) -> None:
        """'fo' prefix-matches 'follow'."""
        s = _make_suggester()
        result = await s.get_suggestion("fo")
        assert result == "follow"

    async def test_fi_suggests_filter(self) -> None:
        """'fi' prefix-matches 'filter'."""
        s = _make_suggester()
        result = await s.get_suggestion("fi")
        assert result == "filter"

    async def test_he_suggests_help(self) -> None:
        """'he' prefix-matches 'help'."""
        s = _make_suggester()
        result = await s.get_suggestion("he")
        assert result == "help"

    async def test_th_suggests_theme(self) -> None:
        """'th' prefix-matches 'theme'."""
        s = _make_suggester()
        result = await s.get_suggestion("th")
        assert result == "theme"


# ---------------------------------------------------------------------------
# 8. Suggester configuration
# ---------------------------------------------------------------------------


class TestSuggesterConfiguration:
    """Verify Textual Suggester base class configuration."""

    def test_use_cache_is_false(self) -> None:
        """use_cache must be False (FR-020: no stale suggestions).

        Textual's Suggester stores use_cache=False as cache=None
        (no LRU cache allocated).
        """
        s = _make_suggester()
        assert s.cache is None

    def test_case_sensitive_is_true(self) -> None:
        """case_sensitive must be True (FR-018: mixed-case handling)."""
        s = _make_suggester()
        assert s.case_sensitive is True


# ---------------------------------------------------------------------------
# 9. History fallback integration tests (T019)
# ---------------------------------------------------------------------------


def _make_suggester_with_history(entries: list[str]) -> TailCommandSuggester:
    """Create a TailCommandSuggester pre-populated with history entries."""
    history = TailCommandHistory(max_entries=100)
    for entry in entries:
        history.add(entry)
    return TailCommandSuggester(
        history=history,
        completion_data=TAIL_COMPLETION_DATA,
        dynamic_sources={},
    )


class TestHistoryFallback:
    """History fallback integration tests (T019).

    Exercises the structural-then-history pipeline in get_suggestion():
    - Structural completion returns None (empty suffix or free-form slot)
    - History search_prefix() is tried as fallback
    - Case-sensitive matching is preserved throughout
    """

    @pytest.mark.asyncio
    async def test_structural_empty_suffix_falls_to_history(self) -> None:
        """Structural matches 'error' exactly (empty suffix), so falls to history.

        Input 'level error': structural resolves 'error' from LEVEL_VALUES but
        suffix is empty -> no ghost text from structural. History has 'level error+'
        which starts with 'level error' and is longer -> history returns it.
        """
        s = _make_suggester_with_history(["level error+"])
        result = await s.get_suggestion("level error")
        assert result == "level error+"

    @pytest.mark.asyncio
    async def test_free_form_falls_to_history(self) -> None:
        """filter's first positional is free-form (None slot), so structural returns None.

        Input 'filter /dead': structural sees free-form positional -> None.
        History has 'filter /deadlock/i' -> fallback returns it.
        """
        s = _make_suggester_with_history(["filter /deadlock/i"])
        result = await s.get_suggestion("filter /dead")
        assert result == "filter /deadlock/i"

    @pytest.mark.asyncio
    async def test_structural_takes_priority(self) -> None:
        """Structural finds '5m' from TIME_PRESETS (non-empty suffix 'm') -> no fallback.

        Input 'since 5': structural resolves '5m' (starts with '5'), suffix='m' ->
        returns 'since 5m'. History has 'since 5m' but structural wins.
        """
        s = _make_suggester_with_history(["since 5m"])
        result = await s.get_suggestion("since 5")
        assert result == "since 5m"

    @pytest.mark.asyncio
    async def test_no_match_anywhere(self) -> None:
        """Unknown command with trailing space and empty history returns None.

        Input 'xyzabc ': command='xyzabc', no completion spec -> structural None.
        History is empty -> history None. Pipeline returns None.
        """
        s = _make_suggester_with_history([])
        result = await s.get_suggestion("xyzabc ")
        assert result is None

    @pytest.mark.asyncio
    async def test_history_case_sensitive_in_fallback(self) -> None:
        """History fallback uses case-sensitive search_prefix().

        Input 'level error': structural matches 'error' exactly (empty suffix) ->
        falls through to history. History has 'Level error+' (capital L).
        search_prefix('level error') is case-sensitive: 'Level error+' does not
        start with 'level error' -> no match -> returns None.
        """
        s = _make_suggester_with_history(["Level error+"])
        result = await s.get_suggestion("level error")
        assert result is None


# ---------------------------------------------------------------------------
# T015 Argument completion tests
# ---------------------------------------------------------------------------
#
# Helper for tests that need a dynamic_sources mock.
#


def _make_suggester_with_dynamics(
    dynamic_sources: dict,
) -> TailCommandSuggester:
    """Create a TailCommandSuggester with empty history and provided dynamic sources."""
    history = TailCommandHistory(max_entries=100)
    return TailCommandSuggester(
        history=history,
        completion_data=TAIL_COMPLETION_DATA,
        dynamic_sources=dynamic_sources,
    )


# ---------------------------------------------------------------------------
# 10. Static value completion (positionals with static_values lists)
# ---------------------------------------------------------------------------


class TestStaticValueCompletion:
    """Positional slots backed by static_values lists return prefix matches."""

    @pytest.mark.asyncio
    async def test_level_space_suggests_first_level(self) -> None:
        """'level ' → first alphabetical level value ('debug')."""
        from pgtail_py.tail_completion_data import LEVEL_VALUES

        s = _make_suggester()
        result = await s.get_suggestion("level ")
        assert result == f"level {LEVEL_VALUES[0]}"

    @pytest.mark.asyncio
    async def test_level_e_suggests_error(self) -> None:
        """'level e' → 'level error' (prefix match within LEVEL_VALUES)."""
        s = _make_suggester()
        result = await s.get_suggestion("level e")
        assert result == "level error"

    @pytest.mark.asyncio
    async def test_since_space_suggests_first_time_preset(self) -> None:
        """'since ' → first time preset from TIME_PRESETS."""
        from pgtail_py.tail_completion_data import TIME_PRESETS

        s = _make_suggester()
        result = await s.get_suggestion("since ")
        assert result == f"since {TIME_PRESETS[0]}"

    @pytest.mark.asyncio
    async def test_slow_space_suggests_first_threshold_preset(self) -> None:
        """'slow ' → first threshold preset from THRESHOLD_PRESETS."""
        from pgtail_py.tail_completion_data import THRESHOLD_PRESETS

        s = _make_suggester()
        result = await s.get_suggestion("slow ")
        assert result == f"slow {THRESHOLD_PRESETS[0]}"

    @pytest.mark.asyncio
    async def test_theme_space_suggests_first_builtin_theme(self) -> None:
        """'theme ' → first built-in theme from BUILTIN_THEME_NAMES."""
        from pgtail_py.tail_completion_data import BUILTIN_THEME_NAMES

        s = _make_suggester()
        result = await s.get_suggestion("theme ")
        assert result == f"theme {BUILTIN_THEME_NAMES[0]}"

    @pytest.mark.asyncio
    async def test_theme_d_suggests_dark(self) -> None:
        """'theme d' → 'theme dark' (prefix match on 'd')."""
        s = _make_suggester()
        result = await s.get_suggestion("theme d")
        assert result == "theme dark"


# ---------------------------------------------------------------------------
# 11. Subcommand completion
# ---------------------------------------------------------------------------


class TestSubcommandCompletion:
    """'highlight' dispatches to subcommand completion."""

    @pytest.mark.asyncio
    async def test_highlight_space_suggests_first_subcommand(self) -> None:
        """'highlight ' → first alphabetical subcommand ('add')."""
        s = _make_suggester()
        result = await s.get_suggestion("highlight ")
        # 'add' comes first alphabetically among highlight subcommands
        assert result == "highlight add"

    @pytest.mark.asyncio
    async def test_highlight_l_suggests_list(self) -> None:
        """'highlight l' → 'highlight list' (prefix match on 'l')."""
        s = _make_suggester()
        result = await s.get_suggestion("highlight l")
        assert result == "highlight list"

    @pytest.mark.asyncio
    async def test_highlight_enable_space_suggests_dynamic_highlighter(self) -> None:
        """'highlight enable ' → first highlighter name from dynamic source."""
        s = _make_suggester_with_dynamics(
            {
                "highlighter_names": lambda: ["duration", "sqlstate", "timestamp"],
            }
        )
        result = await s.get_suggestion("highlight enable ")
        assert result == "highlight enable duration"

    @pytest.mark.asyncio
    async def test_highlight_list_space_returns_none(self) -> None:
        """'highlight list ' → None (list subcommand is no_args=True)."""
        s = _make_suggester()
        result = await s.get_suggestion("highlight list ")
        assert result is None

    @pytest.mark.asyncio
    async def test_highlight_enable_duration_space_returns_none(self) -> None:
        """'highlight enable duration ' → None (positional slots exhausted)."""
        s = _make_suggester_with_dynamics(
            {
                "highlighter_names": lambda: ["duration", "sqlstate", "timestamp"],
            }
        )
        result = await s.get_suggestion("highlight enable duration ")
        assert result is None


# ---------------------------------------------------------------------------
# 12. Flag completion (boolean and value-taking flags)
# ---------------------------------------------------------------------------


class TestFlagCompletion:
    """Flag scanning algorithm correctly handles boolean and value-taking flags."""

    @pytest.mark.asyncio
    async def test_errors_trend_space_suggests_clear(self) -> None:
        """'errors --trend ' → 'errors --trend clear' (--trend is boolean, positional[0] active)."""
        s = _make_suggester()
        result = await s.get_suggestion("errors --trend ")
        assert result == "errors --trend clear"

    @pytest.mark.asyncio
    async def test_errors_code_space_suggests_sqlstate_code(self) -> None:
        """'errors --code ' → first alphabetical SQLSTATE code."""
        from pgtail_py.tail_completion_data import SQLSTATE_CODES

        s = _make_suggester()
        result = await s.get_suggestion("errors --code ")
        assert result == f"errors --code {SQLSTATE_CODES[0]}"

    @pytest.mark.asyncio
    async def test_errors_since_space_suggests_time_preset(self) -> None:
        """'errors --since ' → first time preset."""
        from pgtail_py.tail_completion_data import TIME_PRESETS

        s = _make_suggester()
        result = await s.get_suggestion("errors --since ")
        assert result == f"errors --since {TIME_PRESETS[0]}"

    @pytest.mark.asyncio
    async def test_errors_since_5m_code_space_suggests_sqlstate(self) -> None:
        """'errors --since 5m --code ' → first SQLSTATE code (--since consumed by 5m)."""
        from pgtail_py.tail_completion_data import SQLSTATE_CODES

        s = _make_suggester()
        result = await s.get_suggestion("errors --since 5m --code ")
        assert result == f"errors --since 5m --code {SQLSTATE_CODES[0]}"

    @pytest.mark.asyncio
    async def test_errors_trend_code_space_suggests_sqlstate(self) -> None:
        """'errors --trend --code ' → first SQLSTATE code (--trend is boolean)."""
        from pgtail_py.tail_completion_data import SQLSTATE_CODES

        s = _make_suggester()
        result = await s.get_suggestion("errors --trend --code ")
        assert result == f"errors --trend --code {SQLSTATE_CODES[0]}"


# ---------------------------------------------------------------------------
# 13. Flag=value inline completion
# ---------------------------------------------------------------------------


class TestFlagEqualsValue:
    """Inline --flag=value partial is completed in-place."""

    @pytest.mark.asyncio
    async def test_export_format_eq_suggests_csv(self) -> None:
        """'export --format=' → 'export --format=csv' (first format value)."""
        s = _make_suggester()
        result = await s.get_suggestion("export --format=")
        assert result == "export --format=csv"

    @pytest.mark.asyncio
    async def test_export_format_eq_j_suggests_json(self) -> None:
        """'export --format=j' → 'export --format=json' (prefix 'j')."""
        s = _make_suggester()
        result = await s.get_suggestion("export --format=j")
        assert result == "export --format=json"

    @pytest.mark.asyncio
    async def test_connections_db_eq_returns_none(self) -> None:
        """'connections --db=' → None (--db has empty CompletionSpec with no values)."""
        s = _make_suggester()
        result = await s.get_suggestion("connections --db=")
        assert result is None


# ---------------------------------------------------------------------------
# 14. Positional tracking across multiple slots
# ---------------------------------------------------------------------------


class TestPositionalTracking:
    """Multiple positional slots are tracked by index."""

    @pytest.mark.asyncio
    async def test_between_first_arg_suggests_second_time_preset(self) -> None:
        """'between 5m ' → second positional slot → first TIME_PRESETS value."""
        from pgtail_py.tail_completion_data import TIME_PRESETS

        s = _make_suggester()
        result = await s.get_suggestion("between 5m ")
        # positional_index=1 after consuming '5m', slot[1] is TIME_PRESETS
        assert result == f"between 5m {TIME_PRESETS[0]}"

    @pytest.mark.asyncio
    async def test_between_both_args_exhausted_returns_none(self) -> None:
        """'between 5m 15:00 ' → None (both positionals exhausted)."""
        s = _make_suggester()
        result = await s.get_suggestion("between 5m 15:00 ")
        assert result is None


# ---------------------------------------------------------------------------
# 15. Free-form positional slots skip structural completion
# ---------------------------------------------------------------------------


class TestFreeFormSkip:
    """Positional slots marked None (free-form) return None for structural completion."""

    @pytest.mark.asyncio
    async def test_filter_slash_returns_none(self) -> None:
        """'filter /' → None (free-form positional slot)."""
        s = _make_suggester()
        result = await s.get_suggestion("filter /")
        assert result is None

    @pytest.mark.asyncio
    async def test_export_path_then_space_returns_none(self) -> None:
        """'export /tmp/file ' → None (positional exhausted after free-form path)."""
        s = _make_suggester()
        result = await s.get_suggestion("export /tmp/file ")
        assert result is None


# ---------------------------------------------------------------------------
# 16. No-args commands: trailing space returns None
# ---------------------------------------------------------------------------


class TestNoArgsAfterSpace:
    """Commands with no_args=True produce no argument suggestions."""

    @pytest.mark.asyncio
    async def test_pause_space_returns_none(self) -> None:
        """'pause ' → None (pause is no_args=True)."""
        s = _make_suggester()
        result = await s.get_suggestion("pause ")
        assert result is None

    @pytest.mark.asyncio
    async def test_q_space_returns_none(self) -> None:
        """'q ' → None (q is no_args=True)."""
        s = _make_suggester()
        result = await s.get_suggestion("q ")
        assert result is None


# ---------------------------------------------------------------------------
# 17. Flag name completion (partial "--" prefix)
# ---------------------------------------------------------------------------


class TestFlagNameCompletion:
    """Partial "--" prefix triggers flag name completion."""

    @pytest.mark.asyncio
    async def test_export_double_dash_suggests_first_flag(self) -> None:
        """'export /tmp/out.csv --' → first alphabetical flag of export."""
        s = _make_suggester()
        result = await s.get_suggestion("export /tmp/out.csv --")
        # export flags sorted: --format, --highlighted
        assert result == "export /tmp/out.csv --format"

    @pytest.mark.asyncio
    async def test_errors_double_dash_suggests_first_flag(self) -> None:
        """'errors --' → first alphabetical flag among errors flags."""
        s = _make_suggester()
        result = await s.get_suggestion("errors --")
        # errors flags sorted: --code, --live, --since, --trend
        assert result == "errors --code"


# ---------------------------------------------------------------------------
# 18. Dynamic source completion
# ---------------------------------------------------------------------------


class TestDynamicSources:
    """Dynamic sources are called at suggestion time and matched by prefix."""

    @pytest.mark.asyncio
    async def test_set_space_suggests_setting_key(self) -> None:
        """'set ' → first setting key from dynamic source."""
        s = _make_suggester_with_dynamics(
            {
                "setting_keys": lambda: [
                    "default.follow",
                    "display.show_pid",
                    "slow.warn",
                ],
            }
        )
        result = await s.get_suggestion("set ")
        assert result == "set default.follow"

    @pytest.mark.asyncio
    async def test_help_space_suggests_help_topic(self) -> None:
        """'help ' → first help topic from dynamic source."""
        s = _make_suggester_with_dynamics(
            {
                "help_topics": lambda: ["errors", "filter", "keys", "level"],
            }
        )
        result = await s.get_suggestion("help ")
        assert result == "help errors"


# ---------------------------------------------------------------------------
# 19. Case sensitivity in argument completion
# ---------------------------------------------------------------------------


class TestCaseSensitivity:
    """Static value completion is case-insensitive; dynamic is case-sensitive."""

    @pytest.mark.asyncio
    async def test_level_uppercase_e_suggests_with_preserved_casing(self) -> None:
        """'level E' → 'level Error' (static: case-insensitive match, preserves value casing).

        Static values are stored lowercase ('error'). The match is case-insensitive
        so 'E' matches 'error'. The matched value 'error' is appended as a suffix
        to the user's typed 'E', yielding 'E' + 'rror' = 'Error'.
        The full suggestion is the original input 'level E' + suffix 'rror' = 'level Error'.
        """
        s = _make_suggester()
        result = await s.get_suggestion("level E")
        assert result == "level Error"

    @pytest.mark.asyncio
    async def test_level_uppercase_er_suggests_error(self) -> None:
        """'level Er' → 'level Error' (static case-insensitive match)."""
        s = _make_suggester()
        result = await s.get_suggestion("level Er")
        assert result == "level Error"

    @pytest.mark.asyncio
    async def test_dynamic_case_sensitive_uppercase_matches(self) -> None:
        """Dynamic source: 'highlight enable D' → 'highlight enable Duration' (exact prefix)."""
        s = _make_suggester_with_dynamics(
            {
                "highlighter_names": lambda: ["Duration", "sqlstate"],
            }
        )
        result = await s.get_suggestion("highlight enable D")
        assert result == "highlight enable Duration"

    @pytest.mark.asyncio
    async def test_dynamic_case_sensitive_lowercase_no_match(self) -> None:
        """Dynamic source: 'highlight enable d' → None (case-sensitive, no match for 'd')."""
        s = _make_suggester_with_dynamics(
            {
                "highlighter_names": lambda: ["Duration", "sqlstate"],
            }
        )
        result = await s.get_suggestion("highlight enable d")
        assert result is None


# ---------------------------------------------------------------------------
# 20. Unknown command returns None
# ---------------------------------------------------------------------------


class TestUnknownCommand:
    """Commands not in completion data return None for argument completion."""

    @pytest.mark.asyncio
    async def test_unknown_command_returns_none(self) -> None:
        """'foobar ' → None (no spec found for 'foobar')."""
        s = _make_suggester()
        result = await s.get_suggestion("foobar ")
        assert result is None


# ---------------------------------------------------------------------------
# SC-002: Suggestion computation performance (<1ms average)
# ---------------------------------------------------------------------------


class TestSuggestionPerformance:
    """Verify suggestion computation meets SC-002 latency target."""

    @pytest.mark.asyncio
    async def test_suggestion_under_1ms_average(self) -> None:
        """100 get_suggestion calls on varied input average <1ms each."""
        import time

        s = _make_suggester()
        inputs = [
            "le",
            "level ",
            "level e",
            "errors --since 5m --code ",
            "highlight enable ",
            "since 5",
            "filter /dead",
            "export /tmp/out.csv --format=j",
            "theme d",
            "xyz",
        ]
        start = time.perf_counter()
        for _ in range(10):
            for inp in inputs:
                await s.get_suggestion(inp)
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 1.0, f"Average suggestion time {avg_ms:.3f}ms exceeds 1ms target"
