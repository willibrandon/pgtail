# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## NO DEFERRAL POLICY

**CRITICAL**: You MUST NOT defer, simplify, deprioritize, or skip ANY work. This applies to ALL tasks:

- Do NOT suggest "addressing later" or "in a future phase"
- Do NOT propose "MVP" scope reductions unless explicitly requested
- Do NOT skip "nice-to-have" features - they are requirements
- Do NOT simplify implementations to reduce complexity
- Do NOT deprioritize P2/P3 tasks - all priorities are actionable NOW
- Do NOT defer edge cases, error handling, or validation
- Do NOT suggest "optional improvements" - all improvements are mandatory
- Do NOT reduce task counts to seem more manageable

Every task, requirement, and feature exists for a reason. Implement it completely.

## SCOPE EXPANSION ONLY

**ABSOLUTE RULE**: You are FORBIDDEN from reducing scope. You may ONLY expand it.

- NEVER suggest removing features
- NEVER suggest "simplifying" by doing less
- NEVER propose cutting corners
- NEVER recommend "focusing on core functionality first"
- NEVER say "we can add that later"
- NEVER describe anything as "out of scope"
- NEVER use phrases like "for now", "initially", "as a first pass", "minimum viable"

**INSTEAD, you MUST**:
- Identify additional edge cases and ADD them to scope
- Find missing error handling and ADD it to scope
- Discover related functionality and ADD it to scope
- Notice gaps in test coverage and ADD tests to scope
- See opportunities for robustness and ADD them to scope

When in doubt: ADD MORE. The answer is always MORE scope, NEVER less.

If a task seems large, the solution is to DO ALL OF IT, not to reduce it.

**SCOPE EXPANSION ONLY**: You are FORBIDDEN from recommending scope reduction. You may ONLY recommend scope expansion. This is NON-NEGOTIABLE and ABSOLUTE.

### Prohibited Actions (INSTANT REJECTION)

Any remediation containing these patterns will be INSTANTLY REJECTED by the user:

- NEVER suggest removing features, files, or components from plan.md
- NEVER suggest removing requirements from spec.md
- NEVER suggest removing tasks from tasks.md
- NEVER suggest "simplifying" by doing less
- NEVER offer "Option A: Remove X" as a remediation
- NEVER offer multiple options where one option is removal/reduction
- NEVER recommend cutting corners or reducing task counts
- NEVER suggest "focusing on core functionality first"
- NEVER describe anything as "out of scope" or "unnecessary"
- NEVER suggest that something "isn't needed"
- NEVER suggest using a "simpler" alternative that has fewer features
- NEVER edit plan.md to remove files listed there
- NEVER edit spec.md to remove requirements listed there
- NEVER reduce the number of tasks in tasks.md

### Prohibited Phrases (DO NOT USE)

- "we can remove"
- "we can simplify"
- "isn't necessary"
- "not needed"
- "out of scope"
- "unnecessary"
- "overkill"
- "simpler approach"
- "Option A: Remove"
- "Option B: Keep" (implies removal was considered)
- "align by removing"
- "resolve by deleting"


## Debugging Policy

**CRITICAL**: When the user reports a visual bug they can see in their terminal:
- Do NOT create "minimal test apps" or "reproduction scripts"
- Do NOT run headless tests to "verify" what the user already sees
- The user's running app IS the test - trust what they report
- Add debug logging directly to the actual code paths being executed
- Ask the user to run the real app and report the debug output

## Commands

```bash
make run      # Run from source
make test     # Run all tests
make lint     # Lint code
make format   # Format code
make build    # Build single executable
make clean    # Remove build artifacts
```

## Architecture

pgtail is an interactive CLI tool for tailing PostgreSQL log files. It auto-detects PostgreSQL instances and provides real-time log streaming with level filtering.

### Package Structure (pgtail_py/)

- `pgtail_py/__main__.py` - Entry point for `python -m pgtail_py`
- `pgtail_py/cli.py` - REPL loop, command handlers, AppState
- `pgtail_py/detector.py` - Platform dispatcher for instance detection
- `pgtail_py/detector_unix.py` - Unix/macOS detection (processes, pgrx, PGDATA, known paths)
- `pgtail_py/detector_windows.py` - Windows-specific detection
- `pgtail_py/instance.py` - Instance dataclass and DetectionSource enum
- `pgtail_py/parser.py` - PostgreSQL log line parsing, LogEntry dataclass, format dispatch
- `pgtail_py/parser_csv.py` - CSV log format (csvlog) parser, 26 fields
- `pgtail_py/parser_json.py` - JSON log format (jsonlog) parser, 29 fields
- `pgtail_py/format_detector.py` - LogFormat enum, auto-detection from line content
- `pgtail_py/filter.py` - LogLevel enum, level filtering logic
- `pgtail_py/regex_filter.py` - Regex pattern filtering and highlighting
- `pgtail_py/field_filter.py` - Field-based filtering (app=, db=, user=) for structured logs
- `pgtail_py/time_filter.py` - Time-based filtering (since, until, between)
- `pgtail_py/slow_query.py` - Slow query detection, thresholds, duration stats
- `pgtail_py/tailer.py` - Log file tailing with polling (handles rotation, format detection, resilient to restarts)
- `pgtail_py/colors.py` - Color output using prompt_toolkit styles
- `pgtail_py/display.py` - Display modes (compact, full, custom) and output formats (text, JSON)
- `pgtail_py/commands.py` - Command definitions, PgtailCompleter for autocomplete
- `pgtail_py/config.py` - Configuration file support, platform-specific paths, config schema
- `pgtail_py/enable_logging.py` - Enable logging_collector in postgresql.conf
- `pgtail_py/export.py` - Export formatting, file writing, pipe to external commands
- `pgtail_py/error_stats.py` - Error event tracking, SQLSTATE lookups, session statistics
- `pgtail_py/error_trend.py` - Sparkline visualization and per-minute bucketing
- `pgtail_py/cli_errors.py` - errors command handlers (summary, trend, live, code filter)
- `pgtail_py/sql_tokenizer.py` - SQL tokenization (keywords, identifiers, strings, numbers, operators, comments, functions)
- `pgtail_py/sql_highlighter.py` - SQL syntax highlighting with FormattedText output
- `pgtail_py/sql_detector.py` - SQL content detection in PostgreSQL log messages
- `pgtail_py/tail_buffer.py` - TailBuffer deque (10,000 line) with scroll position, FormattedLogEntry dataclass
- `pgtail_py/tail_status.py` - TailStatus for status bar state (counts, filters, mode, instance info)
- `pgtail_py/tail_layout.py` - TailLayout with HSplit (log/status/input), TailModeCompleter
- `pgtail_py/tail_app.py` - TailApp coordinator, asyncio entry consumer, Application lifecycle
- `pgtail_py/cli_tail.py` - Tail mode command handlers (level, filter, since, errors, etc.)

**Detection priority:** Running processes → ~/.pgrx/data-* → PGDATA env → platform-specific paths

**Key dependencies:**
- `prompt_toolkit` - REPL with autocomplete and history
- `psutil` - Cross-platform process detection

## Tech Stack

- Python 3.10+
- prompt_toolkit >=3.0.0 (REPL, autocomplete, styled output)
- psutil >=5.9.0 (process detection)
- re (stdlib, regex filtering)

## Configuration

Settings persist in a TOML config file at platform-specific locations:
- **macOS**: `~/Library/Application Support/pgtail/config.toml`
- **Linux**: `~/.config/pgtail/config.toml` (XDG_CONFIG_HOME)
- **Windows**: `%APPDATA%/pgtail/config.toml`

**Config commands:**
- `set <key> [value]` - Set a config value (e.g., `set slow.warn 50`)
- `unset <key>` - Remove a setting, revert to default
- `config` - Show current configuration as TOML
- `config path` - Show config file location
- `config edit` - Open in $EDITOR
- `config reset` - Reset to defaults (creates backup)

**Available settings:**
- `default.levels` - Default log level filter (e.g., `["ERROR", "WARNING"]`)
- `default.follow` - Auto-follow new entries (bool)
- `slow.warn`, `slow.error`, `slow.critical` - Threshold values in ms
- `display.timestamp_format` - strftime format string
- `display.show_pid`, `display.show_level` - Toggle output fields
- `theme.name` - Color theme (dark, light, high-contrast, monokai, solarized-dark, solarized-light, or custom)
- `notifications.enabled`, `notifications.levels`, `notifications.quiet_hours`

## Time Filtering

Time-based filtering commands support multiple formats:
- **Relative**: `5m`, `30s`, `2h`, `1d` (duration from now)
- **Time only**: `14:30`, `14:30:45` (today at specified time)
- **ISO 8601**: `2024-01-15T14:30`, `2024-01-15T14:30:00Z`

Commands:
- `since <time>` - Show entries from time onward
- `until <time>` - Show entries up to time
- `between <start> <end>` - Show entries in time range
- `tail <id> --since <time>` - Start tailing with time filter

Filter order (cheapest first): time → level → field → regex

## Error Statistics

The `errors` command tracks ERROR, FATAL, PANIC, and WARNING entries during tailing:

**Commands:**
- `errors` - Summary with counts by SQLSTATE code and severity level
- `errors --trend` - Sparkline visualization of error rate (last 60 minutes)
- `errors --live` - Real-time updating counter (Ctrl+C to exit)
- `errors --code CODE` - Filter by 5-character SQLSTATE code (e.g., 23505)
- `errors --since TIME` - Time-scoped statistics (e.g., `errors --since 30m`)
- `errors clear` - Reset all statistics

**Flag combinations:**
- `--since` can combine with `--trend` or `--code`
- `--live` cannot combine with other flags
- `--trend` and `--code` are mutually exclusive

**Implementation:**
- Session-scoped, in-memory only (deque with maxlen=10000)
- Tracks via `on_entry` callback in LogTailer (before filtering)
- SQLSTATE lookups for ~23 common codes and 45 category classes

## Log Format Support

pgtail auto-detects and parses three PostgreSQL log formats:

**Formats:**
- **TEXT** (stderr) - Standard log format, parsed from line structure
- **CSV** (csvlog) - 26 fields, set with `log_destination = 'csvlog'`
- **JSON** (jsonlog) - 29 fields, set with `log_destination = 'jsonlog'` (PG15+)

**Display modes** (`display` command):
- `compact` - Single line: timestamp [pid] level sql_state: message (default)
- `full` - All fields with labels, indented secondary fields
- `fields <f1,f2,...>` - Custom field selection

**Output formats** (`output` command):
- `text` - Colored terminal output (default)
- `json` - JSON Lines format for piping to `jq`

**Field filtering** (`filter field=value`):
- Filter by structured fields: `filter app=myapp`, `filter db=prod`, `filter user=postgres`
- Available fields: application, database, user, pid, backend
- Only effective for CSV/JSON formats (warns on text format)

## Desktop Notifications

The `notify` command configures desktop notifications for log events:

**Commands:**
- `notify` - Show current notification settings and status
- `notify on LEVEL...` - Enable for log levels (e.g., `notify on FATAL PANIC ERROR`)
- `notify on /pattern/` - Enable for regex pattern matches (e.g., `notify on /deadlock/i`)
- `notify on errors > N/min` - Alert when error rate exceeds threshold
- `notify on slow > Nms` - Alert when query duration exceeds threshold
- `notify off` - Disable all notifications
- `notify test` - Send a test notification (bypasses rate limiting)
- `notify quiet HH:MM-HH:MM` - Set quiet hours (e.g., `notify quiet 22:00-08:00`)
- `notify quiet off` - Disable quiet hours
- `notify clear` - Remove all notification rules

**Features:**
- Rate limiting: Max 1 notification per 5 seconds to prevent spam
- Quiet hours: Suppress notifications during configured time ranges (handles overnight spans)
- Platform detection: macOS (osascript), Linux (notify-send), Windows (PowerShell)
- Graceful degradation: Silent fallback when notification system unavailable

**Implementation:**
- Session-scoped notification manager with config persistence
- Checks in order: quiet hours → level rules → pattern rules → error rate → slow query
- Error rate uses ErrorStats for per-minute bucketing

**New modules:**
- `pgtail_py/notify.py` - NotificationRule, NotificationConfig, NotificationManager, RateLimiter, QuietHours
- `pgtail_py/notifier.py` - Notifier abstract interface, NoOpNotifier fallback, create_notifier() factory
- `pgtail_py/notifier_unix.py` - MacOSNotifier (osascript), LinuxNotifier (notify-send)
- `pgtail_py/notifier_windows.py` - WindowsNotifier (PowerShell toast)
- `pgtail_py/cli_notify.py` - notify command handlers

## Connection Statistics

The `connections` command tracks connection/disconnection events during tailing:

**Commands:**
- `connections` - Summary with active count and breakdowns by database/user/application
- `connections --history` - Sparkline visualization of connect/disconnect rates (last 60 min)
- `connections --watch` - Live stream of connection events (Ctrl+C to exit)
- `connections --db=NAME` - Filter by database name
- `connections --user=NAME` - Filter by user name
- `connections --app=NAME` - Filter by application name
- `connections clear` - Reset all statistics

**Flag combinations:**
- Filter flags (`--db`, `--user`, `--app`) work with all views
- `--history` and `--watch` are mutually exclusive

**Implementation:**
- Session-scoped, in-memory only (deque with maxlen=10000)
- Tracks via `on_entry` callback in LogTailer (before filtering)
- Requires PostgreSQL `log_connections=on` and `log_disconnections=on`
- ConnectionFilter dataclass with AND logic for multi-criteria filtering

**New modules:**
- `pgtail_py/connection_event.py` - ConnectionEvent dataclass, ConnectionEventType enum
- `pgtail_py/connection_parser.py` - Regex patterns for connection log messages
- `pgtail_py/connection_stats.py` - ConnectionStats aggregator, ConnectionFilter
- `pgtail_py/cli_connections.py` - connections command handlers

## Color Themes

The `theme` command manages color schemes for log output:

**Commands:**
- `theme` - Show current theme
- `theme <name>` - Switch to a theme (e.g., `theme light`, `theme monokai`)
- `theme list` - Show all available themes (built-in and custom)
- `theme preview <name>` - Preview a theme with sample log output
- `theme edit <name>` - Create or edit a custom theme (opens $EDITOR)
- `theme reload` - Reload current theme from disk after external edits

**Built-in themes:** dark (default), light, high-contrast, monokai, solarized-dark, solarized-light

**Custom themes:**
- TOML files stored in platform-specific themes directory:
  - **macOS**: `~/Library/Application Support/pgtail/themes/`
  - **Linux**: `~/.config/pgtail/themes/`
  - **Windows**: `%APPDATA%/pgtail/themes/`
- Use `theme edit mytheme` to create a new theme from template
- Theme defines colors for log levels (PANIC, FATAL, ERROR, etc.) and UI elements (timestamp, pid, highlight)

**Implementation:**
- ThemeManager handles loading, switching, and validating themes
- Colors: ANSI names (ansiRed), hex codes (#ff6b6b), or CSS named colors (DarkRed)
- Theme persists in config.toml under `theme.name`
- Respects NO_COLOR environment variable (disables all colors)

**New modules:**
- `pgtail_py/theme.py` - Theme, ColorStyle dataclasses; ThemeManager; color validation
- `pgtail_py/themes/` - Built-in theme definitions (dark.py, light.py, etc.)
- `pgtail_py/cli_theme.py` - theme command handlers

## SQL Syntax Highlighting

SQL syntax highlighting is an **always-on** feature that automatically colors SQL statements in PostgreSQL log messages. No configuration required.

**What Gets Highlighted:**

| Element | Token Type | Default Color (dark theme) |
|---------|------------|---------------------------|
| Keywords | `sql_keyword` | Blue (bold) |
| Identifiers | `sql_identifier` | Cyan |
| Strings | `sql_string` | Green |
| Numbers | `sql_number` | Magenta |
| Operators | `sql_operator` | Yellow |
| Comments | `sql_comment` | Gray |
| Functions | `sql_function` | Blue |

**Where SQL Is Detected:**
- `LOG: statement:` - Statement logging
- `LOG: execute <name>:` - Prepared statement execution
- `LOG: parse <name>:` - Prepared statement parsing
- `LOG: bind <name>:` - Parameter binding
- `LOG: duration: ... statement:` - Query timing
- `DETAIL:` - Error context details

**Implementation:**
- `sql_detector.py` - Regex patterns to detect SQL content in log messages
- `sql_tokenizer.py` - Tokenizes SQL into KEYWORD, IDENTIFIER, STRING, NUMBER, OPERATOR, COMMENT, FUNCTION types
- `sql_highlighter.py` - Converts tokens to FormattedText with style classes
- `display.py` - Integration via `_format_message_with_sql()` in all format functions

**Token Matching Order** (per research.md):
1. Whitespace
2. Block comments (`/* ... */`)
3. Line comments (`--`)
4. Dollar-quoted strings (`$$...$$`, `$tag$...$tag$`)
5. Single-quoted strings (`'...'`)
6. Quoted identifiers (`"..."`)
7. Numbers
8. Keywords (case-insensitive, 70+ SQL keywords)
9. Functions (identifier followed by `(`)
10. Multi-char operators (`<>`, `!=`, `<=`, `>=`, `||`, `::`)
11. Single-char operators
12. Punctuation

**Graceful Degradation:**
- Malformed SQL: Recognized tokens highlighted, unrecognized text displayed plain
- NO_COLOR=1: All SQL highlighting disabled
- Missing theme keys: Falls back to default text color

**New modules:**
- `pgtail_py/sql_tokenizer.py` - SQLTokenType enum, SQLToken dataclass, SQLTokenizer class
- `pgtail_py/sql_highlighter.py` - SQLHighlighter class, TOKEN_TO_STYLE mapping, highlight_sql() function
- `pgtail_py/sql_detector.py` - SQLDetectionResult namedtuple, detect_sql_content() function

## Status Bar Tail Mode

The `tail` command enters a split-screen interface with three areas:
- **Log output** (top): Scrollable log entries, 10,000 line buffer
- **Command input** (middle): Always-visible prompt for filter commands
- **Status bar** (bottom): Live stats and filter state

**Status bar format:** `MODE | E:X W:Y | N lines | filters... | PGver:port`
- Error/warning counts and line count respect active filters
- Filters shown: `levels:`, `filter:/pattern/`, `since:`, `slow:>`

**Navigation keys:**
- Up/Down: Scroll 1 line
- Page Up/Down: Scroll full page
- Ctrl+u/d: Scroll half page
- Ctrl+b/f: Scroll full page
- Home: Go to top
- End: Resume FOLLOW mode

**Implementation:**
- `tail_app.py`: TailApp coordinator with asyncio entry consumer
- `tail_buffer.py`: TailBuffer deque with scroll position and filter support
- `tail_layout.py`: HSplit layout, key bindings, TailModeCompleter
- `tail_status.py`: TailStatus for status bar state
- `cli_tail.py`: Command handlers (level, filter, since, clear, errors, etc.)

Filter changes trigger `_rebuild_buffer_filters()` which recalculates error/warning counts from buffer.

## Recent Changes
- 017-log-selection: Replace prompt_toolkit tail mode with Textual for built-in text selection and clipboard support (textual>=0.89.0, pyperclip>=1.8.0)
- 016-status-bar-tail: Split-screen tail mode with scrollable log output, status bar, command input. Error/warning/line counts respect active filters.
- 016-resilient-tailing: Tailer automatically detects new log files after PostgreSQL restart using current_logfiles

## Active Technologies
- Python 3.10+ + prompt_toolkit >=3.0.0 (Application, HSplit, Window, FormattedTextControl, BufferControl, TextArea) (016-status-bar-tail)
- textual>=0.89.0 + pyperclip>=1.8.0 (017-log-selection - new Textual-based tail mode)
- In-memory ring buffer (10,000 lines max), no persistence (016-status-bar-tail)
