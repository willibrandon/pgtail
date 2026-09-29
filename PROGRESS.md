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

## Decisions

- Settings the Python release validated and stored but never read are not ported: `default.follow`,
  `display.timestamp_format`, `display.show_pid`, `display.show_level`, and `buffer.*`. The statistics and tail buffers
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

