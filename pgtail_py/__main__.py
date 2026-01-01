"""Entry point for running pgtail as a module: python -m pgtail_py"""

import sys

# Check Python version before importing anything else
# This ensures a clear error message instead of syntax errors from 3.10+ features
if sys.version_info < (3, 10):  # noqa: UP036 - runtime check needed for clear error message
    sys.stderr.write(
        f"Error: pgtail requires Python 3.10+, but you are running Python "
        f"{sys.version_info.major}.{sys.version_info.minor}\n"
    )
    sys.exit(1)

from pgtail_py.cli_main import cli_main

if __name__ == "__main__":
    cli_main()
