"""Terminal initialization and cleanup for Windows support."""

import sys


def enable_vt100_mode() -> bool:
    """Enable VT100 escape sequence processing on Windows.

    On Windows 10+, this enables ANSI color codes in the console.
    On other platforms, this is a no-op and returns True.

    Returns:
        True if VT100 mode is enabled or not needed, False on failure.
    """
    if sys.platform != "win32":
        return True

    try:
        from ctypes import byref, windll
        from ctypes.wintypes import DWORD, HANDLE

        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

        hconsole = HANDLE(windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE))
        mode = DWORD(0)
        windll.kernel32.GetConsoleMode(hconsole, byref(mode))

        # Enable VT100 mode
        new_mode = DWORD(mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        result = windll.kernel32.SetConsoleMode(hconsole, new_mode)
        return result != 0
    except Exception:
        return False


def reset_terminal() -> None:
    """Reset terminal state after interruption.

    Ensures cursor is visible and at the start of a new line.
    """
    # Flush stdout to ensure any pending output is written
    sys.stdout.flush()

    # Print a newline to ensure we're at the start of a line
    # This helps prevent prompt mangling after Ctrl+C
    print("\033[0m", end="", flush=True)  # Reset any pending ANSI state
