# Changelog

All notable changes to pgtail are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **pgtail is now a .NET 10 application** published with Native AOT: each release is a single native executable per
  platform, with no Python or other runtime to install. The REPL, tail mode, and editor are built on
  [Hex1b](https://github.com/mitchdenny/hex1b); log matching, globbing, and detection use Scout's byte-oriented regular
  expressions and file walking.
- Commands come from one catalog per mode that drives dispatch, completion, and help, so the REPL's completion menu, tail
  mode's suggestions, and `help` always agree.
- `config edit`, `pgtail config --edit`, and `theme edit` open a built-in editor with TOML highlighting that checks the
  file before saving, instead of `$EDITOR`.
- Tail mode keeps every entry it reads and applies filters when displaying, so `clear` brings back entries that a
  narrower filter hid.
- Moving the cursor off the newest line in tail mode stops following and shows `PAUSED`; returning to the end resumes.
  Long lines scroll sideways to keep the cursor in view.
- `export --highlighted` keeps colors as ANSI escapes, and text export writes log lines exactly as PostgreSQL wrote them.
- `pipe` runs its command through the shell, so pipelines and quoting work.
- Tail mode reports unknown commands and bad filter values instead of ignoring them.
- Update checks suggest the upgrade command for the way pgtail was installed.
- Shell completion offers options once the word starts with `-`, so `pgtail <Tab>` lists commands.
- Time windows and `errors --trend` compare timestamps in UTC, fixing errors when mixing logs with and without time zones.
- In text logs, a message's `DETAIL:`, `HINT:`, `CONTEXT:`, `STATEMENT:`, `QUERY:`, and `LOCATION:` lines and the
  further lines of a multi-line message stay with the entry they belong to, so level filters keep them and an error
  counts once.

### Added
- **.NET tool**: `dotnet tool install -g pgtail` installs the native executable for Windows, Linux, and macOS on x64 and
  Arm64, or a framework-dependent build elsewhere.
- Windows Arm64 archive (`pgtail-windows-arm64.zip`), also offered through Scoop.
- `pgtail list` as an alias of `pgtail list-instances`, and `pgtail enable-logging <id>` on the command line.
- `pgtail tail --stdin --stream` prints piped input through the filters, for use without a terminal.
- Mouse support in tail mode: the wheel scrolls (Shift scrolls sideways), a click selects a line, and a drag selects
  text and copies it.
- Detection finds every Debian cluster, PGDG `/var/lib/pgsql/*/data`, every Homebrew `postgresql@*`, and Postgres.app
  data directories.

### Removed
- The settings `default.follow`, `display.timestamp_format`, `display.show_pid`, `display.show_level`, and `buffer.*`,
  which were validated and stored but never used.
- Installing with pip, pipx, or uv.

## [0.6.1] - 2026-06-10

### Changed
- Minimum Python is now 3.11 (dropped 3.10); CI tests 3.11, 3.12, and 3.13

### Fixed
- Tail view crash on log lines with a backslash directly before highlighted text, such as Windows paths in `COPY ... TO 'c:\...'` or regex character classes in logged SQL; log content is now rendered as Rich Text rather than parsed as Rich markup

## [0.6.0] - 2026-03-20

### Added
- **Command history** in tail mode with Up/Down arrow navigation, persisted across sessions (up to 500 entries)
- **Ghost text autocomplete** in tail command input with context-aware suggestions for commands, flags, values, and history fallback
- **WinRT COM toast notifications** on Windows, replacing PowerShell-based notifications for faster, more reliable desktop alerts

### Changed
- Removed deprecated prompt_toolkit tail modules (`tail_app.py`, `tail_buffer.py`, `tail_layout.py`) and ~2,100 lines of dead code paths
- Removed specs, speckit, and claude agent scaffolding (~45,000 lines)

### Performance
- Converted highlighter `Match` from frozen dataclass to `NamedTuple` for 75% faster highlighting throughput (4,100 → 7,200 lines/sec)
- Re-enabled LRU render cache in tail log display
- Fast-path append in `OccupancyTracker.mark_occupied` and cached property lookups in hot loops

### Fixed
- Non-blocking rebuild in tail mode with correct status feedback
- Makefile UV path using backslashes that MSYS bash can't parse
- Build script missing `--extra dev` flag for nuitka dependency

## [0.5.1] - 2026-03-01

### Fixed
- Debian/Ubuntu PostgreSQL detection: config files in `/etc/postgresql/<version>/<cluster>/` are now found correctly
- Version detection falls back to extracting from Debian data directory path when `PG_VERSION` is unreadable
- Platform-aware permission advice: Windows shows icacls/Administrator guidance, Linux shows log_file_mode/usermod, macOS shows Homebrew-specific paths
- Status bar shows "(permission denied)" instead of generic "(unavailable)" when log file exists but is unreadable
- `enable-logging` command threads config path through for Debian layout and shows checked paths on failure
- Tailer handles Windows edge case where deleted files briefly raise PermissionError instead of FileNotFoundError
- Windows test stability: retry file unlink when tailer poll thread holds handle open

## [0.5.0] - 2026-01-16

### Added
- **Semantic Highlighting**: 29 built-in highlighters for PostgreSQL log patterns
  - Timestamps, PIDs, SQLSTATE codes, durations, identifiers
  - WAL segments, LSNs, transaction IDs
  - Lock types, checkpoint messages, recovery events
  - Connection info, IP addresses, backend types
  - SQL keywords, strings, numbers, parameters (context-aware)
- `highlight` command with subcommands:
  - `highlight list` - Show all highlighters with enable/disable status
  - `highlight enable/disable <name>` - Toggle individual highlighters
  - `highlight on/off` - Global highlighting toggle
  - `highlight add <name> <pattern> [--style]` - Custom regex highlighters
  - `highlight remove <name>` - Remove custom highlighters
  - `highlight preview` - Preview all highlighters with sample output
  - `highlight reset` - Reset all settings to defaults
  - `highlight export [--file]` - Export configuration as TOML
  - `highlight import <path>` - Import configuration from file
- Duration threshold coloring (configurable slow/very slow/critical thresholds)
- SQL context awareness (SQL highlighters only apply within detected SQL regions)
- Configuration persistence for highlighting settings in config.toml

### Changed
- Consolidated SQL highlighting modules into single `highlighters/sql.py`
- Performance optimizations for 10,000+ lines/second highlighting throughput:
  - Interval-based OccupancyTracker with O(log n) availability checks
  - Cached sorted highlighter lists
  - Style lookup caching
  - Combined SQL detection regex

### Fixed
- Tail mode separator lines now span full terminal width using Rule widget

## [0.4.1] - 2026-01-14

### Fixed
- Windows log file flip-flopping between .log and .csv when PostgreSQL logs to both formats simultaneously
- Disabled mtime-based rotation detection on Windows (file reads can update mtime, causing false triggers)

## [0.4.0] - 2026-01-13

### Added
- REPL bottom toolbar showing instance count, active filters, and current theme
- Shell mode indicator ("SHELL • Press Escape to exit") in toolbar
- Toolbar styles for all 6 built-in themes (dark, light, high-contrast, monokai, solarized-dark, solarized-light)
- `ls` command as alias for `list`
- Shell completion documentation

### Fixed
- Escape key now responds instantly in shell mode (removed 2-second delay)

## [0.3.0] - 2026-01-12

### Added
- `tail --file <path>` option to tail arbitrary log files
- `tail --stdin` option to read log data from pipes
- Glob pattern support for multi-file tailing (`tail --file "*.log"`)
- Multi-file interleaving with `[filename]` prefix indicators
- Windows application icon

## [0.2.4] - 2026-01-04

### Fixed
- Windows REPL startup error handling

## [0.2.3] - 2026-01-03

### Fixed
- Exit silently when stdin is not a TTY

## [0.2.2] - 2026-01-02

### Fixed
- Windows standalone launch detection for winget compatibility

## [0.2.1] - 2026-01-02

### Added
- pgtail logo in docs and README

### Fixed
- Exit gracefully when stdin is not a TTY
- Windows scroll animation timing in tests

## [0.2.0] - 2026-01-01

### Added
- Nuitka standalone binary distribution (replaces PyInstaller)
- Windows MSI installer with WiX
- winget package submission
- Homebrew tap with tar.gz archives
- Automatic update checking

### Changed
- Migrated build system from PyInstaller to Nuitka for better performance

## [0.1.0] - 2026-01-01

### Added
- Initial release
- Auto-detection of PostgreSQL instances
- Real-time log tailing with Textual UI
- Vim-style navigation (j/k, g/G, Ctrl+d/u)
- Visual mode text selection and clipboard support
- Log level filtering with flexible syntax (error+, warning-)
- Regex pattern filtering (include, exclude, AND/OR)
- Time-based filtering (since, until, between)
- Field filtering for CSV/JSON logs (app=, db=, user=)
- Slow query detection with configurable thresholds
- SQL syntax highlighting in log messages
- 6 built-in color themes
- Desktop notifications for critical events
- Error and connection statistics
- Export to file and pipe to external commands
- Cross-platform support (macOS, Linux, Windows)

[0.6.0]: https://github.com/willibrandon/pgtail/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/willibrandon/pgtail/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/willibrandon/pgtail/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/willibrandon/pgtail/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/willibrandon/pgtail/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/willibrandon/pgtail/compare/v0.2.4...v0.3.0
[0.2.4]: https://github.com/willibrandon/pgtail/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/willibrandon/pgtail/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/willibrandon/pgtail/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/willibrandon/pgtail/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/willibrandon/pgtail/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/willibrandon/pgtail/releases/tag/v0.1.0
