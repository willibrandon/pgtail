"""Start Menu shortcut creation for Windows toast AUMID registration.

Creates a .lnk shortcut in the Start Menu with the System.AppUserModel.ID
property set, which is required for toast notifications to appear in
Action Center under the app name.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import os
import sys

from pgtail_py._winrt import GUID, S_OK, vcall_check, vcall

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AUMID = "pgtail.pgtail"

CLSCTX_INPROC_SERVER = 1

CLSID_ShellLink = GUID.from_string("{00021401-0000-0000-C000-000000000046}")
IID_IShellLinkW = GUID.from_string("{000214F9-0000-0000-C000-000000000046}")
IID_IPropertyStore = GUID.from_string("{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}")
IID_IPersistFile = GUID.from_string("{0000010B-0000-0000-C000-000000000046}")

# PKEY_AppUserModel_ID = {9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}, 5
_PKEY_AUMID_FMTID = GUID.from_string("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}")
_PKEY_AUMID_PID = 5

# ---------------------------------------------------------------------------
# COM structures for IPropertyStore
# ---------------------------------------------------------------------------


class PROPERTYKEY(ctypes.Structure):
    _fields_ = [
        ("fmtid", GUID),
        ("pid", ctypes.c_uint32),
    ]


class PROPVARIANT(ctypes.Structure):
    _fields_ = [
        ("vt", ctypes.c_uint16),
        ("reserved1", ctypes.c_uint16),
        ("reserved2", ctypes.c_uint16),
        ("reserved3", ctypes.c_uint16),
        ("pwszVal", ctypes.c_wchar_p),
        ("padding", ctypes.c_uint64),
    ]


# ---------------------------------------------------------------------------
# DLL bindings
# ---------------------------------------------------------------------------

_ole32 = ctypes.windll.ole32

_CoCreateInstance = _ole32.CoCreateInstance
_CoCreateInstance.restype = ctypes.HRESULT
_CoCreateInstance.argtypes = [
    ctypes.POINTER(GUID),
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.POINTER(GUID),
    ctypes.POINTER(ctypes.c_void_p),
]

_CoInitializeEx = _ole32.CoInitializeEx
_CoInitializeEx.restype = ctypes.HRESULT
_CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_uint32]


# ---------------------------------------------------------------------------
# Shortcut path
# ---------------------------------------------------------------------------


def _get_shortcut_path() -> str:
    appdata = os.environ.get("APPDATA", "")
    return os.path.join(
        appdata, "Microsoft", "Windows", "Start Menu", "Programs", "pgtail.lnk"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ensure_shortcut() -> bool:
    """Create Start Menu shortcut with AUMID if it doesn't exist.

    Returns True if shortcut exists (created or already present), False on failure.
    """
    lnk_path = _get_shortcut_path()

    if os.path.exists(lnk_path):
        logger.debug("Shortcut already exists: %s", lnk_path)
        return True

    try:
        return _create_shortcut(lnk_path)
    except OSError as e:
        logger.warning("Failed to create Start Menu shortcut: %s", e)
        return False


def _create_shortcut(lnk_path: str) -> bool:
    """Create the .lnk shortcut with AUMID property."""
    # Ensure classic COM is initialized
    hr = _CoInitializeEx(None, 0)
    # Accept S_OK, S_FALSE, RPC_E_CHANGED_MODE
    if hr not in (S_OK, 1) and (hr & 0xFFFFFFFF) != 0x80010106:
        raise OSError(f"CoInitializeEx failed: 0x{hr & 0xFFFFFFFF:08X}")

    # CoCreateInstance(CLSID_ShellLink) -> IShellLinkW
    shell_link = ctypes.c_void_p()
    hr = _CoCreateInstance(
        ctypes.byref(CLSID_ShellLink),
        None,
        CLSCTX_INPROC_SERVER,
        ctypes.byref(IID_IShellLinkW),
        ctypes.byref(shell_link),
    )
    if hr != S_OK:
        raise OSError(f"CoCreateInstance(ShellLink) failed: 0x{hr & 0xFFFFFFFF:08X}")

    # IShellLinkW::SetPath (slot 20)
    vcall_check(shell_link, 20, ctypes.c_wchar_p, sys.executable)

    # IShellLinkW::SetDescription (slot 7)
    vcall_check(shell_link, 7, ctypes.c_wchar_p, "pgtail - PostgreSQL log tailer")

    # QI -> IPropertyStore
    from pgtail_py._winrt import qi
    prop_store = qi(shell_link, IID_IPropertyStore)

    # Set PKEY_AppUserModel_ID
    pkey = PROPERTYKEY(_PKEY_AUMID_FMTID, _PKEY_AUMID_PID)
    pv = PROPVARIANT()
    pv.vt = 31  # VT_LPWSTR
    pv.pwszVal = AUMID

    # IPropertyStore::SetValue (slot 6)
    vcall_check(
        prop_store, 6,
        ctypes.POINTER(PROPERTYKEY), ctypes.byref(pkey),
        ctypes.POINTER(PROPVARIANT), ctypes.byref(pv),
    )

    # IPropertyStore::Commit (slot 7)
    vcall_check(prop_store, 7)

    # QI -> IPersistFile
    persist_file = qi(shell_link, IID_IPersistFile)

    # Ensure directory exists
    os.makedirs(os.path.dirname(lnk_path), exist_ok=True)

    # IPersistFile::Save (slot 6)
    vcall_check(persist_file, 6, ctypes.c_wchar_p, lnk_path, ctypes.c_int32, 1)

    logger.info("Created Start Menu shortcut: %s", lnk_path)
    return True
