"""Low-level WinRT COM interop via ctypes.

This module provides all COM plumbing for Windows toast notifications:
GUID/HSTRING management, vtable calls, COM initialization, activation
factories, and DateTime boxing.

This module is the mock seam for cross-platform testing — notifier_windows.py
imports all COM operations from here.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import threading
from collections.abc import Generator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

S_OK = 0
S_FALSE = 1
RPC_E_CHANGED_MODE = 0x80010106
RO_INIT_MULTITHREADED = 1

# Permanent failure HRESULTs — these should disable notifications
E_ACCESSDENIED = 0x80070005
CLASS_NOT_REGISTERED = 0x80040154
PERMANENT_HRESULTS = frozenset({E_ACCESSDENIED, CLASS_NOT_REGISTERED})

HSTRING = ctypes.c_void_p

# ---------------------------------------------------------------------------
# GUID
# ---------------------------------------------------------------------------


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_uint8 * 8),
    ]

    @classmethod
    def from_string(cls, s: str) -> GUID:
        s = s.strip("{}")
        parts = s.split("-")
        d1 = int(parts[0], 16)
        d2 = int(parts[1], 16)
        d3 = int(parts[2], 16)
        d4_bytes = bytes.fromhex(parts[3] + parts[4])
        d4 = (ctypes.c_uint8 * 8)(*d4_bytes)
        return cls(d1, d2, d3, d4)

    def __repr__(self) -> str:
        d4 = bytes(self.Data4)
        return (
            f"{{{self.Data1:08X}-{self.Data2:04X}-{self.Data3:04X}"
            f"-{d4[0]:02X}{d4[1]:02X}-{d4[2]:02X}{d4[3]:02X}"
            f"{d4[4]:02X}{d4[5]:02X}{d4[6]:02X}{d4[7]:02X}}}"
        )


# ---------------------------------------------------------------------------
# Interface IIDs
# ---------------------------------------------------------------------------

IID_IToastNotificationManagerStatics = GUID.from_string("{50AC103F-D235-4598-BBEF-98FE4D1A3AD4}")
IID_IToastNotificationManagerStatics2 = GUID.from_string("{7AB93C52-0E48-4750-BA9D-1A4113981847}")
IID_IToastNotificationFactory = GUID.from_string("{04124B20-82C6-4229-B109-FD9ED4662B53}")
IID_IToastNotification2 = GUID.from_string("{9DFB9FD1-143A-490E-90BF-B9FBA7132DE7}")
IID_IToastNotification4 = GUID.from_string("{15154935-28EA-4727-88E9-C58680E2D118}")
IID_IToastNotificationHistory = GUID.from_string("{5BC3CBF2-F2C1-4A5B-80E3-07D70AEFB053}")
IID_IXmlDocumentIO = GUID.from_string("{6CD0E74E-EE65-4489-9EBF-CA43E87BA637}")
IID_IPropertyValueStatics = GUID.from_string("{629BDBC8-D932-4FF4-96B9-8D96C5C1E858}")

# ---------------------------------------------------------------------------
# DLL bindings
# ---------------------------------------------------------------------------

_combase = ctypes.windll.combase

_RoInitialize = _combase.RoInitialize
_RoInitialize.restype = ctypes.HRESULT
_RoInitialize.argtypes = [ctypes.c_int32]

_WindowsCreateString = _combase.WindowsCreateString
_WindowsCreateString.restype = ctypes.HRESULT
_WindowsCreateString.argtypes = [
    ctypes.c_wchar_p,
    ctypes.c_uint32,
    ctypes.POINTER(HSTRING),
]

_WindowsDeleteString = _combase.WindowsDeleteString
_WindowsDeleteString.restype = ctypes.HRESULT
_WindowsDeleteString.argtypes = [HSTRING]

_RoGetActivationFactory = _combase.RoGetActivationFactory
_RoGetActivationFactory.restype = ctypes.HRESULT
_RoGetActivationFactory.argtypes = [
    HSTRING,
    ctypes.POINTER(GUID),
    ctypes.POINTER(ctypes.c_void_p),
]

_RoActivateInstance = _combase.RoActivateInstance
_RoActivateInstance.restype = ctypes.HRESULT
_RoActivateInstance.argtypes = [HSTRING, ctypes.POINTER(ctypes.c_void_p)]

# ---------------------------------------------------------------------------
# Per-thread COM initialization
# ---------------------------------------------------------------------------

_tls = threading.local()


def ensure_com_initialized() -> None:
    """Initialize WinRT COM on the current thread if not already done.

    Handles S_OK (success), S_FALSE (already initialized same apartment),
    and RPC_E_CHANGED_MODE (different apartment model — acceptable).
    Never calls RoUninitialize.
    """
    if getattr(_tls, "initialized", False):
        return

    hr = _RoInitialize(RO_INIT_MULTITHREADED)
    if hr == S_OK:
        logger.debug("RoInitialize: S_OK")
    elif hr == S_FALSE:
        logger.debug("RoInitialize: S_FALSE (already initialized)")
    elif (hr & 0xFFFFFFFF) == RPC_E_CHANGED_MODE:
        logger.debug("RoInitialize: RPC_E_CHANGED_MODE (different apartment, acceptable)")
    else:
        raise OSError(f"RoInitialize failed: 0x{hr & 0xFFFFFFFF:08X}")

    _tls.initialized = True


# ---------------------------------------------------------------------------
# HSTRING management
# ---------------------------------------------------------------------------


def _create_hstring(text: str) -> HSTRING:
    hs = HSTRING()
    hr = _WindowsCreateString(text, len(text), ctypes.byref(hs))
    if hr != S_OK:
        raise OSError(f"WindowsCreateString failed: 0x{hr & 0xFFFFFFFF:08X}")
    return hs


def _delete_hstring(hs: HSTRING) -> None:
    _WindowsDeleteString(hs)


@contextmanager
def hstring(text: str) -> Generator[HSTRING, None, None]:
    """Create an HSTRING, yield it, and auto-delete on exit."""
    hs = _create_hstring(text)
    try:
        yield hs
    finally:
        _delete_hstring(hs)


# ---------------------------------------------------------------------------
# Vtable call helpers
# ---------------------------------------------------------------------------

# Size of vtable we allocate for reading — 64 slots is more than enough
_VTABLE_SIZE = 64


def _get_vtable(ptr: ctypes.c_void_p) -> ctypes.Array:
    """Read the vtable pointer array from a COM object."""
    vptr = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p)).contents
    return ctypes.cast(vptr, ctypes.POINTER(ctypes.c_void_p * _VTABLE_SIZE)).contents


def qi(ptr: ctypes.c_void_p, iid: GUID) -> ctypes.c_void_p:
    """QueryInterface on a COM pointer."""
    vtable = _get_vtable(ptr)
    fn = ctypes.WINFUNCTYPE(
        ctypes.HRESULT,
        ctypes.c_void_p,
        ctypes.POINTER(GUID),
        ctypes.POINTER(ctypes.c_void_p),
    )(vtable[0])
    result = ctypes.c_void_p()
    hr = fn(ptr, ctypes.byref(iid), ctypes.byref(result))
    if hr != S_OK:
        raise OSError(f"QueryInterface failed: 0x{hr & 0xFFFFFFFF:08X}")
    return result


def vcall(ptr: ctypes.c_void_p, slot: int, restype, *args_spec):
    """Call a vtable slot.

    args_spec is alternating (argtype, value) pairs after the implicit
    'this' pointer.  Returns the raw result (usually HRESULT).
    """
    vtable = _get_vtable(ptr)
    argtypes = [ctypes.c_void_p]  # this
    argvalues = [ptr]
    for i in range(0, len(args_spec), 2):
        argtypes.append(args_spec[i])
        argvalues.append(args_spec[i + 1])
    fn = ctypes.WINFUNCTYPE(restype, *argtypes)(vtable[slot])
    return fn(*argvalues)


def vcall_check(ptr: ctypes.c_void_p, slot: int, *args_spec) -> int:
    """Call a vtable slot and raise OSError if HRESULT indicates failure."""
    hr = vcall(ptr, slot, ctypes.HRESULT, *args_spec)
    if hr != S_OK:
        raise OSError(f"vtable[{slot}] failed: 0x{hr & 0xFFFFFFFF:08X}")
    return hr


# ---------------------------------------------------------------------------
# Factory activation
# ---------------------------------------------------------------------------


def get_activation_factory(class_name: str, iid: GUID) -> ctypes.c_void_p:
    """Get an activation factory for a WinRT class."""
    with hstring(class_name) as hs:
        factory = ctypes.c_void_p()
        hr = _RoGetActivationFactory(hs, ctypes.byref(iid), ctypes.byref(factory))
        if hr != S_OK:
            raise OSError(f"RoGetActivationFactory({class_name}) failed: 0x{hr & 0xFFFFFFFF:08X}")
        return factory


def activate_instance(class_name: str) -> ctypes.c_void_p:
    """Activate a default instance of a WinRT class."""
    with hstring(class_name) as hs:
        instance = ctypes.c_void_p()
        hr = _RoActivateInstance(hs, ctypes.byref(instance))
        if hr != S_OK:
            raise OSError(f"RoActivateInstance({class_name}) failed: 0x{hr & 0xFFFFFFFF:08X}")
        return instance


# ---------------------------------------------------------------------------
# DateTime boxing
# ---------------------------------------------------------------------------

# Offset between Unix epoch (1970-01-01) and Windows FILETIME epoch (1601-01-01)
# in seconds.
_EPOCH_OFFSET_SECONDS = 11644473600
_TICKS_PER_SECOND = 10_000_000


def unix_to_ticks(unix_timestamp: float) -> int:
    """Convert Unix timestamp to Windows FILETIME ticks (100ns since 1601-01-01)."""
    return int((unix_timestamp + _EPOCH_OFFSET_SECONDS) * _TICKS_PER_SECOND)


def box_datetime(unix_timestamp: float) -> ctypes.c_void_p:
    """Box a Unix timestamp as IReference<DateTime> via IPropertyValueStatics.

    Uses IPropertyValueStatics::CreateDateTime at vtable slot [21].
    """
    ticks = unix_to_ticks(unix_timestamp)

    factory = get_activation_factory(
        "Windows.Foundation.PropertyValue",
        IID_IPropertyValueStatics,
    )

    datetime_ref = ctypes.c_void_p()
    hr = vcall(
        factory,
        21,
        ctypes.HRESULT,
        ctypes.c_int64,
        ticks,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.byref(datetime_ref),
    )
    if hr != S_OK:
        raise OSError(f"CreateDateTime failed: 0x{hr & 0xFFFFFFFF:08X}")
    return datetime_ref


def is_permanent_failure(hresult: int) -> bool:
    """Check if an HRESULT represents a permanent (non-recoverable) failure."""
    return (hresult & 0xFFFFFFFF) in PERMANENT_HRESULTS
