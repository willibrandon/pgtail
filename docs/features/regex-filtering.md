# Feature: Regex Pattern Filtering

## Problem

The current level-based filtering (ERROR, WARNING, etc.) is useful but limited. Developers often need to filter by:
- Specific table names
- Connection sources (IP addresses, application names)
- Query patterns
- Error codes
- Custom application identifiers

## Proposed Solution

Add regex-based filtering that works alongside level filtering. Users can include or exclude lines matching patterns. Multiple patterns can be combined with AND/OR logic.

## User Scenarios

### Scenario 1: Filter by Table
Developer debugging an issue with the "orders" table:
```
pgtail> filter /orders/
Showing only lines matching: orders
```

### Scenario 2: Exclude Noise
DBA wants to see errors but exclude routine connection messages:
```
pgtail> levels ERROR
pgtail> filter -/connection authorized/
Excluding lines matching: connection authorized
```

### Scenario 3: Complex Pattern
Developer looking for slow queries on specific tables:
```
pgtail> filter /duration: [0-9]{4,}.*users|products/
Showing lines with 4+ digit duration on users or products tables
```

### Scenario 4: Highlight Without Filter
Developer wants to see all logs but highlight a pattern:
```
pgtail> highlight /SELECT.*FROM users/
Highlighting matches (still showing all lines)
```

## Commands

```
filter /pattern/       Include only matching lines
filter -/pattern/      Exclude matching lines
filter +/pattern/      Add additional include pattern (OR)
filter &/pattern/      Add required pattern (AND)
filter clear           Remove all filters
filter                 Show current filters

highlight /pattern/    Highlight without filtering
highlight clear        Remove highlights
```

## Success Criteria

1. Standard regex syntax (Python `re` module)
2. Case-insensitive by default, `/pattern/i` for sensitive
3. Multiple filters combine logically (documented behavior)
4. Filter applies to full raw line (timestamp, PID, level, message)
5. Filters persist during session
6. Performance: regex compiled once, matching doesn't slow output
7. Invalid regex shows helpful error message

## Out of Scope

- Saved/named filter presets
- Filter history
- Regex builder/helper
- Structural queries (e.g., "PID = 1234")
