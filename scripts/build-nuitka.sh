#!/usr/bin/env bash
# Build pgtail using Nuitka with all required flags
#
# Usage: ./scripts/build-nuitka.sh
#
# Output: dist/pgtail-{platform}-{arch}/pgtail (or pgtail.exe on Windows)
#
# This script:
#   1. Detects the current platform and architecture
#   2. Runs Nuitka with standalone mode and all required flags
#   3. Renames output folder to platform-specific name

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# =============================================================================
# Platform Detection (T009)
# =============================================================================

detect_platform() {
    local os arch

    # Detect OS
    case "$(uname -s)" in
        Darwin)
            os="macos"
            ;;
        Linux)
            os="linux"
            ;;
        MINGW*|MSYS*|CYGWIN*|Windows_NT)
            os="windows"
            ;;
        *)
            echo "ERROR: Unsupported operating system: $(uname -s)" >&2
            exit 1
            ;;
    esac

    # Detect architecture
    case "$(uname -m)" in
        arm64|aarch64)
            arch="arm64"
            ;;
        x86_64|amd64)
            arch="x86_64"
            ;;
        *)
            echo "ERROR: Unsupported architecture: $(uname -m)" >&2
            exit 1
            ;;
    esac

    echo "${os}-${arch}"
}

PLATFORM=$(detect_platform)
echo "Building for platform: $PLATFORM"

# =============================================================================
# Nuitka Build (T008)
# =============================================================================

# Clean previous build artifacts
rm -rf dist/pgtail.build dist/pgtail.dist dist/pgtail.onefile-build

# Run Nuitka with all required flags per research.md
# IMPORTANT:
#   - Use --mode=standalone (NOT --mode=onefile) for instant startup
#   - NEVER use --python-flag=no_docstrings (breaks Typer CLI help)
echo "Running Nuitka build..."

uv run nuitka \
    --mode=standalone \
    --output-dir=dist \
    --output-filename=pgtail \
    --include-package=pgtail_py \
    --include-package=psutil \
    --include-package-data=certifi \
    --include-module=pgtail_py.detector_unix \
    --include-module=pgtail_py.detector_windows \
    --include-module=pgtail_py.notifier_unix \
    --include-module=pgtail_py.notifier_windows \
    --python-flag=no_asserts \
    --assume-yes-for-downloads \
    pgtail_py/__main__.py

# =============================================================================
# Post-Build Rename (T010)
# =============================================================================

# Nuitka outputs to either pgtail.dist/ or __main__.dist/ depending on input
# Rename to pgtail-{platform}-{arch}/
OUTPUT_DIR="dist/pgtail-$PLATFORM"

NUITKA_OUTPUT=""
if [ -d "dist/pgtail.dist" ]; then
    NUITKA_OUTPUT="dist/pgtail.dist"
elif [ -d "dist/__main__.dist" ]; then
    NUITKA_OUTPUT="dist/__main__.dist"
else
    echo "ERROR: Nuitka output directory not found (looked for dist/pgtail.dist and dist/__main__.dist)" >&2
    exit 1
fi

rm -rf "$OUTPUT_DIR"
mv "$NUITKA_OUTPUT" "$OUTPUT_DIR"
echo "Renamed $NUITKA_OUTPUT to: $OUTPUT_DIR"

# Clean up intermediate build directories
rm -rf dist/pgtail.build dist/__main__.build dist/pgtail.onefile-build dist/__main__.onefile-build

# Verify build
EXECUTABLE="$OUTPUT_DIR/pgtail"
if [ "$PLATFORM" = "windows-x86_64" ]; then
    EXECUTABLE="$OUTPUT_DIR/pgtail.exe"
fi

if [ -x "$EXECUTABLE" ] || [ -f "$EXECUTABLE" ]; then
    echo ""
    echo "Build successful!"
    echo "Executable: $EXECUTABLE"
    echo ""
    echo "Verifying version..."
    "$EXECUTABLE" --version
else
    echo "ERROR: Executable not found at $EXECUTABLE" >&2
    exit 1
fi
