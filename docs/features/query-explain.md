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

### Scenario 1: Quick Explain
Developer sees a slow query in the log:
```
10:23:45 [12345] LOG: duration: 2345.678 ms  statement: SELECT * FROM orders WHERE...
```
They can immediately get the plan:
```
pgtail> explain last
EXPLAIN for query at 10:23:45:

Seq Scan on orders  (cost=0.00..1234.00 rows=50000 width=100)
  Filter: (status = 'pending')

Note: Sequential scan on large table. Consider index on 'status'.
```

### Scenario 2: Explain Specific Query
Developer wants to explain a query they saw earlier:
```
pgtail> explain "SELECT * FROM users WHERE email = 'foo@bar.com'"
Index Scan using users_email_idx on users  (cost=0.29..8.31 rows=1 width=200)
  Index Cond: (email = 'foo@bar.com'::text)
```

### Scenario 3: Explain Analyze (with execution)
DBA wants actual timing:
```
pgtail> explain analyze last
⚠️  This will execute the query. Continue? [y/N] y

Index Scan using users_email_idx on users  (cost=0.29..8.31 rows=1 width=200) (actual time=0.023..0.025 rows=1 loops=1)
Planning Time: 0.087 ms
Execution Time: 0.042 ms
```

### Scenario 4: Connect for Explain
pgtail needs database connection:
```
pgtail> explain last
Not connected. Connect with: connect <instance>

pgtail> connect 0
Connected to instance 0 (localhost:5432/postgres)

pgtail> explain last
[Shows plan]
```

## Commands

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
3. EXPLAIN output formatted readably
4. EXPLAIN ANALYZE requires explicit confirmation
5. Handle multi-line queries correctly
6. Timeout prevents hanging on bad queries
7. Connection credentials handled securely (prompt, env, pgpass)
8. Clear error messages for connection failures

## Out of Scope

- Query rewriting/optimization suggestions
- Plan visualization (graphical)
- Plan comparison between runs
- Index recommendations
- Query execution (beyond EXPLAIN ANALYZE)
