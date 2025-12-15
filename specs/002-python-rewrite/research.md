# Research: pgtail Python Rewrite

## prompt_toolkit REPL Implementation

**Decision**: Use `PromptSession` with custom completer and history file

**Rationale**:
- `PromptSession` provides persistent history, key bindings, and completion out of the box
- `FileHistory` class handles cross-platform history file management
- `WordCompleter` or custom `Completer` subclass for command/argument completion
- Built-in support for `NO_COLOR` environment variable via color depth detection

**Alternatives considered**:
- `prompt()` function: Simpler but no persistent state between calls
- Raw readline: Not cross-platform (no Windows support)
- cmd module: No autocomplete, no persistent history

**Key API patterns**:
```python
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter

session = PromptSession(
    history=FileHistory(history_path),
    completer=command_completer,
)
result = session.prompt("pgtail> ")
```

## psutil Process Detection

**Decision**: Use `psutil.process_iter()` with `name()` and `cmdline()` filtering

**Rationale**:
- Cross-platform API for process enumeration
- Can extract data directory from `postgres -D /path` command line
- Handles permission errors gracefully (returns None for inaccessible attributes)

**Alternatives considered**:
- `subprocess.run(['pgrep'])`: Unix-only
- `/proc` filesystem: Linux-only
- Windows WMI: Windows-only

**Key API patterns**:
```python
import psutil

for proc in psutil.process_iter(['name', 'cmdline', 'pid']):
    if proc.info['name'] == 'postgres':
        cmdline = proc.info['cmdline']
        # Extract -D argument for data directory
```

## watchdog File Monitoring

**Decision**: Use `Observer` with `FileSystemEventHandler` subclass, polling fallback

**Rationale**:
- Cross-platform with native backends (FSEvents on macOS, inotify on Linux, ReadDirectoryChangesW on Windows)
- `PollingObserver` fallback for edge cases (NFS, network drives)
- Event-based rather than polling by default (efficient)

**Alternatives considered**:
- `inotify`: Linux-only
- `pyinotify`: Linux-only, unmaintained
- Manual polling: Inefficient, misses rapid changes

**Key API patterns**:
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class LogHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == self.log_path:
            self.read_new_lines()

observer = Observer()
observer.schedule(handler, path=log_dir, recursive=False)
observer.start()
```

## Color Output Strategy

**Decision**: Use prompt_toolkit's built-in styling with `print_formatted_text()`

**Rationale**:
- prompt_toolkit automatically detects terminal capabilities (1-bit, 4-bit, 8-bit, 24-bit)
- Handles `NO_COLOR` and `TERM=dumb` automatically
- Consistent styling between prompt and output
- ANSI styles degrade gracefully on limited terminals

**Alternatives considered**:
- `colorama`: Requires explicit init on Windows, separate from prompt_toolkit
- `rich`: Heavy dependency, overkill for simple log coloring
- Raw ANSI codes: No terminal capability detection

**Key API patterns**:
```python
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText

styles = {
    'ERROR': 'ansired bold',
    'WARNING': 'ansiyellow',
    'NOTICE': 'ansicyan',
    'DEBUG': 'ansibrightblack',
}

def print_log(level, message):
    print_formatted_text(FormattedText([
        (styles.get(level, ''), f'{level}: {message}')
    ]))
```

## Platform-Specific Paths

**Decision**: Use `platformdirs` patterns with stdlib `pathlib`

**Rationale**:
- History file: `~/.local/share/pgtail/history` (Linux XDG), `~/Library/Application Support/pgtail/history` (macOS), `%APPDATA%\pgtail\history` (Windows)
- No additional dependency needed; simple platform detection with `sys.platform`

**Key patterns**:
```python
from pathlib import Path
import sys

def get_history_path() -> Path:
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'pgtail' / 'history'
    elif sys.platform == 'win32':
        return Path(os.environ.get('APPDATA', '')) / 'pgtail' / 'history'
    else:  # Linux/Unix
        xdg_data = os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))
        return Path(xdg_data) / 'pgtail' / 'history'
```

## PostgreSQL Log Parsing

**Decision**: Regex-based parsing with fallback for non-standard formats

**Rationale**:
- PostgreSQL default log format: `timestamp [pid] level: message`
- Single regex handles common formats
- Graceful fallback: unparseable lines shown as-is with default styling

**Pattern**:
```python
import re

LOG_PATTERN = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)? \w+)\s+'
    r'(?:\[(?P<pid>\d+)\]\s+)?'
    r'(?P<level>PANIC|FATAL|ERROR|WARNING|NOTICE|LOG|INFO|DEBUG[1-5]?):\s+'
    r'(?P<message>.*)$'
)
```

## PyInstaller Distribution

**Decision**: PyInstaller with `--onefile` for single executable

**Rationale**:
- Mature, well-documented tool
- Supports macOS, Linux, Windows
- `--onefile` creates single distributable binary
- Handles prompt_toolkit, psutil, watchdog dependencies

**Build command**:
```bash
pyinstaller --onefile --name pgtail pgtail_py/__main__.py
```

**Alternatives considered**:
- Nuitka: Faster startup but more complex setup
- cx_Freeze: Less active development
- shiv: Requires Python on target system
