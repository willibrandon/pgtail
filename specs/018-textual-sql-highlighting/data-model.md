# Data Model: SQL Syntax Highlighting in Textual Tail Mode

**Date**: 2025-12-31
**Feature**: 018-textual-sql-highlighting

## Overview

This feature reuses existing data structures and adds one transformation layer for Rich markup output. No new persistent data models are introduced.

---

## Existing Entities (No Changes)

### SQLTokenType (Enum)

**Location**: `pgtail_py/sql_tokenizer.py:14-31`

Token categories for SQL syntax elements.

| Value | Description | Rich Markup Style |
|-------|-------------|-------------------|
| `KEYWORD` | SQL reserved words | Theme: `sql_keyword` |
| `IDENTIFIER` | Table/column names | Theme: `sql_identifier` |
| `QUOTED_IDENTIFIER` | Double-quoted identifiers | Theme: `sql_identifier` |
| `STRING` | String literals | Theme: `sql_string` |
| `NUMBER` | Numeric literals | Theme: `sql_number` |
| `OPERATOR` | SQL operators | Theme: `sql_operator` |
| `COMMENT` | SQL comments | Theme: `sql_comment` |
| `FUNCTION` | Function names | Theme: `sql_function` |
| `PUNCTUATION` | Parentheses, commas | No styling |
| `WHITESPACE` | Spaces, tabs, newlines | No styling |
| `UNKNOWN` | Unrecognized tokens | No styling |

### SQLToken (Dataclass)

**Location**: `pgtail_py/sql_tokenizer.py:34-55`

Immutable token representing a parsed SQL segment.

```python
@dataclass(frozen=True, slots=True)
class SQLToken:
    type: SQLTokenType   # Token category
    text: str            # Actual token text
    start: int           # Start position in source
    end: int             # End position (exclusive)
```

**Invariants**:
- `start >= 0`
- `end > start`

### SQLDetectionResult (NamedTuple)

**Location**: `pgtail_py/sql_detector.py:12-24`

Result of detecting SQL content in a log message.

```python
class SQLDetectionResult(NamedTuple):
    prefix: str   # Text before SQL (e.g., "LOG: statement: ")
    sql: str      # The SQL content to highlight
    suffix: str   # Text after SQL (often empty)
```

**Usage**:
```python
detection = detect_sql_content("LOG: statement: SELECT * FROM users")
# SQLDetectionResult(
#     prefix="LOG: statement: ",
#     sql="SELECT * FROM users",
#     suffix=""
# )
```

### ColorStyle (Dataclass)

**Location**: `pgtail_py/theme.py:262-340`

Style specification for colors and text modifiers.

```python
@dataclass
class ColorStyle:
    fg: str | None = None        # Foreground color
    bg: str | None = None        # Background color
    bold: bool = False           # Bold modifier
    dim: bool = False            # Dim modifier
    italic: bool = False         # Italic modifier
    underline: bool = False      # Underline modifier

    def to_style_string(self) -> str:
        """Convert to prompt_toolkit style string."""
        # Returns: "fg:red bg:yellow bold"
```

### Theme (Dataclass)

**Location**: `pgtail_py/theme.py:347-437`

Complete theme definition with level and UI styles.

```python
@dataclass
class Theme:
    name: str
    description: str = ""
    levels: dict[str, ColorStyle] = field(default_factory=dict)
    ui: dict[str, ColorStyle] = field(default_factory=dict)

    def get_ui_style(self, element: str) -> ColorStyle:
        """Get style for a UI element (e.g., 'sql_keyword')."""
        return self.ui.get(element, ColorStyle())
```

**SQL Token Keys in `ui` dict**:
- `sql_keyword`
- `sql_identifier`
- `sql_string`
- `sql_number`
- `sql_operator`
- `sql_comment`
- `sql_function`

---

## New Transformations

### Token Type to Theme Key Mapping

Maps SQLTokenType enum values to theme UI keys.

```python
# Location: pgtail_py/sql_highlighter.py (new)

TOKEN_TYPE_TO_THEME_KEY: dict[SQLTokenType, str] = {
    SQLTokenType.KEYWORD: "sql_keyword",
    SQLTokenType.IDENTIFIER: "sql_identifier",
    SQLTokenType.QUOTED_IDENTIFIER: "sql_identifier",
    SQLTokenType.STRING: "sql_string",
    SQLTokenType.NUMBER: "sql_number",
    SQLTokenType.OPERATOR: "sql_operator",
    SQLTokenType.COMMENT: "sql_comment",
    SQLTokenType.FUNCTION: "sql_function",
    # No styling for these types
    SQLTokenType.PUNCTUATION: "",
    SQLTokenType.WHITESPACE: "",
    SQLTokenType.UNKNOWN: "",
}
```

### ColorStyle to Rich Markup Conversion

Converts a ColorStyle to Rich console markup tag content.

```python
def _color_style_to_rich_markup(style: ColorStyle) -> str:
    """Convert ColorStyle to Rich markup tag content.

    Args:
        style: ColorStyle with fg, bg, bold, dim, etc.

    Returns:
        Rich markup tag content, e.g., "bold blue" or "dim".
        Empty string if no styling defined.

    Examples:
        ColorStyle(fg="blue", bold=True) → "bold blue"
        ColorStyle(fg="#268bd2") → "#268bd2"
        ColorStyle(dim=True) → "dim"
        ColorStyle() → ""
    """
```

**Mapping Rules**:

| ColorStyle Field | Rich Markup |
|------------------|-------------|
| `fg="blue"` | `blue` |
| `fg="#268bd2"` | `#268bd2` |
| `fg="ansicyan"` | `cyan` (strip "ansi" prefix) |
| `bg="yellow"` | `on yellow` |
| `bold=True` | `bold` |
| `dim=True` | `dim` |
| `italic=True` | `italic` |
| `underline=True` | `underline` |

**Special Cases**:
- ANSI colors: Strip `ansi` or `ansibright` prefix for Rich compatibility
- Hex colors: Pass through unchanged (`#268bd2`)
- CSS named colors: Pass through unchanged (`darkblue`)

---

## Data Flow Diagram

```
LogEntry.message
       │
       ▼
┌─────────────────────┐
│  detect_sql_content │  (sql_detector.py)
│                     │
│  Returns:           │
│  - prefix           │
│  - sql              │
│  - suffix           │
│  (or None)          │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  SQLTokenizer       │  (sql_tokenizer.py)
│  .tokenize(sql)     │
│                     │
│  Returns:           │
│  list[SQLToken]     │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  highlight_sql_rich │  (sql_highlighter.py - NEW)
│                     │
│  For each token:    │
│  1. Get theme color │
│  2. Escape brackets │
│  3. Wrap in markup  │
│                     │
│  Returns:           │
│  Rich markup string │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ format_entry_compact│  (tail_rich.py - MODIFIED)
│                     │
│  Assembles:         │
│  prefix (escaped) + │
│  highlighted_sql +  │
│  suffix (escaped)   │
│                     │
│  Returns:           │
│  Complete markup    │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  TailLog.write_line │  (tail_log.py)
│                     │
│  Stores markup in   │
│  _lines buffer      │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ _render_line_strip  │  (tail_log.py)
│                     │
│  Text.from_markup() │
│  → Rich Text object │
│  → Rendered Strip   │
└─────────────────────┘
```

---

## Validation Rules

### Input Validation

1. **Empty SQL**: Return empty string (no tokens)
2. **None detection**: Return original message escaped
3. **NO_COLOR set**: Return SQL with escaped brackets only

### Token Validation

1. **Missing theme key**: Return unstyled token text
2. **Invalid color in theme**: Skip styling (graceful degradation)
3. **Malformed SQL**: Tokenizer produces UNKNOWN tokens (displayed unstyled)

### Output Validation

1. **Bracket balance**: Not guaranteed (Rich handles incomplete tags gracefully)
2. **Markup correctness**: All user-controlled text is bracket-escaped

---

## Schema Summary

| Entity | Type | Status | Location |
|--------|------|--------|----------|
| SQLTokenType | Enum | Existing | sql_tokenizer.py |
| SQLToken | Dataclass | Existing | sql_tokenizer.py |
| SQLDetectionResult | NamedTuple | Existing | sql_detector.py |
| ColorStyle | Dataclass | Existing | theme.py |
| Theme | Dataclass | Existing | theme.py |
| TOKEN_TYPE_TO_THEME_KEY | dict | New | sql_highlighter.py |
| highlight_sql_rich() | Function | New | sql_highlighter.py |
| _color_style_to_rich_markup() | Function | New | sql_highlighter.py |
