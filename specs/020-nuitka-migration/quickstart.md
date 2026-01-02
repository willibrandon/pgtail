# Quickstart: Local Nuitka Build Verification

**Feature Branch**: `020-nuitka-migration`

This guide walks through building and verifying a Nuitka-compiled pgtail binary locally before CI integration.

---

## Prerequisites

1. **Python 3.10+** installed
2. **uv** package manager installed
3. **C compiler** available:
   - macOS: Xcode Command Line Tools (`xcode-select --install`)
   - Linux: GCC (`apt install build-essential` or equivalent)
   - Windows: Visual Studio 2022 or MinGW-w64

---

## Step 1: Install Dependencies

```bash
# Navigate to pgtail repository
cd /Users/brandon/src/pgtail

# Sync dependencies including Nuitka
uv sync --extra dev
```

Verify Nuitka is installed:
```bash
uv run nuitka --version
# Expected: Nuitka version 2.5.x or higher
```

---

## Step 2: Add Version Fallback (if not already done)

Check `pgtail_py/__init__.py`:
```python
"""pgtail - PostgreSQL log tailer with auto-detection and color output."""

__version__ = "0.2.0"
```

Check `pgtail_py/version.py` has fallback:
```python
def get_version() -> str:
    try:
        return importlib.metadata.version("pgtail")
    except importlib.metadata.PackageNotFoundError:
        from pgtail_py import __version__
        return __version__
```

---

## Step 3: Build with Nuitka

### Option A: Use Makefile (recommended)

```bash
make build
```

### Option B: Direct Command

```bash
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
```

**Expected output**:
- Build takes 10-15 minutes on first run
- Creates `dist/pgtail.dist/` directory

---

## Step 4: Rename Output

```bash
# Detect platform
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
[ "$ARCH" = "aarch64" ] && ARCH="arm64"
[ "$ARCH" = "amd64" ] && ARCH="x86_64"

# Rename
mv dist/pgtail.dist dist/pgtail-${PLATFORM}-${ARCH}

echo "Build complete: dist/pgtail-${PLATFORM}-${ARCH}/"
```

---

## Step 5: Verify Build

### 5.1 Check Version

```bash
./dist/pgtail-*/pgtail --version
```

**Expected**: `pgtail 0.2.0` (or current version, NOT `0.0.0-dev`)

### 5.2 Check Help Text

```bash
./dist/pgtail-*/pgtail list --help
```

**Expected**: Command descriptions visible (not blank). This confirms docstrings are preserved.

### 5.3 Measure Startup Time

```bash
time ./dist/pgtail-*/pgtail --version
```

**Expected**: < 1 second total (down from 5.1 seconds with PyInstaller)

### 5.4 Test Basic Functionality

```bash
# List PostgreSQL instances
./dist/pgtail-*/pgtail list

# Run REPL (Ctrl+D to exit)
./dist/pgtail-*/pgtail
```

### 5.5 Check Binary Size

```bash
du -sh dist/pgtail-*/
```

**Expected**: 20-30 MB (under 50 MB limit)

---

## Step 6: Create Archive (optional)

### Unix/macOS

```bash
cd dist
tar -czvf pgtail-${PLATFORM}-${ARCH}.tar.gz pgtail-${PLATFORM}-${ARCH}/
ls -lh pgtail-*.tar.gz
```

### Windows (PowerShell)

```powershell
Compress-Archive -Path dist\pgtail-windows-x86_64 -DestinationPath dist\pgtail-windows-x86_64.zip
```

---

## Step 7: Clean Up

```bash
make clean
```

Or manually:
```bash
rm -rf dist/ build/ pgtail.build/ pgtail.dist/
```

---

## Troubleshooting

### Issue: Version shows "0.0.0-dev"

**Cause**: `__version__` fallback not implemented in `pgtail_py/__init__.py`

**Fix**: Add `__version__ = "0.2.0"` to `pgtail_py/__init__.py`

### Issue: Help text is blank

**Cause**: Build used `--python-flag=no_docstrings`

**Fix**: Remove that flag from build command (NEVER use it with Typer)

### Issue: ImportError for psutil

**Cause**: Native extension not included

**Fix**: Add `--include-package=psutil` to build command

### Issue: SSL certificate errors

**Cause**: certifi CA bundle not included

**Fix**: Add `--include-package-data=certifi` to build command

### Issue: Module not found (detector_unix, etc.)

**Cause**: Conditional imports not detected by Nuitka

**Fix**: Add explicit `--include-module=pgtail_py.detector_unix` etc.

### Issue: Build hangs prompting for input

**Cause**: Nuitka waiting for download approval

**Fix**: Add `--assume-yes-for-downloads` flag

---

## Success Criteria Checklist

Before proceeding to CI integration, verify:

- [ ] `pgtail --version` shows correct version (not 0.0.0-dev)
- [ ] `pgtail list --help` shows command descriptions
- [ ] Startup time < 1 second
- [ ] Binary size < 50 MB
- [ ] `pgtail list` detects PostgreSQL instances
- [ ] REPL mode works (`pgtail` command)
- [ ] Archive extracts correctly

---

## Next Steps

After local verification succeeds:
1. Update Makefile `build` target with Nuitka command
2. Update `.github/workflows/release.yml` with new build process
3. Tag release `v0.2.0` to trigger CI workflow
