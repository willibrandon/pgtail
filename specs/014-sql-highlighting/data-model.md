# Data Model: SQL Syntax Highlighting

**Feature**: 014-sql-highlighting
**Date**: 2025-12-17

## Entities

This feature introduces internal data structures for SQL tokenization and highlighting. No persistent storage or user-facing data models are involved.

---

## 1. SQLTokenType (Enum)

**Purpose**: Categorizes tokens parsed from SQL text.

| Value | Description | Style Class |
|-------|-------------|-------------|
| `KEYWORD` | SQL reserved words (SELECT, FROM, WHERE, etc.) | `sql_keyword` |
| `IDENTIFIER` | Table/column names (unquoted) | `sql_identifier` |
| `QUOTED_IDENTIFIER` | Double-quoted identifiers ("MyTable") | `sql_identifier` |
| `STRING` | String literals ('value', $$value$$) | `sql_string` |
| `NUMBER` | Numeric literals (42, 3.14) | `sql_number` |
| `OPERATOR` | Operators (=, <>, ||, ::, etc.) | `sql_operator` |
| `COMMENT` | Comments (-- line, /* block */) | `sql_comment` |
| `FUNCTION` | Function names followed by ( | `sql_function` |
| `PUNCTUATION` | Parentheses, commas, semicolons | (no special style) |
| `WHITESPACE` | Spaces, tabs, newlines | (preserved as-is) |
| `UNKNOWN` | Unrecognized tokens | (no special style) |

---

## 2. SQLToken (Dataclass)

**Purpose**: Represents a single parsed token with type, text, and position.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | `SQLTokenType` | Token category |
| `text` | `str` | The actual token text |
| `start` | `int` | Start position in source string |
| `end` | `int` | End position in source string (exclusive) |

### Validation Rules
- `start >= 0`
- `end > start`
- `text == source[start:end]` (consistency check)

### Example
```python
# For SQL: "SELECT id FROM users"
tokens = [
    SQLToken(type=SQLTokenType.KEYWORD, text="SELECT", start=0, end=6),
    SQLToken(type=SQLTokenType.WHITESPACE, text=" ", start=6, end=7),
    SQLToken(type=SQLTokenType.IDENTIFIER, text="id", start=7, end=9),
    SQLToken(type=SQLTokenType.WHITESPACE, text=" ", start=9, end=10),
    SQLToken(type=SQLTokenType.KEYWORD, text="FROM", start=10, end=14),
    SQLToken(type=SQLTokenType.WHITESPACE, text=" ", start=14, end=15),
    SQLToken(type=SQLTokenType.IDENTIFIER, text="users", start=15, end=20),
]
```

---

## 3. SQLTokenizer (Class)

**Purpose**: Tokenizes SQL text into a sequence of SQLToken objects.

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `tokenize` | `(sql: str) -> list[SQLToken]` | Parse SQL string into tokens |

### State
- Stateless class (can be reused or instantiated per-call)
- Compiled regex patterns stored as class attributes

### Algorithm
1. Initialize position to 0
2. While position < len(sql):
   a. Try each pattern in priority order
   b. On match, create SQLToken, advance position by match length
   c. On no match, consume single char as UNKNOWN, advance by 1
3. Return token list

---

## 4. SQLHighlighter (Class)

**Purpose**: Converts tokenized SQL into styled FormattedText.

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `highlight` | `(sql: str) -> FormattedText` | Tokenize and style SQL |
| `highlight_tokens` | `(tokens: list[SQLToken]) -> FormattedText` | Style pre-tokenized SQL |

### Dependencies
- `ThemeManager` - for current theme's SQL color definitions
- `SQLTokenizer` - for tokenization

### Style Mapping
```python
TOKEN_TO_STYLE = {
    SQLTokenType.KEYWORD: "class:sql_keyword",
    SQLTokenType.IDENTIFIER: "class:sql_identifier",
    SQLTokenType.QUOTED_IDENTIFIER: "class:sql_identifier",
    SQLTokenType.STRING: "class:sql_string",
    SQLTokenType.NUMBER: "class:sql_number",
    SQLTokenType.OPERATOR: "class:sql_operator",
    SQLTokenType.COMMENT: "class:sql_comment",
    SQLTokenType.FUNCTION: "class:sql_function",
    SQLTokenType.PUNCTUATION: "",  # No special styling
    SQLTokenType.WHITESPACE: "",   # Preserved as-is
    SQLTokenType.UNKNOWN: "",      # No special styling
}
```

---

## 5. Theme SQL Colors (Extension)

**Purpose**: Extend existing Theme.ui dict with SQL color definitions.

### New UI Style Keys

| Key | Default (dark theme) | Description |
|-----|---------------------|-------------|
| `sql_keyword` | `fg:blue bold` | SQL keywords |
| `sql_identifier` | `fg:cyan` | Table/column names |
| `sql_string` | `fg:green` | String literals |
| `sql_number` | `fg:magenta` | Numeric literals |
| `sql_operator` | `fg:yellow` | Operators |
| `sql_comment` | `fg:gray` | Comments |
| `sql_function` | `fg:blue` | Function names |

### Validation
- These keys are optional (graceful degradation to default text)
- When present, must pass ColorStyle validation

---

## 6. SQLDetectionResult (NamedTuple)

**Purpose**: Represents detected SQL content within a log message.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `prefix` | `str` | Text before SQL (e.g., "LOG: statement: ") |
| `sql` | `str` | The SQL content to highlight |
| `suffix` | `str` | Text after SQL (often empty) |

### Example
```python
# For message: "LOG: statement: SELECT * FROM users"
result = SQLDetectionResult(
    prefix="LOG: statement: ",
    sql="SELECT * FROM users",
    suffix=""
)
```

---

## Relationships

```
LogEntry.message
    │
    ▼
SQLDetectionResult (if SQL detected)
    │
    ▼
SQLTokenizer.tokenize(sql)
    │
    ▼
list[SQLToken]
    │
    ▼
SQLHighlighter.highlight_tokens()
    │
    ▼
FormattedText (styled output)
    │
    ▼
prompt_toolkit rendering
```

---

## State Transitions

This feature has no state transitions - it's a pure transformation pipeline from log message text to styled output.

---

## Data Volume Assumptions

- **Token count**: Typical SQL statement produces 20-100 tokens
- **Max SQL length**: Support up to 10,000 characters per statement (per SC-004)
- **Memory**: Tokens are transient; no accumulation beyond single render cycle
- **No persistence**: All data structures are ephemeral per log line
