# Feature: Webhook Integrations

## Problem

Teams need to route PostgreSQL alerts to their existing monitoring and communication tools:
- Slack/Discord for team notifications
- PagerDuty/OpsGenie for on-call alerting
- Custom endpoints for internal systems
- SIEM systems for security monitoring

Desktop notifications are personal; webhooks enable team-wide awareness.

## Proposed Solution

Support configurable webhook endpoints that receive POST requests when specified conditions are met. Include relevant log context in a structured JSON payload.

## User Scenarios

### Scenario 1: Slack Alert for Fatal Errors
Team wants FATAL errors in their ops channel:
```
pgtail> webhook add slack https://hooks.slack.com/services/XXX
pgtail> webhook slack on FATAL PANIC
Webhook 'slack' will trigger on: FATAL, PANIC
```

### Scenario 2: PagerDuty Integration
On-call rotation for critical issues:
```
pgtail> webhook add pagerduty https://events.pagerduty.com/v2/enqueue \
    --header "Authorization: Token token=XXX"
pgtail> webhook pagerduty on FATAL
pgtail> webhook pagerduty on errors > 50/min
```

### Scenario 3: Custom Monitoring Endpoint
Internal metrics collection:
```
pgtail> webhook add metrics http://metrics.internal/ingest \
    --format prometheus
pgtail> webhook metrics on errors --continuous
```

### Scenario 4: Test Webhook
Verify configuration works:
```
pgtail> webhook test slack
Sending test payload to slack...
✓ Received 200 OK
```

## Commands

```
webhook add <name> <url>              Add webhook endpoint
webhook add <name> <url> --header K=V Add with custom headers
webhook remove <name>                 Remove webhook
webhook list                          Show configured webhooks

webhook <name> on <levels>            Trigger on log levels
webhook <name> on /<pattern>/         Trigger on pattern match
webhook <name> on errors > N/min      Trigger on error rate
webhook <name> off                    Disable webhook

webhook test <name>                   Send test payload
```

## Payload Format

Default JSON payload:
```json
{
  "timestamp": "2024-01-15T10:23:45.123Z",
  "instance": {
    "id": 0,
    "version": "16",
    "data_dir": "/var/lib/postgresql/16/main"
  },
  "event": {
    "type": "log_entry",
    "level": "FATAL",
    "message": "connection limit exceeded for non-superusers",
    "sqlstate": "53300",
    "pid": 12345
  },
  "trigger": {
    "rule": "level:FATAL",
    "webhook": "slack"
  }
}
```

## Platform-Specific Formats

### Slack
```json
{
  "text": "FATAL: connection limit exceeded",
  "attachments": [{
    "color": "danger",
    "fields": [
      {"title": "Instance", "value": "pg16 (localhost)", "short": true},
      {"title": "Time", "value": "10:23:45", "short": true}
    ]
  }]
}
```

### PagerDuty
```json
{
  "routing_key": "...",
  "event_action": "trigger",
  "payload": {
    "summary": "PostgreSQL FATAL: connection limit exceeded",
    "severity": "critical",
    "source": "pgtail"
  }
}
```

## Success Criteria

1. Support arbitrary HTTP endpoints
2. Custom headers for authentication
3. Built-in formatters for Slack, PagerDuty, Discord
4. Rate limiting prevents webhook spam
5. Failed webhooks retry with backoff
6. Test command verifies connectivity
7. Webhook config persists in config file
8. Async sending doesn't block log tailing

## Out of Scope

- OAuth/complex authentication flows
- Bidirectional integrations
- Webhook response processing
- Built-in Slack/Discord bots
