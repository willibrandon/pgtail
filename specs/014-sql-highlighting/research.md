# Research: SQL Syntax Highlighting

**Feature**: 014-sql-highlighting
**Date**: 2025-12-17

## Research Summary

All technical unknowns have been resolved through codebase exploration. This document captures design decisions, best practices, and rationale.

---

## 1. SQL Tokenization Approach

### Decision: Regex-based tokenizer with ordered token matching

### Rationale
- Regex-based tokenization is simple, performant, and sufficient for SQL highlighting (not semantic parsing)
- Ordered matching (comments first, then strings, then keywords, etc.) prevents false matches inside literals
- No external dependencies needed - Python `re` module provides adequate performance

### Alternatives Considered
1. **Full SQL parser (sqlparse library)**: Rejected - adds dependency, overkill for highlighting, slower
2. **Character-by-character state machine**: Rejected - more complex, similar performance
3. **Pygments lexer**: Rejected - adds dependency, harder to customize for PostgreSQL-specific tokens

### Token Matching Order
1. Multi-line comments (`/* ... */`) - must match before operators containing `*`
2. Single-line comments (`-- ...`) - must match before operators containing `-`
3. Dollar-quoted strings (`$$...$$`, `$tag$...$tag$`) - PostgreSQL-specific
4. Single-quoted strings (`'...'`) - escape handling for `''`
5. Double-quoted identifiers (`"..."`) - must match before operators
6. Numbers (integers and decimals)
7. Keywords (case-insensitive, word boundaries)
8. Function names (identifier followed by `(`)
9. Operators (multi-char first: `<>`, `!=`, `<=`, `>=`, `||`, `::`, then single-char)
10. Identifiers (remaining word patterns)

---

## 2. PostgreSQL SQL Keyword List

### Decision: Comprehensive keyword list covering DDL, DML, and common clauses

### Keyword Set (45+ keywords from spec FR-002)
```
SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP,
FROM, WHERE, JOIN, LEFT, RIGHT, INNER, OUTER, ON,
AND, OR, NOT, IN, EXISTS, BETWEEN, LIKE, IS, NULL,
AS, ORDER, BY, GROUP, HAVING, LIMIT, OFFSET,
UNION, INTERSECT, EXCEPT, WITH, VALUES, SET, INTO,
DISTINCT, ALL, ANY, CASE, WHEN, THEN, ELSE, END,
CAST, COALESCE, NULLIF, TABLE, INDEX, VIEW, TRIGGER,
FUNCTION, PROCEDURE, RETURNS, BEGIN, COMMIT, ROLLBACK,
GRANT, REVOKE, PRIMARY, KEY, FOREIGN, REFERENCES,
CONSTRAINT, DEFAULT, CHECK, UNIQUE, ASC, DESC, NULLS,
FIRST, LAST, OVER, PARTITION, WINDOW, RECURSIVE,
LATERAL, CROSS, FULL, NATURAL, USING, TRUE, FALSE
```

### Rationale
- Covers DML (SELECT, INSERT, UPDATE, DELETE)
- Covers DDL (CREATE, ALTER, DROP, TABLE, INDEX, etc.)
- Covers common clauses (WHERE, JOIN, ORDER BY, GROUP BY, etc.)
- Covers PostgreSQL-specific syntax (LATERAL, RECURSIVE, etc.)
- Excludes PL/pgSQL block keywords (out of scope per spec)

---

## 3. Theme Integration

### Decision: Add new `sql` section to Theme with 7 color style keys

### New Theme Keys (under `ui` section)
```python
ui = {
    # Existing keys...
    "sql_keyword": ColorStyle(fg="blue", bold=True),
    "sql_identifier": ColorStyle(fg="cyan"),
    "sql_string": ColorStyle(fg="green"),
    "sql_number": ColorStyle(fg="magenta"),
    "sql_operator": ColorStyle(fg="yellow"),
    "sql_comment": ColorStyle(fg="gray"),
    "sql_function": ColorStyle(fg="blue"),
}
```

### Rationale
- Matches color scheme from spec's highlighting rules table
- Uses `ui` section (not a new top-level section) for consistency
- Theme validation will require these keys for themes to support SQL highlighting
- Graceful fallback: if keys missing, use default text color

### Built-in Theme Updates Required
All 6 themes need SQL color definitions with appropriate contrast for their palette:
- dark: Blue keywords, cyan identifiers, green strings
- light: Dark blue keywords, teal identifiers, dark green strings
- high-contrast: Bold colors with high saturation
- monokai: Matches Monokai scheme (pink/orange/yellow/green)
- solarized-dark: Matches Solarized Dark palette
- solarized-light: Matches Solarized Light palette

---

## 4. SQL Detection in Log Messages

### Decision: Detect SQL based on PostgreSQL log message prefixes

### Detection Patterns
1. `LOG: statement:` - Direct SQL statement logging (requires `log_statement`)
2. `LOG: execute <name>:` - Prepared statement execution
3. `LOG: duration:` lines containing `ms statement:` - Query timing with SQL
4. `DETAIL:` - Often contains query fragments in error context
5. `ERROR:` - May contain SQL in the error message itself

### Detection Algorithm
```python
def detect_sql_content(entry: LogEntry) -> tuple[str, str, str] | None:
    """Detect SQL content in log message.

    Returns:
        Tuple of (prefix, sql, suffix) if SQL found, None otherwise.
        prefix: Text before SQL (e.g., "LOG: statement: ")
        sql: The SQL content to highlight
        suffix: Text after SQL (usually empty)
    """
```

### Rationale
- Detection is based on PostgreSQL's log message structure, not heuristics
- Avoids false positives from random text that looks like SQL
- Works with all three log formats (TEXT, CSV, JSON)

---

## 5. Performance Optimization

### Decision: Compile regex patterns once at module load, lazy initialization

### Optimizations
1. **Compile patterns at module level**: Regex patterns compiled once, reused
2. **Single-pass tokenization**: One pass through the string, no backtracking
3. **Short-circuit on NO_COLOR**: Skip highlighting entirely when colors disabled
4. **Lazy tokenizer initialization**: Don't create tokenizer until first SQL line detected
5. **Bounded complexity**: O(n) where n is string length; no nested parsing

### Performance Target
- 10,000-character SQL in <100ms
- Expected actual: <10ms based on similar regex tokenizers

---

## 6. FormattedText Integration

### Decision: Return FormattedText with class-based styles for prompt_toolkit

### Integration Pattern
```python
def format_sql(sql: str, theme_manager: ThemeManager) -> FormattedText:
    """Tokenize and format SQL with theme colors.

    Returns:
        FormattedText with (style_class, text) tuples.
    """
    tokens = tokenize_sql(sql)
    parts = []
    for token in tokens:
        style_class = f"class:sql_{token.type.value}"
        parts.append((style_class, token.text))
    return FormattedText(parts)
```

### Rationale
- Uses same FormattedText pattern as existing display.py
- Style classes map to theme colors via ThemeManager.generate_style()
- Consistent with how log levels are styled (e.g., `class:error`, `class:warning`)

---

## 7. Fullscreen TUI Compatibility

### Decision: Use same highlighting code path for both streaming and fullscreen

### Implementation
- Fullscreen buffer stores FormattedText directly (already does this)
- No special handling needed - FormattedText renders identically in both modes
- Search highlighting in fullscreen layered on top (existing behavior preserved)

---

## 8. Graceful Degradation

### Decision: Highlight what's recognizable, leave rest as plain text

### Behavior
- Malformed SQL: Recognized tokens highlighted, unrecognized portions plain text
- Missing theme keys: Fall back to default text color
- Performance issue: If tokenization takes >100ms (unlikely), skip highlighting
- NO_COLOR=1: All SQL highlighting disabled, raw text displayed

### Rationale
- Never crash or error on unexpected input
- User always sees the log message, just with less highlighting if needed
- Constitution Principle III: Graceful Degradation

---

## Summary: No Unresolved Items

All technical decisions documented. No NEEDS CLARIFICATION items remain. Ready for Phase 1.
