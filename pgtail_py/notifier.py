"""Platform-agnostic notification dispatcher.

Provides the Notifier abstract interface and factory for creating
platform-specific notification implementations.
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod


class Notifier(ABC):
    """Abstract interface for sending desktop notifications.

    Platform-specific implementations handle the actual notification
    dispatch using native OS mechanisms.
    """

    @abstractmethod
    def send(self, title: str, body: str, subtitle: str | None = None) -> bool:
        """Send a desktop notification.

        Args:
            title: Notification title.
            body: Notification body text.
            subtitle: Optional subtitle (may not be supported on all platforms).

        Returns:
            True if notification was sent successfully.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if notification system is available.

        Returns:
            True if notifications can be sent on this platform.
        """

    @abstractmethod
    def get_platform_info(self) -> str:
        """Get platform and method description.

        Returns:
            String describing platform and notification method.
        """


class NoOpNotifier(Notifier):
    """Fallback notifier when no platform support is available.

    Used when running in environments without desktop notification support
    (e.g., SSH sessions without X forwarding, headless servers).
    """

    def __init__(self, reason: str = "Notifications unavailable") -> None:
        """Initialize with reason for unavailability.

        Args:
            reason: Human-readable reason notifications are unavailable.
        """
        self._reason = reason

    def send(self, title: str, body: str, subtitle: str | None = None) -> bool:
        """No-op send - always returns False.

        Args:
            title: Ignored.
            body: Ignored.
            subtitle: Ignored.

        Returns:
            False (notification not sent).
        """
        return False

    def is_available(self) -> bool:
        """Notifications are not available.

        Returns:
            False.
        """
        return False

    def get_platform_info(self) -> str:
        """Return reason for unavailability.

        Returns:
            Reason string.
        """
        return self._reason


def create_notifier() -> Notifier:
    """Create appropriate notifier for current platform.

    Returns:
        Platform-specific Notifier implementation, or NoOpNotifier if
        notifications are not available.
    """
    if sys.platform == "darwin":
        from pgtail_py.notifier_unix import MacOSNotifier

        notifier = MacOSNotifier()
        if notifier.is_available():
            return notifier
        return NoOpNotifier("macOS (osascript not found)")

    elif sys.platform == "win32":
        from pgtail_py.notifier_windows import WindowsNotifier

        notifier = WindowsNotifier()
        if notifier.is_available():
            return notifier
        return NoOpNotifier("Windows (PowerShell unavailable)")

    elif sys.platform.startswith("linux") or sys.platform.startswith("freebsd"):
        from pgtail_py.notifier_unix import LinuxNotifier

        notifier = LinuxNotifier()
        if notifier.is_available():
            return notifier
        return NoOpNotifier("Linux (notify-send not found)")

    else:
        return NoOpNotifier(f"Unsupported platform: {sys.platform}")
