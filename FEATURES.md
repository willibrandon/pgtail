# pgtail feature parity checklist

Every feature the Python release documents (README, docs site, CLI reference, CHANGELOG) and every behavior reachable
in its code, listed so the .NET port can be checked off item by item. An item is checked only once it is ported and
verified by a real test or by driving the binary through the `hex1b` CLI.

## Command line

- [x] `pgtail` with no command starts the interactive REPL
- [x] `pgtail` exits silently with status 0 when stdin is not a terminal
- [ ] Windows: exits silently when launched without a parent console (double click, `Start-Process`, winget validation),
      but not when a terminal hosts it in a pseudoconsole: checked on the Windows runners by `scripts/Publish-NativeAot.cs`
      (the REPL in Hex1b's pseudoconsole, then with no console) and by the interactive CLI tests
- [x] `pgtail --version` / `-V` prints `pgtail <version>`
- [x] `pgtail --check-update` checks GitHub releases and prints the result
- [x] `pgtail --help` and `--help` on every command
- [x] `pgtail list-instances [--verbose|-v]` (alias `list`) prints the instance table (exit 1 when none found)
- [x] `pgtail tail [ID]` tails a detected instance (the only instance when ID is omitted)
- [x] `pgtail tail --file|-f <path>` (repeatable), glob patterns with a warning above 10 matches
- [x] `pgtail tail --stdin` reads piped input, then reattaches the keyboard for navigation
- [x] `pgtail tail --since|-s <time>` start with a time filter anchor
- [x] `pgtail tail --stream` legacy streaming output instead of the full screen UI
- [x] Argument validation messages: `--stdin` with `--file` or ID, `--file` with ID, missing files, bad time formats
- [x] `pgtail config [--path|-p] [--edit|-e] [--reset]` (`--edit` opens the built-in editor)
- [x] `pgtail --install-completion` and `--show-completion` for bash, zsh, fish, and PowerShell
- [x] Shell completion of commands, options, instance IDs with `PG<version>:<port> (<status>)`, theme names, config keys
- [x] Startup update check once per 24 hours, disabled with `set updates.check false`

## Instance detection

- [x] Running `postgres`/`postmaster` processes (data directory from the command line or the process)
- [x] pgrx instances under `~/.pgrx/data-*`
- [x] `PGDATA` environment variable
- [x] Platform known paths: Homebrew (`/usr/local/var/postgres`, `/opt/homebrew/var/postgresql@*`), Postgres.app,
      Debian/Ubuntu `/var/lib/postgresql/<ver>/<cluster>`, RHEL and PGDG `/var/lib/pgsql`, and Arch
      `/var/lib/postgres/data` (each layout verified with `list-instances` in a bubblewrap sandbox that places it)
- [ ] Windows known paths (`Program Files\PostgreSQL\<ver>\data`, `%APPDATA%`, `%LOCALAPPDATA%`): covered by
      `ListInstances_UserKnownLocation_ShowsInstance` on the Windows CI runner
- [x] Debian config in `/etc/postgresql/<version>/<cluster>/`, version fallback from the data directory path (verified
      with a real PostgreSQL 18 server laid out as a Debian cluster, running and stopped with its data directory closed)
- [x] Debian and Ubuntu server logs from `pg_ctlcluster` in `/var/log/postgresql` with `adm` group advice, and the
      `'%m [%p] %q%u@%d '` line prefix (new; the Python release showed these lines unparsed)
- [x] Version from `PG_VERSION`, port from `postmaster.pid`/`postgresql.conf`, running status
- [x] Logging status and log path (`logging_collector`, `log_directory`, `log_destination`, `current_logfiles`)
- [x] Latest log file selection in a log directory
- [x] De-duplication across sources

## REPL

- [x] Banner, instance count on startup, `Goodbye!` on exit
- [x] `pgtail>` prompt; `!` shell prompt; `paused [id]>` prompt after Ctrl+C pauses a streaming tail
- [x] Bottom toolbar: instance count or "No instances (run 'refresh')", active filters, theme; `SHELL • Press Escape to exit`
- [x] Tab completion of commands, subcommands, arguments, instance IDs, themes, config keys, highlighter names, paths
- [x] Persistent command history with Up/Down
- [x] Shell mode: `!<cmd>` runs immediately, `!` alone enters shell mode, Escape and Backspace on empty leave it
- [x] Ctrl+C at the prompt abandons the line, Ctrl+C during a streaming tail pauses output, Ctrl+D exits
- [x] Quoted arguments (shell-style splitting with fallback)
- [x] Unknown command message
- [x] `list` / `ls`, `refresh`, `help`, `clear`, `quit` / `exit` / `q`, `stop`
- [x] `tail <id|path>` with `--file`, `-f`, `--since`, `--stream`; errors for ambiguity and missing logs
- [x] Permission advice when logs cannot be read, logging-not-enabled advice
- [x] `levels [LEVEL...]`, `levels ALL`
- [x] `filter /re/`, `-/re/`, `+/re/`, `&/re/`, `/re/c`, `/re/i`, `field=value`, `clear`, no args shows filters
- [x] `highlight /re/` legacy highlight patterns and `highlight` semantic highlighter management (see Highlighting)
- [x] `since`, `until`, `between` (with optional `and`), `since clear`, `until clear`
- [x] `display [compact|full|fields a,b,c]`
- [x] `output [text|json]`
- [x] `slow [warn [error [critical]]]`, `slow off`
- [x] `stats` query duration statistics (count, average, p50, p95, p99, max)
- [x] `errors [--trend] [--live] [--code CODE] [--since TIME]`, `errors clear`
- [x] `connections [--history] [--watch] [--db=] [--user=] [--app=]`, `connections clear`
- [x] `notify` (see Notifications)
- [x] `theme` (see Themes)
- [x] `set <key> [value]`, `unset <key>`, `config [path|edit|reset]`
- [x] `export` and `pipe` (see Export)
- [x] `enable-logging <id>`

## Streaming tail (legacy `--stream`)

- [x] `Tailing <path>`, active filter summary, `Press Ctrl+C to stop`, `Detected format: <fmt>`
- [x] Compact, full, and custom display modes; JSON Lines output
- [x] Slow query coloring replaces highlighting, legacy highlight patterns with yellow background
- [x] `Switched to: <file>` on rotation or restart

## Tail mode (full screen)

- [x] Layout: header hints, separator, log area, separator, `tail>` input, separator, status bar
- [x] Log buffer of 10,000 lines with live append and FOLLOW
- [x] Status bar: `FOLLOW` (green) / `PAUSED +N new` (yellow), `E:x W:y`, line count, filters, `PG<ver>:<port>` or filename
- [x] Status bar `(unavailable)` and `(permission denied)` indicators, permission warning in the log
- [x] Version and port detected from log content when tailing files
- [x] Multi-file tailing interleaved by timestamp with `[filename]` prefixes; per-file format detection
- [x] Glob watching picks up new files within 5 seconds
- [x] Stdin mode: buffered input, `--- stdin complete (N lines loaded) - press 'q' to quit ---`
- [x] Navigation: `j`/`k`, Down/Up, `g`/`G`, Home/End, Ctrl+d/u, Ctrl+f/b, PageDown/PageUp, `p`, `f`, `q`, `?`, `/`, Tab
- [x] Visual mode: `v`, `V`, `h`/`l`, `j`/`k`, `0`, `$`, `y`, Escape, Ctrl+a, Ctrl+c
- [x] Mouse wheel scrolling, mouse drag selection that copies on release
- [x] Clipboard through OSC 52 plus a platform fallback (`pbcopy`, `wl-copy`, `xclip`, `xsel`, `clip.exe`)
- [x] Help overlay (`?`) with key reference, dismissed with Escape/`q`/`?`
- [x] `tail>` input: history (500 entries, deduplicated, persisted, compacted), Up/Down
- [x] Ghost text suggestions for commands, subcommands, flags, flag values, positional values, dynamic sources, history
- [x] Right/End accepts the suggestion, Escape returns focus to the log, Enter runs the command
- [x] Commands: `level`, `filter`, `since`, `until`, `between`, `slow`, `clear`, `clear force`, `errors`, `connections`,
      `pause`/`p`, `follow`/`f`, `help`, `help keys`, `help <cmd>`, `<cmd> help`, `stop`/`exit`/`q`, `highlight`,
      `theme`, `set`, `export`, `notify` (every command the Python tail handler accepted)
- [x] Filter anchor captured on entry; `clear` resets to it, `clear force` clears everything
- [x] Non-blocking rebuild when filters change, preserving entries that arrive meanwhile
- [x] Buffer preserved after leaving tail mode for `export` and `pipe`

## Log parsing

- [x] Format detection (text, csvlog, jsonlog) from content, per file
- [x] Text format with `log_line_prefix` variations; DETAIL/HINT/CONTEXT/STATEMENT/QUERY/LOCATION and tab-indented
      continuation lines joined to their entry
- [x] csvlog with all 26 fields (and PG version differences)
- [x] jsonlog with all fields (PG15+)
- [x] Timestamps with named zones and offsets compared in UTC and shown as written; naive timestamps treated as local
- [x] Log levels `PANIC FATAL ERROR WARNING NOTICE LOG INFO DEBUG1-5`, abbreviations and `+`/`-` ranges
- [x] Duration extraction (`duration: X ms`, seconds)

## Filtering

- [x] Level filter, regex include/exclude/AND/OR with case options, field filters, time filters
- [x] Filter order: time, level, field, regex
- [x] Field filter warning with text format

## Highlighting and themes

- [x] 30 built-in semantic highlighters in 10 categories with priorities, non-overlapping application
- [x] SQL detection and SQL tokenizer highlighting (keywords, identifiers, strings, dollar quotes, numbers, operators,
      comments, functions, parameters)
- [x] Duration threshold coloring (`highlighting.duration.*`)
- [x] `highlighting.max_length` (10 KB default)
- [x] `highlight list|on|off|enable|disable|add|remove|preview|reset|export|import`
- [x] Custom highlighters with regex, Rich style strings, priority, persistence
- [x] Six built-in themes; custom TOML themes; `theme`, `theme list`, `theme <name>`, `theme preview`, `theme edit`,
      `theme reload`; persisted `theme.name`
- [x] Style strings: ANSI names, hex, CSS names, `fg:`/`bg:`, bold, italic, underline, dim, Rich-style strings
- [x] `NO_COLOR` disables color

## Statistics

- [x] Error statistics by SQLSTATE and level, trend sparkline (60 minutes), live counter, code and time filters
- [x] Connection statistics: active by database/user/application, history sparklines, watch stream, filters
- [x] Query duration statistics

## Notifications

- [x] Rules by level, pattern, error rate, slow query; quiet hours (overnight spans); rate limit 1 per 5 seconds
      (each verified in tail mode against a live PostgreSQL 18 workload, watching `Notify` calls on the session bus
      with `dbus-monitor`; a pattern with spaces, split at the first space in the Python release, now works)
- [x] `notify`, `notify on ...`, `notify off`, `notify test`, `notify quiet HH:MM-HH:MM|off`, `notify clear`
- [x] Linux `notify-send` (verified on the desktop session bus)
- [ ] macOS `osascript` and Windows toast notifications (with Start menu shortcut/AUMID): covered by
      `Notify_Status_NamesPlatformNotifier` (both; on Windows it writes the shortcut and activates the toast API) and
      `NotifyTest_SendsThroughPlatformNotifier` (macOS) on the CI runners; a toast on screen needs a Windows desktop
- [x] Persistence under `[notifications]`

## Export and pipe

- [x] `export [--format text|json|csv] [--since TIME] [--append] [--follow] [--highlighted] <file>`
- [x] `pipe [--format text|json|csv] <command...>`
- [x] "No log file loaded" guidance

## Configuration

- [x] Linux config and history paths: `$XDG_CONFIG_HOME/pgtail` and `$XDG_DATA_HOME/pgtail`, defaulting to
      `~/.config/pgtail` and `~/.local/share/pgtail` (verified with `config --path` both ways)
- [ ] macOS `~/Library/Application Support/pgtail` and Windows `%APPDATA%\pgtail`: covered by
      `ConfigPath_PrintsPlatformConfigFile` on the macOS and Windows CI runners
- [x] TOML settings: `default.levels`, `slow.*`, `theme.*`, `notifications.*`, `highlighting.*`, `updates.*`;
      validation with warnings; comments preserved on `set`/`unset` (the never-applied `default.follow`, `display.*`, and
      `buffer.*` settings are dropped as dead code)
- [x] `config` shows TOML, `config path`, `config edit` (built-in editor, checked before saving), `config reset` (backup)
- [x] History file locations (REPL history and tail history)

## Enable logging

- [x] `enable-logging <id>` edits `postgresql.conf` (logging_collector, log_directory, log_filename), creates the log
      directory, restart guidance

## Distribution

- [x] Native AOT binaries for macOS (arm64, x64), Linux (x64, arm64), Windows (x64, arm64)
- [x] Release workflow keeps every channel: archives, MSI, Homebrew tap, winget manifests, Scoop bucket
- [x] Published to NuGet as a .NET tool (`dotnet tool install -g pgtail`) with per-RID Native AOT tool packages, like ilrepl
- [x] Python sources, tests, packaging (pyproject, uv, Nuitka, ruff, Makefile) and MkDocs removed
- [x] CI builds and runs the full test suite on Linux, macOS, and Windows
- [x] Documentation site and README updated for the .NET build
- [x] Documentation site migrated from MkDocs to Astro Starlight, laid out like ilrepl's `docs/` (pnpm, `astro.config.mjs`,
      content under `src/content/docs`), with the docs workflow building and deploying it to pgtail.dev

## Not yet verified

The unchecked items are ported but have not been exercised on the platform or setup they need:

- Windows without a parent console, and Windows toast notifications: the release workflow's MSI checks start pgtail in
  the ways winget validation does.
- Homebrew, Postgres.app, Debian/Ubuntu, RHEL, and Windows data directory locations, and Debian's `/etc/postgresql`
  configuration: checked on Linux only with `PGDATA`, pgrx, and running servers.
- Notification rules firing during a tail, and macOS `osascript`: `notify test` was delivered through `notify-send`.
- Configuration paths on macOS and Windows: checked on Linux (XDG).

