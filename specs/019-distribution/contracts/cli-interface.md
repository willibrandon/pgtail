# Contract: CLI Interface

**Branch**: `019-distribution` | **Date**: 2026-01-01

## Overview

This contract defines the command-line interface additions for pgtail distribution features: `--version` and `--check-update` flags.

---

## Commands

### --version

**Description**: Display the installed pgtail version and exit.

**Usage**:
```bash
pgtail --version
pgtail -V
```

**Output Format**:
```
pgtail 0.1.0
```

**Exit Code**: 0

**Behavior**:
- Prints version to stdout
- Exits immediately (no REPL, no other output)
- No network calls

---

### --check-update

**Description**: Check for available updates and display upgrade instructions.

**Usage**:
```bash
pgtail --check-update
```

**Output Formats**:

**Up to date**:
```
pgtail 0.1.0 (up to date)
```

**Update available**:
```
pgtail 0.1.0 → 0.2.0 available
Upgrade: brew upgrade pgtail
```

**Network error**:
```
Unable to check for updates. Check your internet connection.
```

**Exit Codes**:
| Condition | Exit Code |
|-----------|-----------|
| Up to date | 0 |
| Update available | 0 |
| Network error | 1 |

**Behavior**:
- Bypasses rate limiting (explicit user request)
- Detects installation method
- Shows method-specific upgrade command
- Updates `last_check` timestamp in config

---

## Startup Update Notification

**Description**: Automatic update check on startup (non-blocking).

**Trigger**: Every startup, rate-limited to once per 24 hours.

**Output Format** (to stderr):
```
pgtail 0.2.0 available (current: 0.1.0). Upgrade: brew upgrade pgtail
```

**Characteristics**:
- Single line to stderr (not stdout)
- Non-blocking (runs in background thread)
- Rate-limited (skip if < 24 hours since last check)
- Respects `updates.check = false` config setting
- Respects NO_COLOR environment variable
- Silent on failure

**Output Timing**:
- Notification appears before REPL prompt
- Does not delay REPL availability

---

## Upgrade Commands by Installation Method

| Method | Upgrade Command |
|--------|-----------------|
| pip | `pip install --upgrade git+https://github.com/willibrandon/pgtail.git` |
| pipx | `pipx upgrade pgtail` |
| uv | `uv pip install --upgrade git+https://github.com/willibrandon/pgtail.git` |
| Homebrew | `brew upgrade pgtail` |
| winget | `winget upgrade willibrandon.pgtail` |
| Binary | `https://github.com/willibrandon/pgtail/releases/latest` |

---

## Color Styling

### Update Available Notification

When colors are enabled:
- Version numbers: bold
- "available": green
- Upgrade command: cyan

When NO_COLOR is set:
- Plain text, no ANSI codes

---

## Configuration Interaction

### Disable Startup Check

```toml
[updates]
check = false
```

When `check = false`:
- Startup notification skipped
- `--check-update` still works (explicit user action)

### Config Commands

No new config commands needed. Existing `set` command works:

```
pgtail> set updates.check false
updates.check = false

pgtail> set updates.check true
updates.check = true
```

---

## Integration with Existing CLI

### Flag Priority

1. `--version` / `-V` → Print version, exit
2. `--check-update` → Check updates, exit
3. `--help` / `-h` → Print help, exit
4. Normal operation → Enter REPL or tail mode

### Help Text Addition

```
pgtail - PostgreSQL log tailer

Usage: pgtail [OPTIONS] [COMMAND]

Options:
  -h, --help          Show this help message and exit
  -V, --version       Show version and exit
  --check-update      Check for available updates
  ...
```

---

## Exit Codes Summary

| Scenario | Exit Code |
|----------|-----------|
| `--version` | 0 |
| `--check-update` (success) | 0 |
| `--check-update` (network error) | 1 |
| Normal REPL exit | 0 |
| REPL error | 1 |

---

## Testing Scenarios

### Version Flag

```bash
# Test: Version output format
$ pgtail --version
pgtail 0.1.0

# Test: Short flag
$ pgtail -V
pgtail 0.1.0

# Test: Exit code
$ pgtail --version; echo $?
pgtail 0.1.0
0
```

### Check Update

```bash
# Test: Up to date (mock API returns current version)
$ pgtail --check-update
pgtail 0.1.0 (up to date)

# Test: Update available (mock API returns newer version)
$ pgtail --check-update
pgtail 0.1.0 → 0.2.0 available
Upgrade: brew upgrade pgtail

# Test: Network error (mock timeout)
$ pgtail --check-update
Unable to check for updates. Check your internet connection.
$ echo $?
1
```

### Startup Notification

```bash
# Test: Notification appears (mock API returns newer version)
$ pgtail
pgtail 0.2.0 available (current: 0.1.0). Upgrade: brew upgrade pgtail
pgtail>

# Test: Rate limiting (second run within 24h shows no notification)
$ pgtail
pgtail>

# Test: Disabled (config updates.check = false)
$ pgtail --config-set updates.check false
$ pgtail
pgtail>
```

---

## Backwards Compatibility

### New Flags
- `--version` / `-V`: New (standard convention)
- `--check-update`: New

### Existing Behavior
- All existing flags unchanged
- REPL commands unchanged
- Config file format backwards compatible (new keys ignored by older versions)
