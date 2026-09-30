# pgtail .NET port progress log

Port of pgtail from Python (Textual/prompt_toolkit/Rich) to C# on .NET 10 with Native AOT and Hex1b.

## Ground rules

- Hex1b is consumed only as a NuGet package reference (latest stable). The hex1b repo is a read-only reference.
- Dependencies are limited to Microsoft and .NET Foundation owned packages, plus Hex1b.
- Tests are real Hex1b terminal tests (terminal emulator plus workloads) and real file/process tests. No mocks.
- The command system is modeled on ilrepl: a single command catalog that drives dispatch, completion, and help.
- Dead code in the Python tree is not ported.
- The MkDocs site moves to Astro Starlight, the same way ilrepl builds its documentation.
- Python and MkDocs are removed entirely; the Python release on `main` is the reference while porting.
- No fallbacks: one code path per behavior, with no compatibility shims for Python-era syntax.
- pgtail also ships as a .NET tool like ilrepl, and every existing channel (Homebrew, winget, Scoop, MSI, archives) stays.
- The binary must work on Linux, macOS, and Windows and publish with Native AOT.

## Log

### 2026-09-29

- Created branch `dotnet-port`.
- Surveyed the Python tree (about 31k lines of source, 23k lines of tests), ilrepl's command catalog and Hex1b TUI,
  and the hex1b repository for API and testing guidance.
- Wrote `FEATURES.md`, the feature parity checklist taken from the README, docs site, CLI reference, and CHANGELOG.
  Items are checked only after they are ported and verified.
- Copied ilrepl's `.editorconfig` verbatim and its layout/documentation analyzers into `src/Pgtail.Analyzers`
  (rules renamed `PGTAIL0001`-`PGTAIL0007`).
- Ported the core (parsing, filtering, statistics, styling, highlighting, TOML, configuration, detection, tailing,
  notifications, export, updates), then the REPL, tail mode, the built-in editor, the command catalogs, and the
  command line.
- Rebuilt the tail log as its own Hex1b view so it follows new rows; added mouse and horizontal scrolling.
- Wrote the terminal test suite: the REPL flow, tail mode, and the built executable in a pseudo-terminal and with
  piped output (86 tests, run repeatedly for flakiness).
- Drove every feature with the `hex1b` CLI, including against real PostgreSQL 18 servers (running process detection,
  logging on and off, `enable-logging`, rotation, csvlog and jsonlog, live connection and error views), which found
  and fixed: continuation lines shown as separate entries, csvlog/jsonlog times shown in UTC, the port not read after
  the version, status lines in piped output, the prompt overwriting streamed output, lost characters in wrapped
  echoes, focus changes applied a frame late, and batched keystrokes ignored in the log.
- Added Ctrl+R history search and the shell's line editing keys, which the prompt_toolkit REPL had.
- Native AOT publish, the .NET tool packages, the release and CI workflows, the Astro Starlight docs site, README,
  CHANGELOG, and the feature checklist.

## Decisions

- Settings the Python release validated and stored but never read are not ported: `default.follow`,
  `display.timestamp_format`, `display.show_pid`, `display.show_level`, `updates.last_version`, and `buffer.*`. Nor are
  helpers it defined but never called (the SQLSTATE class names, the jsonlog field map, connections by application). The statistics and tail buffers
  keep the fixed 10,000 entry limits the Python release actually used.
- Timestamps keep Python's aware/naive distinction as `DateTime` kinds (`Utc` / `Unspecified`); comparisons always
  normalize to UTC, which fixes Python's naive/aware comparison errors in `errors --trend` and time windows.
- Scout (read-only reference at ~/src/scout, consumed as the NuGet packages Scout.Text.Regex, Scout.IO.Globbing, and
  Scout.IO.Ignore 0.6.1) is pgtail's search engine. Every regular expression that searches log content or comes from
  the user (filters, highlights, custom highlighters, notification patterns, the built-in highlighters, SQL detection,
  duration and connection parsing, the text log parser) is a byte-oriented, linear-time Scout regex in ripgrep syntax,
  matched on the raw UTF-8 line where possible. Fixed token syntaxes (time expressions, TOML, colors, config validation)
  use compile-time `[GeneratedRegex]`.
- `--file` globs and detection path patterns use Scout globs expanded with Scout's `FileWalker` (ignore files and
  hidden-file filtering off, since log directories are usually version-control ignored). Detection now finds any
  Debian cluster, PGDG `/var/lib/pgsql/*/data`, every Homebrew `postgresql@*`, and Postgres.app data directories
  instead of the Python release's fixed 14-16 list.
- Tail mode keeps every entry it reads and applies filters when displaying, so `clear` brings back entries a narrower
  filter hid (the Python release lost them because the tailer discarded filtered entries).
- JSON output is compact standard JSON without escaping non-ASCII characters.
- Ported the log model and parsers (text, csvlog, jsonlog, format detection, timestamps), the level/regex/field/time
  filters, and the slow query, duration, error, and connection statistics.
- Wrote our own TOML 1.0 reader and comment-preserving editor (`src/Pgtail.Core/Toml`). It passes all 709 cases of the
  official toml-test 1.0 corpus (checked with a scratch harness outside the repository).
- Program.cs uses top-level statements. System.CommandLine is dropped in favor of our own argument parsing.
- Ported styling: palette-preserving terminal colors, a style parser that reads Rich and prompt_toolkit style strings,
  markup, the six built-in themes (generated from the Python definitions), custom TOML themes, and the theme manager.
- Ported semantic highlighting: our own Aho-Corasick keyword matcher, the occupancy tracker, the highlighter chain
  with SQL-region detection, all 30 built-in highlighters on source-generated regular expressions, custom highlighters,
  and the highlighting configuration with comment-preserving saves. The SQL tokenizer is not ported: Python used it
  only on paths that rendered without a theme, and every path now renders through the themed chain.
- Design: the REPL runs as a Hex1b Flow (inline, scrollback-preserving, like the prompt_toolkit REPL). The tail log is its
  own focusable Hex1b view (an interactable surface) because it must follow new rows, which needs programmatic scrolling
  that Hex1b 0.172.0's editor does not expose; it draws every attribute (dim, reverse) and its own scrollbar, scrolls
  sideways to keep the cursor in sight, and handles typed keys a character at a time so keys that arrive together (fast
  typing, key repeat) all take effect.
- Moving the cursor in the tail log off the newest row stops following and shows `PAUSED`, the way `less +F` behaves;
  returning to the end resumes. A plain click selects a row and a drag selects text and copies it silently on release.
- Commands follow ilrepl's model: one catalog per mode (`ReplCatalog`, `TailCatalog`) holds each command's name,
  aliases, description, argument spec, detailed help, and handler, and drives dispatch, the REPL's completion menu,
  tail mode's inline suggestions, and help. The argument specs follow the Python tail completion data.
- When a command needs the real terminal (a `!` shell command, clearing the screen, streaming output, or a full screen
  app such as tail mode or the built-in editor), the REPL flow ends with a request, the runner serves it on the real
  terminal, and the flow starts again; a command that asked for a full screen app continues where it left off. Tail
  mode and the editor are separate full screen Hex1b apps on the alternate screen, as Textual's were, because a flow's
  full screen step releases the flow's input when its app finishes in Hex1b 0.172.0.
- Flow output uses soft-wrap tombstones so it reflows in scrollback, and is folded one column short of the width so the
  erase-to-end-of-line after a full row cannot drop its last character.
- `config edit` and `theme edit` open a built-in Hex1b editor with TOML highlighting that checks the file before saving.
- `export --highlighted` and tail mode's `export --highlighted` keep colors as ANSI escapes (the Python release wrote
  Rich markup), and text export writes log lines unchanged (the Python release stripped anything in brackets).
- `pipe` runs its command through the shell (`sh -c`, `cmd /c`) with the text typed after the options, so pipelines
  and quoting work.
- Tail mode reports unknown commands and bad filter values instead of ignoring them, and its filter confirmations
  appear after the log is redrawn.
- `pgtail list` works as an alias of `list-instances` (the Python messages already pointed to it), and
  `pgtail enable-logging <id>` exists on the command line because `pgtail tail` suggests it.
- `pgtail tail --stdin --stream` prints piped input through the filters; without a terminal for the keyboard, `--stdin`
  suggests `--stream` instead of printing unfiltered lines.
- Update checks suggest the upgrade command for the .NET distribution channels: `dotnet tool update -g pgtail`,
  Homebrew, winget, Scoop, or the releases page.
- Between the REPL's terminals (the prompt flow, a full screen app, a shell command) pgtail waits 150 ms after a
  terminal stops: Hex1b's Unix console reader notices its terminal stopped between 100 ms waits for input, and could
  otherwise read the next terminal's cursor position reply (the prompt then never returned after a quick `!echo`) or a
  shell command's first keys. After clearing the screen or a full screen app the next prompt's row is known, so the
  terminal is not asked.
- Shell completion offers options once the word starts with `-`, as Click does, so `pgtail <Tab>` lists commands.
- Tests: REPL tests run the REPL's flow in a headless Hex1b terminal (full screen requests are served on a second
  one), tail mode tests run the tail screen on a real log file, and CLI tests run the built executable, in a
  pseudo-terminal for interactive use and with piped output for one-shot commands. The thread pool minimum is raised
  as Hex1b's own tests do, so parallel terminals do not starve.
- Packaging follows ilrepl: `pgtail` is a .NET tool whose pointer package picks a Native AOT runtime package
  (win-x64, win-arm64, linux-x64, linux-arm64, osx-x64, osx-arm64) or the framework-dependent `any` package. A publish
  holds the executable and Hex1b's native files as Hex1b ships them: on Linux and macOS its console driver calls
  `libhex1binterop` to read and set the terminal mode, so the library must stay beside the executable in archives and
  packages. `scripts/Publish-NativeAot.cs` publishes, runs (including the REPL in a pseudo-terminal inside Hex1b's
  headless terminal), packs, and runs the packaged executable for one runtime; CI runs it on every runtime and the
  release workflow builds from it. CLI tests run the executable from its own project's output, so they see the same
  files a user gets.
- The release keeps every channel: the same archive names (with `pgtail-windows-arm64.zip` added), the x64 MSI,
  Homebrew, Scoop (now with arm64), and winget, and adds nuget.org through trusted publishing.
- Text logs: a message's `DETAIL:`, `HINT:`, `CONTEXT:`, `STATEMENT:`, `QUERY:`, and `LOCATION:` lines from the same
  backend, and the tab-indented further lines of a multi-line message, join the entry they belong to (the Python release
  showed each as a separate LOG entry with its label dropped, and sorted tab-indented lines to the top in multi-file
  mode). A level filter now keeps an error's detail and statement with it, the error counts once, and text export still
  writes the lines exactly as PostgreSQL wrote them. Found by tailing a real PostgreSQL 18 server.
- Times show as the log wrote them in every format. The Python release showed csvlog and jsonlog times converted to
  UTC but text times as written, so the same server's logs disagreed by the zone offset. Entries now keep the instant
  (UTC, used for every comparison) and the offset they were written with, text lines in a known zone such as `PDT`
  included, and JSON and CSV export write that offset (`-07:00`).
- .NET caches the cursor position and moves it along with text written through `Console`, but Hex1b writes to the
  terminal directly, so after a stream or a shell command the next prompt started above the output. The REPL writes an
  attribute reset through `Console` before each prompt that asks where the cursor is, which makes .NET ask the terminal.
- Lines printed just before a stream (`Press Ctrl+C to stop`) are written by the stream once Ctrl+C stops it, and the
  REPL ignores Ctrl+C between terminals instead of letting the signal end the process.
- Throughput, measured with a 200,000 line log on the Native AOT build: streaming into a pipe went from 30.8 s to 2.1 s
  (about 95,000 lines a second) and to a terminal, with highlighting, from 30.8 s to 19.6 s. The text prefix is read by
  a byte scanner instead of three capture regexes (15.6 to 2.4 µs a line), SQL is found with plain searches for its
  prefixes instead of one regex with lazy captures (50 to 1.6 µs), duration and connection parsing ask whether a
  pattern matches before extracting its parts, piped output skips semantic highlighting since it drops styles, streams
  write through a buffer flushed per batch, and tail mode trims its entries once per frame.

- Tail mode's prompt, found janky in real use: after each command the Python release, and the port with it, handed the
  focus back to the log, so the next command's letters ran log keys (`v` started visual mode), and command output went
  into the log, where a busy server scrolled it away within a second. The input now keeps the focus, text typed on the
  log that is not one of its keys goes to the input, `tail>` is a prompt rather than a placeholder, and command output
  stays in a panel above the input until the next command or Escape, paging with PgUp/PgDn. The panel's place is always
  in the layout: inserting it moved the input to a new position, Hex1b built a new editor for it, and the focus fell
  back to the log. The `?` overlay was taller than a 24-row terminal; it now fits and scrolls. The harness shortcut
  (Escape, `/`, command) hid all of this, so tests now type commands one after another the way a person does.
- Debian and Ubuntu, checked with a real PostgreSQL 18 server laid out as a Debian cluster in a bubblewrap sandbox
  (data in `/var/lib/postgresql/18/main`, configuration in `/etc/postgresql/18/main`, output sent to
  `/var/log/postgresql/postgresql-18-main.log` as `pg_ctlcluster` does, per postgresql-common's `PgCommon.pm` and
  `pg_ctlcluster`): the cluster was detected but reported logging off, and Debian's default
  `log_line_prefix = '%m [%p] %q%u@%d '`, which the docs also recommend, left every session line unparsed. pgtail now
  tails the `pg_ctlcluster` log when the collector is off, finds a stopped cluster from `/etc/postgresql` when its data
  directory is closed to the user, suggests the `adm` group when the log is unreadable, and reads any prefix that starts
  with the time, keeping `user@database`. Homebrew, Postgres.app, RHEL, PGDG, and Arch layouts were each placed in a
  sandbox and detected. Advice text forms nothing used were removed.
- Notifications on Linux, checked in tail mode against the live workload while `dbus-monitor` watched `Notify` calls on
  the desktop session bus: level, pattern, slow query, and error rate rules each fire with the Python release's titles
  and bodies, at most one every five seconds; quiet hours silence them, including an overnight window, and a window
  that does not cover the current time does not; `notify test` always sends. A pattern with a space was cut at the
  space, as in the Python release, and now takes the rest of the line. Linux config and history paths follow
  `XDG_CONFIG_HOME` and `XDG_DATA_HOME`. What is left unchecked needs macOS or Windows: `osascript` and toast
  notifications, their config paths, the Windows known data directories, and the Windows no-console exit.
- A hands-on pass through the REPL, the way a person uses it, against the live workload: deleting back to an empty line
  opened a menu of every command (now closed until something is typed or Tab is pressed); `level` and `levels` were
  each unknown in the other mode (each mode now takes both); a misspelled setting such as `slow.warning` loaded silently
  and the editor saved it (loading now warns and the editor refuses, with settings earlier releases wrote still
  accepted); undoing edits back to the saved text still counted as unsaved (the editor now compares the text).
  Tail mode clicks, the paused REPL stream, live views, export, and pipe behaved as expected. `tail --since` reads the
  log from its start, as the Python release did, taking about two seconds on a 132,000-line log.
- Windows, reviewed for what CI will meet: Hex1b starts a process straight into a pseudoconsole, as Windows Terminal does
  for a profile whose command is `pgtail`, so pgtail was the only process on its console and the check carried over from
  the Python release (exit when alone, for winget validation) would have ended the REPL at once, failing every
  interactive test and the publish script's REPL check on Windows. A console hosted by a terminal has a
  `PseudoConsoleWindow` stand-in window, so pgtail now exits only when it is alone on a console without one. The publish
  script also starts the REPL on Windows with no console and expects a prompt exit with status 0. New tests name each
  platform's config path, known user data location, and notification backend, and send a real notification on macOS
  and Windows; they run on the CI runners, which need the branch pushed.
- Tail mode's input, used again with a busy log: the grey suggestion was drawn with Hex1b's inline hints, which are
  inlay hints placed before the character at their position, so the editor's drawn cursor sat after the suggestion and
  jumped as it changed. The input is now Hex1b's single-line `TextBox`, whose own predictions draw the suggestion after
  the caret and whose caret is the terminal's cursor, placed at the caret at the end of every synchronized frame. The
  shell line keys work on either input through a small line interface. `q` typed in the input is text; the Python
  release's quit-on-`q`-when-empty is gone, since `q` and Enter runs the `q` command. A complete word such as `level`
  no longer suggests the longer `levels` alias.
- Notifications, after a user got one for a warning from hours earlier while running `tail 0 --since 1d`: sources now
  report `CaughtUp` once they have read what the log held when tailing started, and only entries after that run the
  notification rules (piped input counts as new). Instead of dropping every alert within five seconds of the last one,
  pgtail holds them and shows one notification that counts them and names the most severe; a message shown in the last
  minute, apart from its numbers, is counted as a repeat and reported with its count when it next shows. Checked with a
  day of backlog (140,000 lines, no notifications) and 72 seconds of constant errors and repeated warnings (4
  notifications instead of 14). Hex1b apps get no terminal focus events, so pgtail cannot hold notifications while its
  terminal is in front.
- The tail prompt's suggestion now comes from pgtail each frame and is drawn after a content-width text box: the text
  box's own predictions run on a thread pool task, and one computed for an earlier keystroke could land after Enter had
  emptied the line, leaving a stale grey suggestion on an empty prompt.
- `tail 0 --since 1d` scrolled through the day before settling at the tail: the file was read a megabyte per 100 ms
  poll, tail mode drew 2,000 entries a frame, and a filter change redrew 500 a frame. Now a source reads a backlog back
  to back, tail mode reads it without drawing (the status bar reads `LOADING n`) and then shows the newest entries at
  once, a filter change redraws in one pass, and rows get their semantic highlighting when first drawn, from a quick
  formatting with the same text. Tail mode also reads only the log's last 20,000 lines, found by counting line endings
  back from the end and moving on to the first line that starts an entry, since it keeps 10,000; streaming still reads
  the whole range. A day of the test server's log (142,000 lines) opens at the tail 0.28 s after the screen appears in
  the Native AOT build, against about 5 s of scrolling before; the Debug build spends another second compiling.
- Mouse in tail mode from the REPL: full screen apps were built without `WithMouse()` on the terminal builder, and the
  app option pgtail set does not turn mouse reporting on in the terminal, so clicks and drags never arrived and the
  wheel worked only as the arrow keys some terminals send without mouse reporting. The editor and tail mode now turn it
  on, a test checks the modes a real terminal receives, and the scrollbar can be pressed and dragged. The tail input is
  now drawn by pgtail, since Hex1b's text box shows the terminal's cursor as a steady bar and hides it without focus:
  the block cursor blinks while the input has focus and stays solid while the log has it.
- `10,000 lines` in the status bar was tail mode's limit, not the range: the Python release kept 10,000 lines too, and
  a filter such as `level error` then only saw those. Tail mode now keeps up to 200,000 entries and loads a time
  filter's whole range: the newest 20,000 lines first, then the file read backward a megabyte at a time from where they
  began, each chunk starting at its first line that starts an entry, reported as `Older` entries and put in front
  without moving the view. The log holds one segment per entry, with its row count (one per line of the message), and
  makes rows only when they are drawn, keeping the last 5,000 made. On the test server's day (142,358 lines, two of
  them without a text time, which a time filter leaves out) the Native AOT build shows the tail at 0.5 s and the whole
  day at 1.1 s in 167 MB, and `level error` finds the day's 1,993 errors in about 0.4 s.
- The output panel over the tail input was a mistake: `help` showed its first six lines and "31 more below · PgUp/PgDn
  scroll · Esc closes", which read as nonsense, where the Python release wrote `help` into the log and showed its end,
  the command list. Command output is written into the log again and the panel is gone; the status bar's line count
  leaves such output out. Page Up and Page Down now scroll a whole page with the cursor line along, as a pager does;
  they moved the cursor line a page, so from the newest line the view moved by one line.
- Four review findings, each now covered by a terminal test that fails without the fix. Sources flushed the entry
  grouper after every read, so an error ending a one-megabyte read (or a 64 KiB read of piped input) lost its
  `STATEMENT:` to a separate entry; files now hold the last entry until the read reaches the end, each file of a
  multi-file tail keeps its own grouper, and piped input holds it until more input arrives or 100 ms pass without any.
  Entries read back were counted in the statistics after the newest, which reopened closed connections and moved the
  last error time back; tail mode now clears the statistics once reading back ends and counts every entry kept again in
  order, 5,000 a frame, counting entries that arrive meanwhile when it reaches them and finishing when tail mode ends.
  A truncated file kept the cached first line tail mode detects the format from, and `long.Parse` of a huge relative
  time threw outside the overflow guard.
- The recount first took 675 ms at once for the test server's day (136,336 entries): 3.3 µs an entry went to the
  duration regex, which matches 108,000 of them, and 1.5 µs to encoding each message and matching the connection
  patterns. Durations are now scanned for by hand (same results, by the new stats test run against both) and the
  connection patterns run only on messages with their opening words, so the day recounts in 143 ms over 28 frames of at
  most 27 ms in the Native AOT build.
- A second review found two gaps. Leaving tail mode before `OlderRead` arrived skipped the recount, so older entries
  already read back were never counted; ending now starts the recount itself when history is uncounted. The test warms
  the code up with a first run: cold, the Debug build read the whole range back before the screen's first frame after
  loading, which left no window to leave in, while warm it shows `(loading older)` for about 800 ms, as the Native AOT
  build does, and the test failed three runs of three without the fix. Following the directory now takes a log with the
  same extension written after the file read, and only from a file that was the newest there when tailing began: the
  Python release switched a named file to the directory's newest log at the first idle poll, which made tailing a copy
  read the original too (two copies of the test server's day, 0.47 s apart, showed 261,107 lines instead of 142,356)
  and a named older log turn into the current one. Looking the newest log up by extension also lets a server writing
  both `.log` and `.csv` files be followed; the newest of either kind was looked up and a `.csv` one ignored.
- A full run then failed `Connections_OlderEntriesReadBack_CountInOrder` once: `connections` ran while the recount was
  still spread over frames and printed part of the range. A command in tail mode now finishes the recount first, as a
  user typing `errors` right after loading would otherwise see. The same run failed the cursor blink test, whose wait
  for the log's focus after Tab passed on any frame with the cursor on, focused or not; it now presses `p`, which only
  the log takes, and waits for `PAUSED`.
- The docs build printed three warnings under Astro 7.3.5 and Starlight 0.42.4, both current. Starlight reads an
  `i18n` collection and a docs entry named `404`, and Astro 7 now logs a miss; Starlight's attempt to quiet the first
  replaces `console.warn`, which Astro's logger does not use. The collection is now declared as the Starlight i18n
  guide shows, with an `en.yml` that changes no strings and says so, and the not found page is `src/pages/404.astro`
  with `disable404Route`, as Starlight's configuration reference describes: a `404.md` entry, as Starlight's own docs
  use, also clashes with the injected route and Astro warns about that. Rolldown's `MODULE_LEVEL_DIRECTIVE` warning
  on the `"use astro:head-inject"` Astro puts in MDX asset modules is dropped by an `onLog` filter for that directive
  only, as other Astro 7 sites do, until withastro/astro#18088 removes the dead directive. The landing page's text is
  unchanged; the not found page is titled "Page not found" and links home.
