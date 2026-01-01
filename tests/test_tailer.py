"""Tests for pgtail_py/tailer.py - LogTailer class."""

from __future__ import annotations

import os
import tempfile
import threading
import time
from pathlib import Path

import pytest

from pgtail_py.filter import LogLevel
from pgtail_py.format_detector import LogFormat
from pgtail_py.tailer import DEFAULT_BUFFER_MAX_SIZE, LogTailer


class TestLogTailerBasics:
    """Basic LogTailer functionality tests."""

    def test_tailer_starts_and_stops(self, tmp_path: Path) -> None:
        """Tailer can be started and stopped."""
        log_file = tmp_path / "test.log"
        log_file.write_text("2024-01-15 10:00:00.000 UTC [12345] LOG:  test message\n")

        tailer = LogTailer(log_file)
        assert not tailer.is_running

        tailer.start()
        assert tailer.is_running

        tailer.stop()
        assert not tailer.is_running

    def test_tailer_reads_new_lines(self, tmp_path: Path) -> None:
        """Tailer reads new lines as they are written."""
        log_file = tmp_path / "test.log"
        log_file.write_text("2024-01-15 10:00:00.000 UTC [12345] LOG:  initial\n")

        tailer = LogTailer(log_file, poll_interval=0.01)
        tailer.start()

        try:
            # Wait for initial read
            time.sleep(0.05)

            # Write new line
            with open(log_file, "a") as f:
                f.write("2024-01-15 10:00:01.000 UTC [12345] LOG:  new message\n")

            # Should see the new line
            time.sleep(0.05)
            entry = tailer.get_entry(timeout=0.1)
            assert entry is not None
            assert "new message" in entry.message
        finally:
            tailer.stop()

    def test_log_path_property(self, tmp_path: Path) -> None:
        """Tailer exposes the current log path."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        tailer = LogTailer(log_file)
        assert tailer.log_path == log_file


class TestLogTailerRotation:
    """Tests for log file rotation handling."""

    def test_detects_file_truncation(self, tmp_path: Path) -> None:
        """Tailer resets position when file is truncated."""
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "2024-01-15 10:00:00.000 UTC [12345] LOG:  message 1\n"
            "2024-01-15 10:00:01.000 UTC [12345] LOG:  message 2\n"
        )

        tailer = LogTailer(log_file, poll_interval=0.01)
        tailer.start()

        try:
            # Wait for initial read
            time.sleep(0.05)

            # Truncate the file (simulating log rotation with copy-truncate)
            with open(log_file, "w") as f:
                f.write("2024-01-15 10:00:02.000 UTC [12345] LOG:  after truncate\n")

            # Tailer should detect truncation and read new content
            time.sleep(0.05)
            entry = tailer.get_entry(timeout=0.1)
            assert entry is not None
            assert "after truncate" in entry.message
        finally:
            tailer.stop()

    def test_detects_file_recreation(self, tmp_path: Path) -> None:
        """Tailer resets position when file is deleted and recreated."""
        log_file = tmp_path / "test.log"
        log_file.write_text("2024-01-15 10:00:00.000 UTC [12345] LOG:  original\n")

        tailer = LogTailer(log_file, poll_interval=0.01)
        tailer.start()

        try:
            # Wait for initial read
            time.sleep(0.05)

            # Delete and recreate the file (simulating log rotation)
            os.unlink(log_file)
            log_file.write_text("2024-01-15 10:00:01.000 UTC [12345] LOG:  new file\n")

            # Tailer should detect new file and read from beginning
            time.sleep(0.1)
            entry = tailer.get_entry(timeout=0.1)
            assert entry is not None
            assert "new file" in entry.message
        finally:
            tailer.stop()


class TestLogTailerBuffer:
    """Tests for buffer functionality."""

    def test_buffer_stores_entries(self, tmp_path: Path) -> None:
        """Buffer stores entries for later retrieval."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        tailer = LogTailer(log_file, poll_interval=0.01)
        tailer.start()

        try:
            # Wait for initial read
            time.sleep(0.05)

            # Write entries after tailer started
            with open(log_file, "a") as f:
                f.write("2024-01-15 10:00:00.000 UTC [12345] LOG:  message 1\n")
                f.write("2024-01-15 10:00:01.000 UTC [12345] LOG:  message 2\n")
                f.write("2024-01-15 10:00:02.000 UTC [12345] LOG:  message 3\n")

            time.sleep(0.1)

            # Buffer should contain entries
            buffer = tailer.get_buffer()
            assert len(buffer) == 3
            assert tailer.buffer_size == 3
        finally:
            tailer.stop()

    def test_buffer_respects_max_size(self, tmp_path: Path) -> None:
        """Buffer discards oldest entries when max size is reached."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        max_size = 5
        tailer = LogTailer(log_file, poll_interval=0.01, buffer_max_size=max_size)
        tailer.start()

        try:
            time.sleep(0.05)

            # Write more entries than buffer size
            with open(log_file, "a") as f:
                for i in range(10):
                    f.write(f"2024-01-15 10:00:{i:02d}.000 UTC [12345] LOG:  message {i}\n")

            time.sleep(0.1)

            buffer = tailer.get_buffer()
            assert len(buffer) == max_size
            # Oldest entries should be discarded, newest kept
            assert "message 5" in buffer[0].message
            assert "message 9" in buffer[-1].message
        finally:
            tailer.stop()

    def test_default_buffer_max_size(self, tmp_path: Path) -> None:
        """Buffer defaults to DEFAULT_BUFFER_MAX_SIZE."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        tailer = LogTailer(log_file)
        assert tailer.buffer_max_size == DEFAULT_BUFFER_MAX_SIZE

    def test_clear_buffer(self, tmp_path: Path) -> None:
        """Buffer can be cleared."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        tailer = LogTailer(log_file, poll_interval=0.01)
        tailer.start()

        try:
            time.sleep(0.05)

            # Write an entry
            with open(log_file, "a") as f:
                f.write("2024-01-15 10:00:00.000 UTC [12345] LOG:  message\n")

            time.sleep(0.1)
            assert tailer.buffer_size > 0

            tailer.clear_buffer()
            assert tailer.buffer_size == 0
        finally:
            tailer.stop()


class TestLogTailerFilters:
    """Tests for filter functionality."""

    def test_level_filter(self, tmp_path: Path) -> None:
        """Tailer applies level filter correctly."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        tailer = LogTailer(
            log_file, active_levels={LogLevel.ERROR}, poll_interval=0.01
        )
        tailer.start()

        try:
            time.sleep(0.05)

            # Write entries after tailer started
            with open(log_file, "a") as f:
                f.write("2024-01-15 10:00:00.000 UTC [12345] ERROR:  error message\n")
                f.write("2024-01-15 10:00:01.000 UTC [12345] LOG:  log message\n")
                f.write("2024-01-15 10:00:02.000 UTC [12345] WARNING:  warning message\n")

            time.sleep(0.1)

            # Should only have ERROR entries
            buffer = tailer.get_buffer()
            assert len(buffer) == 1
            assert buffer[0].level == LogLevel.ERROR
        finally:
            tailer.stop()

    def test_update_levels_filter(self, tmp_path: Path) -> None:
        """Level filter can be updated dynamically."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        tailer = LogTailer(log_file, active_levels={LogLevel.ERROR}, poll_interval=0.01)
        tailer.start()

        try:
            # Update to include WARNING
            tailer.update_levels({LogLevel.ERROR, LogLevel.WARNING})

            # Write entries
            with open(log_file, "a") as f:
                f.write("2024-01-15 10:00:00.000 UTC [12345] WARNING:  warning\n")
                f.write("2024-01-15 10:00:01.000 UTC [12345] LOG:  log\n")

            time.sleep(0.1)

            # Should have WARNING but not LOG
            buffer = tailer.get_buffer()
            assert len(buffer) == 1
            assert buffer[0].level == LogLevel.WARNING
        finally:
            tailer.stop()


class TestLogTailerFormat:
    """Tests for format detection."""

    def test_detects_text_format(self, tmp_path: Path) -> None:
        """Tailer detects TEXT format."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        tailer = LogTailer(log_file, poll_interval=0.01)
        tailer.start()

        try:
            time.sleep(0.05)

            # Write entry after tailer started
            with open(log_file, "a") as f:
                f.write("2024-01-15 10:00:00.000 UTC [12345] LOG:  text format\n")

            time.sleep(0.1)
            assert tailer.format == LogFormat.TEXT
        finally:
            tailer.stop()

    def test_format_callback(self, tmp_path: Path) -> None:
        """Format callback is called when format is detected."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        detected_formats: list[LogFormat] = []

        tailer = LogTailer(log_file, poll_interval=0.01)
        tailer.set_format_callback(lambda fmt: detected_formats.append(fmt))
        tailer.start()

        try:
            time.sleep(0.05)

            # Write entry after tailer started
            with open(log_file, "a") as f:
                f.write("2024-01-15 10:00:00.000 UTC [12345] LOG:  message\n")

            time.sleep(0.1)
            assert len(detected_formats) == 1
            assert detected_formats[0] == LogFormat.TEXT
        finally:
            tailer.stop()


class TestLogTailerCallback:
    """Tests for on_entry callback."""

    def test_on_entry_called_before_filtering(self, tmp_path: Path) -> None:
        """on_entry callback is called for all entries before filtering."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        all_entries: list = []

        tailer = LogTailer(
            log_file,
            active_levels={LogLevel.ERROR},  # Filter out LOG
            poll_interval=0.01,
            on_entry=lambda e: all_entries.append(e),
        )
        tailer.start()

        try:
            time.sleep(0.05)

            # Write entries after tailer started
            with open(log_file, "a") as f:
                f.write("2024-01-15 10:00:00.000 UTC [12345] ERROR:  error\n")
                f.write("2024-01-15 10:00:01.000 UTC [12345] LOG:  log\n")

            time.sleep(0.1)

            # on_entry should see all entries
            assert len(all_entries) == 2

            # But buffer should only have filtered entries
            assert tailer.buffer_size == 1
        finally:
            tailer.stop()


class TestLogTailerEdgeCases:
    """Edge case tests."""

    def test_empty_file(self, tmp_path: Path) -> None:
        """Tailer handles empty files gracefully."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        tailer = LogTailer(log_file, poll_interval=0.01)
        tailer.start()

        try:
            time.sleep(0.05)
            assert tailer.buffer_size == 0
            assert tailer.get_entry(timeout=0.01) is None
        finally:
            tailer.stop()

    def test_file_with_blank_lines(self, tmp_path: Path) -> None:
        """Tailer skips blank lines."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        tailer = LogTailer(log_file, poll_interval=0.01)
        tailer.start()

        try:
            time.sleep(0.05)

            # Write entries with blank lines
            with open(log_file, "a") as f:
                f.write("2024-01-15 10:00:00.000 UTC [12345] LOG:  message 1\n")
                f.write("\n")
                f.write("   \n")
                f.write("2024-01-15 10:00:01.000 UTC [12345] LOG:  message 2\n")

            time.sleep(0.1)

            # Should only have non-blank lines
            buffer = tailer.get_buffer()
            assert len(buffer) == 2
        finally:
            tailer.stop()

    def test_multiple_start_calls(self, tmp_path: Path) -> None:
        """Calling start() multiple times is safe."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        tailer = LogTailer(log_file)
        tailer.start()
        tailer.start()  # Should be no-op
        tailer.start()  # Should be no-op

        assert tailer.is_running
        tailer.stop()
        assert not tailer.is_running

    def test_stop_without_start(self, tmp_path: Path) -> None:
        """Calling stop() without start() is safe."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        tailer = LogTailer(log_file)
        tailer.stop()  # Should not raise
        assert not tailer.is_running
