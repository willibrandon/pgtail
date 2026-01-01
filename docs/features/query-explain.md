# Feature: Query EXPLAIN Integration

## Problem

When seeing slow or problematic queries in logs, developers want to understand why:
- What's the query plan?
- Is it using indexes?
- Where is time being spent?

Currently, developers must copy the query, connect to psql, and run EXPLAIN manually.

## Proposed Solution

Add a command to run EXPLAIN on queries seen in the logs. Parse logged queries and execute EXPLAIN (or EXPLAIN ANALYZE) against the connected instance.

## User Scenarios

### Scenario 1: Quick Explain in Tail Mode
Developer sees a slow query in the Textual tail mode log viewer:
```
10:23:45 [12345] LOG: duration: 2345.678 ms  statement: SELECT * FROM orders WHERE...
```
They can immediately get the plan from the tail mode command prompt:
```
tail> explain last
EXPLAIN for query at 10:23:45:

Seq Scan on orders  (cost=0.00..1234.00 rows=50000 width=100)
  Filter: (status = 'pending')

Note: Sequential scan on large table. Consider index on 'status'.
```

### Scenario 2: Explain Specific Query
Developer wants to explain a query they saw earlier:
```
tail> explain "SELECT * FROM users WHERE email = 'foo@bar.com'"
Index Scan using users_email_idx on users  (cost=0.29..8.31 rows=1 width=200)
  Index Cond: (email = 'foo@bar.com'::text)
```

### Scenario 3: Explain Analyze (with execution)
DBA wants actual timing:
```
tail> explain analyze last
⚠️  This will execute the query. Continue? [y/N] y

Index Scan using users_email_idx on users  (cost=0.29..8.31 rows=1 width=200) (actual time=0.023..0.025 rows=1 loops=1)
Planning Time: 0.087 ms
Execution Time: 0.042 ms
```

### Scenario 4: Connect for Explain
pgtail needs database connection:
```
tail> explain last
Not connected. Connect with: connect <instance>

tail> connect 0
Connected to instance 0 (localhost:5432/postgres)

tail> explain last
[Shows plan]
```

## Commands

Available in both REPL and Textual tail mode:

```
connect <id>              Connect to instance for queries
connect <id> -d <dbname>  Connect to specific database
disconnect                Close connection

explain <query>           EXPLAIN a query string
explain last              EXPLAIN the last logged query
explain @N                EXPLAIN query N lines back

explain analyze <query>   EXPLAIN ANALYZE (executes query!)
explain analyze last      EXPLAIN ANALYZE last query

explain format json last  Output plan as JSON
```

## Textual Tail Mode Integration

### UI Considerations

1. **EXPLAIN Output Display**
   - Show EXPLAIN output in the log viewer area with distinct styling
   - Use Rich markup for plan formatting (indentation, cost highlighting)
   - Prefix output with `[EXPLAIN]` to distinguish from log entries

2. **Query Selection**
   - `explain last` uses the most recent query from stored entries
   - `explain @N` selects query N lines back in the log buffer
   - Visual mode selection could enable `explain selection` (future)

3. **Confirmation Dialog**
   - For `EXPLAIN ANALYZE`, show warning in log viewer
   - Accept y/n input via the command prompt
   - Default to N (safe) if Enter pressed

4. **Connection Status**
   - Status bar shows connection state: `Connected: postgres@localhost:5432`
   - Or: `Not connected` when disconnected
   - Connection persists across filter changes

### Implementation Notes

- Commands handled in `cli_tail.py` dispatcher
- New module: `pgtail_py/explain.py` for EXPLAIN execution
- New module: `pgtail_py/db_connection.py` for PostgreSQL connection management
- Query extraction uses existing `sql_detector.py` patterns
- EXPLAIN output formatted with Rich markup for Textual display

## Safety Considerations

- `EXPLAIN` alone is safe (doesn't execute)
- `EXPLAIN ANALYZE` executes the query - requires confirmation
- Never auto-run EXPLAIN ANALYZE on INSERT/UPDATE/DELETE
- Read-only connection option for safety
- Timeout for long-running explains

## Query Extraction

Parse queries from:
- `LOG: statement:` entries
- `LOG: execute <name>:` entries
- `LOG: duration: X ms  statement:` entries

Handle:
- Multi-line queries (continuation lines)
- Parameter placeholders ($1, $2)
- Prepared statement parameters

## Success Criteria

1. Extract queries from standard log formats
2. Connect to PostgreSQL instances detected by pgtail
3. EXPLAIN output formatted readably with Rich markup
4. EXPLAIN ANALYZE requires explicit confirmation
5. Handle multi-line queries correctly
6. Timeout prevents hanging on bad queries
7. Connection credentials handled securely (prompt, env, pgpass)
8. Clear error messages for connection failures
9. Works in both REPL and Textual tail mode
10. Status bar shows connection state

## Out of Scope

- Query rewriting/optimization suggestions
- Plan visualization (graphical)
- Plan comparison between runs
- Index recommendations
- Query execution (beyond EXPLAIN ANALYZE)

---

## Documentation Requirements

When this feature is implemented, the following documentation must be created/updated:

### Public Documentation (mkdocs)

1. **New Guide Page**: `docs/guide/query-explain.md`
   - User-facing guide explaining how to use EXPLAIN integration
   - Examples for both REPL and tail mode
   - Connection setup instructions
   - Safety warnings for EXPLAIN ANALYZE

2. **Update**: `docs/guide/tail-mode.md`
   - Add EXPLAIN commands to tail mode command reference
   - Add connection status to status bar documentation

3. **Update**: `docs/cli-reference.md`
   - Add `connect`, `disconnect`, `explain` commands
   - Document all flags and options

4. **Update**: `mkdocs.yml`
   - Add `Query Explain: guide/query-explain.md` to User Guide nav

### Internal Documentation

5. **Update**: `CLAUDE.md`
   - Add Query EXPLAIN section describing implementation
   - Document new modules (explain.py, db_connection.py)
   - Add commands to command reference

6. **Update**: `README.md`
   - Add EXPLAIN feature to Features list
   - Add example usage in Usage section
