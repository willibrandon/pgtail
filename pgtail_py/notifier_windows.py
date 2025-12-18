"""Windows notification implementation using PowerShell.

Uses built-in PowerShell and .NET toast notifications for
Windows 10+ without external dependencies.
"""

from __future__ import annotations

import shutil
import subprocess

from pgtail_py.notifier import Notifier


class WindowsNotifier(Notifier):
    """Windows notification sender using PowerShell.

    Uses the Windows.UI.Notifications API via PowerShell for
    toast notifications on Windows 10 and later.
    """

    def __init__(self) -> None:
        """Initialize and check PowerShell availability."""
        self._powershell_path = shutil.which("powershell")

    def send(self, title: str, body: str, subtitle: str | None = None) -> bool:
        """Send notification via PowerShell toast.

        Args:
            title: Notification title.
            body: Notification body text.
            subtitle: Optional subtitle (displayed in body on Windows).

        Returns:
            True if notification was sent successfully.
        """
        if not self._powershell_path:
            return False

        # Include subtitle in body if provided
        full_body = body
        if subtitle:
            full_body = f"{subtitle}: {body}"

        # Escape single quotes for PowerShell
        title_escaped = title.replace("'", "''")
        body_escaped = full_body.replace("'", "''")

        # PowerShell script for Windows toast notification
        # Uses built-in .NET classes available in Windows 10+
        script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast>
    <visual>
        <binding template="ToastText02">
            <text id="1">{title_escaped}</text>
            <text id="2">{body_escaped}</text>
        </binding>
    </visual>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('pgtail').Show($toast)
"""

        try:
            subprocess.run(
                [self._powershell_path, "-NoProfile", "-Command", script],
                capture_output=True,
                timeout=10,
                check=False,
            )
            return True
        except (subprocess.TimeoutExpired, OSError):
            return False

    def is_available(self) -> bool:
        """Check if PowerShell is available.

        Note: This only checks for PowerShell presence.
        Toast notifications may still fail on older Windows versions.

        Returns:
            True if PowerShell can be used.
        """
        return self._powershell_path is not None

    def get_platform_info(self) -> str:
        """Return platform description.

        Returns:
            Platform info string.
        """
        if self._powershell_path:
            return "Windows (PowerShell)"
        return "Windows (PowerShell not found)"
