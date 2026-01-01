# Quick Start

## Starting pgtail

Launch the interactive REPL:

```bash
pgtail
```

You'll see the prompt:

```
pgtail>
```

## List PostgreSQL Instances

```
pgtail> list
```

pgtail automatically detects PostgreSQL instances from:

1. Running processes (`postgres` or `postmaster`)
2. pgrx development instances (`~/.pgrx/data-*`)
3. `PGDATA` environment variable
4. Platform-specific paths (Homebrew, system packages)

Example output:

```
ID  Version  Port   Status   Source
0   16.0     5432   running  process
1   15.4     5433   stopped  pgrx
```

## Start Tailing

Tail instance 0:

```
pgtail> tail 0
```

This enters the **tail mode** - a split-screen interface with:

- Log display area (scrollable, vim navigation)
- Command input (`tail>` prompt)
- Status bar (mode, counts, filters)

## Tail Mode Navigation

| Key | Action |
|-----|--------|
| `j` / `k` | Scroll down / up |
| `g` / `G` | Go to top / bottom |
| `Ctrl+d` / `Ctrl+u` | Half page down / up |
| `p` | Pause auto-scroll |
| `f` | Resume follow mode |
| `v` | Enter visual mode (character) |
| `V` | Enter visual mode (line) |
| `y` | Yank (copy) selection |
| `?` | Show help overlay |
| `/` | Focus command input |
| `q` | Quit tail mode |

## Filter Logs

In tail mode, use the command input:

```
tail> level error          # Show only ERROR
tail> level warning+       # WARNING and above (ERROR, FATAL, PANIC)
tail> filter /deadlock/    # Regex filter
tail> since 5m             # Last 5 minutes
tail> clear                # Reset filters
```

## Exit

Press `q` or type `stop` to exit tail mode.

Type `exit` or `quit` to exit pgtail.
