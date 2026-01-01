# Contract: Nuitka Build Interface

This document defines the interface contract for building pgtail with Nuitka.

## Build Command Contract

### Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entry_point` | path | Yes | `pgtail_py/__main__.py` |
| `mode` | enum | Yes | `standalone` |
| `output_dir` | path | Yes | `dist` |
| `output_filename` | string | Yes | `pgtail` |

### Required Packages

| Package | Reason |
|---------|--------|
| `pgtail_py` | Main application package |
| `psutil` | Native extension with platform DLLs |

### Required Package Data

| Package | Reason |
|---------|--------|
| `certifi` | CA bundle (cacert.pem) for HTTPS |

### Required Modules (Conditional Imports)

| Module | Reason |
|--------|--------|
| `pgtail_py.detector_unix` | Platform detection on Unix |
| `pgtail_py.detector_windows` | Platform detection on Windows |
| `pgtail_py.notifier_unix` | Notifications on Unix |
| `pgtail_py.notifier_windows` | Notifications on Windows |

### Optimization Flags

| Flag | Status | Reason |
|------|--------|--------|
| `--python-flag=no_asserts` | ALLOWED | Safe optimization |
| `--python-flag=no_docstrings` | FORBIDDEN | Breaks Typer CLI help |

### CI Flags

| Flag | When |
|------|------|
| `--assume-yes-for-downloads` | CI builds only |

## Output Contract

### Directory Structure

```
dist/pgtail.dist/
├── pgtail              # Unix executable
├── pgtail.exe          # Windows executable
├── library.zip         # Python modules (optional)
├── certifi/
│   └── cacert.pem      # CA certificates
├── psutil/             # Native extension
└── ... (platform dependencies)
```

### Post-Build Rename

After Nuitka build, rename output:
```
pgtail.dist/ -> pgtail-{platform}-{arch}/
```

Where:
- `platform`: `macos`, `linux`, `windows`
- `arch`: `arm64`, `x86_64`

## Verification Contract

### Required Checks

1. **Executable exists**:
   ```bash
   test -f dist/pgtail-{platform}-{arch}/pgtail
   ```

2. **Version displays correctly**:
   ```bash
   ./dist/pgtail-{platform}-{arch}/pgtail --version
   # Expected: pgtail X.Y.Z (not 0.0.0-dev)
   ```

3. **Help text displays**:
   ```bash
   ./dist/pgtail-{platform}-{arch}/pgtail list --help
   # Expected: Command descriptions visible (not blank)
   ```

### Binary Size Constraint

- Maximum: 50 MB per platform
- Expected: 20-30 MB

## Archive Contract

### Unix Archives (tar.gz)

```bash
tar -czvf pgtail-{platform}-{arch}.tar.gz pgtail-{platform}-{arch}/
```

Structure:
```
pgtail-macos-arm64.tar.gz
└── pgtail-macos-arm64/
    ├── pgtail
    └── ... (dependencies)
```

### Windows Archives

**ZIP (portable)**:
```powershell
Compress-Archive -Path pgtail-windows-x86_64 -DestinationPath pgtail-windows-x86_64.zip
```

**MSI (winget)**:
Built with WiX Toolset 5.x, installs to `Program Files\pgtail\` and adds to PATH.

## Error Handling Contract

### Build Failures

If Nuitka build fails:
- Exit with non-zero status
- Log full error output
- Do not create partial artifacts

### Verification Failures

If `--version` check fails:
- Do not proceed to archive creation
- Report clear error message
- Fail the CI job

## Dependency Contract

### Build Dependencies (dev extras)

```toml
[project.optional-dependencies]
dev = [
    "nuitka>=2.5,<3.0",
    # ... other dev deps
]
```

### Runtime Dependencies (bundled)

All runtime dependencies are bundled in the standalone distribution:
- prompt_toolkit
- psutil (native)
- textual
- rich
- typer
- certifi
- pyperclip
- tomlkit
- pygments
