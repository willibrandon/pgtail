# Contributing

Install the .NET 10 SDK that `global.json` names, or a newer 10.0 feature band. Then build and test:

```console
dotnet build
dotnet test
```

The tests use MSTest on Microsoft.Testing.Platform and need no PostgreSQL server or other setup. They run pgtail in
real Hex1b terminals, both in process and as the built executable, so they take a minute or two. Tests that cannot run
on your platform report themselves as skipped.

## Code

The build enforces the layout rules through `.editorconfig` and the analyzers in `src/Pgtail.Analyzers`, and warnings
are errors, so fix what it reports. Do not suppress a rule. In short: one type per file, explicit types rather than
`var`, lines of at most 140 characters, braces on their own lines around every body, a blank line after a closing
brace, and triple slash documentation on every public or internal type and member with a three-line `<summary>`.

pgtail is published with Native AOT, so code must be trimmable: no reflection over types the compiler cannot see, and
regular expressions through `GeneratedRegex`. Dependencies are Hex1b, Scout, and the .NET libraries; a small local
implementation is preferred to a new package.

## Tests

Tests exercise the real thing, through a terminal, the way a user would. Every test must be safe to run in parallel
with every other, so give each its own `TestEnvironment`. Wait for a condition on the screen, never for a fixed time.

## Scripts and documentation

Repository utilities are .NET file-based apps under `scripts/`. When you add or change one, update `scripts/README.md`.

The documentation site under `docs/` is built with pnpm; see the README. User-facing changes go in `CHANGELOG.md`.

## Pull requests

Describe the change in a few plain sentences. CI runs the tests on Linux, Windows, and macOS, publishes the Native AOT
executable for each platform and checks its size, and scans for secrets. CodeQL scans the C# source, and any finding
fails its check.
