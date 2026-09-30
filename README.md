<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="art/pgtail-logo-gh-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="art/pgtail-logo-gh-light.png">
    <img alt="pgtail logo" src="art/pgtail-logo-gh-light.png" width="200">
  </picture>
</p>

# pgtail

An interactive PostgreSQL log tailer. It finds the PostgreSQL instances on your machine, follows their logs in a full
screen view, and colors and filters what matters while the log keeps running.

Documentation: https://pgtail.dev/

## Install

```sh
dotnet tool install -g pgtail
```

| Method | Command |
|--------|---------|
| Homebrew (macOS, Linux) | `brew tap willibrandon/tap && brew install pgtail` |
| winget (Windows) | `winget install willibrandon.pgtail` |
| Scoop (Windows) | `scoop bucket add willibrandon https://github.com/willibrandon/scoop-bucket && scoop install pgtail` |
| Archive or MSI | [GitHub Releases](https://github.com/willibrandon/pgtail/releases/latest) |

pgtail is a native executable for Windows, Linux, and macOS on x64 and Arm64, with nothing else to install. The
[installation guide](https://pgtail.dev/getting-started/installation/) covers each method, upgrading, and shell
completion.

## Use

```sh
pgtail                           # The interactive prompt
pgtail list                      # The PostgreSQL instances it found
pgtail tail 0                    # Follow instance 0 in tail mode
pgtail tail 0 --since 1h         # Starting an hour back
pgtail tail --file ./server.log  # Any log file, or a glob of them
pgtail tail 0 --stream           # Print entries instead, for piping
```

In tail mode the log scrolls with vim keys or the mouse, and commands typed at the `tail>` input change what it shows:

```
tail> level error+        # ERROR and more severe
tail> filter /deadlock/   # A regular expression
tail> since 5m            # The last five minutes
tail> errors              # Error statistics
tail> clear               # Back to where tail mode started
```

The [quick start](https://pgtail.dev/getting-started/quickstart/) walks through a first session.

## What it does

- Finds instances from running processes, pgrx, `PGDATA`, and the usual Homebrew, Debian and Ubuntu, PGDG, Postgres.app,
  and Windows locations, and follows PostgreSQL to its next log file after a rotation or restart
- Reads text, csvlog, and jsonlog, from an instance, from files and globs, or from a pipe
- Filters by level, regular expression, time range, and csvlog or jsonlog fields, changed while the log runs
- Highlights SQL, durations, SQLSTATE codes, LSNs, locks, and more with thirty semantic highlighters, plus your own
  patterns, in six built-in color themes or one you write
- Reports error, connection, and query duration statistics, and flags slow queries by threshold
- Sends desktop notifications for levels, patterns, error rates, and slow queries, with quiet hours
- Exports the filtered entries as text, JSON Lines, or CSV, or pipes them to any command

Each of these has a page in the [guide](https://pgtail.dev/guide/tail-mode/); the
[command reference](https://pgtail.dev/cli-reference/) lists every command and the
[configuration reference](https://pgtail.dev/configuration/) every setting.

## Building

pgtail needs the [.NET 10 SDK](https://dotnet.microsoft.com/download).

```sh
git clone https://github.com/willibrandon/pgtail.git
cd pgtail
dotnet build
dotnet test
dotnet run --project src/Pgtail
```

`scripts/Publish-NativeAot.cs` publishes the native executable for a runtime as the release does; see
`scripts/README.md`. The documentation site in `docs/` is built with [pnpm](https://pnpm.io/installation):
`pnpm install`, then `pnpm build` or `pnpm dev`. [CONTRIBUTING.md](CONTRIBUTING.md) has the conventions.

## License

MIT
