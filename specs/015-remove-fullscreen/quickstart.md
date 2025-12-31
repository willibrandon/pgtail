# Quickstart: Remove Fullscreen TUI

**Feature**: 015-remove-fullscreen

## Overview

This is a removal feature. The implementation involves:

1. Deleting files
2. Removing imports
3. Removing command handlers
4. Updating documentation

## Quick Implementation Checklist

### Step 1: Delete Source Files

```bash
rm -rf pgtail_py/fullscreen/
rm pgtail_py/cli_fullscreen.py
```

### Step 2: Delete Test Files

```bash
rm -rf tests/unit/fullscreen/
rm tests/integration/test_fullscreen.py
```

### Step 3: Update cli.py

Remove:
- Line 33: `from pgtail_py.cli_fullscreen import fullscreen_command`
- Line 57: `from pgtail_py.fullscreen import FullscreenState, LogBuffer`
- Lines 108-109: `fullscreen_buffer` and `fullscreen_state` fields
- Lines 202-212: `get_or_create_buffer()` and `get_or_create_fullscreen_state()` methods
- Lines 310-311: fullscreen command handling
- Lines 475-477: Update pause message

### Step 4: Update commands.py

Remove from `COMMANDS` dict:
- `"fullscreen": "Enter fullscreen TUI mode with vim-style navigation"`
- `"fs": "Enter fullscreen TUI mode (alias for fullscreen)"`

### Step 5: Update CLAUDE.md

Remove the entire "## Fullscreen TUI Mode" section and any references in other sections.

## Verification

```bash
# Check for import errors
python -c "from pgtail_py import cli"

# Run tests
make test

# Check no fullscreen references remain
grep -r "fullscreen" pgtail_py/ --include="*.py"
# Should return nothing
```
