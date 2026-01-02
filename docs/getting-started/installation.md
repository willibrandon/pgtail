# Installation

## Requirements

- Python 3.10 or higher (for pip/pipx/uv installation)
- PostgreSQL with logging enabled

## pip / pipx / uv (Python 3.10+)

```bash
# pip
pip install git+https://github.com/willibrandon/pgtail.git

# pipx (recommended for CLI tools - isolated environment)
pipx install git+https://github.com/willibrandon/pgtail.git

# uv (fast Python package manager)
uv tool install git+https://github.com/willibrandon/pgtail.git
```

Install a specific version:

```bash
pip install git+https://github.com/willibrandon/pgtail.git@v0.2.0
```

## Homebrew (macOS / Linux)

```bash
brew tap willibrandon/tap
brew install pgtail
```

## winget (Windows)

```powershell
winget install willibrandon.pgtail
```

## Binary Download

Download pre-built archives from [GitHub Releases](https://github.com/willibrandon/pgtail/releases/latest).

| Platform | Archive | Python Required |
|----------|---------|-----------------|
| macOS (Apple Silicon) | `pgtail-macos-arm64.tar.gz` | No |
| macOS (Intel) | `pgtail-macos-x86_64.tar.gz` | No |
| Linux (x86_64) | `pgtail-linux-x86_64.tar.gz` | No |
| Linux (ARM64) | `pgtail-linux-arm64.tar.gz` | No |
| Windows (x86_64) | `pgtail-windows-x86_64.zip` or `.msi` | No |

### macOS / Linux Installation

```bash
# Download the archive for your platform
curl -LO https://github.com/willibrandon/pgtail/releases/latest/download/pgtail-macos-arm64.tar.gz

# Extract the archive
tar -xzf pgtail-macos-arm64.tar.gz

# Run pgtail from the extracted folder
./pgtail-macos-arm64/pgtail --version

# Optional: Install to PATH
sudo cp -r pgtail-macos-arm64 /usr/local/lib/
sudo ln -s /usr/local/lib/pgtail-macos-arm64/pgtail /usr/local/bin/pgtail
```

### Windows Installation

**Option 1: MSI Installer (Recommended)**

The MSI installer requires administrator privileges and automatically adds pgtail to your system PATH.

```powershell
# Download and run the MSI
msiexec /i pgtail-windows-x86_64.msi

# After installation, pgtail is available system-wide
pgtail --version
```

**Option 2: ZIP (Portable)**

The ZIP archive requires no admin privileges and can be run from any location.

```powershell
# Download and extract
Expand-Archive pgtail-windows-x86_64.zip -DestinationPath .

# Run from the extracted folder
.\pgtail-windows-x86_64\pgtail.exe --version

# Optional: Add to PATH manually via System Properties
```

| Method | Admin Required | Adds to PATH | Best For |
|--------|----------------|--------------|----------|
| MSI | Yes | Yes | Permanent installation |
| ZIP | No | No | Portable/USB, testing |

## From Source

```bash
git clone https://github.com/willibrandon/pgtail.git
cd pgtail
pip install -e .
```

## Development Setup

```bash
git clone https://github.com/willibrandon/pgtail
cd pgtail
make run  # Run from source
make test # Run tests
make lint # Lint code
```

## Installation Summary

| Method | Platforms | Python Required | Auto-Update | Notes |
|--------|-----------|-----------------|-------------|-------|
| pip / pipx / uv | All | Yes (3.10+) | Manual | |
| Homebrew | macOS, Linux | No | `brew upgrade` | |
| winget | Windows | No | `winget upgrade` | |
| MSI | Windows | No | Manual | Admin required, adds to PATH |
| ZIP/tar.gz | All | No | Manual | Portable, extract and run |

## Verify Installation

```bash
pgtail --version
```

Or start the REPL:

```bash
pgtail
pgtail> help
```

## Upgrading

Check for available updates:

```bash
pgtail --check-update
```

Upgrade commands by installation method:

| Method | Upgrade Command |
|--------|-----------------|
| pip | `pip install --upgrade git+https://github.com/willibrandon/pgtail.git` |
| pipx | `pipx upgrade pgtail` |
| uv | `uv tool upgrade pgtail` |
| Homebrew | `brew upgrade pgtail` |
| winget | `winget upgrade willibrandon.pgtail` |
| MSI | Download and run new MSI |
| ZIP/tar.gz | Re-download and extract from [releases](https://github.com/willibrandon/pgtail/releases/latest) |

pgtail checks for updates automatically on startup (once per 24 hours). Disable with:

```bash
pgtail set updates.check false
```

## Troubleshooting

### macOS: Binary won't run (Gatekeeper)

macOS blocks unsigned binaries downloaded from the internet. Remove the quarantine flag from the extracted folder:

```bash
xattr -dr com.apple.quarantine pgtail-macos-arm64/
```

Or: **System Preferences → Security & Privacy → General → Allow Anyway**

### macOS: Wrong architecture

If you see `Bad CPU type in executable`, download the correct archive:

- Apple Silicon (M1/M2/M3): `pgtail-macos-arm64.tar.gz`
- Intel Mac: `pgtail-macos-x86_64.tar.gz`

Check your architecture: `uname -m` (arm64 or x86_64)

### Windows: SmartScreen warning

Windows SmartScreen may block the executable. Click **"More info"** → **"Run anyway"**.

For the MSI installer, you may also see this warning during installation.

### Windows: Antivirus blocking dependencies

Some antivirus software may flag the bundled Python libraries. If pgtail fails to start:

1. Add the pgtail folder to your antivirus exclusions
2. Or use the MSI installer (signed with Microsoft's requirements)
3. Check Windows Defender: **Windows Security → Virus & threat protection → Protection history**

### Linux: Wrong architecture

If you see `cannot execute binary file: Exec format error`, download the correct archive:

- x86_64 (Intel/AMD): `pgtail-linux-x86_64.tar.gz`
- ARM64 (Raspberry Pi 4, AWS Graviton): `pgtail-linux-arm64.tar.gz`

Check your architecture: `uname -m` (x86_64 or aarch64)

### Missing dependency folder

pgtail is distributed as a folder containing the executable and its dependencies. If you see errors about missing libraries:

- Ensure the **entire folder** was extracted (not just the `pgtail` executable)
- The executable must remain in its folder with all `.so`/`.dylib`/`.dll` files
- Do not move only the executable; move the entire folder
- If using symlinks, link to the executable, not the folder

**Example correct structure:**
```
pgtail-macos-arm64/
├── pgtail           # Main executable
├── Python           # Python runtime
├── libssl.3.dylib   # SSL library
├── certifi/         # CA certificates
└── ...              # Other dependencies
```

### Windows: MSI vs ZIP installation paths

| Install Method | Installation Path | PATH |
|----------------|------------------|------|
| MSI | `C:\Program Files\pgtail\` | Automatically added |
| ZIP | Wherever you extract | Manual configuration |

If you have both installed, the MSI version takes precedence if its path is listed first in the system PATH.

### Unsupported platform/architecture

If your platform/architecture is not listed in the release assets, you can compile from source:

```bash
git clone https://github.com/willibrandon/pgtail.git
cd pgtail

# Option 1: Install as Python package
pip install -e .

# Option 2: Build standalone binary with Nuitka
pip install nuitka
make build
# Output: dist/pgtail-{platform}-{arch}/pgtail
```

Supported platforms for pre-built binaries:
- macOS: Apple Silicon (arm64), Intel (x86_64)
- Linux: x86_64, ARM64 (aarch64)
- Windows: x86_64

### Update check fails

If `pgtail --check-update` shows "Unable to check for updates":

- Check your internet connection
- The GitHub API may be rate-limited (60 requests/hour for unauthenticated users)
- No releases exist yet (404 is handled silently)

### Binary updates

Pre-built archives do not auto-update. To update:

1. Download the new version from [GitHub Releases](https://github.com/willibrandon/pgtail/releases/latest)
2. Extract and replace the old folder
3. On macOS, you may need to remove the quarantine flag again
4. Update any symlinks if you created them

## PostgreSQL Configuration

For pgtail to work, PostgreSQL logging must be enabled. The minimal configuration in `postgresql.conf`:

```ini
# Enable logging
logging_collector = on
log_directory = 'log'

# Choose your preferred format
log_destination = 'stderr'  # TEXT format (default)
# log_destination = 'csvlog'  # CSV format (26 fields)
# log_destination = 'jsonlog' # JSON format (PG15+)

# Recommended: log all statements for development
log_statement = 'all'
log_duration = on
```

Reload PostgreSQL after changes:

```bash
pg_ctl reload
```
