"""Tests for regex pattern filtering."""

import re

import pytest

from pgtail_py.regex_filter import (
    FilterState,
    FilterType,
    Highlight,
    RegexFilter,
    parse_filter_arg,
)


class TestFilterType:
    """Tests for FilterType enum."""

    def test_filter_types_exist(self) -> None:
        """All required filter types are defined."""
        assert FilterType.INCLUDE.value == "include"
        assert FilterType.EXCLUDE.value == "exclude"
        assert FilterType.AND.value == "and"


class TestRegexFilter:
    """Tests for RegexFilter dataclass."""

    def test_create_basic(self) -> None:
        """Create a basic include filter."""
        f = RegexFilter.create("error", FilterType.INCLUDE)
        assert f.pattern == "error"
        assert f.filter_type == FilterType.INCLUDE
        assert f.case_sensitive is False
        assert f.compiled is not None

    def test_create_case_sensitive(self) -> None:
        """Create a case-sensitive filter."""
        f = RegexFilter.create("ERROR", FilterType.INCLUDE, case_sensitive=True)
        assert f.case_sensitive is True

    def test_create_exclude(self) -> None:
        """Create an exclude filter."""
        f = RegexFilter.create("debug", FilterType.EXCLUDE)
        assert f.filter_type == FilterType.EXCLUDE

    def test_create_and(self) -> None:
        """Create an AND filter."""
        f = RegexFilter.create("SELECT", FilterType.AND)
        assert f.filter_type == FilterType.AND

    def test_create_invalid_regex(self) -> None:
        """Invalid regex raises re.error."""
        with pytest.raises(re.error):
            RegexFilter.create("[unclosed", FilterType.INCLUDE)

    def test_matches_basic(self) -> None:
        """Basic pattern matching."""
        f = RegexFilter.create("error", FilterType.INCLUDE)
        assert f.matches("This is an error message")
        assert f.matches("ERROR: something failed")  # case-insensitive
        assert not f.matches("This is a warning")

    def test_matches_case_insensitive(self) -> None:
        """Case-insensitive matching (default)."""
        f = RegexFilter.create("ERROR", FilterType.INCLUDE)
        assert f.matches("error message")
        assert f.matches("Error message")
        assert f.matches("ERROR MESSAGE")

    def test_matches_case_sensitive(self) -> None:
        """Case-sensitive matching."""
        f = RegexFilter.create("ERROR", FilterType.INCLUDE, case_sensitive=True)
        assert f.matches("ERROR message")
        assert not f.matches("error message")
        assert not f.matches("Error message")

    def test_matches_regex_pattern(self) -> None:
        """Regex patterns work correctly."""
        f = RegexFilter.create(r"duration: \d+", FilterType.INCLUDE)
        assert f.matches("duration: 123 ms")
        assert f.matches("duration: 0 ms")
        assert not f.matches("duration: slow")


class TestHighlight:
    """Tests for Highlight dataclass."""

    def test_create_basic(self) -> None:
        """Create a basic highlight."""
        h = Highlight.create("SELECT")
        assert h.pattern == "SELECT"
        assert h.case_sensitive is False
        assert h.compiled is not None

    def test_create_case_sensitive(self) -> None:
        """Create a case-sensitive highlight."""
        h = Highlight.create("SELECT", case_sensitive=True)
        assert h.case_sensitive is True

    def test_create_invalid_regex(self) -> None:
        """Invalid regex raises re.error."""
        with pytest.raises(re.error):
            Highlight.create("[unclosed")

    def test_find_spans_basic(self) -> None:
        """Find match spans in text."""
        h = Highlight.create("SELECT")
        spans = h.find_spans("SELECT * FROM users SELECT")
        assert spans == [(0, 6), (20, 26)]

    def test_find_spans_case_insensitive(self) -> None:
        """Case-insensitive span matching."""
        h = Highlight.create("error")
        spans = h.find_spans("Error ERROR error")
        assert len(spans) == 3
        assert spans[0] == (0, 5)
        assert spans[1] == (6, 11)
        assert spans[2] == (12, 17)

    def test_find_spans_case_sensitive(self) -> None:
        """Case-sensitive span matching."""
        h = Highlight.create("ERROR", case_sensitive=True)
        spans = h.find_spans("Error ERROR error")
        assert len(spans) == 1
        assert spans[0] == (6, 11)

    def test_find_spans_no_match(self) -> None:
        """No matches returns empty list."""
        h = Highlight.create("SELECT")
        spans = h.find_spans("UPDATE users SET name = 'foo'")
        assert spans == []

    def test_find_spans_regex_pattern(self) -> None:
        """Regex patterns work in find_spans."""
        h = Highlight.create(r"\d+")
        spans = h.find_spans("id=123 count=456")
        assert spans == [(3, 6), (13, 16)]


class TestFilterState:
    """Tests for FilterState dataclass."""

    def test_empty_state(self) -> None:
        """Create empty filter state."""
        state = FilterState.empty()
        assert state.includes == []
        assert state.excludes == []
        assert state.ands == []
        assert state.highlights == []

    def test_has_filters_empty(self) -> None:
        """Empty state has no filters."""
        state = FilterState.empty()
        assert state.has_filters() is False

    def test_has_filters_with_include(self) -> None:
        """State with include filter."""
        state = FilterState.empty()
        state.includes.append(RegexFilter.create("test", FilterType.INCLUDE))
        assert state.has_filters() is True

    def test_has_filters_with_exclude(self) -> None:
        """State with exclude filter."""
        state = FilterState.empty()
        state.excludes.append(RegexFilter.create("test", FilterType.EXCLUDE))
        assert state.has_filters() is True

    def test_has_filters_with_and(self) -> None:
        """State with AND filter."""
        state = FilterState.empty()
        state.ands.append(RegexFilter.create("test", FilterType.AND))
        assert state.has_filters() is True

    def test_has_highlights(self) -> None:
        """State with highlights."""
        state = FilterState.empty()
        assert state.has_highlights() is False
        state.highlights.append(Highlight.create("test"))
        assert state.has_highlights() is True

    def test_clear_filters(self) -> None:
        """Clear all filters."""
        state = FilterState.empty()
        state.includes.append(RegexFilter.create("a", FilterType.INCLUDE))
        state.excludes.append(RegexFilter.create("b", FilterType.EXCLUDE))
        state.ands.append(RegexFilter.create("c", FilterType.AND))
        state.clear_filters()
        assert state.has_filters() is False
        assert state.includes == []
        assert state.excludes == []
        assert state.ands == []

    def test_clear_highlights(self) -> None:
        """Clear all highlights."""
        state = FilterState.empty()
        state.highlights.append(Highlight.create("test"))
        state.clear_highlights()
        assert state.has_highlights() is False

    def test_add_filter_include(self) -> None:
        """Add include filter via add_filter."""
        state = FilterState.empty()
        f = RegexFilter.create("test", FilterType.INCLUDE)
        state.add_filter(f)
        assert len(state.includes) == 1
        assert state.includes[0] == f

    def test_add_filter_exclude(self) -> None:
        """Add exclude filter via add_filter."""
        state = FilterState.empty()
        f = RegexFilter.create("test", FilterType.EXCLUDE)
        state.add_filter(f)
        assert len(state.excludes) == 1

    def test_add_filter_and(self) -> None:
        """Add AND filter via add_filter."""
        state = FilterState.empty()
        f = RegexFilter.create("test", FilterType.AND)
        state.add_filter(f)
        assert len(state.ands) == 1

    def test_set_include(self) -> None:
        """Set single include replaces previous includes."""
        state = FilterState.empty()
        state.includes.append(RegexFilter.create("old", FilterType.INCLUDE))
        state.includes.append(RegexFilter.create("other", FilterType.INCLUDE))
        f = RegexFilter.create("new", FilterType.INCLUDE)
        state.set_include(f)
        assert len(state.includes) == 1
        assert state.includes[0].pattern == "new"


class TestFilterStateShouldShow:
    """Tests for FilterState.should_show() logic."""

    def test_no_filters_shows_all(self) -> None:
        """No filters means show everything."""
        state = FilterState.empty()
        assert state.should_show("any text") is True
        assert state.should_show("error message") is True

    def test_include_filter_basic(self) -> None:
        """Include filter shows only matching lines."""
        state = FilterState.empty()
        state.includes.append(RegexFilter.create("error", FilterType.INCLUDE))
        assert state.should_show("error message") is True
        assert state.should_show("warning message") is False

    def test_include_filter_or_logic(self) -> None:
        """Multiple includes use OR logic."""
        state = FilterState.empty()
        state.includes.append(RegexFilter.create("error", FilterType.INCLUDE))
        state.includes.append(RegexFilter.create("warning", FilterType.INCLUDE))
        assert state.should_show("error message") is True
        assert state.should_show("warning message") is True
        assert state.should_show("info message") is False

    def test_exclude_filter_basic(self) -> None:
        """Exclude filter hides matching lines."""
        state = FilterState.empty()
        state.excludes.append(RegexFilter.create("debug", FilterType.EXCLUDE))
        assert state.should_show("error message") is True
        assert state.should_show("debug message") is False

    def test_exclude_takes_precedence(self) -> None:
        """Exclude wins over include for same line."""
        state = FilterState.empty()
        state.includes.append(RegexFilter.create("message", FilterType.INCLUDE))
        state.excludes.append(RegexFilter.create("debug", FilterType.EXCLUDE))
        assert state.should_show("error message") is True
        assert state.should_show("debug message") is False  # excluded

    def test_and_filter_basic(self) -> None:
        """AND filter requires all AND patterns to match."""
        state = FilterState.empty()
        state.ands.append(RegexFilter.create("SELECT", FilterType.AND))
        state.ands.append(RegexFilter.create("users", FilterType.AND))
        assert state.should_show("SELECT * FROM users") is True
        assert state.should_show("SELECT * FROM orders") is False
        assert state.should_show("UPDATE users SET") is False

    def test_combined_include_and_and(self) -> None:
        """Include OR with AND requirements."""
        state = FilterState.empty()
        state.includes.append(RegexFilter.create("SELECT", FilterType.INCLUDE))
        state.ands.append(RegexFilter.create("users", FilterType.AND))
        # Must match include (SELECT) AND match AND filter (users)
        assert state.should_show("SELECT * FROM users") is True
        assert state.should_show("SELECT * FROM orders") is False
        assert state.should_show("UPDATE users SET") is False

    def test_combined_all_filter_types(self) -> None:
        """All filter types combined."""
        state = FilterState.empty()
        state.includes.append(RegexFilter.create("SELECT", FilterType.INCLUDE))
        state.includes.append(RegexFilter.create("UPDATE", FilterType.INCLUDE))
        state.excludes.append(RegexFilter.create("debug", FilterType.EXCLUDE))
        state.ands.append(RegexFilter.create("users", FilterType.AND))

        # SELECT + users = show
        assert state.should_show("SELECT * FROM users") is True
        # UPDATE + users = show
        assert state.should_show("UPDATE users SET name") is True
        # SELECT + orders (no users) = hide
        assert state.should_show("SELECT * FROM orders") is False
        # SELECT + users + debug = hide (excluded)
        assert state.should_show("debug: SELECT * FROM users") is False
        # INSERT (no include match) = hide
        assert state.should_show("INSERT INTO users") is False


class TestParseFilterArg:
    """Tests for parse_filter_arg() function."""

    def test_basic_pattern(self) -> None:
        """Parse basic /pattern/ syntax."""
        pattern, case_sensitive = parse_filter_arg("/error/")
        assert pattern == "error"
        assert case_sensitive is False

    def test_case_sensitive_pattern(self) -> None:
        """Parse /pattern/c case-sensitive syntax."""
        pattern, case_sensitive = parse_filter_arg("/ERROR/c")
        assert pattern == "ERROR"
        assert case_sensitive is True

    def test_pattern_with_spaces(self) -> None:
        """Parse pattern containing spaces."""
        pattern, case_sensitive = parse_filter_arg("/connection authorized/")
        assert pattern == "connection authorized"
        assert case_sensitive is False

    def test_pattern_with_regex_chars(self) -> None:
        """Parse pattern with regex special characters."""
        pattern, _ = parse_filter_arg(r"/duration: \d+/")
        assert pattern == r"duration: \d+"

    def test_pattern_with_slashes(self) -> None:
        """Parse pattern containing forward slashes."""
        pattern, _ = parse_filter_arg("/path/to/file/")
        assert pattern == "path/to/file"

    def test_missing_start_slash(self) -> None:
        """Error if pattern doesn't start with /."""
        with pytest.raises(ValueError, match="must start with /"):
            parse_filter_arg("error/")

    def test_missing_end_slash(self) -> None:
        """Error if pattern doesn't end with / or /c."""
        with pytest.raises(ValueError, match="must end with / or /c"):
            parse_filter_arg("/error")

    def test_empty_pattern(self) -> None:
        """Error if pattern is empty."""
        with pytest.raises(ValueError, match="Empty pattern not allowed"):
            parse_filter_arg("//")

    def test_empty_pattern_case_sensitive(self) -> None:
        """Error if case-sensitive pattern is empty."""
        with pytest.raises(ValueError, match="Empty pattern not allowed"):
            parse_filter_arg("//c")
