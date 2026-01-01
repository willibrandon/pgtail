Plan: Address All Code Review Issues

 Source Reviews:
 - CODE_REVIEW.md (Claude) - 17 issues + 8 test coverage gaps
 - codex-review.md (Codex) - 4 findings (2 unique)
 - gemini-review.md (Gemini) - 2 suggestions

 Total Unique Issues: 21

 ---
 Issue Consolidation

 Overlapping Issues (deduplicated)

 - Claude #1 = Codex #2: Timezone handling in time_filter.py
 - Claude #2 = Codex #3: Unbounded buffer in LogTailer

 Unique Issues by Source

 - Claude: 17 issues
 - Codex: 2 unique (export/pipe broken, flaky performance tests)
 - Gemini: 2 suggestions (docs site, CLI parsing library)

 ---
 Implementation Plan

 Phase 1: P0 Critical Bugs (4 issues)

 1.1 Fix timezone handling in time_filter.py

 Files: pgtail_py/time_filter.py, pgtail_py/parser.py, pgtail_py/parser_csv.py,
 pgtail_py/parser_json.py
 Tasks:
 - Make all datetime parsing timezone-aware using UTC
 - Update parse_time() to use datetime.now(timezone.utc)
 - Update CSV/JSON parsers to preserve timezone info or normalize to UTC
 - Handle ISO-8601 offset formats (+00:00, Z)
 - Add tests for timezone-aware comparisons

 1.2 Add buffer size limits to LogTailer

 Files: pgtail_py/tailer.py, pgtail_py/config.py
 Tasks:
 - Replace _buffer: list[str] with collections.deque(maxlen=N)
 - Add buffer.max_size config option
 - Default to 10000 entries
 - Add test for buffer overflow behavior

 1.3 Fix DurationStats percentile crash

 Files: pgtail_py/slow_query.py
 Tasks:
 - Check sample count before calling statistics.quantiles()
 - Use statistics.median() for p50 when samples < 100
 - Handle edge cases: 0, 1, 2 samples
 - Add tests for boundary sample counts (1, 2, 50, 99, 100)

 1.4 Fix export/pipe commands in Textual mode (Codex)

 Files: pgtail_py/cli_core.py, pgtail_py/cli_export.py, pgtail_py/tail_textual.py
 Tasks:
 - Expose TailApp's LogTailer through state after tail mode exits
 - Or persist recent entries to shared location
 - Ensure export/pipe commands work after Textual tail mode
 - Add integration test for export after tail

 ---
 Phase 2: P1 High Severity Bugs (5 issues)

 2.1 Fix event handler type annotations

 Files: pgtail_py/cli.py
 Tasks:
 - Import KeyPressEvent from prompt_toolkit
 - Replace event: object with proper type
 - Remove # type: ignore comments
 - Verify mypy passes

 2.2 Fix magic number in visual mode

 Files: pgtail_py/tail_log.py
 Tasks:
 - Replace 10000 with sys.maxsize or calculate actual line length
 - Add constant END_OF_LINE = sys.maxsize
 - Test with lines > 10000 chars

 2.3 Add Rich markup error handling

 Files: pgtail_py/tail_log.py
 Tasks:
 - Import MarkupError from rich.errors
 - Wrap Text.from_markup() in try/except
 - Fall back to plain Text() on parse failure
 - Add test with malformed markup

 2.4 Fix deprecated asyncio API

 Files: pgtail_py/tail_textual.py
 Tasks:
 - Replace asyncio.get_event_loop() with asyncio.get_running_loop()
 - Verify no deprecation warnings in Python 3.10+
 - Add test to verify no warnings

 2.5 Fix silent exception swallowing

 Files: pgtail_py/tail_textual.py
 Tasks:
 - Replace bare except Exception: pass with logging
 - Import logging module
 - Log exception with traceback at debug level
 - Consider handling specific exception types

 ---
 Phase 3: P2 Medium Severity Issues (5 issues)

 3.1 Complete SQL keyword list

 Files: pgtail_py/sql_tokenizer.py
 Tasks:
 - Add missing DDL keywords: EXPLAIN, ANALYZE, VACUUM, REINDEX, CLUSTER, TRUNCATE
 - Add utility keywords: LOCK, COPY, LISTEN, NOTIFY, UNLISTEN
 - Add object types: MATERIALIZED, SCHEMA, EXTENSION, TYPE, DOMAIN, SEQUENCE
 - Add cursor keywords: CURSOR, DECLARE, FETCH, CLOSE
 - Add prepared statement keywords: PREPARE, EXECUTE, DEALLOCATE
 - Add session keywords: DISCARD, RESET, SET, SHOW, REFRESH
 - Add tests for new keywords

 3.2 Fix CSV parser timezone stripping

 Files: pgtail_py/parser_csv.py, pgtail_py/parser_json.py
 Tasks:
 - Use regex to detect timezone formats
 - Handle ISO 8601 offsets: +00:00, -05:00, Z
 - Handle named timezones: America/New_York
 - Handle short codes: PST, EST, UTC
 - Add tests for all timezone formats

 3.3 Add TOML theme path validation

 Files: pgtail_py/theme.py
 Tasks:
 - Use theme_file.resolve() to get absolute path
 - Verify resolved path is within themes_dir
 - Skip files that resolve outside themes_dir
 - Add test for symlink attack prevention

 3.4 Cache percentile calculations

 Files: pgtail_py/slow_query.py
 Tasks:
 - Add _cached_quantiles: list[float] | None field
 - Invalidate cache in add() method
 - Calculate quantiles once per access cycle
 - Add test for cache invalidation

 3.5 Improve notification subprocess handling

 Files: pgtail_py/notifier_unix.py
 Tasks:
 - Check subprocess return code
 - Log failures at debug level
 - Handle large output edge case
 - Add test for notification failure logging

 ---
 Phase 4: P3 Low Severity Issues (4 issues)

 4.1 Fix AppleScript string escaping

 Files: pgtail_py/notifier_unix.py
 Tasks:
 - Escape backslashes before double quotes
 - title.replace('\\', '\\\\').replace('"', '\\"')
 - Add test with backslash-containing strings

 4.2 Add host field to field_filter

 Files: pgtail_py/field_filter.py
 Tasks:
 - Add "host": "connection_from" to FIELD_ALIASES
 - Add "connection_from": "connection_from" to FIELD_ATTRIBUTES
 - Add test for host filtering

 4.3 Consolidate NO_COLOR checks

 Files: pgtail_py/colors.py, pgtail_py/sql_highlighter.py, new pgtail_py/utils.py
 Tasks:
 - Create pgtail_py/utils.py with is_color_disabled() function
 - Import from utils in colors.py and sql_highlighter.py
 - Remove duplicate implementations
 - Add test for NO_COLOR behavior

 4.4 Make buffer limits configurable

 Files: pgtail_py/config.py, pgtail_py/error_stats.py, pgtail_py/connection_stats.py,
 pgtail_py/tail_log.py
 Tasks:
 - Add buffer.error_stats_max, buffer.connection_stats_max, buffer.tail_log_max config
 options
 - Default all to 10000
 - Pass config values to respective classes
 - Add tests for custom buffer sizes

 ---
 Phase 5: Test Coverage Gaps (8 modules)

 5.1 tailer.py tests

 - Add test for file rotation mid-tail
 - Add test for truncated file handling
 - Add test for PostgreSQL restart during tail

 5.2 time_filter.py tests

 - Add tests for timezone-aware entry comparison
 - Add tests for all ISO-8601 variants
 - Add tests for relative time with timezone

 5.3 tail_textual.py tests

 - Add async consumer error path tests
 - Add tests for exception handling in entry consumption
 - Add tests for graceful degradation

 5.4 cli.py tests

 - Add tests for command history persistence
 - Add tests for history file creation
 - Add tests for history file corruption recovery

 5.5 notifier_unix.py tests

 - Add tests for AppleScript special character escaping
 - Add tests for notify-send special characters
 - Add platform-specific test markers

 5.6 parser_csv.py tests

 - Add tests for ISO 8601 timezone offsets
 - Add tests for named timezones
 - Add tests for various PostgreSQL timestamp formats

 5.7 config.py tests

 - Add tests for config file corruption recovery
 - Add tests for partial config files
 - Add tests for invalid TOML syntax

 5.8 slow_query.py tests

 - Add tests for percentile with 1 sample
 - Add tests for percentile with 2 samples
 - Add tests for percentile with 99 samples
 - Add tests for percentile with 100+ samples

 ---
 Phase 6: Codex-Specific Issues (1 remaining)

 6.1 Fix flaky performance tests

 Files: tests/test_performance.py
 Tasks:
 - Add pytest marker for performance tests (@pytest.mark.performance)
 - Update Makefile to exclude performance tests by default
 - Add make test-perf target for explicit performance testing
 - Increase timing thresholds by 3x for CI variance
 - Document performance test requirements

 ---
 Phase 7: Gemini Suggestions (2 items)

 7.1 Create documentation site

 Files: New docs/ directory, mkdocs.yml
 Tasks:
 - Set up MkDocs with Material theme
 - Migrate README sections to dedicated pages
 - Create navigation structure
 - Add API reference generation
 - Keep README as concise entry point
 - Add make docs target

 7.2 Improve CLI argument parsing

 Files: pgtail_py/cli_core.py, other cli_*.py files
 Tasks:
 - Evaluate Typer vs Click vs argparse
 - Implement argument parsing with chosen library
 - Auto-generate --help output
 - Maintain backward compatibility with existing commands
 - Add tests for argument parsing edge cases

 ---
 Execution Order

 1. Phase 1 - P0 Critical (blocks everything)
 2. Phase 2 - P1 High (stability)
 3. Phase 5.1-5.8 - Add tests as each phase completes
 4. Phase 3 - P2 Medium (quality)
 5. Phase 4 - P3 Low (polish)
 6. Phase 6 - Codex flaky tests
 7. Phase 7 - Gemini suggestions

 ---
 Files to Modify

 | File                          | Issues        |
 |-------------------------------|---------------|
 | pgtail_py/time_filter.py      | 1.1           |
 | pgtail_py/parser.py           | 1.1           |
 | pgtail_py/parser_csv.py       | 1.1, 3.2      |
 | pgtail_py/parser_json.py      | 1.1, 3.2      |
 | pgtail_py/tailer.py           | 1.2           |
 | pgtail_py/slow_query.py       | 1.3, 3.4      |
 | pgtail_py/cli_core.py         | 1.4, 7.2      |
 | pgtail_py/cli_export.py       | 1.4           |
 | pgtail_py/tail_textual.py     | 1.4, 2.4, 2.5 |
 | pgtail_py/cli.py              | 2.1           |
 | pgtail_py/tail_log.py         | 2.2, 2.3, 4.4 |
 | pgtail_py/sql_tokenizer.py    | 3.1           |
 | pgtail_py/theme.py            | 3.3           |
 | pgtail_py/notifier_unix.py    | 3.5, 4.1      |
 | pgtail_py/field_filter.py     | 4.2           |
 | pgtail_py/colors.py           | 4.3           |
 | pgtail_py/sql_highlighter.py  | 4.3           |
 | pgtail_py/config.py           | 1.2, 4.4      |
 | pgtail_py/error_stats.py      | 4.4           |
 | pgtail_py/connection_stats.py | 4.4           |
 | tests/test_performance.py     | 6.1           |
 | New: pgtail_py/utils.py       | 4.3           |
 | New: docs/                    | 7.1           |
 | New: mkdocs.yml               | 7.1           |

 ---
 Success Criteria

 - All 505 existing tests pass
 - New tests added for each fix
 - No mypy errors
 - No deprecation warnings in Python 3.10+
 - make lint passes
 - All 21 issues resolved