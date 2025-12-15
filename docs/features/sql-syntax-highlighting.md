# Feature: SQL Syntax Highlighting

## Problem

PostgreSQL logs contain SQL statements that are often long and complex. Reading raw SQL in monochrome makes it hard to:
- Quickly identify query structure (SELECT, JOIN, WHERE)
- Spot table and column names
- Find string literals and parameters
- Distinguish SQL from surrounding log context

## Proposed Solution

Apply syntax highlighting to SQL statements detected in log messages. Keywords, identifiers, strings, numbers, and operators each get distinct colors. The highlighting should work both in streaming mode and full-screen TUI.

## User Scenarios

### Scenario 1: Scanning for Query Types
Developer is looking for INSERT statements among many SELECTs. With highlighting, INSERT keyword stands out in a different color, making visual scanning fast.

### Scenario 2: Finding Table References
DBA wants to see all queries touching the "users" table. Table names highlighted in a distinct color (e.g., cyan) make them easy to spot while scrolling.

### Scenario 3: Identifying Parameters
Developer debugging parameterized queries can quickly see where string literals appear (quoted, highlighted) versus column references.

## Highlighting Rules

| Element | Example | Color |
|---------|---------|-------|
| Keywords | SELECT, FROM, WHERE, JOIN | Blue/Bold |
| Tables/Columns | users, created_at | Cyan |
| String literals | 'hello world' | Green |
| Numbers | 42, 3.14 | Magenta |
| Operators | =, <>, AND, OR | Yellow |
| Comments | -- comment | Gray |
| Functions | COUNT(), NOW() | Blue |

## Detection

SQL should be detected in:
- `LOG: statement:` lines
- `LOG: execute <name>:` lines
- `DETAIL:` lines containing queries
- `ERROR:` messages with query context

## Success Criteria

1. Common SQL keywords highlighted correctly (SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, etc.)
2. Quoted identifiers ("table") and string literals ('value') distinguished
3. Nested queries and CTEs highlighted correctly
4. Highlighting doesn't break on malformed/partial SQL
5. Performance: no visible lag on high-volume output
6. Works with NO_COLOR=1 disabled

## Out of Scope

- PL/pgSQL procedure highlighting
- Query formatting/pretty-printing
- Semantic analysis (table existence, etc.)
