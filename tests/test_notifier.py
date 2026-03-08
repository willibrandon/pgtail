"""Tests for the notification system.

Tier 1: Pure logic tests (all platforms)
Tier 2: Real platform tests (platform-specific, real COM/osascript/notify-send)
Tier 3: Integration tests (NotificationManager → Notifier flow)
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from pgtail_py._toast_xml import (
    EXPIRY_SECONDS,
    build_toast_xml,
    escape_xml,
)
from pgtail_py.filter import LogLevel
from pgtail_py.notifier import NoOpNotifier, create_notifier
from pgtail_py.notify import (
    NotificationConfig,
    NotificationManager,
    NotificationRule,
    _level_to_severity,
    _make_tag,
)

# ===================================================================
# Tier 1: Pure logic tests — all platforms, no COM
# ===================================================================


class TestEscapeXml:
    """XML escaping for toast content."""

    def test_ampersand(self):
        assert escape_xml("A & B") == "A &amp; B"

    def test_less_than(self):
        assert escape_xml("a < b") == "a &lt; b"

    def test_greater_than(self):
        assert escape_xml("a > b") == "a &gt; b"

    def test_double_quote(self):
        assert escape_xml('say "hello"') == "say &quot;hello&quot;"

    def test_single_quote(self):
        assert escape_xml("it's") == "it&apos;s"

    def test_combined(self):
        assert escape_xml('<a & "b">') == "&lt;a &amp; &quot;b&quot;&gt;"

    def test_no_escape_needed(self):
        assert escape_xml("plain text 123") == "plain text 123"

    def test_empty_string(self):
        assert escape_xml("") == ""


class TestBuildToastXml:
    """Toast XML builder with severity templates."""

    def test_info_severity(self):
        xml = build_toast_xml("Title", "Body", severity="info")
        assert 'duration="short"' in xml
        assert "scenario" not in xml
        assert 'src="ms-winsoundevent:Notification.Default"' in xml
        assert "loop" not in xml
        assert "attribution" not in xml

    def test_warning_severity(self):
        xml = build_toast_xml("Title", "Body", severity="warning")
        assert 'duration="short"' in xml
        assert "scenario" not in xml
        assert 'src="ms-winsoundevent:Notification.Default"' in xml
        assert "loop" not in xml
        assert 'placement="attribution">Warning<' in xml

    def test_error_severity(self):
        xml = build_toast_xml("Title", "Body", severity="error")
        assert 'duration="long"' in xml
        assert "scenario" not in xml
        assert 'src="ms-winsoundevent:Notification.Default"' in xml
        assert "loop" not in xml
        assert 'placement="attribution">Error<' in xml

    def test_critical_severity(self):
        xml = build_toast_xml("Title", "Body", severity="critical")
        assert 'duration="long"' in xml
        assert 'scenario="alarm"' in xml
        assert 'src="ms-winsoundevent:Notification.Looping.Alarm"' in xml
        assert 'loop="true"' in xml
        assert 'placement="attribution">Critical<' in xml

    def test_title_and_body_present(self):
        xml = build_toast_xml("My Title", "My Body")
        assert "<text>My Title</text>" in xml
        assert "<text>My Body</text>" in xml

    def test_subtitle_included(self):
        xml = build_toast_xml("Title", "Body", subtitle="Sub")
        assert "<text>Sub</text>" in xml

    def test_xml_escaping_in_content(self):
        xml = build_toast_xml("A & B", "<script>alert('x')</script>")
        assert "A &amp; B" in xml
        assert "&lt;script&gt;" in xml
        assert "&apos;x&apos;" in xml

    def test_unknown_severity_defaults_to_info(self):
        xml = build_toast_xml("Title", "Body", severity="unknown")
        assert 'duration="short"' in xml

    def test_toastgeneric_template(self):
        xml = build_toast_xml("Title", "Body")
        assert 'template="ToastGeneric"' in xml


class TestExpirationDefaults:
    """Expiration time configuration per severity."""

    def test_info_expiry(self):
        assert EXPIRY_SECONDS["info"] == 120

    def test_warning_expiry(self):
        assert EXPIRY_SECONDS["warning"] == 600

    def test_error_expiry(self):
        assert EXPIRY_SECONDS["error"] == 1800

    def test_critical_no_expiry(self):
        assert EXPIRY_SECONDS["critical"] is None


class TestLevelToSeverity:
    """LogLevel → severity string mapping."""

    def test_panic(self):
        assert _level_to_severity(LogLevel.PANIC) == "critical"

    def test_fatal(self):
        assert _level_to_severity(LogLevel.FATAL) == "critical"

    def test_error(self):
        assert _level_to_severity(LogLevel.ERROR) == "error"

    def test_warning(self):
        assert _level_to_severity(LogLevel.WARNING) == "warning"

    def test_notice(self):
        assert _level_to_severity(LogLevel.NOTICE) == "info"

    def test_log(self):
        assert _level_to_severity(LogLevel.LOG) == "info"

    def test_info(self):
        assert _level_to_severity(LogLevel.INFO) == "info"

    def test_debug(self):
        assert _level_to_severity(LogLevel.DEBUG1) == "info"

    def test_none(self):
        assert _level_to_severity(None) == "info"


class TestMakeTag:
    """Tag generation from rule category and entry."""

    @dataclass
    class _FakeEntry:
        level: LogLevel | None = None
        message: str | None = None

    def test_level_alert_tag(self):
        entry = self._FakeEntry(level=LogLevel.ERROR, message="something")
        tag = _make_tag("Level Alert", entry)
        assert tag == "lvl:ERROR"
        assert len(tag) <= 16

    def test_pattern_match_tag(self):
        entry = self._FakeEntry(level=LogLevel.ERROR, message="deadlock detected")
        tag = _make_tag("Pattern Match", entry)
        assert tag.startswith("pat:")
        assert len(tag) <= 16

    def test_long_level_name_truncated(self):
        # All LogLevel names are short, but test the truncation logic
        entry = self._FakeEntry(level=LogLevel.WARNING, message="x")
        tag = _make_tag("Level Alert", entry)
        assert len(tag) <= 16

    def test_generic_category_truncated(self):
        entry = self._FakeEntry(level=None, message="")
        tag = _make_tag("Some Very Long Category Name Here", entry)
        assert len(tag) <= 16


# ===================================================================
# Windows-only: GUID and HSTRING tests
# ===================================================================


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
class TestGUID:
    """GUID parsing from string."""

    def test_round_trip(self):
        from pgtail_py._winrt import GUID

        iid_str = "{50AC103F-D235-4598-BBEF-98FE4D1A3AD4}"
        guid = GUID.from_string(iid_str)
        assert guid.Data1 == 0x50AC103F
        assert guid.Data2 == 0xD235
        assert guid.Data3 == 0x4598
        assert repr(guid) == iid_str

    def test_lowercase_input(self):
        from pgtail_py._winrt import GUID

        guid = GUID.from_string("{50ac103f-d235-4598-bbef-98fe4d1a3ad4}")
        assert guid.Data1 == 0x50AC103F


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
class TestHSTRING:
    """HSTRING creation and deletion."""

    def test_create_delete(self):
        from pgtail_py._winrt import hstring

        with hstring("hello world") as hs:
            assert hs is not None
            assert hs.value is not None  # type: ignore[union-attr]

    def test_empty_string(self):
        from pgtail_py._winrt import hstring

        with hstring("") as _hs:
            # Empty HSTRING may be None, which is valid
            pass  # Just ensure no exception


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
class TestTicksConversion:
    """FILETIME ticks conversion formula."""

    def test_known_timestamp(self):
        from pgtail_py._winrt import unix_to_ticks

        # Unix epoch (1970-01-01T00:00:00Z) = 116444736000000000 ticks
        ticks = unix_to_ticks(0.0)
        assert ticks == 116444736000000000

    def test_positive_timestamp(self):
        from pgtail_py._winrt import unix_to_ticks

        # 2000-01-01T00:00:00Z = Unix 946684800
        ticks = unix_to_ticks(946684800.0)
        expected = int((946684800 + 11644473600) * 10_000_000)
        assert ticks == expected


# ===================================================================
# Tier 2: Real platform tests
# ===================================================================


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
class TestWindowsComInit:
    """Real COM initialization on Windows."""

    def test_ro_initialize_succeeds(self):
        from pgtail_py._winrt import ensure_com_initialized

        ensure_com_initialized()  # Should not raise

    def test_idempotent(self):
        from pgtail_py._winrt import ensure_com_initialized

        ensure_com_initialized()
        ensure_com_initialized()  # Second call should be no-op

    def test_activation_factory_resolves(self):
        from pgtail_py._winrt import (
            IID_IToastNotificationManagerStatics,
            ensure_com_initialized,
            get_activation_factory,
        )

        ensure_com_initialized()
        factory = get_activation_factory(
            "Windows.UI.Notifications.ToastNotificationManager",
            IID_IToastNotificationManagerStatics,
        )
        assert factory.value is not None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
class TestWindowsShortcut:
    """Real shortcut creation on Windows."""

    def test_ensure_shortcut(self):
        import os

        from pgtail_py._win_shortcut import ensure_shortcut

        result = ensure_shortcut()
        assert result is True

        appdata = os.environ.get("APPDATA", "")
        lnk_path = os.path.join(
            appdata, "Microsoft", "Windows", "Start Menu", "Programs", "pgtail.lnk"
        )
        assert os.path.exists(lnk_path)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
class TestWindowsNotifier:
    """Real toast notification tests on Windows."""

    def test_is_available(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        assert notifier.is_available() is True

    def test_platform_info(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        assert notifier.get_platform_info() == "Windows (WinRT Toast)"

    def test_send_info(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        result = notifier.send("Test INFO", "Info test notification", severity="info")
        assert result is True

    def test_send_warning(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        result = notifier.send("Test WARNING", "Warning notification", severity="warning")
        assert result is True

    def test_send_error(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        result = notifier.send("Test ERROR", "Error notification", severity="error")
        assert result is True

    def test_send_critical(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        result = notifier.send("Test CRITICAL", "Critical notification", severity="critical")
        assert result is True

    def test_send_with_tag(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        result = notifier.send("Tagged", "Tag test", tag="test-tag")
        assert result is True

    def test_send_with_subtitle(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        result = notifier.send("Subtitled", "Body", subtitle="MySub")
        assert result is True

    def test_send_xml_special_chars(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        result = notifier.send(
            "A & B",
            '<script>alert("xss")</script>',
            severity="info",
        )
        assert result is True

    def test_tag_truncation(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        long_tag = "a" * 30
        result = notifier.send("Truncation", "Tag truncation test", tag=long_tag)
        assert result is True

    def test_dismiss_doesnt_raise(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        # Send with tag, then dismiss
        notifier.send("Dismiss Test", "Will be dismissed", tag="dismiss-test")
        time.sleep(0.5)
        result = notifier.dismiss("dismiss-test")
        assert result is True

    def test_dismiss_nonexistent_tag(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        # Dismissing a tag that doesn't exist should not raise
        result = notifier.dismiss("nonexistent-tag")
        # May return True or False depending on Windows behavior
        assert isinstance(result, bool)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
class TestWindowsFailureTracking:
    """Consecutive failure tracking on Windows."""

    def test_consecutive_failures_disable(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        # Simulate consecutive failures
        notifier._consecutive_failures = 5
        notifier._disabled_until = time.time() + 60

        result = notifier.send("Test", "Should be blocked")
        assert result is False

    def test_cooldown_expiry_resets(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        # Set expired cooldown
        notifier._consecutive_failures = 5
        notifier._disabled_until = time.time() - 1  # Already expired

        result = notifier.send("Test", "Should succeed after cooldown")
        assert result is True
        assert notifier._consecutive_failures == 0
        assert notifier._disabled_until is None

    def test_permanent_failure_disables(self):
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        # Manually test the _available flag
        notifier._available = False
        result = notifier.send("Test", "Should fail")
        assert result is False


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only")
class TestMacOSNotifier:
    """Real macOS notification tests."""

    def test_is_available(self):
        from pgtail_py.notifier_unix import MacOSNotifier

        notifier = MacOSNotifier()
        # osascript should be available on macOS
        assert notifier.is_available() is True

    def test_send_basic(self):
        from pgtail_py.notifier_unix import MacOSNotifier

        notifier = MacOSNotifier()
        if notifier.is_available():
            result = notifier.send("Test", "macOS notification test")
            assert result is True

    def test_new_params_accepted(self):
        from pgtail_py.notifier_unix import MacOSNotifier

        notifier = MacOSNotifier()
        if notifier.is_available():
            result = notifier.send(
                "Test", "Body", severity="error", tag="test", suppress_popup=True
            )
            assert result is True

    def test_dismiss_returns_false(self):
        from pgtail_py.notifier_unix import MacOSNotifier

        notifier = MacOSNotifier()
        assert notifier.dismiss("tag") is False


@pytest.mark.skipif(sys.platform != "linux", reason="Linux-only")
class TestLinuxNotifier:
    """Real Linux notification tests."""

    def test_new_params_accepted(self):
        from pgtail_py.notifier_unix import LinuxNotifier

        notifier = LinuxNotifier()
        if notifier.is_available():
            result = notifier.send(
                "Test", "Body", severity="error", tag="test", suppress_popup=True
            )
            assert result is True

    def test_dismiss_returns_false(self):
        from pgtail_py.notifier_unix import LinuxNotifier

        notifier = LinuxNotifier()
        assert notifier.dismiss("tag") is False


# ===================================================================
# Tier 3: Integration tests
# ===================================================================


class _FakeLogEntry:
    """Minimal LogEntry stand-in for integration tests."""

    def __init__(
        self,
        level: LogLevel = LogLevel.ERROR,
        message: str = "test error message",
        database_name: str | None = None,
    ):
        self.level = level
        self.message = message
        self.raw = message
        self.database_name = database_name
        self.timestamp = None
        self.pid = None


class TestNotificationManagerIntegration:
    """Integration tests for NotificationManager → Notifier flow."""

    def _make_manager(self) -> tuple[NotificationManager, MagicMock]:
        mock_notifier = MagicMock()
        mock_notifier.send.return_value = True
        mock_notifier.is_available.return_value = True

        config = NotificationConfig(enabled=True)
        config.add_rule(
            NotificationRule.level_rule(
                {
                    LogLevel.ERROR,
                    LogLevel.FATAL,
                    LogLevel.PANIC,
                }
            )
        )

        manager = NotificationManager(notifier=mock_notifier, config=config)
        return manager, mock_notifier

    def test_fatal_sends_critical_severity(self):
        manager, mock = self._make_manager()
        entry = _FakeLogEntry(level=LogLevel.FATAL)
        manager.check(entry)

        mock.send.assert_called_once()
        call_kwargs = mock.send.call_args
        assert call_kwargs.kwargs["severity"] == "critical"

    def test_error_sends_error_severity(self):
        manager, mock = self._make_manager()
        entry = _FakeLogEntry(level=LogLevel.ERROR)
        manager.check(entry)

        mock.send.assert_called_once()
        assert mock.send.call_args.kwargs["severity"] == "error"

    def test_panic_sends_critical_severity(self):
        manager, mock = self._make_manager()
        config = NotificationConfig(enabled=True)
        config.add_rule(NotificationRule.level_rule({LogLevel.PANIC}))
        manager.config = config

        entry = _FakeLogEntry(level=LogLevel.PANIC)
        manager.check(entry)

        mock.send.assert_called_once()
        assert mock.send.call_args.kwargs["severity"] == "critical"

    def test_tag_generated(self):
        manager, mock = self._make_manager()
        entry = _FakeLogEntry(level=LogLevel.ERROR)
        manager.check(entry)

        mock.send.assert_called_once()
        tag = mock.send.call_args.kwargs["tag"]
        assert tag is not None
        assert len(tag) <= 16
        assert tag == "lvl:ERROR"

    def test_pattern_rule_tag(self):
        mock_notifier = MagicMock()
        mock_notifier.send.return_value = True
        mock_notifier.is_available.return_value = True

        config = NotificationConfig(enabled=True)
        config.add_rule(NotificationRule.pattern_rule("deadlock"))

        manager = NotificationManager(notifier=mock_notifier, config=config)
        entry = _FakeLogEntry(level=LogLevel.ERROR, message="deadlock detected")
        manager.check(entry)

        mock_notifier.send.assert_called_once()
        tag = mock_notifier.send.call_args.kwargs["tag"]
        assert tag.startswith("pat:")

    def test_disabled_config_no_send(self):
        manager, mock = self._make_manager()
        manager.config.enabled = False
        entry = _FakeLogEntry(level=LogLevel.ERROR)
        result = manager.check(entry)

        assert result is False
        mock.send.assert_not_called()

    def test_non_matching_level_no_send(self):
        manager, mock = self._make_manager()
        entry = _FakeLogEntry(level=LogLevel.INFO)
        result = manager.check(entry)

        assert result is False
        mock.send.assert_not_called()

    def test_send_test_bypasses_rate_limit(self):
        manager, mock = self._make_manager()
        # First send to trigger rate limiter
        entry = _FakeLogEntry(level=LogLevel.ERROR)
        manager.check(entry)

        # send_test should still work
        manager.send_test()
        assert mock.send.call_count == 2


class TestNoOpNotifier:
    """NoOpNotifier accepts new params without error."""

    def test_send_new_params(self):
        n = NoOpNotifier()
        result = n.send("title", "body", severity="error", tag="test", suppress_popup=True)
        assert result is False

    def test_dismiss(self):
        n = NoOpNotifier()
        assert n.dismiss("tag") is False

    def test_not_available(self):
        n = NoOpNotifier()
        assert n.is_available() is False


class TestCreateNotifier:
    """Factory creates correct notifier for platform."""

    def test_creates_notifier(self):
        notifier = create_notifier()
        # Should return something, regardless of platform
        assert notifier is not None
        assert hasattr(notifier, "send")
        assert hasattr(notifier, "dismiss")
        assert hasattr(notifier, "is_available")


# ===================================================================
# Phase 7.4: Mock seam tests — _winrt module replacement
# ===================================================================


class _ComRecorder:
    """Records all COM calls made through the _winrt mock seam."""

    def __init__(self):
        self.calls: list[tuple] = []  # (function_name, *args)
        self.vcalls: list[tuple] = []  # (ptr, slot, *args)
        self._ptr_counter = 1000

    def next_ptr(self) -> int:
        self._ptr_counter += 1
        return self._ptr_counter


@pytest.fixture
def com_recorder():
    return _ComRecorder()


@pytest.fixture
def mock_winrt_notifier(com_recorder):
    """Create a WindowsNotifier with the _winrt module mocked."""
    import contextlib
    import ctypes
    from contextlib import contextmanager

    recorder = com_recorder

    def fake_ensure_com():
        recorder.calls.append(("ensure_com_initialized",))

    def fake_get_factory(class_name, iid):
        ptr = ctypes.c_void_p(recorder.next_ptr())
        recorder.calls.append(("get_activation_factory", class_name, repr(iid)))
        return ptr

    def fake_activate(class_name):
        ptr = ctypes.c_void_p(recorder.next_ptr())
        recorder.calls.append(("activate_instance", class_name))
        return ptr

    def fake_qi(ptr, iid):
        result = ctypes.c_void_p(recorder.next_ptr())
        recorder.calls.append(("qi", ptr.value if hasattr(ptr, "value") else ptr, repr(iid)))
        return result

    def fake_vcall(ptr, slot, restype, *args_spec):
        # Extract just values from the arg pairs
        values = []
        for i in range(0, len(args_spec), 2):
            val = args_spec[i + 1] if i + 1 < len(args_spec) else None
            # Dereference pointer outputs so the caller gets a valid pointer back
            if hasattr(val, "contents") or (hasattr(val, "_type_") and hasattr(val, "value")):
                pass
            values.append(val)
        ptr_val = ptr.value if hasattr(ptr, "value") else ptr
        recorder.vcalls.append(("vcall", ptr_val, slot, *values))
        # For calls that output a pointer (via ctypes.byref), set a fake value
        for i in range(0, len(args_spec), 2):
            argtype = args_spec[i]
            if i + 1 < len(args_spec):
                argval = args_spec[i + 1]
                if hasattr(argtype, "_type_") and argtype._type_ == ctypes.c_void_p:
                    with contextlib.suppress(AttributeError, TypeError):
                        argval.value = recorder.next_ptr()
        return 0  # S_OK

    def fake_vcall_check(ptr, slot, *args_spec):
        return fake_vcall(ptr, slot, ctypes.HRESULT, *args_spec)

    def fake_box_datetime(unix_ts):
        ptr = ctypes.c_void_p(recorder.next_ptr())
        recorder.calls.append(("box_datetime", unix_ts))
        return ptr

    @contextmanager
    def fake_hstring(text):
        recorder.calls.append(("hstring", text))
        yield ctypes.c_void_p(recorder.next_ptr())

    def fake_is_permanent(hr):
        return (hr & 0xFFFFFFFF) in (0x80070005, 0x80040154)

    patches = {
        "pgtail_py.notifier_windows.ensure_com_initialized": fake_ensure_com,
        "pgtail_py.notifier_windows.get_activation_factory": fake_get_factory,
        "pgtail_py.notifier_windows.activate_instance": fake_activate,
        "pgtail_py.notifier_windows.qi": fake_qi,
        "pgtail_py.notifier_windows.vcall": fake_vcall,
        "pgtail_py.notifier_windows.vcall_check": fake_vcall_check,
        "pgtail_py.notifier_windows.box_datetime": fake_box_datetime,
        "pgtail_py.notifier_windows.hstring": fake_hstring,
        "pgtail_py.notifier_windows.is_permanent_failure": fake_is_permanent,
        "pgtail_py.notifier_windows.ensure_shortcut": lambda: True,
    }

    from pgtail_py.notifier_windows import WindowsNotifier

    with patch.multiple(
        "pgtail_py.notifier_windows", **{k.split(".")[-1]: v for k, v in patches.items()}
    ):
        notifier = WindowsNotifier()
        yield notifier, recorder


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only (ctypes.windll at import)")
class TestMockSeamSend:
    """Test notifier_windows.py end-to-end via _winrt mock seam."""

    def test_send_info_builds_xml_and_shows(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        result = notifier.send("Title", "Body", severity="info")

        assert result is True
        # Verify XML was loaded via IXmlDocumentIO (LoadXml at slot 6)
        load_xml_calls = [c for c in recorder.vcalls if c[2] == 6 and len(c) > 3]
        assert len(load_xml_calls) >= 1

        # Verify Show was called on the notifier (slot 6)
        show_calls = [c for c in recorder.vcalls if c[2] == 6]
        assert len(show_calls) >= 2  # LoadXml + Show

    def test_send_sets_expiration_for_info(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier.send("Title", "Body", severity="info")

        # box_datetime should have been called with a timestamp ~120s from now
        box_calls = [c for c in recorder.calls if c[0] == "box_datetime"]
        assert len(box_calls) == 1
        ts = box_calls[0][1]
        now = time.time()
        assert now + 115 < ts < now + 125  # ~120s in future

        # put_ExpirationTime at slot 7 on the toast
        expiry_vcalls = [c for c in recorder.vcalls if c[2] == 7]
        assert len(expiry_vcalls) >= 1

    def test_send_no_expiration_for_critical(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier.send("Title", "Body", severity="critical")

        # box_datetime should NOT have been called
        box_calls = [c for c in recorder.calls if c[0] == "box_datetime"]
        assert len(box_calls) == 0

    def test_send_sets_tag_and_group(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier.send("Title", "Body", tag="my-tag")

        # QI to IToastNotification2
        qi_calls = [c for c in recorder.calls if c[0] == "qi"]
        iids_queried = [c[2] for c in qi_calls]
        n2_iid = repr(
            __import__(
                "pgtail_py._winrt", fromlist=["IID_IToastNotification2"]
            ).IID_IToastNotification2
        )
        assert n2_iid in iids_queried

        # hstring calls for tag and group
        hs_calls = [c for c in recorder.calls if c[0] == "hstring"]
        hs_texts = [c[1] for c in hs_calls]
        assert "my-tag" in hs_texts
        assert "pgtail" in hs_texts

    def test_send_truncates_long_tag(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier.send("Title", "Body", tag="a" * 30)

        # The hstring for the tag should be truncated to 16 chars
        hs_calls = [c for c in recorder.calls if c[0] == "hstring"]
        tag_texts = [c[1] for c in hs_calls if len(c[1]) <= 16 and c[1].startswith("a")]
        assert any(len(t) == 16 for t in tag_texts)

    def test_send_sets_suppress_popup(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier.send("Title", "Body", suppress_popup=True)

        # put_SuppressPopup at slot 10 on IToastNotification2
        slot10_calls = [c for c in recorder.vcalls if c[2] == 10]
        assert len(slot10_calls) >= 1

    def test_send_sets_priority_for_error(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier.send("Title", "Body", severity="error")

        # QI to IToastNotification4, then put_Priority at slot 9
        slot9_calls = [c for c in recorder.vcalls if c[2] == 9]
        assert len(slot9_calls) >= 1

    def test_send_sets_priority_for_critical(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier.send("Title", "Body", severity="critical")

        slot9_calls = [c for c in recorder.vcalls if c[2] == 9]
        assert len(slot9_calls) >= 1

    def test_send_no_priority_for_info(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier.send("Title", "Body", severity="info")

        # No QI to IToastNotification4 for info
        n4_iid = repr(
            __import__(
                "pgtail_py._winrt", fromlist=["IID_IToastNotification4"]
            ).IID_IToastNotification4
        )
        qi_calls = [c for c in recorder.calls if c[0] == "qi" and c[2] == n4_iid]
        assert len(qi_calls) == 0

    def test_send_no_priority_for_warning(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier.send("Title", "Body", severity="warning")

        n4_iid = repr(
            __import__(
                "pgtail_py._winrt", fromlist=["IID_IToastNotification4"]
            ).IID_IToastNotification4
        )
        qi_calls = [c for c in recorder.calls if c[0] == "qi" and c[2] == n4_iid]
        assert len(qi_calls) == 0

    def test_send_calls_ensure_com(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier.send("Title", "Body")

        # ensure_com_initialized called during send (for cross-thread safety)
        com_calls = [c for c in recorder.calls if c[0] == "ensure_com_initialized"]
        # At least 1 from __init__ + 1 from send
        assert len(com_calls) >= 2


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only (ctypes.windll at import)")
class TestMockSeamDismiss:
    """Test dismiss() via _winrt mock seam."""

    def test_dismiss_calls_history_remove(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        result = notifier.dismiss("my-tag")

        assert result is True

        # QI to IToastNotificationManagerStatics2
        n2_iid = repr(
            __import__(
                "pgtail_py._winrt", fromlist=["IID_IToastNotificationManagerStatics2"]
            ).IID_IToastNotificationManagerStatics2
        )
        qi_calls = [c for c in recorder.calls if c[0] == "qi" and c[2] == n2_iid]
        assert len(qi_calls) >= 1

        # hstring for tag and group
        hs_calls = [c for c in recorder.calls if c[0] == "hstring"]
        hs_texts = [c[1] for c in hs_calls]
        assert "my-tag" in hs_texts
        assert "pgtail" in hs_texts

    def test_dismiss_when_unavailable(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier._available = False
        result = notifier.dismiss("tag")
        assert result is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only (ctypes.windll at import)")
class TestMockSeamFailureTracking:
    """Test failure tracking via _winrt mock seam."""

    def test_transient_failure_increments_counter(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier

        # Make vcall_check raise a transient error for Show()
        with patch("pgtail_py.notifier_windows.vcall_check", side_effect=OSError("0x80070001")):
            result = notifier.send("Title", "Body")

        assert result is False
        assert notifier._consecutive_failures == 1

    def test_five_failures_sets_cooldown(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier._consecutive_failures = 4

        with patch("pgtail_py.notifier_windows.vcall_check", side_effect=OSError("0x80070001")):
            notifier.send("Title", "Body")

        assert notifier._consecutive_failures == 5
        assert notifier._disabled_until is not None
        assert notifier._disabled_until > time.time()

    def test_permanent_failure_disables(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier

        err = OSError("0x80070005")
        err.winerror = 0x80070005  # E_ACCESSDENIED

        with patch("pgtail_py.notifier_windows.vcall_check", side_effect=err):
            notifier.send("Title", "Body")

        assert notifier._available is False

    def test_disabled_send_returns_false(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier._disabled_until = time.time() + 60
        notifier._consecutive_failures = 5

        result = notifier.send("Title", "Body")
        assert result is False

    def test_cooldown_expired_retries(self, mock_winrt_notifier):
        notifier, recorder = mock_winrt_notifier
        notifier._disabled_until = time.time() - 1
        notifier._consecutive_failures = 5

        result = notifier.send("Title", "Body")
        assert result is True
        assert notifier._consecutive_failures == 0
        assert notifier._disabled_until is None


# ---------------------------------------------------------------------------
# CLI notify command tests
# ---------------------------------------------------------------------------


class TestNotifyCommandLevels:
    """Test that notify_command correctly parses level arguments including range syntax."""

    @pytest.fixture
    def state_with_manager(self):
        """Create an AppState-like object with a NotificationManager."""
        notifier = NoOpNotifier()
        manager = NotificationManager(notifier=notifier)

        @dataclass
        class FakeState:
            notification_manager: NotificationManager | None = None

        state = FakeState(notification_manager=manager)
        return state

    def _run(self, state, args: list[str]) -> list[str]:
        """Run notify_command and capture output lines."""
        from pgtail_py.cli_notify import notify_command

        lines: list[str] = []
        with patch("pgtail_py.cli_notify._persist_notification_config"):
            notify_command(state, ["on"] + args, log_widget=None)
        return lines

    def _get_levels(self, state) -> set[LogLevel]:
        return state.notification_manager.config.get_level_rules()

    def test_exact_levels(self, state_with_manager):
        """Exact level names should be added as-is."""
        from pgtail_py.cli_notify import notify_command

        with patch("pgtail_py.cli_notify._persist_notification_config"):
            notify_command(state_with_manager, ["on", "ERROR", "FATAL"], log_widget=None)

        levels = self._get_levels(state_with_manager)
        assert levels == {LogLevel.ERROR, LogLevel.FATAL}

    def test_range_plus(self, state_with_manager):
        """ERROR+ should expand to ERROR, FATAL, PANIC."""
        from pgtail_py.cli_notify import notify_command

        with patch("pgtail_py.cli_notify._persist_notification_config"):
            notify_command(state_with_manager, ["on", "ERROR+"], log_widget=None)

        levels = self._get_levels(state_with_manager)
        assert levels == {LogLevel.ERROR, LogLevel.FATAL, LogLevel.PANIC}

    def test_range_minus(self, state_with_manager):
        """WARNING- should expand to WARNING and all less severe levels."""
        from pgtail_py.cli_notify import notify_command

        with patch("pgtail_py.cli_notify._persist_notification_config"):
            notify_command(state_with_manager, ["on", "WARNING-"], log_widget=None)

        levels = self._get_levels(state_with_manager)
        assert LogLevel.WARNING in levels
        assert LogLevel.NOTICE in levels
        assert LogLevel.DEBUG1 in levels
        # Should not include more severe levels
        assert LogLevel.ERROR not in levels

    def test_range_abbreviation(self, state_with_manager):
        """Abbreviated range like e+ should work."""
        from pgtail_py.cli_notify import notify_command

        with patch("pgtail_py.cli_notify._persist_notification_config"):
            notify_command(state_with_manager, ["on", "e+"], log_widget=None)

        levels = self._get_levels(state_with_manager)
        assert levels == {LogLevel.ERROR, LogLevel.FATAL, LogLevel.PANIC}
