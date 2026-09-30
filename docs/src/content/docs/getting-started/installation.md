---
title: Installation
description: Install pgtail as a .NET tool, with Homebrew, winget, or Scoop, or from a release archive.
---

pgtail is a single Native AOT executable: it needs no runtime, and nothing else has to be installed beside it.
PostgreSQL must write its logs to files, which needs `logging_collector = on` (see
[PostgreSQL configuration](#postgresql-configuration) below).

## dotnet tool

```sh
dotnet tool install -g pgtail
pgtail
```

Installing with `dotnet tool` needs the .NET 10 SDK. On Windows, Linux, and macOS on x64 and Arm64 the tool is the
Native AOT executable. On any other platform the SDK installs the portable build, which runs on the .NET 10 runtime.

## Homebrew (macOS and Linux)

```sh
brew install willibrandon/tap/pgtail
```

## winget (Windows)

```powershell
winget install willibrandon.pgtail
```

## Scoop (Windows)

```powershell
scoop bucket add willibrandon https://github.com/willibrandon/scoop-bucket
scoop install pgtail
```

## Release archives

Download an archive from [GitHub Releases](https://github.com/willibrandon/pgtail/releases/latest). Each one holds a
folder with the `pgtail` executable and the license.

| Platform | Archive |
|----------|---------|
| macOS (Apple Silicon) | `pgtail-macos-arm64.tar.gz` |
| macOS (Intel) | `pgtail-macos-x86_64.tar.gz` |
| Linux (x86_64) | `pgtail-linux-x86_64.tar.gz` |
| Linux (ARM64) | `pgtail-linux-arm64.tar.gz` |
| Windows (x86_64) | `pgtail-windows-x86_64.zip` or `pgtail-windows-x86_64.msi` |
| Windows (ARM64) | `pgtail-windows-arm64.zip` |

Every archive has a `.sha256` file beside it with its checksum.

### macOS and Linux

```sh
curl -LO https://github.com/willibrandon/pgtail/releases/latest/download/pgtail-macos-arm64.tar.gz
tar -xzf pgtail-macos-arm64.tar.gz
./pgtail-macos-arm64/pgtail --version

# Optional: put it on your PATH
sudo install -m 755 pgtail-macos-arm64/pgtail /usr/local/bin/pgtail
```

### Windows

**MSI installer (x64).** The installer needs administrator rights, installs to `C:\Program Files\pgtail\`, and adds
that folder to the system `PATH`.

```powershell
msiexec /i pgtail-windows-x86_64.msi
pgtail --version
```

**ZIP (portable).** The ZIP needs no administrator rights and runs from any folder.

```powershell
Expand-Archive pgtail-windows-x86_64.zip -DestinationPath .
.\pgtail-windows-x86_64\pgtail.exe --version
```

| Method | Admin required | Adds to PATH | Best for |
|--------|----------------|--------------|----------|
| MSI | Yes | Yes | A permanent installation |
| ZIP | No | No | Portable use and trying it out |

## From source

Building needs the .NET 10 SDK.

```sh
git clone https://github.com/willibrandon/pgtail.git
cd pgtail
dotnet build
dotnet test
dotnet run --project src/Pgtail
```

To build the Native AOT executable for your machine, publish it for your runtime identifier, such as `linux-x64`,
`linux-arm64`, `osx-arm64`, `osx-x64`, `win-x64`, or `win-arm64`:

```sh
dotnet publish src/Pgtail -c Release -r linux-x64 -o publish
./publish/pgtail --version
```

`dotnet run --file scripts/Publish-NativeAot.cs -- --rid linux-x64` publishes the same way, runs a set of checks on
the executable, and packs the runtime-specific tool package.

## Installation summary

| Method | Platforms | Update with |
|--------|-----------|-------------|
| dotnet tool | All | `dotnet tool update -g pgtail` |
| Homebrew | macOS, Linux | `brew upgrade pgtail` |
| winget | Windows | `winget upgrade willibrandon.pgtail` |
| Scoop | Windows | `scoop update pgtail` |
| MSI | Windows x64 | Download and run the new MSI |
| ZIP / tar.gz | All | Download and extract the new archive |

## Verify the installation

```sh
pgtail --version
```

Or start the REPL:

```sh
pgtail
pgtail> help
```

## Shell completion

Tab completion for commands, options, file paths, and instance IDs is available for bash, zsh, fish, and PowerShell.
Install it for your current shell:

```sh
pgtail --install-completion
```

Then restart your shell. zsh, fish, and PowerShell show each instance ID with its version, port, and status; in zsh:

```sh
$ pgtail tail <TAB>
0  -- PG17:5432 (running)
1  -- PG16:5433 (stopped)
```

See [Shell completion](/cli-reference/#shell-completion) for the details.

## Upgrading

Check for a newer release:

```sh
pgtail --check-update
```

When one exists, pgtail names the command that upgrades your installation: `dotnet tool update -g pgtail`,
`brew upgrade pgtail`, `winget upgrade willibrandon.pgtail`, or `scoop update pgtail`, or the
[releases page](https://github.com/willibrandon/pgtail/releases) for the MSI and archives.

The REPL also checks once every 24 hours when it starts, in the background, and prints a notice when a newer release
is out. To turn that off, run this in the REPL:

```pgtail
pgtail> set updates.check false
```

## Troubleshooting

### macOS: the executable won't run (Gatekeeper)

macOS blocks unsigned executables downloaded from the internet. Remove the quarantine flag:

```sh
xattr -dr com.apple.quarantine pgtail-macos-arm64/
```

Or allow it in **System Settings → Privacy & Security**.

### Wrong architecture

`Bad CPU type in executable` (macOS) or `cannot execute binary file: Exec format error` (Linux) means the archive is
for another architecture. Check yours with `uname -m`:

- `arm64` or `aarch64`: `pgtail-macos-arm64.tar.gz` or `pgtail-linux-arm64.tar.gz`
- `x86_64`: `pgtail-macos-x86_64.tar.gz` or `pgtail-linux-x86_64.tar.gz`

### Windows: SmartScreen warning

SmartScreen may block the executable or the MSI. Click **More info**, then **Run anyway**.

### Windows: MSI and ZIP both installed

The MSI installs to `C:\Program Files\pgtail\` and adds it to `PATH`; a ZIP runs from wherever you extracted it. When
both are on `PATH`, the one listed first runs.

### Update check fails

If `pgtail --check-update` says `Unable to check for updates. Check your network connection.`:

- Check your internet connection.
- The GitHub API allows 60 unauthenticated requests an hour; try again later.

## PostgreSQL configuration

PostgreSQL must write its logs to files. The minimum in `postgresql.conf`:

```ini
# Enable logging
logging_collector = on
log_directory = 'log'

# Choose your preferred format
log_destination = 'stderr'    # TEXT format (default)
# log_destination = 'csvlog'  # CSV format
# log_destination = 'jsonlog' # JSON format (PostgreSQL 15+)

# Recommended for development: log all statements
log_statement = 'all'
log_duration = on
```

Changing `logging_collector` needs a restart; other settings take effect on a reload:

```sh
pg_ctl restart   # after changing logging_collector
pg_ctl reload    # after changing other settings
```

`pgtail enable-logging <id>`, or `enable-logging <id>` in the REPL, turns on the logging collector for a detected
instance: it sets `logging_collector = on`, and `log_directory` and `log_filename` when they are not set, keeping a
backup of `postgresql.conf`. Restart PostgreSQL afterward.
