"""Windows notification implementation using WinRT COM via ctypes.

Uses the Windows.UI.Notifications toast API directly through COM vtable
calls — no PowerShell, no external dependencies.
"""

from __future__ import annotations

import ctypes
import logging
import time

from pgtail_py._toast_xml import EXPIRY_SECONDS, build_toast_xml
from pgtail_py._win_shortcut import AUMID, ensure_shortcut
from pgtail_py._winrt import (
    HSTRING,
    IID_IToastNotification2,
    IID_IToastNotification4,
    IID_IToastNotificationFactory,
    IID_IToastNotificationManagerStatics,
    IID_IToastNotificationManagerStatics2,
    IID_IXmlDocumentIO,
    activate_instance,
    box_datetime,
    ensure_com_initialized,
    get_activation_factory,
    hstring,
    is_permanent_failure,
    qi,
    vcall,
    vcall_check,
)
from pgtail_py.notifier import Notifier

logger = logging.getLogger(__name__)

# Maximum tag length for toast notifications
_MAX_TAG_LEN = 16

# Consecutive failure threshold before disabling
_FAILURE_THRESHOLD = 5

# Cooldown period after hitting failure threshold (seconds)
_COOLDOWN_SECONDS = 60

S_OK = 0


class WindowsNotifier(Notifier):
    """Windows notification sender using WinRT COM toast API.

    Uses direct ctypes COM vtable calls to Windows.UI.Notifications
    for toast notifications on Windows 10 and later.
    """

    def __init__(self) -> None:
        """Initialize WinRT COM toast notification infrastructure."""
        self._available = False
        self._toast_notifier: ctypes.c_void_p | None = None
        self._toast_factory: ctypes.c_void_p | None = None
        self._mgr_factory: ctypes.c_void_p | None = None
        self._consecutive_failures = 0
        self._disabled_until: float | None = None

        try:
            ensure_com_initialized()
            if not ensure_shortcut():
                raise OSError("AUMID shortcut registration failed")

            # Get ToastNotificationManagerStatics factory
            self._mgr_factory = get_activation_factory(
                "Windows.UI.Notifications.ToastNotificationManager",
                IID_IToastNotificationManagerStatics,
            )

            # CreateToastNotifierWithId(AUMID) — slot [7]
            with hstring(AUMID) as hs_aumid:
                notifier = ctypes.c_void_p()
                hr = vcall(
                    self._mgr_factory,
                    7,
                    ctypes.HRESULT,
                    HSTRING,
                    hs_aumid,
                    ctypes.POINTER(ctypes.c_void_p),
                    ctypes.byref(notifier),
                )
                if hr != S_OK:
                    raise OSError(f"CreateToastNotifierWithId failed: 0x{hr & 0xFFFFFFFF:08X}")
                self._toast_notifier = notifier

            # Cache ToastNotificationFactory
            self._toast_factory = get_activation_factory(
                "Windows.UI.Notifications.ToastNotification",
                IID_IToastNotificationFactory,
            )

            self._available = True
            logger.debug("WindowsNotifier initialized (WinRT COM)")

        except OSError as e:
            logger.warning("WinRT toast init failed: %s", e)
            self._available = False

    def send(
        self,
        title: str,
        body: str,
        subtitle: str | None = None,
        severity: str = "info",
        tag: str | None = None,
        suppress_popup: bool = False,
    ) -> bool:
        """Send a toast notification.

        Args:
            title: Notification title.
            body: Notification body text.
            subtitle: Optional subtitle.
            severity: One of "info", "warning", "error", "critical".
            tag: Optional tag for toast replacement (max 16 chars).
            suppress_popup: If True, send silently to Action Center only.

        Returns:
            True if notification was sent successfully.
        """
        if not self._available:
            return False

        # Check cooldown
        now = time.time()
        if self._disabled_until is not None:
            if now < self._disabled_until:
                return False
            # Cooldown expired — reset and retry
            logger.info("Notification cooldown expired, retrying")
            self._consecutive_failures = 0
            self._disabled_until = None

        try:
            # Per-thread COM init — send() may fire on a different thread
            ensure_com_initialized()

            # Build and load XML
            xml_string = build_toast_xml(title, body, subtitle, severity)
            xml_doc = activate_instance("Windows.Data.Xml.Dom.XmlDocument")
            doc_io = qi(xml_doc, IID_IXmlDocumentIO)
            with hstring(xml_string) as hs_xml:
                vcall_check(doc_io, 6, HSTRING, hs_xml)  # LoadXml

            # Create toast notification
            toast = ctypes.c_void_p()
            hr = vcall(
                self._toast_factory,
                6,
                ctypes.HRESULT,
                ctypes.c_void_p,
                xml_doc,
                ctypes.POINTER(ctypes.c_void_p),
                ctypes.byref(toast),
            )
            if hr != S_OK:
                raise OSError(f"CreateToastNotification failed: 0x{hr & 0xFFFFFFFF:08X}")

            # Set ExpirationTime (unless critical — never expires)
            expiry_secs = EXPIRY_SECONDS.get(severity)
            if expiry_secs is not None:
                expiry_unix = now + expiry_secs
                datetime_ref = box_datetime(expiry_unix)
                # put_ExpirationTime — slot [7] on IToastNotification
                # The factory returns the toast on the IToastNotification vtable,
                # so we call directly without QI.
                vcall_check(toast, 7, ctypes.c_void_p, datetime_ref)

            # Set tag and group
            if tag is not None:
                if len(tag) > _MAX_TAG_LEN:
                    logger.warning(
                        "Toast tag truncated from %d to %d chars: %r",
                        len(tag),
                        _MAX_TAG_LEN,
                        tag,
                    )
                    tag = tag[:_MAX_TAG_LEN]
                toast2 = qi(toast, IID_IToastNotification2)
                with hstring(tag) as hs_tag:
                    vcall_check(toast2, 6, HSTRING, hs_tag)  # put_Tag
                with hstring("pgtail") as hs_group:
                    vcall_check(toast2, 8, HSTRING, hs_group)  # put_Group

            # Set SuppressPopup
            if suppress_popup:
                toast2 = qi(toast, IID_IToastNotification2)
                # put_SuppressPopup — slot [10]
                vcall_check(toast2, 10, ctypes.c_int32, 1)  # boolean True

            # Set Priority for error/critical
            if severity in ("error", "critical"):
                try:
                    toast4 = qi(toast, IID_IToastNotification4)
                    # put_Priority — slot [9], High=1
                    vcall_check(toast4, 9, ctypes.c_int32, 1)
                except OSError:
                    # IToastNotification4 not available on older Windows
                    logger.debug("IToastNotification4 not available, skipping Priority")

            # Show the toast
            vcall_check(self._toast_notifier, 6, ctypes.c_void_p, toast)

            # Success — reset failure counter
            self._consecutive_failures = 0
            return True

        except OSError as e:
            hresult = _extract_hresult(e)
            logger.warning("Toast notification failed: %s", e)

            if is_permanent_failure(hresult):
                logger.error(
                    "Permanent notification failure (0x%08X), disabling",
                    hresult & 0xFFFFFFFF,
                )
                self._available = False
                return False

            self._consecutive_failures += 1
            if self._consecutive_failures >= _FAILURE_THRESHOLD:
                self._disabled_until = time.time() + _COOLDOWN_SECONDS
                logger.warning(
                    "Toast notification failed %d times consecutively, disabling for %ds",
                    self._consecutive_failures,
                    _COOLDOWN_SECONDS,
                )
            return False

    def dismiss(self, tag: str, group: str = "pgtail") -> bool:
        """Dismiss a toast notification from Action Center.

        Args:
            tag: Tag of the notification to dismiss.
            group: Group name (default "pgtail").

        Returns:
            True if dismissal succeeded.
        """
        if not self._available or self._mgr_factory is None:
            return False

        try:
            ensure_com_initialized()

            # QI to IToastNotificationManagerStatics2
            mgr2 = qi(self._mgr_factory, IID_IToastNotificationManagerStatics2)

            # get_History — slot [6] (single custom method)
            history = ctypes.c_void_p()
            hr = vcall(
                mgr2,
                6,
                ctypes.HRESULT,
                ctypes.POINTER(ctypes.c_void_p),
                ctypes.byref(history),
            )
            if hr != S_OK:
                raise OSError(f"get_History failed: 0x{hr & 0xFFFFFFFF:08X}")

            # RemoveGroupedTag — slot [7]
            with hstring(tag) as hs_tag, hstring(group) as hs_group:
                vcall_check(history, 7, HSTRING, hs_tag, HSTRING, hs_group)

            return True

        except OSError as e:
            logger.debug("Toast dismiss failed: %s", e)
            return False

    def is_available(self) -> bool:
        """Check if WinRT toast notifications are available.

        Returns:
            True if the notification system initialized successfully.
        """
        return self._available

    def get_platform_info(self) -> str:
        """Return platform description.

        Returns:
            Platform info string.
        """
        if self._available:
            return "Windows (WinRT Toast)"
        return "Windows (WinRT unavailable)"


def _extract_hresult(e: OSError) -> int:
    """Extract HRESULT from an OSError, defaulting to E_FAIL."""
    if e.winerror is not None:
        return e.winerror
    # Try to parse from message
    msg = str(e)
    if "0x" in msg:
        try:
            hex_str = msg[msg.rindex("0x") :]
            return int(hex_str.split()[0].rstrip("]"), 16)
        except (ValueError, IndexError):
            pass
    return 0x80004005  # E_FAIL
