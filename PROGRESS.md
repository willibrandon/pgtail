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
