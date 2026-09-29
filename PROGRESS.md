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
- Regular expressions are .NET regular expressions; Python-only syntax such as `(?P<name>...)` is not translated.
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
- Design: the REPL runs as a Hex1b Flow (inline, scrollback-preserving, like the prompt_toolkit REPL), tail mode is a
  full-screen Flow step, and the tail log is a read-only Hex1b editor with decoration providers (the dotsider approach).
