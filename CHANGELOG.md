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
- `slow` in tail mode colors slow queries in the log, as streamed output does, instead of only updating the status bar.
- Update checks suggest the upgrade command for the way pgtail was installed.
- Shell completion offers options once the word starts with `-`, so `pgtail <Tab>` lists commands.
- Time windows and `errors --trend` compare timestamps in UTC, fixing errors when mixing logs with and without time zones.
- Times show as the log wrote them in every format; csvlog and jsonlog times were shown converted to UTC. JSON and CSV
  export keep the offset the time was written with.
- In text logs, a message's `DETAIL:`, `HINT:`, `CONTEXT:`, `STATEMENT:`, `QUERY:`, and `LOCATION:` lines and the
  further lines of a multi-line message stay with the entry they belong to, so level filters keep them and an error
  counts once.
- Tail mode's `tail>` input keeps the focus after a command, so the next one can be typed at once instead of the keys
  scrolling or selecting in the log; text typed on the log that is not one of its keys goes to the input, and `tail>`
  stays in front of the text. A command's output shows in a panel above the input until the next command or Escape,
  instead of in the log where new entries scrolled it away. The `?` key reference fits the screen and scrolls.

### Added
- **.NET tool**: `dotnet tool install -g pgtail` installs the native executable for Windows, Linux, and macOS on x64 and
  Arm64, or a framework-dependent build elsewhere.
- Windows Arm64 archive (`pgtail-windows-arm64.zip`), also offered through Scoop.
- `pgtail list` as an alias of `pgtail list-instances`, and `pgtail enable-logging <id>` on the command line.
- `pgtail tail --stdin --stream` prints piped input through the filters, for use without a terminal.
- `Ctrl+R` reverse history search at the REPL prompt, and the shell's line editing keys (Ctrl+A/E/B/F/K/U/W/Y,
  Alt+B/F/D) at the prompt and in tail mode's command input, as prompt_toolkit gave the Python REPL.
- Mouse support in tail mode: the wheel scrolls (Shift scrolls sideways), a click selects a line, and a drag selects
  text and copies it.
- Detection finds every Debian cluster, PGDG `/var/lib/pgsql/*/data`, every Homebrew `postgresql@*`, Arch Linux's
  `/var/lib/postgres/data`, and Postgres.app data directories. A Debian or Ubuntu cluster is found from its
  configuration in `/etc/postgresql` even when its data directory is closed to the user.
- Debian and Ubuntu clusters with the logging collector off, as installed, are tailed from the file `pg_ctlcluster`
  writes, `/var/log/postgresql/postgresql-<version>-<cluster>.log` (or the target of the cluster's `log` link), and a
  permission error there suggests joining the `adm` group.
- Text logs with a longer `log_line_prefix` that starts with the time are read, such as Debian and Ubuntu's
  `'%m [%p] %q%u@%d '`, whose lines were shown unparsed; its user and database show in the full display.

### Fixed
- `notify on /pattern with spaces/` keeps the whole pattern; it was cut at the first space.
- Deleting back to an empty line at the REPL prompt closes the completion menu instead of listing every command.
- `level` works at the REPL prompt and `levels` in tail mode, so the level filter command has the same name in both.
- A misspelled setting in `config.toml` is reported at startup instead of being ignored silently, and the built-in
  editor saves only settings pgtail knows with valid values.
- The editor no longer reports unsaved changes after edits are undone back to the saved text.
- On Windows, copying from tail mode through `clip.exe` sends a byte order mark, which `clip.exe` needs to read the text
  as UTF-16.
- On Windows, pgtail started directly by a terminal, such as a Windows Terminal profile whose command is `pgtail`, runs
  the REPL instead of exiting at once; it still exits silently when started with no terminal, as by package validation.

### Removed
- The settings `default.follow`, `display.timestamp_format`, `display.show_pid`, `display.show_level`,
  `updates.last_version`, and `buffer.*`,
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
