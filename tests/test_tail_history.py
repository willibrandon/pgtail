"""Tests for TailCommandHistory in-memory operations.

Covers all 7 navigation state transitions from data-model.md,
add() validation, edge cases, search_prefix, and properties.
"""

import pytest

from pgtail_py.tail_history import TailCommandHistory

# ── Navigation State Transitions ─────────────────────────────────────────


class TestTransitionAtRestUpToAtHistoryEntry:
    """Transition 1: at-rest -> Up -> at-history-entry."""

    def test_navigate_back_saves_input_and_returns_newest(self) -> None:
        h = TailCommandHistory()
        h.add("level error")
        h.add("since 5m")

        result = h.navigate_back("partial")

        assert result == "since 5m"
        assert not h.at_rest

    def test_navigate_back_saves_current_input(self) -> None:
        """Saved input is restored when navigating past newest."""
        h = TailCommandHistory()
        h.add("level error")

        h.navigate_back("my partial input")
        # Navigate forward past newest to retrieve saved input
        text, is_restored = h.navigate_forward()

        assert text == "my partial input"
        assert is_restored is True


class TestTransitionAtRestDownToAtRest:
    """Transition 2: at-rest -> Down -> at-rest (no-op)."""

    def test_navigate_forward_at_rest_returns_none(self) -> None:
        h = TailCommandHistory()
        h.add("level error")

        result = h.navigate_forward()

        assert result == (None, False)
        assert h.at_rest


class TestTransitionAtRestTypeSubmitToAtRest:
    """Transition 3: at-rest -> type/submit -> at-rest (no-op on navigation)."""

    def test_add_while_at_rest_stays_at_rest(self) -> None:
        h = TailCommandHistory()
        h.add("first")
        assert h.at_rest

        h.add("second")
        assert h.at_rest

    def test_reset_navigation_while_at_rest_is_noop(self) -> None:
        h = TailCommandHistory()
        h.add("first")
        assert h.at_rest

        h.reset_navigation()
        assert h.at_rest


class TestTransitionAtHistoryEntryUpToAtHistoryEntry:
    """Transition 4: at-history-entry -> Up -> at-history-entry (cursor decrements, clamped at 0)."""

    def test_successive_up_moves_to_older_entries(self) -> None:
        h = TailCommandHistory()
        h.add("first")
        h.add("second")
        h.add("third")

        assert h.navigate_back("") == "third"
        assert h.navigate_back("") == "second"
        assert h.navigate_back("") == "first"

    def test_cursor_clamped_at_oldest(self) -> None:
        h = TailCommandHistory()
        h.add("first")
        h.add("second")

        h.navigate_back("")  # -> "second"
        h.navigate_back("")  # -> "first"
        result = h.navigate_back("")  # clamped at 0

        assert result == "first"
        assert not h.at_rest


class TestTransitionAtHistoryEntryDownStillInHistory:
    """Transition 5: at-history-entry -> Down (cursor+1 < len) -> at-history-entry."""

    def test_navigate_forward_moves_to_newer_entry(self) -> None:
        h = TailCommandHistory()
        h.add("first")
        h.add("second")
        h.add("third")

        h.navigate_back("")  # -> "third"
        h.navigate_back("")  # -> "second"
        h.navigate_back("")  # -> "first"

        text, is_restored = h.navigate_forward()

        assert text == "second"
        assert is_restored is False
        assert not h.at_rest


class TestTransitionAtHistoryEntryDownPastNewest:
    """Transition 6: at-history-entry -> Down (cursor+1 == len) -> past-newest -> at-rest."""

    def test_navigate_forward_past_newest_restores_saved_input(self) -> None:
        h = TailCommandHistory()
        h.add("level error")

        h.navigate_back("my typing")
        text, is_restored = h.navigate_forward()

        assert text == "my typing"
        assert is_restored is True
        assert h.at_rest

    def test_past_newest_with_multi_entry_history(self) -> None:
        h = TailCommandHistory()
        h.add("first")
        h.add("second")

        h.navigate_back("draft")  # -> "second"
        h.navigate_forward()  # past newest -> restore "draft"

        assert h.at_rest

    def test_saved_input_cleared_after_restore(self) -> None:
        """After restoring, a second forward is a no-op (at-rest)."""
        h = TailCommandHistory()
        h.add("cmd")

        h.navigate_back("saved")
        h.navigate_forward()  # restores "saved", now at-rest

        text, is_restored = h.navigate_forward()
        assert text is None
        assert is_restored is False


class TestTransitionAtHistoryEntryTypeSubmitToAtRest:
    """Transition 7: at-history-entry -> type/submit -> at-rest (reset clears cursor and saved_input)."""

    def test_reset_navigation_from_history_entry(self) -> None:
        h = TailCommandHistory()
        h.add("first")
        h.add("second")

        h.navigate_back("")  # now at-history-entry
        assert not h.at_rest

        h.reset_navigation()
        assert h.at_rest

    def test_add_resets_from_history_entry(self) -> None:
        h = TailCommandHistory()
        h.add("first")

        h.navigate_back("")  # now at-history-entry
        assert not h.at_rest

        h.add("new command")
        assert h.at_rest

    def test_reset_clears_saved_input(self) -> None:
        """After reset, navigating back starts fresh (no stale saved_input)."""
        h = TailCommandHistory()
        h.add("first")
        h.add("second")

        h.navigate_back("my draft")  # saves "my draft"
        h.reset_navigation()  # clears saved_input

        # Navigate again, this time saving different input
        h.navigate_back("new draft")
        text, _ = h.navigate_forward()
        assert text == "new draft"


# ── Edge Cases ────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge cases for navigation."""

    def test_empty_history_up_returns_none(self) -> None:
        h = TailCommandHistory()

        result = h.navigate_back("partial")

        assert result is None
        assert h.at_rest

    def test_single_entry_up_down_cycle(self) -> None:
        h = TailCommandHistory()
        h.add("only")

        entry = h.navigate_back("draft")
        assert entry == "only"

        text, is_restored = h.navigate_forward()
        assert text == "draft"
        assert is_restored is True
        assert h.at_rest

    def test_at_oldest_up_returns_same_entry(self) -> None:
        h = TailCommandHistory()
        h.add("oldest")
        h.add("newest")

        h.navigate_back("")  # -> "newest"
        h.navigate_back("")  # -> "oldest"
        result = h.navigate_back("")  # clamped at 0

        assert result == "oldest"

    def test_navigate_back_saves_input_only_on_first_call(self) -> None:
        """Subsequent navigate_back calls preserve the original saved_input."""
        h = TailCommandHistory()
        h.add("first")
        h.add("second")
        h.add("third")

        h.navigate_back("original draft")  # first call: saves "original draft"
        h.navigate_back("should be ignored")  # second call: should NOT overwrite

        # Navigate all the way forward to restore
        h.navigate_forward()  # -> "third"
        text, is_restored = h.navigate_forward()  # past newest

        assert text == "original draft"
        assert is_restored is True

    def test_full_cycle_back_and_forward(self) -> None:
        """Navigate all the way back and all the way forward."""
        h = TailCommandHistory()
        h.add("a")
        h.add("b")
        h.add("c")

        # Go all the way back
        assert h.navigate_back("draft") == "c"
        assert h.navigate_back("") == "b"
        assert h.navigate_back("") == "a"
        assert h.navigate_back("") == "a"  # clamped

        # Go all the way forward
        text, restored = h.navigate_forward()
        assert text == "b"
        assert restored is False

        text, restored = h.navigate_forward()
        assert text == "c"
        assert restored is False

        text, restored = h.navigate_forward()
        assert text == "draft"
        assert restored is True
        assert h.at_rest

    def test_navigate_back_with_empty_saved_input(self) -> None:
        """Saving empty string as input is valid."""
        h = TailCommandHistory()
        h.add("cmd")

        h.navigate_back("")
        text, is_restored = h.navigate_forward()

        assert text == ""
        assert is_restored is True


# ── add() Validation ─────────────────────────────────────────────────────


class TestAddValidation:
    """Tests for add() recording and validation."""

    def test_empty_string_rejected(self) -> None:
        h = TailCommandHistory()
        h.add("")
        assert len(h) == 0

    def test_whitespace_only_rejected(self) -> None:
        h = TailCommandHistory()
        h.add("   ")
        h.add("\t")
        h.add(" \n ")
        assert len(h) == 0

    def test_consecutive_dedup(self) -> None:
        h = TailCommandHistory()
        h.add("level error")
        h.add("level error")
        assert len(h) == 1

    def test_consecutive_dedup_three_times(self) -> None:
        h = TailCommandHistory()
        h.add("same")
        h.add("same")
        h.add("same")
        assert len(h) == 1
        assert h.entries == ["same"]

    def test_non_consecutive_duplicate_kept(self) -> None:
        h = TailCommandHistory()
        h.add("A")
        h.add("B")
        h.add("A")
        assert len(h) == 3
        assert h.entries == ["A", "B", "A"]

    def test_add_returns_true_on_success(self) -> None:
        h = TailCommandHistory()
        assert h.add("level error") is True

    def test_add_returns_false_on_empty(self) -> None:
        h = TailCommandHistory()
        assert h.add("") is False
        assert h.add("   ") is False

    def test_add_returns_false_on_consecutive_dedup(self) -> None:
        h = TailCommandHistory()
        assert h.add("same") is True
        assert h.add("same") is False
        assert h.add("different") is True
        assert h.add("different") is False

    def test_max_entries_trimming(self) -> None:
        h = TailCommandHistory(max_entries=500)
        for i in range(501):
            h.add(f"cmd-{i}")

        assert len(h) == 500
        # Oldest (cmd-0) should have been dropped
        assert h.entries[0] == "cmd-1"
        assert h.entries[-1] == "cmd-500"

    def test_max_entries_small_limit(self) -> None:
        h = TailCommandHistory(max_entries=3)
        h.add("a")
        h.add("b")
        h.add("c")
        h.add("d")

        assert len(h) == 3
        assert h.entries == ["b", "c", "d"]

    def test_add_resets_navigation_to_at_rest(self) -> None:
        h = TailCommandHistory()
        h.add("first")
        h.add("second")

        h.navigate_back("")  # at-history-entry
        assert not h.at_rest

        h.add("third")
        assert h.at_rest

    def test_add_duplicate_resets_navigation_to_at_rest(self) -> None:
        """Even when dedup skips the add, navigation is still reset."""
        h = TailCommandHistory()
        h.add("cmd")

        h.navigate_back("")
        assert not h.at_rest

        h.add("cmd")  # consecutive dedup, but should still reset
        assert h.at_rest


# ── Properties ────────────────────────────────────────────────────────────


class TestProperties:
    """Tests for at_rest, entries, and __len__."""

    def test_at_rest_true_at_init(self) -> None:
        h = TailCommandHistory()
        assert h.at_rest is True

    def test_at_rest_false_after_navigate_back(self) -> None:
        h = TailCommandHistory()
        h.add("cmd")

        h.navigate_back("")
        assert h.at_rest is False

    def test_at_rest_true_after_reset_navigation(self) -> None:
        h = TailCommandHistory()
        h.add("cmd")

        h.navigate_back("")
        assert not h.at_rest

        h.reset_navigation()
        assert h.at_rest is True

    def test_entries_returns_copy(self) -> None:
        h = TailCommandHistory()
        h.add("cmd")

        entries = h.entries
        entries.append("injected")
        entries.clear()

        assert h.entries == ["cmd"]
        assert len(h) == 1

    def test_len_returns_correct_count(self) -> None:
        h = TailCommandHistory()
        assert len(h) == 0

        h.add("a")
        assert len(h) == 1

        h.add("b")
        assert len(h) == 2

        h.add("c")
        assert len(h) == 3

    def test_entries_oldest_first(self) -> None:
        h = TailCommandHistory()
        h.add("first")
        h.add("second")
        h.add("third")

        assert h.entries == ["first", "second", "third"]


# ── search_prefix ─────────────────────────────────────────────────────────


class TestSearchPrefix:
    """Tests for search_prefix() method."""

    def test_finds_most_recent_match(self) -> None:
        h = TailCommandHistory()
        h.add("level error")
        h.add("level warning")

        result = h.search_prefix("level")

        assert result == "level warning"

    def test_returns_none_for_no_match(self) -> None:
        h = TailCommandHistory()
        h.add("level error")

        result = h.search_prefix("since")

        assert result is None

    def test_returns_none_for_exact_match_only(self) -> None:
        """Entry must be strictly longer than prefix."""
        h = TailCommandHistory()
        h.add("level")

        result = h.search_prefix("level")

        assert result is None

    def test_returns_none_for_empty_history(self) -> None:
        h = TailCommandHistory()

        result = h.search_prefix("anything")

        assert result is None

    def test_case_sensitive_matching(self) -> None:
        h = TailCommandHistory()
        h.add("Level error")

        assert h.search_prefix("Level") == "Level error"
        assert h.search_prefix("level") is None

    def test_skips_shorter_entries(self) -> None:
        """Entries shorter than prefix are not matches."""
        h = TailCommandHistory()
        h.add("le")
        h.add("level error")

        result = h.search_prefix("level")

        assert result == "level error"


class TestSearchPrefixAdditional:
    """Additional tests for search_prefix() method (T018)."""

    def test_case_sensitive_level_prefix(self) -> None:
        """Capital 'L' does not match lowercase 'level' entries (case-sensitive)."""
        h = TailCommandHistory()
        h.add("level error+")
        h.add("level error-")

        result = h.search_prefix("Level error")

        assert result is None

    def test_most_recent_wins(self) -> None:
        """When multiple entries match, the most recently added one is returned."""
        h = TailCommandHistory()
        h.add("level error+")
        h.add("level error-")

        result = h.search_prefix("level error")

        assert result == "level error-"

    def test_empty_prefix_matches_any(self) -> None:
        """Empty prefix matches all entries; most recent is returned."""
        h = TailCommandHistory()
        h.add("abc")
        h.add("def")

        result = h.search_prefix("")

        assert result == "def"

    def test_special_characters_preserved(self) -> None:
        """Entries with regex special characters are matched and returned intact."""
        h = TailCommandHistory()
        h.add("filter /deadlock/i")

        result = h.search_prefix("filter /dead")

        assert result == "filter /deadlock/i"


# ── get_tail_history_path() ───────────────────────────────────────────────


class TestGetTailHistoryPath:
    """Tests for platform-specific path resolution in get_tail_history_path()."""

    def test_macos_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On macOS, path is under ~/Library/Application Support/pgtail/tail_history."""
        import pgtail_py.tail_history as mod

        monkeypatch.setattr(mod.sys, "platform", "darwin")

        path = mod.get_tail_history_path()
        path_str = path.as_posix()

        assert "Library/Application Support/pgtail/tail_history" in path_str

    def test_linux_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On Linux without XDG_DATA_HOME, path is under ~/.local/share/pgtail/tail_history."""
        import pgtail_py.tail_history as mod

        monkeypatch.setattr(mod.sys, "platform", "linux")
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)

        path = mod.get_tail_history_path()
        path_str = path.as_posix()

        assert ".local/share/pgtail/tail_history" in path_str

    def test_linux_xdg_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On Linux with XDG_DATA_HOME set, path is rooted under that directory."""
        import pgtail_py.tail_history as mod

        monkeypatch.setattr(mod.sys, "platform", "linux")
        monkeypatch.setenv("XDG_DATA_HOME", "/custom/data")

        path = mod.get_tail_history_path()
        path_str = path.as_posix()

        assert path_str.startswith("/custom/data/pgtail/tail_history")

    def test_windows_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On Windows with APPDATA set, path is under APPDATA/pgtail/tail_history."""
        import pgtail_py.tail_history as mod

        monkeypatch.setattr(mod.sys, "platform", "win32")
        monkeypatch.setenv("APPDATA", "C:\\Users\\test\\AppData\\Roaming")

        path = mod.get_tail_history_path()
        # Normalize all separators to forward slashes for cross-platform assertion.
        # On non-Windows, Path treats backslashes as literal filename chars, so
        # as_posix() alone won't convert them.
        path_str = str(path).replace("\\", "/")

        assert "pgtail/tail_history" in path_str
        assert "Users/test/AppData/Roaming" in path_str

    def test_windows_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On Windows without APPDATA, path falls back to ~/AppData/Roaming/pgtail/tail_history."""
        import pgtail_py.tail_history as mod

        monkeypatch.setattr(mod.sys, "platform", "win32")
        monkeypatch.delenv("APPDATA", raising=False)

        path = mod.get_tail_history_path()
        path_str = path.as_posix()

        assert "AppData/Roaming/pgtail/tail_history" in path_str


# ── load() ────────────────────────────────────────────────────────────────


class TestLoad:
    """Tests for TailCommandHistory.load() file reading."""

    def test_load_normal(self, tmp_path) -> None:
        """Loading a file with 5 lines produces 5 entries in correct order."""
        history_file = tmp_path / "tail_history"
        commands = ["level error", "since 5m", "filter /panic/", "slow 200", "follow"]
        history_file.write_text("\n".join(commands) + "\n", encoding="utf-8")

        h = TailCommandHistory(history_path=history_file)
        h.load()

        assert h.entries == commands
        assert len(h) == 5

    def test_load_empty_file(self, tmp_path) -> None:
        """Loading an empty file produces empty history without error."""
        history_file = tmp_path / "tail_history"
        history_file.write_text("", encoding="utf-8")

        h = TailCommandHistory(history_path=history_file)
        h.load()

        assert len(h) == 0
        assert h.entries == []

    def test_load_missing_file(self, tmp_path) -> None:
        """Loading a non-existent path produces empty history without error."""
        missing = tmp_path / "nonexistent_tail_history"

        h = TailCommandHistory(history_path=missing)
        h.load()

        assert len(h) == 0
        assert h.entries == []

    def test_load_corrupt_binary(self, tmp_path) -> None:
        """Lines with invalid UTF-8 bytes are loaded with replacement chars, not skipped."""
        history_file = tmp_path / "tail_history"
        # \x80\x81 are invalid UTF-8 continuation bytes when appearing alone
        valid_before = b"level error\n"
        corrupt_line = b"corrupt \x80\x81 line\n"
        valid_after = b"since 10m\n"
        history_file.write_bytes(valid_before + corrupt_line + valid_after)

        h = TailCommandHistory(history_path=history_file)
        h.load()

        # All 3 lines loaded (corrupt bytes replaced with U+FFFD, not dropped)
        assert len(h) == 3
        assert h.entries[0] == "level error"
        assert h.entries[2] == "since 10m"
        assert "\ufffd" in h.entries[1]

    def test_load_oversized_lines(self, tmp_path) -> None:
        """Lines exceeding 4096 bytes are skipped; shorter lines are kept."""
        history_file = tmp_path / "tail_history"
        oversized = "x" * 5000  # 5000 bytes in UTF-8 > 4096 limit
        normal = "level warning"
        history_file.write_text(f"{oversized}\n{normal}\n", encoding="utf-8")

        h = TailCommandHistory(history_path=history_file)
        h.load()

        assert len(h) == 1
        assert h.entries[0] == normal

    def test_load_max_entries(self, tmp_path) -> None:
        """When file has more lines than max_entries, only the last max_entries are kept."""
        history_file = tmp_path / "tail_history"
        all_commands = [f"cmd-{i}" for i in range(1000)]
        history_file.write_text("\n".join(all_commands) + "\n", encoding="utf-8")

        h = TailCommandHistory(max_entries=500, history_path=history_file)
        h.load()

        assert len(h) == 500
        # Should have the last 500 commands (cmd-500 through cmd-999)
        assert h.entries[0] == "cmd-500"
        assert h.entries[-1] == "cmd-999"

    def test_load_resets_navigation(self, tmp_path) -> None:
        """load() resets navigation to at-rest regardless of prior navigation state."""
        history_file = tmp_path / "tail_history"
        history_file.write_text("cmd-a\ncmd-b\n", encoding="utf-8")

        h = TailCommandHistory(history_path=history_file)
        h.load()

        # Navigate away from at-rest
        h.navigate_back("draft")
        assert not h.at_rest

        # A second load() must reset navigation back to at-rest
        h.load()
        assert h.at_rest


# ── save() ────────────────────────────────────────────────────────────────


class TestSave:
    """Tests for TailCommandHistory.save() file writing."""

    def test_save_normal(self, tmp_path) -> None:
        """Saving 3 commands writes 3 lines in correct order."""
        history_file = tmp_path / "tail_history"
        h = TailCommandHistory(history_path=history_file)

        h.save("level error")
        h.save("since 5m")
        h.save("follow")

        lines = history_file.read_text(encoding="utf-8").splitlines()
        assert lines == ["level error", "since 5m", "follow"]

    def test_save_creates_dir(self, tmp_path) -> None:
        """save() creates missing parent directories before writing the file."""
        history_file = tmp_path / "subdir" / "tail_history"
        assert not history_file.parent.exists()

        h = TailCommandHistory(history_path=history_file)
        h.save("level error")

        assert history_file.exists()
        lines = history_file.read_text(encoding="utf-8").splitlines()
        assert lines == ["level error"]

    def test_save_appends(self, tmp_path) -> None:
        """save() appends to an existing file rather than overwriting it."""
        history_file = tmp_path / "tail_history"
        history_file.write_text("existing-a\nexisting-b\n", encoding="utf-8")

        h = TailCommandHistory(history_path=history_file)
        h.save("new-command")

        lines = history_file.read_text(encoding="utf-8").splitlines()
        assert lines == ["existing-a", "existing-b", "new-command"]

    def test_save_none_path(self) -> None:
        """When history_path is None, save() does nothing and raises no error."""
        h = TailCommandHistory(history_path=None)
        # Must complete silently
        h.save("level error")


# ── compact() ─────────────────────────────────────────────────────────────


class TestCompact:
    """Tests for TailCommandHistory.compact() file rewriting."""

    def test_compact_under_threshold(self, tmp_path) -> None:
        """Files at or under compact_threshold lines are not rewritten."""
        history_file = tmp_path / "tail_history"
        # max_entries=500 → compact_threshold=1000; write 500 lines (well under threshold)
        lines = [f"cmd-{i}" for i in range(500)]
        history_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        original_mtime = history_file.stat().st_mtime

        h = TailCommandHistory(max_entries=500, history_path=history_file)
        h.compact()

        assert history_file.stat().st_mtime == original_mtime
        reread = history_file.read_text(encoding="utf-8").splitlines()
        assert reread == lines

    def test_compact_over_threshold(self, tmp_path) -> None:
        """Files over compact_threshold are rewritten with only the last max_entries lines."""
        history_file = tmp_path / "tail_history"
        # max_entries=500 → compact_threshold=1000; write 1500 lines (over threshold)
        all_lines = [f"cmd-{i}" for i in range(1500)]
        history_file.write_text("\n".join(all_lines) + "\n", encoding="utf-8")

        h = TailCommandHistory(max_entries=500, history_path=history_file)
        h.compact()

        reread = history_file.read_text(encoding="utf-8").splitlines()
        assert len(reread) == 500
        assert reread[0] == "cmd-1000"
        assert reread[-1] == "cmd-1499"

    def test_compact_missing_file(self, tmp_path) -> None:
        """compact() on a non-existent file does nothing and raises no error."""
        missing = tmp_path / "nonexistent_tail_history"
        h = TailCommandHistory(history_path=missing)
        h.compact()  # Must not raise

    def test_compact_none_path(self) -> None:
        """compact() with history_path=None does nothing and raises no error."""
        h = TailCommandHistory(history_path=None)
        h.compact()  # Must not raise


# ── Persistence round-trip ────────────────────────────────────────────────


class TestPersistenceRoundTrip:
    """Integration tests verifying save() and load() work together correctly."""

    def test_save_then_load(self, tmp_path) -> None:
        """Commands saved via save() are fully recovered by load() in a new instance."""
        history_file = tmp_path / "tail_history"
        commands = ["level error", "since 5m", "follow"]

        # First instance: save commands to disk
        h1 = TailCommandHistory(history_path=history_file)
        for cmd in commands:
            h1.save(cmd)

        # Second instance: load from disk and verify
        h2 = TailCommandHistory(history_path=history_file)
        h2.load()

        assert h2.entries == commands

    def test_full_persistence_integration(self, tmp_path) -> None:
        """Full workflow: add + save in one session, load in another — entries match."""
        history_file = tmp_path / "tail_history"
        submitted = ["level warning", "filter /deadlock/i", "slow 500", "errors"]

        # First session: record and persist each command
        h1 = TailCommandHistory(history_path=history_file)
        for cmd in submitted:
            h1.add(cmd)
            h1.save(cmd)

        # Second session: load from disk
        h2 = TailCommandHistory(history_path=history_file)
        h2.load()

        assert h2.entries == submitted
        assert len(h2) == len(submitted)
        assert h2.at_rest

    def test_consecutive_dedup_not_persisted(self, tmp_path) -> None:
        """Consecutive duplicates rejected by add() must not appear on disk.

        Regression test: previously save() was called unconditionally after
        add(), writing duplicate lines even when add() rejected the command.
        After restart, load() would see duplicate lines.
        """
        history_file = tmp_path / "tail_history"

        # Session 1: enter same command three times in a row
        h1 = TailCommandHistory(history_path=history_file)
        for cmd in ["level error", "level error", "level error"]:
            if h1.add(cmd):
                h1.save(cmd)

        # Only one line should be on disk
        lines = history_file.read_text(encoding="utf-8").splitlines()
        assert lines == ["level error"]

        # Session 2: load and verify no duplicates
        h2 = TailCommandHistory(history_path=history_file)
        h2.load()
        assert h2.entries == ["level error"]
