---
title: Command line
description: Every pgtail command-line option, REPL command, tail mode command, and key.
---

## Command line

```
pgtail [OPTIONS] COMMAND [ARGS]...
```

Without a command, pgtail starts the interactive REPL.

### Global options

| Option | Description |
|--------|-------------|
| `-V`, `--version` | Show the version and exit |
| `--check-update` | Check for a newer release and exit |
| `--install-completion [SHELL]` | Install completion for the current shell (bash, zsh, fish, pwsh) |
| `--show-completion [SHELL]` | Print the completion script, to copy it or customize the installation |
| `-h`, `--help` | Show help and exit; `pgtail COMMAND --help` shows a command's options |

### Commands

| Command | Description |
|---------|-------------|
| `list-instances` (or `list`) | List detected PostgreSQL instances |
| `tail` | Tail logs for a PostgreSQL instance or arbitrary log files |
| `config` | Show or manage the configuration |
| `enable-logging` | Enable `logging_collector` for an instance |

#### list-instances

```
pgtail list-instances [-v | --verbose]
```

Prints the instances found, with their ID, version, port, status, and source. `--verbose` adds each data directory,
log path, and whether logging is enabled.

#### tail

```
pgtail tail [OPTIONS] [INSTANCE_ID]
```

| Option | Description |
|--------|-------------|
| `-f`, `--file TEXT` | Path or glob pattern to tail; repeat for more files |
| `--stdin` | Read log data from a pipe |
| `-s`, `--since TEXT` | Show entries from a time (`5m`, `1h`, `14:30`) |
| `--stream` | Print entries to standard output instead of the full screen view |

```sh
pgtail tail 0                                 # By instance ID
pgtail tail --file ./tmp_check/log/postmaster.log
pgtail tail --file "*.log"                    # Glob pattern (multiple files)
pgtail tail --file a.log --file b.log         # Multiple explicit files
cat log.gz | gunzip | pgtail tail --stdin     # From a pipe
cat log.gz | gunzip | pgtail tail --stdin --stream   # From a pipe, printed through the filters
pgtail tail --file ./test.log --since 5m      # Start with a time filter
```

Notes:

- With one instance detected, `pgtail tail` tails it; with several, give an ID or `--file`.
- `--file` and an instance ID cannot be combined, and `--stdin` works with neither.
- Glob patterns expand to files ordered most recently modified first.
- Tailing several files marks each entry with its `[filename]`.
- `--stream` follows a single file (or the pipe with `--stdin`).
- With `--stdin` and no `--stream`, the piped data is read in full before tail mode opens, and the keyboard is read
  from the terminal.

#### config

```
pgtail config [-p | --path] [-e | --edit] [--reset]
```

Without options, prints the configuration as TOML. `--path` prints the file's location, `--edit` opens it in the
built-in editor, and `--reset` resets it to the defaults, keeping a backup. See [Configuration](/configuration/).

#### enable-logging

```
pgtail enable-logging INSTANCE
```

Edits the instance's `postgresql.conf`, keeping a backup, to turn on the logging collector. `INSTANCE` is an
instance ID or data directory. PostgreSQL must be restarted afterward.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | The command failed, such as a file that does not exist or an instance without logging |
| 2 | The command line was invalid, such as an unknown command or option |

## REPL commands

### Instances

| Command | Description |
|---------|-------------|
| `list` (or `ls`) | Show detected PostgreSQL instances |
| `refresh` | Scan for instances again |
| `enable-logging <id>` | Enable `logging_collector` for an instance |

### Tailing

| Command | Description |
|---------|-------------|
| `tail <id>` | Open tail mode for an instance (by ID or data directory) |
| `tail <id> --since <time>` | Start with a time filter |
| `tail --file <path>` (or `-f`) | Tail a log file; repeat for more files, or use a glob pattern |
| `tail <id> --stream` | Print entries in the REPL instead of opening tail mode |
| `stop` | Stop a streaming tail |

While streaming, `Ctrl+C` pauses the output and the prompt changes to `paused [id]>`; `stop` stops the stream.

### Filtering

| Command | Description |
|---------|-------------|
| `levels [LEVEL...]` | Set the level filter (`levels ERROR WARNING`, `levels error+`); with no levels, show it |
| `levels ALL` | Show every level |
| `filter /pattern/` | Show only lines matching a regular expression, ignoring case |
| `filter /pattern/c` | The same, matching case |
| `filter -/pattern/` | Hide matching lines |
| `filter +/pattern/` | Add an OR pattern |
| `filter &/pattern/` | Add an AND pattern |
| `filter field=value` | Filter by a field (CSV and JSON logs) |
| `filter clear` | Clear the regular expression and field filters |

See [Filtering](/guide/filtering/).

### Time filters

| Command | Description |
|---------|-------------|
| `since <time>` | Show entries from a time on |
| `until <time>` | Show entries up to a time |
| `between <start> <end>` | Show entries in a range |
| `since clear` | Remove the time filter |

See [Time filters](/guide/time-filters/).

### Display

| Command | Description |
|---------|-------------|
| `display` | Show the display mode |
| `display compact` | One line per entry (default) |
| `display full` | Every field an entry has, with labels |
| `display fields <f1,f2>` | Only the chosen fields |
| `output text` | Colored text (default) |
| `output json` | One JSON object per entry |

The fields for `display fields` are `application`, `backend_type`, `command_tag`, `context`, `database`, `detail`,
`hint`, `level`, `location`, `message`, `pid`, `query`, `session_id`, `sql_state`, `timestamp`, and `user`.

### Slow queries

| Command | Description |
|---------|-------------|
| `slow` | Show the slow query thresholds |
| `slow <warning> <slow> <critical>` | Set the thresholds in milliseconds |
| `slow off` | Turn slow query highlighting off |
| `stats` | Show query duration statistics |

### Statistics

| Command | Description |
|---------|-------------|
| `errors` | Error summary |
| `errors --trend` | Error rate sparkline for the last 60 minutes |
| `errors --live` | Live error counter (`Ctrl+C` to exit) |
| `errors --code <CODE>` | Errors with one SQLSTATE |
| `errors --since <time>` | Errors in a time window |
| `errors clear` | Reset the statistics |
| `connections` | Connection summary |
| `connections --history` | Connects and disconnects over the last hour |
| `connections --watch` | Live stream of connection events (`Ctrl+C` to exit) |
| `connections --db=NAME` | Filter by database (also `--user=NAME`, `--app=NAME`) |
| `connections clear` | Reset the statistics |

### Export

| Command | Description |
|---------|-------------|
| `export <file>` | Export the filtered entries to a file |
| `export --format <fmt> <file>` | As `text`, `json`, or `csv` |
| `export --append <file>` | Add to an existing file |
| `export --since <time> <file>` | Only entries after a time |
| `export --follow <file>` | Keep writing new entries (`Ctrl+C` to stop) |
| `export --highlighted <file>` | Keep colors as ANSI escapes |
| `pipe <command>` | Pipe the filtered entries to a shell command |
| `pipe --format <fmt> <command>` | Pipe in a format |

See [Export and pipe](/guide/export/).

### Notifications

| Command | Description |
|---------|-------------|
| `notify` | Show the notification settings |
| `notify on <levels>` | Notify for levels (`FATAL PANIC`, `error+`) |
| `notify on /pattern/` | Notify for a pattern (`/pattern/i` ignores case) |
| `notify on errors > N/min` | Notify when the error rate exceeds N a minute |
| `notify on slow > Nms` | Notify for queries slower than N ms |
| `notify off` | Stop notifying |
| `notify test [severity]` | Send a test notification (`info`, `warning`, `error`, `critical`) |
| `notify quiet HH:MM-HH:MM` | Set quiet hours (`notify quiet off` removes them) |
| `notify clear` | Remove every rule |

### Configuration

| Command | Description |
|---------|-------------|
| `config` | Show the configuration as TOML |
| `config path` | Show the config file path |
| `config edit` | Edit it in the built-in editor |
| `config reset` | Reset to the defaults, keeping a backup |
| `set <key> [value]` | Set a value, or show it |
| `unset <key>` | Remove a value, going back to its default |

### Themes

| Command | Description |
|---------|-------------|
| `theme` | Show the current theme |
| `theme <name>` | Switch theme |
| `theme list` | List the themes |
| `theme preview <name>` | Preview a theme without switching |
| `theme edit <name>` | Create or edit a custom theme in the built-in editor |
| `theme reload` | Reload the current theme from its file |

### Highlighting

| Command | Description |
|---------|-------------|
| `highlight` / `highlight list` | Show the global status and every highlighter |
| `highlight on` / `highlight off` | Turn highlighting on or off |
| `highlight enable <name>` / `highlight disable <name>` | Turn one highlighter on or off |
| `highlight add <name> <pattern> [--style <style>] [--priority <n>]` | Add a custom highlighter |
| `highlight remove <name>` | Remove a custom highlighter |
| `highlight preview` | Preview with sample log lines |
| `highlight reset` | Reset to the defaults |
| `highlight export [--file <path>]` | Export the settings as TOML |
| `highlight import <path>` | Import settings from a file |
| `highlight /pattern/` | Mark matches in streamed output (`/pattern/c` matches case) |
| `highlight clear` | Remove the `/pattern/` marks |

**Examples:**

```
highlight disable timestamp
highlight add request_id "REQ-[A-Z]{3}-\d{6}" --style "cyan"
highlight add txn_id "TXN:[0-9a-f]{16}" --style "bold magenta" --priority 500
highlight export --file ~/highlight.toml
highlight import ~/highlight.toml
```

See [Highlighting](/guide/highlighting/).

### General

| Command | Description |
|---------|-------------|
| `help` | Show the command reference |
| `clear` | Clear the screen |
| `quit` / `exit` / `q` | Leave pgtail |
| `!<command>` | Run a shell command |
| `!` | Enter shell mode |

An unknown command prints `Unknown command: <name>` and points to `help`.

## REPL keys

| Key | Action |
|-----|--------|
| `Tab` | Complete; with the menu open, select the next item |
| `Shift+Tab` | Select the previous item in the menu |
| `Up` / `Down` | Move through the menu, or through command history when it is closed |
| `Enter` | Run the command |
| `Escape` | Close the menu, or leave shell mode |
| `Ctrl+C` | Abandon the line |
| `Ctrl+D` | Leave pgtail on an empty line |
| `Ctrl+L` | Clear the screen |
| `Ctrl+A` / `Ctrl+E` | Move to the start or end of the line |
| `Ctrl+B` / `Ctrl+F`, `Alt+B` / `Alt+F` | Move back or forward a character, or a word |
| `Ctrl+K` / `Ctrl+U` | Cut to the end or the start of the line |
| `Ctrl+W` / `Alt+D` | Cut the word before or after the caret |
| `Ctrl+Y` | Paste the last cut text |
| `Ctrl+R` | Search the history backward: type part of a command, `Ctrl+R` again for an older one; `Enter` runs it, `Escape` or an arrow key keeps it for editing, `Ctrl+G` cancels |

Completions appear as you type, with a description of each command, subcommand, flag, and value. The REPL history is
kept across sessions (see [Configuration](/configuration/#config-file-location)).

## REPL bottom toolbar

The REPL keeps a toolbar at the bottom of the terminal:

```
 3 instances • levels:ERROR,WARNING filter:/timeout/i • Theme: monokai
```

| Section | Description |
|---------|-------------|
| Instance count | `N instances`, or `No instances (run 'refresh')` |
| Active filters | Levels, regular expression, and time filters |
| Theme | The current color theme |

## Shell mode

Run shell commands without leaving pgtail:

| Key or command | Description |
|----------------|-------------|
| `!<command>` | Run a shell command at once |
| `!` on an empty line | Enter shell mode: each line runs in the shell |
| `Escape` | Leave shell mode (also Backspace on an empty line) |

In shell mode the prompt is `!` and the toolbar shows:

```
 SHELL • Press Escape to exit
```

**Examples:**

```
pgtail> !ls -la           # Run ls
pgtail> !                 # Enter shell mode
! echo "hello"            # Runs in the shell
```

Commands run in `sh` (`powershell` or `cmd` on Windows) on the terminal itself, so interactive programs such as
`psql` work.

## Tail mode commands

In tail mode, the `tail>` input offers command history (Up/Down, kept across sessions) and completion suggestions
(Right or End to accept).

| Command | Description |
|---------|-------------|
| `level <lvl>` | Level filter (`error`, `error+`, `warning-`, `error,warning`, `all`) |
| `filter /pattern/` | Regular expression filter (`/c`, `-/`, `+/`, `&/`, `field=value`, `clear`) |
| `since <time>` | Time filter |
| `until <time>` | End time filter |
| `between <s> <e>` | Time range |
| `slow <ms>` | Slow query threshold (`slow off`) |
| `clear` | Reset to the filters tail mode started with |
| `clear force` | Clear every filter |
| `errors` | Error statistics |
| `connections` | Connection statistics |
| `highlight` | Manage semantic highlighters |
| `set <key> [value]` | Show or change a setting |
| `export <path>` | Export the shown entries |
| `theme <name>` | Switch theme |
| `notify` | Configure notifications |
| `pause` / `p` | Pause |
| `follow` / `f` | Resume following |
| `help [command\|keys]` | Show help |
| `stop` / `exit` / `q` | Leave tail mode |

See [Tail mode](/guide/tail-mode/) for every key.

## Shell completion

pgtail completes commands, options, file paths, and instance IDs in bash, zsh, fish, and PowerShell.

### Installing completion

`--install-completion` detects your shell:

```sh
pgtail --install-completion
```

Or name it: `pgtail --install-completion zsh`. Then restart your shell, or load its configuration:

```sh
# Bash
source ~/.bashrc

# Zsh
source ~/.zshrc

# Fish loads it automatically
```

To print the script without installing it:

```sh
pgtail --show-completion
```

### What gets completed

| Context | Completion |
|---------|------------|
| `pgtail <TAB>` | Commands |
| `pgtail -<TAB>` | Global options |
| `pgtail tail <TAB>` | Instance IDs with version, port, and status |
| `pgtail tail --<TAB>` | Options (`--file`, `--stdin`, `--since`, `--stream`) |
| `pgtail tail --file <TAB>` | File paths |
| `pgtail tail --since <TAB>` | Time presets |
| `pgtail config --<TAB>` | Options |
| `pgtail enable-logging <TAB>` | Instance IDs |

Options are offered once the word starts with `-`.

### Instance ID completion

zsh, fish, and PowerShell show each instance's version, port, and status:

```sh
$ pgtail tail <TAB>
0  -- PG17:5432 (running)
1  -- PG16:5433 (stopped)
2  -- PG15:5434 (running)
```

### Troubleshooting

**Completion not working after installation:**

1. Restart your shell or load its configuration
2. Check that the script was installed:
   - Bash: `~/.bash_completions/pgtail.sh`, sourced from `~/.bashrc`
   - Zsh: `~/.zfunc/_pgtail`, with `fpath+=~/.zfunc` and `compinit` in `~/.zshrc`
   - Fish: `~/.config/fish/completions/pgtail.fish`
   - PowerShell: your PowerShell profile

**Zsh: command not found: compdef**

Enable the completion system in `~/.zshrc`:

```sh
autoload -Uz compinit && compinit
```

**Bash: complete: command not found**

Install bash-completion:

```sh
# macOS
brew install bash-completion@2

# Ubuntu/Debian
sudo apt install bash-completion
```

**Removing completion:** delete the installed script (listed above), and the line pgtail added to your shell's
configuration file.
