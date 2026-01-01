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
pip install git+https://github.com/willibrandon/pgtail.git@v0.1.0
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

Download pre-built binaries from [GitHub Releases](https://github.com/willibrandon/pgtail/releases/latest).

| Platform | Binary | Python Required |
|----------|--------|-----------------|
| macOS (Apple Silicon) | `pgtail-macos-arm64` | No |
| macOS (Intel) | `pgtail-macos-x86_64` | No |
| Linux (x86_64) | `pgtail-linux-x86_64` | No |
| Linux (ARM64) | `pgtail-linux-arm64` | No |
| Windows (x86_64) | `pgtail-windows-x86_64.exe` | No |

After downloading, make the binary executable (macOS/Linux):

```bash
chmod +x pgtail-macos-arm64
./pgtail-macos-arm64 --version
```

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

| Method | Platforms | Python Required | Auto-Update |
|--------|-----------|-----------------|-------------|
| pip / pipx / uv | All | Yes (3.10+) | Manual |
| Homebrew | macOS, Linux | No | `brew upgrade` |
| winget | Windows | No | `winget upgrade` |
| Binary | All | No | Manual re-download |

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
| Binary | Re-download from [releases](https://github.com/willibrandon/pgtail/releases/latest) |

pgtail checks for updates automatically on startup (once per 24 hours). Disable with:

```bash
pgtail set updates.check false
```

## Troubleshooting

### macOS: Binary won't run (Gatekeeper)

macOS blocks unsigned binaries downloaded from the internet. Remove the quarantine flag:

```bash
xattr -d com.apple.quarantine pgtail-macos-arm64
```

Or: **System Preferences → Security & Privacy → General → Allow Anyway**

### macOS: Wrong architecture binary

If you see `Bad CPU type in executable`, download the correct binary:

- Apple Silicon (M1/M2/M3): `pgtail-macos-arm64`
- Intel Mac: `pgtail-macos-x86_64`

Check your architecture: `uname -m` (arm64 or x86_64)

### Windows: SmartScreen warning

Windows SmartScreen may block the binary. Click **"More info"** → **"Run anyway"**.

### Linux: Wrong architecture binary

If you see `cannot execute binary file: Exec format error`, download the correct binary:

- x86_64 (Intel/AMD): `pgtail-linux-x86_64`
- ARM64 (Raspberry Pi 4, AWS Graviton): `pgtail-linux-arm64`

Check your architecture: `uname -m` (x86_64 or aarch64)

### Update check fails

If `pgtail --check-update` shows "Unable to check for updates":

- Check your internet connection
- The GitHub API may be rate-limited (60 requests/hour for unauthenticated users)
- No releases exist yet (404 is handled silently)

### Binary updates

Pre-built binaries do not auto-update. To update:

1. Download the new version from [GitHub Releases](https://github.com/willibrandon/pgtail/releases/latest)
2. Replace the old binary
3. On macOS, you may need to remove the quarantine flag again

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
