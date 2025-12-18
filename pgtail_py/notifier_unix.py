"""Unix notification implementations for macOS and Linux.

Uses osascript on macOS and notify-send on Linux.
"""

from __future__ import annotations

import shutil
import subprocess

from pgtail_py.notifier import Notifier


class MacOSNotifier(Notifier):
    """macOS notification sender using osascript.

    Uses the built-in osascript command with AppleScript's
    'display notification' for zero-dependency notifications.
    """

    def __init__(self) -> None:
        """Initialize and check osascript availability."""
        self._osascript_path = shutil.which("osascript")

    def send(self, title: str, body: str, subtitle: str | None = None) -> bool:
        """Send notification via osascript.

        Args:
            title: Notification title.
            body: Notification body text.
            subtitle: Optional subtitle.

        Returns:
            True if notification was sent successfully.
        """
        if not self._osascript_path:
            return False

        # Escape double quotes for AppleScript
        title_escaped = title.replace('"', '\\"')
        body_escaped = body.replace('"', '\\"')

        # Build AppleScript command
        script = f'display notification "{body_escaped}"'
        if subtitle:
            subtitle_escaped = subtitle.replace('"', '\\"')
            script += f' subtitle "{subtitle_escaped}"'
        script += f' with title "{title_escaped}"'

        try:
            subprocess.run(
                [self._osascript_path, "-e", script],
                capture_output=True,
                timeout=5,
                check=False,
            )
            return True
        except (subprocess.TimeoutExpired, OSError):
            return False

    def is_available(self) -> bool:
        """Check if osascript is available.

        Returns:
            True if osascript can be used.
        """
        return self._osascript_path is not None

    def get_platform_info(self) -> str:
        """Return platform description.

        Returns:
            Platform info string.
        """
        if self._osascript_path:
            return "macOS (osascript)"
        return "macOS (osascript not found)"


class LinuxNotifier(Notifier):
    """Linux notification sender using notify-send.

    Uses libnotify's notify-send command, the standard notification
    tool on most Linux desktop environments.
    """

    def __init__(self) -> None:
        """Initialize and check notify-send availability."""
        self._notify_send_path = shutil.which("notify-send")

    def send(self, title: str, body: str, subtitle: str | None = None) -> bool:
        """Send notification via notify-send.

        Args:
            title: Notification title.
            body: Notification body text.
            subtitle: Optional subtitle (prepended to body on Linux).

        Returns:
            True if notification was sent successfully.
        """
        if not self._notify_send_path:
            return False

        # notify-send doesn't have native subtitle support
        # Prepend subtitle to body if provided
        full_body = body
        if subtitle:
            full_body = f"{subtitle}\n{body}"

        try:
            subprocess.run(
                [
                    self._notify_send_path,
                    "-u",
                    "normal",  # Urgency: low, normal, critical
                    "-a",
                    "pgtail",  # Application name
                    title,
                    full_body,
                ],
                capture_output=True,
                timeout=5,
                check=False,
            )
            return True
        except (subprocess.TimeoutExpired, OSError):
            return False

    def is_available(self) -> bool:
        """Check if notify-send is available.

        Returns:
            True if notify-send can be used.
        """
        return self._notify_send_path is not None

    def get_platform_info(self) -> str:
        """Return platform description with install hint if needed.

        Returns:
            Platform info string.
        """
        if self._notify_send_path:
            return "Linux (notify-send)"
        return "Linux (notify-send not found)"
