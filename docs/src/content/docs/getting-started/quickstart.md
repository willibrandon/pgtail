---
title: Quick start
description: Start the REPL, find your PostgreSQL instances, and tail their logs.
---

## Starting pgtail

Launch the interactive REPL:

```sh
pgtail
```

pgtail prints a banner, then the prompt with a toolbar at the bottom of the terminal:

```
pgtail - PostgreSQL log tailer

Found 2 PostgreSQL instances. Type 'list' to see details.
Type 'help' for available commands, 'quit' to exit.

pgtail>

 2 instances • Theme: dark
```

The toolbar shows:

- **Instance count**: the number of detected PostgreSQL instances, or `No instances (run 'refresh')`
- **Active filters**: levels, regular expression, and time filters, when any are set
- **Theme**: the current color theme

As you type, a menu offers the commands and arguments that fit; **Tab** completes, and **Up** and **Down** move
through the menu or, when it is closed, through your command history.

## List PostgreSQL instances

```pgtail
pgtail> list
```

pgtail finds PostgreSQL instances from:

1. Running processes (`postgres` or `postmaster`)
2. pgrx development instances (`~/.pgrx/data-*`)
3. The `PGDATA` environment variable
4. Platform locations: Homebrew, Debian and Ubuntu clusters, PGDG and RPM layouts, Arch Linux, Postgres.app, and the
   Windows installer's `Program Files\PostgreSQL\*\data`

A Debian or Ubuntu cluster is found from `/etc/postgresql/<version>/<cluster>` even though its data directory is closed
to other users. With the logging collector off, as installed, `pg_ctlcluster` writes the server log to
`/var/log/postgresql/postgresql-<version>-<cluster>.log`, and pgtail tails that file; members of the `adm` group can
read it.

Example output:

```
  #  VERSION  PORT   STATUS   LOG  SOURCE  DATA DIRECTORY
  0  17       5432   running  on   process /var/lib/postgresql/17/main
  1  16       5433   stopped  on   pgrx    ~/.pgrx/data-16
```

`LOG` says whether the instance logs to files: the logging collector is on, or a Debian or Ubuntu cluster logs through
`pg_ctlcluster`. Run `refresh` to scan again after starting an instance.

## Start tailing

Tail instance 0:

```pgtail
pgtail> tail 0
```

Or tail log files directly, from the REPL or the command line:

```sh
pgtail tail --file /path/to/postgresql.log
pgtail tail --file "*.log"                  # Glob pattern (multiple files)
cat log.gz | gunzip | pgtail tail --stdin   # From a pipe
```

This opens **tail mode**, a full screen view with:

- The log, which follows new entries and scrolls with vim keys or the mouse
- A command input (`tail>`) with command history (Up/Down) and suggestions as you type. It keeps the focus after each
  command, and a command's output, such as `help`, is written into the log
- A status bar with the mode, error and warning counts, the line count, filters, and the instance

## Tail mode keys

| Key | Action |
|-----|--------|
| `j` / `k` | Down / up one line |
| `g` / `G` | Top / bottom |
| `Ctrl+d` / `Ctrl+u` | Half page down / up |
| `p` | Pause |
| `f` | Resume following |
| `v` | Visual mode (character) |
| `V` | Visual mode (line) |
| `y` | Yank (copy) the selection |
| `?` | Show the key reference |
| `/` or `Tab` | Focus the command input (typing a command on the log also does) |
| `PgUp` / `PgDn` | Scroll the log a page, from the input too |
| `Escape` | In the input, clear it and move to the log |
| `q` | Leave tail mode from the log; in the input, type `q` and Enter |

## Filter logs

In tail mode, type commands at the `tail>` input:

```pgtail
tail> level error          # Only ERROR
tail> level warning+       # WARNING and above (ERROR, FATAL, PANIC)
tail> filter /deadlock/    # Regular expression, ignoring case
tail> since 5m             # The last 5 minutes
tail> clear                # Back to the filters tail mode started with
```

The log redraws with every entry that matches, including ones read before the filter changed.

## Exit

Press `q` in the log, or type `stop`, to leave tail mode and return to the REPL.

Type `quit` or `exit`, or press `Ctrl+D` on an empty line, to leave pgtail.
