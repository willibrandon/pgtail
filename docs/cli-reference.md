# CLI Reference

Complete reference for all pgtail commands.

## REPL Commands

### Instance Management

| Command | Description |
|---------|-------------|
| `list` | List detected PostgreSQL instances |
| `select <id>` | Select an instance for commands |
| `scan` | Re-scan for instances |

### Tailing

| Command | Description |
|---------|-------------|
| `tail <id>` | Enter tail mode for instance |
| `tail <id> --since <time>` | Tail with time filter |
| `tail --file <path>` | Tail arbitrary log file |
| `tail --file "*.log"` | Tail files matching glob pattern |
| `tail --file a.log --file b.log` | Tail multiple explicit files |
| `tail --stdin` | Read log data from stdin pipe |
| `tail <id> --stream` | Legacy streaming mode |
| `stop` | Stop tailing |

**File Tailing Examples:**

```bash
# Single file (CLI)
pgtail tail --file /path/to/postgresql.log
pgtail tail -f ./test.log  # Short form

# Glob patterns
pgtail tail --file "*.log"
pgtail tail --file "/var/log/postgresql/*.log"

# Multiple files
pgtail tail --file a.log --file b.log

# From stdin (compressed logs)
cat log.gz | gunzip | pgtail tail --stdin
zcat archived.log.gz | pgtail tail --stdin

# With time filter
pgtail tail --file ./test.log --since 5m
```

**Notes:**
- `--file` and instance ID are mutually exclusive
- `--stdin` cannot be used with `--file` or instance ID
- Glob patterns expand to files sorted by modification time (newest first)
- Multi-file tailing shows `[filename]` source indicator
- Stdin data is buffered before display for keyboard navigation

### Filtering

| Command | Description |
|---------|-------------|
| `level <lvl>` | Set level filter |
| `level <lvl>+` | Level and more severe |
| `level <lvl>-` | Level and less severe |
| `filter /pattern/` | Add regex filter |
| `filter /pattern/i` | Case-insensitive regex |
| `filter field=value` | Field filter (CSV/JSON) |
| `unfilter /pattern/` | Remove regex filter |

### Time Filters

| Command | Description |
|---------|-------------|
| `since <time>` | Show from time onward |
| `until <time>` | Show up to time |
| `between <start> <end>` | Time range |
| `since clear` | Clear since filter |
| `until clear` | Clear until filter |

### Statistics

| Command | Description |
|---------|-------------|
| `errors` | Error summary |
| `errors --trend` | Error rate sparkline |
| `errors --live` | Live error counter |
| `errors --code <CODE>` | Filter by SQLSTATE |
| `errors clear` | Reset statistics |
| `connections` | Connection summary |
| `connections --history` | Connection history |
| `connections --watch` | Live connection stream |
| `connections clear` | Reset statistics |

### Export

| Command | Description |
|---------|-------------|
| `export <file>` | Export to file |
| `export --format <fmt> <file>` | Export with format |
| `export --append <file>` | Append to file |
| `export --since <time> <file>` | Time-scoped export |
| `export --follow <file>` | Continuous export |
| `pipe <cmd>` | Pipe to command |
| `pipe --format <fmt> <cmd>` | Pipe with format |

### Notifications

| Command | Description |
|---------|-------------|
| `notify` | Show notification status |
| `notify on <levels>` | Enable for levels |
| `notify on /pattern/` | Enable for pattern |
| `notify on errors > N/min` | Enable for error rate |
| `notify on slow > Nms` | Enable for slow queries |
| `notify off` | Disable all |
| `notify test` | Send test notification |
| `notify quiet HH:MM-HH:MM` | Set quiet hours |
| `notify clear` | Remove all rules |

### Configuration

| Command | Description |
|---------|-------------|
| `config` | Show current config |
| `config path` | Show config file path |
| `config edit` | Edit in $EDITOR |
| `config reset` | Reset to defaults |
| `set <key> <value>` | Set config value |
| `unset <key>` | Remove config value |

### Themes

| Command | Description |
|---------|-------------|
| `theme` | Show current theme |
| `theme <name>` | Switch theme |
| `theme list` | List available themes |
| `theme preview <name>` | Preview theme |
| `theme edit <name>` | Create/edit custom theme |
| `theme reload` | Reload current theme |

### Display

| Command | Description |
|---------|-------------|
| `display` | Show display mode |
| `display compact` | Compact single-line mode |
| `display full` | Full multi-line mode |
| `display fields <f1,f2>` | Custom field selection |
| `output text` | Text output format |
| `output json` | JSON Lines format |

### PostgreSQL

| Command | Description |
|---------|-------------|
| `enable-logging <id>` | Enable logging for instance |

### Slow Queries

| Command | Description |
|---------|-------------|
| `slow <ms>` | Set slow query threshold |
| `slow off` | Disable slow query highlighting |

### General

| Command | Description |
|---------|-------------|
| `help` | Show help |
| `clear` | Clear filters |
| `clear force` | Clear all including anchor |
| `exit` / `quit` | Exit pgtail |

## Tail Mode Commands

In tail mode (after `tail <id>`), use the `tail>` prompt:

| Command | Description |
|---------|-------------|
| `level <lvl>` | Level filter |
| `filter /pattern/` | Regex filter |
| `since <time>` | Time filter |
| `until <time>` | End time filter |
| `between <s> <e>` | Time range |
| `slow <ms>` | Slow query threshold |
| `clear` | Reset to anchor filters |
| `clear force` | Clear all filters |
| `errors` | Show error stats |
| `connections` | Show connection stats |
| `pause` / `p` | Pause auto-scroll |
| `follow` / `f` | Resume follow |
| `help` | Show help |
| `stop` / `q` | Exit tail mode |

## Tail Mode Keys

See [Tail Mode](guide/tail-mode.md) for complete key reference.

## REPL Bottom Toolbar

The REPL displays a persistent bottom toolbar showing current state:

```
 3 instances • levels:ERROR,WARNING filter:/timeout/i • Theme: monokai
```

**Sections:**

| Section | Description |
|---------|-------------|
| Instance count | "N instances" or "No instances (run 'refresh')" |
| Active filters | Level, regex, time, and slow query filters |
| Theme | Current color theme name |

The toolbar updates automatically when state changes.

## Shell Mode

Run shell commands without leaving pgtail:

| Key/Command | Description |
|-------------|-------------|
| `!<command>` | Run shell command immediately |
| `!` (empty) | Enter shell mode |
| `Escape` | Exit shell mode |

When in shell mode, the toolbar shows:

```
 SHELL • Press Escape to exit
```

**Examples:**

```
pgtail> !ls -la           # Run ls immediately
pgtail> !                  # Enter shell mode
! echo "hello"             # Run in shell mode
! <Escape>                 # Exit shell mode
```

## Shell Completion

pgtail provides intelligent shell completion for commands, options, and PostgreSQL instance IDs.

### Installing Completion

The `--install-completion` flag auto-detects your current shell:

```bash
pgtail --install-completion
```

After installation, restart your shell or source your shell's config file:

```bash
# Bash
source ~/.bashrc

# Zsh
source ~/.zshrc

# Fish (automatic)
```

To view the completion script without installing (for manual setup or customization):

```bash
pgtail --show-completion
```

### What Gets Completed

| Context | Completion |
|---------|------------|
| `pgtail <TAB>` | Commands (tail, list, config, etc.) |
| `pgtail tail <TAB>` | Instance IDs with version/port/status |
| `pgtail tail --<TAB>` | Options (--file, --since, --stdin) |
| `pgtail tail --file <TAB>` | File paths |
| `pgtail theme <TAB>` | Theme names |
| `pgtail set <TAB>` | Config keys |

### Instance ID Completion

When completing instance IDs, pgtail shows helpful context:

```bash
$ pgtail tail <TAB>
0  -- PG17:5432 (running)
1  -- PG16:5433 (stopped)
2  -- PG15:5434 (running)
```

The format is: `ID -- PGversion:port (status)`

### Troubleshooting

**Completion not working after installation:**

1. Ensure you restarted your shell or sourced the config
2. Check that the completion script was installed:
   - Bash: `~/.bash_completions/pgtail.sh`
   - Zsh: `~/.zfunc/_pgtail`
   - Fish: `~/.config/fish/completions/pgtail.fish`

**Zsh: command not found: compdef**

Enable the completion system in `~/.zshrc`:

```bash
autoload -Uz compinit && compinit
```

**Bash: complete command not found**

Ensure bash-completion is installed:

```bash
# macOS
brew install bash-completion@2

# Ubuntu/Debian
sudo apt install bash-completion
```

**Removing completion:**

```bash
pgtail --show-completion  # View the script to find the installed location
# Then manually delete the completion script from that location
```
