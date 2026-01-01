"""Shared utility functions for pgtail.

This module provides common utility functions used across multiple modules.
"""

from __future__ import annotations

import os


def is_color_disabled() -> bool:
    """Check if color output should be disabled.

    Respects the NO_COLOR environment variable (https://no-color.org/).
    When NO_COLOR is set (to any value), color output should be disabled.

    Returns:
        True if NO_COLOR is set, False otherwise.
    """
    return "NO_COLOR" in os.environ
