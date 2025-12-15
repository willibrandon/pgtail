# pgtail Feature Ideas

Feature specifications for potential pgtail enhancements. Each document is formatted for use with `/speckit.specify`.

## Usage

To implement a feature:
```
/speckit.specify <paste feature description>
```

Or reference the file directly when planning.

---

## Features by Category

### Full Screen TUI
| Feature | Description | Complexity |
|---------|-------------|------------|
| [full-screen-tui](full-screen-tui.md) | Scrollable buffer with vim navigation | High |
| [split-panes](split-panes.md) | Multiple instances in split view | High |

### Display & Formatting
| Feature | Description | Complexity |
|---------|-------------|------------|
| [sql-syntax-highlighting](sql-syntax-highlighting.md) | Color SQL keywords in logs | Medium |
| [themes](themes.md) | Dark/light/custom color themes | Medium |
| [slow-query-detection](slow-query-detection.md) | Highlight queries by duration | Low |

### Filtering & Search
| Feature | Description | Complexity |
|---------|-------------|------------|
| [regex-filtering](regex-filtering.md) | Filter by regex pattern | Low |
| [time-based-filtering](time-based-filtering.md) | Filter by time range | Medium |

### Log Format Support
| Feature | Description | Complexity |
|---------|-------------|------------|
| [csvlog-jsonlog-support](csvlog-jsonlog-support.md) | Parse CSV and JSON log formats | Medium |

### Dashboards & Stats
| Feature | Description | Complexity |
|---------|-------------|------------|
| [connection-tracking](connection-tracking.md) | Track active connections | Medium |
| [error-stats-dashboard](error-stats-dashboard.md) | Error counts and trends | Medium |

### Alerts & Integrations
| Feature | Description | Complexity |
|---------|-------------|------------|
| [desktop-notifications](desktop-notifications.md) | Native OS notifications | Low |
| [webhooks](webhooks.md) | Slack, PagerDuty, custom webhooks | Medium |

### Export & Output
| Feature | Description | Complexity |
|---------|-------------|------------|
| [export-and-pipe](export-and-pipe.md) | Save logs, pipe to commands | Low |

### Configuration
| Feature | Description | Complexity |
|---------|-------------|------------|
| [config-file](config-file.md) | Persistent settings in TOML | Low |

### PostgreSQL Integration
| Feature | Description | Complexity |
|---------|-------------|------------|
| [query-explain](query-explain.md) | Run EXPLAIN on logged queries | High |

---

## Suggested Implementation Order

### Phase 1: Quick Wins (Low complexity, high value)
1. regex-filtering
2. slow-query-detection
3. config-file
4. export-and-pipe

### Phase 2: Enhanced Filtering
5. time-based-filtering
6. csvlog-jsonlog-support

### Phase 3: Monitoring
7. error-stats-dashboard
8. connection-tracking
9. desktop-notifications

### Phase 4: Full TUI
10. full-screen-tui
11. themes
12. sql-syntax-highlighting

### Phase 5: Advanced
13. split-panes
14. webhooks
15. query-explain
