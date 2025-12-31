<!--
Sync Impact Report
==================
Version Change: 2.0.0 → 2.1.0
Bump Rationale: MINOR - Added Textual as approved TUI library for fullscreen interfaces

Modified Principles:
- VI. Minimal Dependencies: Expanded approved dependencies to include Textual for rich TUI applications

Added Sections: None

Removed Sections: None

Templates Requiring Updates:
- .specify/templates/plan-template.md: ✅ Compatible (language-agnostic placeholders)
- .specify/templates/spec-template.md: ✅ Compatible (no language-specific references)
- .specify/templates/tasks-template.md: ✅ Compatible (language-agnostic placeholders)
- .specify/templates/checklist-template.md: ✅ Compatible (no language-specific references)
- .specify/templates/agent-file-template.md: ✅ Compatible (no language-specific references)

Follow-up TODOs: None
-->

# pgtail Constitution

## Core Principles

### I. Simplicity First

pgtail MUST prioritize simplicity in all design decisions:

- **Zero Configuration**: Common use cases (pgrx development, Homebrew installs, standard system packages) MUST work without any user configuration
- **Memorable Commands**: The command set MUST be small enough to memorize; prefer fewer commands with clear semantics over many specialized commands
- **Self-Documenting**: New users MUST be productive after reading only the `help` output; no external documentation required for basic usage

**Rationale**: Developers use pgtail to solve an immediate problem (finding logs). Any friction defeats the tool's purpose.

### II. Cross-Platform Parity

pgtail MUST behave identically on macOS, Linux, and Windows:

- **Feature Equivalence**: Every feature available on one platform MUST be available on all platforms (or gracefully degrade with clear messaging)
- **Isolation of Platform Code**: Platform-specific code MUST be isolated in dedicated modules (e.g., `detector_unix.py`, `detector_windows.py`)
- **Path Handling**: All file path operations MUST use `pathlib` or `os.path`; never hardcode path separators
- **Cross-Platform Libraries**: Use only dependencies that support all three platforms (e.g., `psutil`, `textual`)

**Rationale**: PostgreSQL developers work across platforms. A tool that only works on one OS provides limited value.

### III. Graceful Degradation

pgtail MUST never crash or halt due to detection or access failures:

- **Continue on Failure**: If one detection method fails (e.g., process scanning), continue with remaining methods (path scanning, env vars)
- **Skip Unreadable Logs**: If a log file cannot be read (permissions, locked), report the issue and skip—do not error out
- **Partial Results**: Always return whatever information was successfully gathered, even if incomplete
- **Clear Error Attribution**: When skipping a source, explain why (e.g., "Skipped /var/lib/pgsql: permission denied")

**Rationale**: Users need whatever information is available, not a perfect result or nothing.

### IV. User-Friendly Feedback

All user-facing messages MUST be actionable and helpful:

- **Actionable Errors**: Error messages MUST suggest next steps (e.g., "Did you mean...?", "Try running with sudo")
- **State Visibility**: The prompt MUST indicate current state (selected instance, active filters)
- **Color-Coded Output**: Log levels MUST be color-coded for quick visual scanning (ERROR=red, WARNING=yellow, etc.)
- **Consistent Formatting**: Tables and lists MUST align properly; use consistent spacing

**Rationale**: A CLI tool's usability depends heavily on the quality of its feedback.

### V. Focused Scope

pgtail MUST NOT expand beyond its core purpose:

- **Local Only**: No remote instance support; this is explicitly out of scope
- **Tailing Only**: No log aggregation, persistence, or long-term storage
- **Detection Only**: No PostgreSQL administration features (start/stop/configure)
- **Basic Filtering Only**: Support log level filtering; no complex query languages or regex matching

**Rationale**: A focused tool that does one thing well is more valuable than a bloated tool that does many things poorly.

### VI. Minimal Dependencies

pgtail MUST minimize external dependencies:

- **Justified Additions**: Each dependency MUST provide clear cross-platform value that would be expensive to replicate
- **Standard Library Preference**: Prefer Python standard library when functionality is adequate
- **Mandatory REPL Library**: The REPL MUST use `prompt_toolkit` for autocomplete and history; no custom or simplified implementations. Reference source: `../python-prompt-toolkit/`
- **Approved TUI Library**: For rich fullscreen terminal interfaces (log selection, interactive browsers), `textual` MAY be used. Reference source: `../textual/`
- **Approved Dependencies**: Core approved dependencies are:
  - `prompt_toolkit` (REPL with autocomplete/history - REQUIRED) - Local reference: `../python-prompt-toolkit/`
  - `textual` (fullscreen TUI applications with widgets - OPTIONAL for advanced interfaces) - Local reference: `../textual/`
  - `psutil` (cross-platform process detection)
  - `watchdog` (file system monitoring)

**Rationale**: Fewer dependencies mean easier maintenance, faster builds, and fewer security vulnerabilities. prompt_toolkit is mandatory because autocomplete and history are core UX requirements, not optional polish. python-prompt-toolkit has superior terminal color detection compared to alternatives. Textual provides a modern widget system for complex interactive screens without reimplementing terminal UI primitives.

### VII. Developer Workflow Priority

pgtail MUST optimize for the developer experience, especially pgrx workflows:

- **10-Second Goal**: A developer MUST be able to find and tail any PostgreSQL log within 10 seconds of launching pgtail
- **pgrx First-Class**: pgrx data directories (`~/.pgrx/data-{version}`) MUST be auto-detected with highest priority after running processes
- **No Manual Configuration**: Auto-detection MUST work for all common installation methods without requiring user input

**Rationale**: The primary audience is PostgreSQL extension developers who need fast access to logs during development.

## Technical Constraints

- **Language**: Python 3.10+
- **Build Target**: Single executable via PyInstaller or similar for each platform
- **Terminal Support**: MUST work in standard terminals (iTerm2, Terminal.app, Windows Terminal, GNOME Terminal, etc.)
- **Minimum Terminal Width**: 80 columns; gracefully truncate wider output

## Quality Standards

- **Test Coverage**: Core detection and parsing logic MUST have unit tests
- **Error Handling**: All errors MUST be handled; no unhandled exceptions except for truly unrecoverable situations
- **Documentation**: Each Python module MUST have a docstring explaining its purpose
- **Linting**: Code MUST pass `ruff` or equivalent linter with default configuration
- **Type Hints**: All public functions MUST have type annotations

## Governance

This constitution supersedes all other project guidelines. All contributions MUST comply with these principles.

**Amendment Process**:
1. Propose changes via pull request with rationale
2. Changes require explicit approval from project maintainers
3. Breaking changes to principles require migration plan for existing code

**Version Policy**:
- MAJOR: Principle removal or fundamental redefinition
- MINOR: New principle added or existing principle materially expanded
- PATCH: Clarifications, wording improvements, non-semantic changes

**Compliance Review**:
- All PRs MUST be verified against these principles before merge
- Complexity additions MUST be justified against Simplicity First and Minimal Dependencies principles

**Version**: 2.1.0 | **Ratified**: 2025-12-14 | **Last Amended**: 2025-12-31
