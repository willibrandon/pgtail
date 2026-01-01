#!/usr/bin/env bash
# Check that pgtail_py/__init__.py.__version__ matches pyproject.toml version
#
# Usage: ./scripts/check-version-sync.sh
#
# Exit codes:
#   0 - Versions match
#   1 - Versions do not match

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Extract version from pyproject.toml
PYPROJECT_VERSION=$(grep -E '^version = ' "$PROJECT_ROOT/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')

# Extract version from pgtail_py/__init__.py
INIT_VERSION=$(grep -E '^__version__ = ' "$PROJECT_ROOT/pgtail_py/__init__.py" | sed 's/__version__ = "\(.*\)"/\1/')

if [ -z "$PYPROJECT_VERSION" ]; then
    echo "ERROR: Could not extract version from pyproject.toml"
    exit 1
fi

if [ -z "$INIT_VERSION" ]; then
    echo "ERROR: Could not extract version from pgtail_py/__init__.py"
    exit 1
fi

if [ "$PYPROJECT_VERSION" != "$INIT_VERSION" ]; then
    echo "ERROR: Version mismatch!"
    echo "  pyproject.toml:          $PYPROJECT_VERSION"
    echo "  pgtail_py/__init__.py:   $INIT_VERSION"
    echo ""
    echo "Update both files to the same version before releasing."
    exit 1
fi

echo "OK: Versions match ($PYPROJECT_VERSION)"
exit 0
