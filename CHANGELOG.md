# Changelog

All notable changes to pgtail are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-01-13

### Added
- REPL bottom toolbar showing instance count, active filters, and current theme
- Shell mode indicator ("SHELL • Press Escape to exit") in toolbar
- Toolbar styles for all 6 built-in themes (dark, light, high-contrast, monokai, solarized-dark, solarized-light)
- `ls` command as alias for `list`
- Shell completion documentation

### Fixed
- Escape key now responds instantly in shell mode (removed 2-second delay)

## [0.3.0] - 2025-01-12

### Added
- `tail --file <path>` option to tail arbitrary log files
- `tail --stdin` option to read log data from pipes
- Glob pattern support for multi-file tailing (`tail --file "*.log"`)
- Multi-file interleaving with `[filename]` prefix indicators
- Windows application icon

## [0.2.4] - 2025-01-04

### Fixed
- Windows REPL startup error handling

## [0.2.3] - 2025-01-03

### Fixed
- Exit silently when stdin is not a TTY

## [0.2.2] - 2025-01-02

### Fixed
- Windows standalone launch detection for winget compatibility

## [0.2.1] - 2025-01-02

### Added
- pgtail logo in docs and README

### Fixed
- Exit gracefully when stdin is not a TTY
- Windows scroll animation timing in tests

## [0.2.0] - 2025-01-01

### Added
- Nuitka standalone binary distribution (replaces PyInstaller)
- Windows MSI installer with WiX
- winget package submission
- Homebrew tap with tar.gz archives
- Automatic update checking

### Changed
- Migrated build system from PyInstaller to Nuitka for better performance

## [0.1.0] - 2025-01-01

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

[0.4.0]: https://github.com/willibrandon/pgtail/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/willibrandon/pgtail/compare/v0.2.4...v0.3.0
[0.2.4]: https://github.com/willibrandon/pgtail/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/willibrandon/pgtail/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/willibrandon/pgtail/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/willibrandon/pgtail/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/willibrandon/pgtail/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/willibrandon/pgtail/releases/tag/v0.1.0
