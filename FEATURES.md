# pgtail feature parity checklist

Every feature the Python release documents (README, docs site, CLI reference, CHANGELOG) and every behavior reachable
in its code, listed so the .NET port can be checked off item by item. An item is checked only once it is ported and
verified by a real test or by driving the binary through the `hex1b` CLI.

## Command line

- [ ] `pgtail` with no command starts the interactive REPL
- [ ] `pgtail` exits silently with status 0 when stdin is not a terminal
- [ ] Windows: exits silently when launched without a parent console (double click, `Start-Process`, winget validation)
- [ ] `pgtail --version` / `-V` prints `pgtail <version>`
- [ ] `pgtail --check-update` checks GitHub releases and prints the result
- [ ] `pgtail --help` and `--help` on every command
- [ ] `pgtail list-instances [--verbose|-v]` prints the instance table (exit 1 when none found)
- [ ] `pgtail tail [ID]` tails a detected instance (the only instance when ID is omitted)
- [ ] `pgtail tail --file|-f <path>` (repeatable), glob patterns with a warning above 10 matches
- [ ] `pgtail tail --stdin` reads piped input, then reattaches the keyboard for navigation
- [ ] `pgtail tail --since|-s <time>` start with a time filter anchor
- [ ] `pgtail tail --stream` legacy streaming output instead of the full screen UI
- [ ] Argument validation messages: `--stdin` with `--file` or ID, `--file` with ID, missing files, bad time formats
- [ ] `pgtail config [--path|-p] [--edit|-e] [--reset]`
- [ ] `pgtail --install-completion` and `--show-completion` for bash, zsh, fish, and PowerShell
- [ ] Shell completion of commands, options, instance IDs with `PG<version>:<port> (<status>)`, theme names, config keys
- [ ] Startup update check once per 24 hours, disabled with `set updates.check false`

## Instance detection

- [ ] Running `postgres`/`postmaster` processes (data directory from the command line or the process)
- [ ] pgrx instances under `~/.pgrx/data-*`
- [ ] `PGDATA` environment variable
- [ ] Platform known paths: Homebrew, Postgres.app, Debian/Ubuntu `/var/lib/postgresql/<ver>/<cluster>`, RHEL, Windows
- [ ] Debian config in `/etc/postgresql/<version>/<cluster>/`, version fallback from the data directory path
- [ ] Version from `PG_VERSION`, port from `postmaster.pid`/`postgresql.conf`, running status
- [ ] Logging status and log path (`logging_collector`, `log_directory`, `log_destination`, `current_logfiles`)
- [ ] Latest log file selection in a log directory
- [ ] De-duplication across sources

## REPL

- [ ] Banner, instance count on startup, `Goodbye!` on exit
- [ ] `pgtail>` prompt; `!` shell prompt; `tailing [id]>` and `paused [id]>` prompts during streaming tails
- [ ] Bottom toolbar: instance count or "No instances (run 'refresh')", active filters, theme; `SHELL • Press Escape to exit`
- [ ] Tab completion of commands, subcommands, arguments, instance IDs, themes, config keys, highlighter names, paths
- [ ] Persistent command history with Up/Down
- [ ] Shell mode: `!<cmd>` runs immediately, `!` alone enters shell mode, Escape and Backspace on empty leave it
- [ ] Ctrl+C at the prompt is ignored, Ctrl+C during a streaming tail pauses output, Ctrl+D exits
- [ ] Quoted arguments (shell-style splitting with fallback)
- [ ] Unknown command message
- [ ] `list` / `ls`, `refresh`, `help`, `clear`, `quit` / `exit` / `q`, `stop`
- [ ] `tail <id|path>` with `--file`, `-f`, `--since`, `--stream`; errors for ambiguity and missing logs
- [ ] Permission advice when logs cannot be read, logging-not-enabled advice
- [ ] `levels [LEVEL...]`, `levels ALL`
- [ ] `filter /re/`, `-/re/`, `+/re/`, `&/re/`, `/re/c`, `/re/i`, `field=value`, `clear`, no args shows filters
- [ ] `highlight /re/` legacy highlight patterns and `highlight` semantic highlighter management (see Highlighting)
- [ ] `since`, `until`, `between` (with optional `and`), `since clear`, `until clear`
- [ ] `display [compact|full|fields a,b,c]`
- [ ] `output [text|json]`
- [ ] `slow [warn [error [critical]]]`, `slow off`
- [ ] `stats` query duration statistics (count, average, p50, p95, p99, max)
- [ ] `errors [--trend] [--live] [--code CODE] [--since TIME]`, `errors clear`
- [ ] `connections [--history] [--watch] [--db=] [--user=] [--app=]`, `connections clear`
- [ ] `notify` (see Notifications)
- [ ] `theme` (see Themes)
- [ ] `set <key> [value]`, `unset <key>`, `config [path|edit|reset]`
- [ ] `export` and `pipe` (see Export)
- [ ] `enable-logging <id>`

## Streaming tail (legacy `--stream`)

- [ ] `Tailing <path>`, active filter summary, `Press Ctrl+C to stop`, `Detected format: <fmt>`
- [ ] Compact, full, and custom display modes; JSON Lines output
- [ ] Slow query coloring replaces highlighting, legacy highlight patterns with yellow background
- [ ] `Switched to: <file>` on rotation or restart

## Tail mode (full screen)

- [ ] Layout: header hints, separator, log area, separator, `tail>` input, separator, status bar
- [ ] Log buffer of 10,000 lines (`buffer.tail_log_max`) with live append and FOLLOW
- [ ] Status bar: `FOLLOW` (green) / `PAUSED +N new` (yellow), `E:x W:y`, line count, filters, `PG<ver>:<port>` or filename
- [ ] Status bar `(unavailable)` and `(permission denied)` indicators, permission warning in the log
- [ ] Version and port detected from log content when tailing files
- [ ] Multi-file tailing interleaved by timestamp with `[filename]` prefixes; per-file format detection
- [ ] Glob watching picks up new files within 5 seconds
- [ ] Stdin mode: buffered input, `--- stdin complete (N lines loaded) - press 'q' to quit ---`
- [ ] Navigation: `j`/`k`, Down/Up, `g`/`G`, Home/End, Ctrl+d/u, Ctrl+f/b, PageDown/PageUp, `p`, `f`, `q`, `?`, `/`, Tab
- [ ] Visual mode: `v`, `V`, `h`/`l`, `j`/`k`, `0`, `$`, `y`, Escape, Ctrl+a, Ctrl+c
- [ ] Mouse wheel scrolling, mouse drag selection that copies on release
- [ ] Clipboard through OSC 52 plus a platform fallback (`pbcopy`, `wl-copy`, `xclip`, `xsel`, `clip.exe`)
- [ ] Help overlay (`?`) with key reference, dismissed with Escape/`q`/`?`
- [ ] `tail>` input: history (500 entries, deduplicated, persisted, compacted), Up/Down
- [ ] Ghost text suggestions for commands, subcommands, flags, flag values, positional values, dynamic sources, history
- [ ] Right/End accepts the suggestion, Escape returns focus to the log, Enter runs the command
- [ ] Commands: `level`, `filter`, `since`, `until`, `between`, `slow`, `clear`, `clear force`, `errors`, `connections`,
      `pause`/`p`, `follow`/`f`, `help`, `help keys`, `help <cmd>`, `stop`/`q`, `highlight`, `theme`, `set`, `unset`,
      `export`, `pipe`, `notify`, `display`, `output`, `stats` (every command the tail handler accepts)
- [ ] Filter anchor captured on entry; `clear` resets to it, `clear force` clears everything
- [ ] Non-blocking rebuild when filters change, preserving entries that arrive meanwhile
- [ ] Buffer preserved after leaving tail mode for `export` and `pipe`

## Log parsing

- [ ] Format detection (text, csvlog, jsonlog) from content, per file
- [ ] Text format with `log_line_prefix` variations, multi-line continuation (DETAIL/HINT/CONTEXT/STATEMENT)
- [ ] csvlog with all 26 fields (and PG version differences)
- [ ] jsonlog with all fields (PG15+)
- [ ] Timestamps with named zones and offsets normalized to UTC; naive timestamps treated as local
- [ ] Log levels `PANIC FATAL ERROR WARNING NOTICE LOG INFO DEBUG1-5`, abbreviations and `+`/`-` ranges
- [ ] Duration extraction (`duration: X ms`, seconds)

## Filtering

- [ ] Level filter, regex include/exclude/AND/OR with case options, field filters, time filters
- [ ] Filter order: time, level, field, regex
- [ ] Field filter warning with text format

## Highlighting and themes

- [ ] 29 built-in semantic highlighters in 10 categories with priorities, non-overlapping application
- [ ] SQL detection and SQL tokenizer highlighting (keywords, identifiers, strings, dollar quotes, numbers, operators,
      comments, functions, parameters)
- [ ] Duration threshold coloring (`highlighting.duration.*`)
- [ ] `highlighting.max_length` (10 KB default)
- [ ] `highlight list|on|off|enable|disable|add|remove|preview|reset|export|import`
- [ ] Custom highlighters with regex, Rich style strings, priority, persistence
- [ ] Six built-in themes; custom TOML themes; `theme`, `theme list`, `theme <name>`, `theme preview`, `theme edit`,
      `theme reload`; persisted `theme.name`
- [ ] Style strings: ANSI names, hex, CSS names, `fg:`/`bg:`, bold, italic, underline, dim, Rich-style strings
- [ ] `NO_COLOR` disables color

## Statistics

- [ ] Error statistics by SQLSTATE and level, trend sparkline (60 minutes), live counter, code and time filters
- [ ] Connection statistics: active by database/user/application, history sparklines, watch stream, filters
- [ ] Query duration statistics

## Notifications

- [ ] Rules by level, pattern, error rate, slow query; quiet hours (overnight spans); rate limit 1 per 5 seconds
- [ ] `notify`, `notify on ...`, `notify off`, `notify test`, `notify quiet HH:MM-HH:MM|off`, `notify clear`
- [ ] macOS `osascript`, Linux `notify-send`, Windows toast notifications (with Start menu shortcut/AUMID)
- [ ] Persistence under `[notifications]`

## Export and pipe

- [ ] `export [--format text|json|csv] [--since TIME] [--append] [--follow] <file>`
- [ ] `pipe [--format text|json|csv] <command...>`
- [ ] "No log file loaded" guidance

## Configuration

- [ ] Platform config paths (macOS Application Support, XDG on Linux, `%APPDATA%` on Windows)
- [ ] TOML settings: `default.*`, `slow.*`, `display.*`, `theme.*`, `notifications.*`, `highlighting.*`, `buffer.*`,
      `updates.*`; validation with warnings; comments preserved on `set`/`unset`
- [ ] `config` shows TOML, `config path`, `config edit` (`$EDITOR`), `config reset` (backup)
- [ ] History file locations (REPL history and tail history)

## Enable logging

- [ ] `enable-logging <id>` edits `postgresql.conf` (logging_collector, log_directory, etc.), backup, restart guidance

## Distribution

- [ ] Native AOT single binaries for macOS (arm64, x64), Linux (x64, arm64), Windows (x64)
- [ ] Release workflow keeps every channel: archives, MSI, Homebrew tap, winget manifests, Scoop bucket
- [ ] Published to NuGet as a .NET tool (`dotnet tool install -g pgtail`) with per-RID Native AOT tool packages, like ilrepl
- [ ] Python sources, tests, packaging (pyproject, uv, Nuitka, ruff, Makefile) and MkDocs removed
- [ ] CI builds and runs the full test suite on Linux, macOS, and Windows
- [ ] Documentation site and README updated for the .NET build
- [ ] Documentation site migrated from MkDocs to Astro Starlight, laid out like ilrepl's `docs/` (pnpm, `astro.config.mjs`,
      content under `src/content/docs`), with the docs workflow building and deploying it to pgtail.dev
