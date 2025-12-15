package tailer

import (
	"regexp"
	"strconv"
	"strings"
)

// LogEntry represents a parsed PostgreSQL log line.
type LogEntry struct {
	// Timestamp is the original timestamp string from the log.
	Timestamp string

	// PID is the PostgreSQL backend process ID.
	PID int

	// Level is the parsed log level.
	Level LogLevel

	// Message is the log message content.
	Message string

	// Raw is the original unparsed line.
	Raw string

	// IsContinuation indicates this is a continuation of a previous log entry.
	IsContinuation bool
}

// Common PostgreSQL log line pattern.
// Matches: "2024-01-15 10:23:45.123 PST [12345] LOG: message"
// Also matches: "2024-01-15 10:23:45.123 PST [12345] ERROR: message"
var logPattern = regexp.MustCompile(
	`^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+\w+)\s+` + // timestamp with timezone
		`\[(\d+)\]\s+` + // PID in brackets
		`(\w+):\s*` + // level followed by colon
		`(.*)$`, // message
)

// Alternative pattern for simpler log formats without timezone.
// Matches: "2024-01-15 10:23:45 [12345] LOG: message"
var simpleLogPattern = regexp.MustCompile(
	`^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+` + // timestamp
		`\[(\d+)\]\s+` + // PID in brackets
		`(\w+):\s*` + // level followed by colon
		`(.*)$`, // message
)

// Pattern for log formats without PID (common on Windows).
// Matches: "2024-01-15 10:23:45 PST LOG: message"
var noPidPattern = regexp.MustCompile(
	`^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+\w+)\s+` + // timestamp with timezone
		`(\w+):\s*` + // level followed by colon (no PID)
		`(.*)$`, // message
)

// ParseLogLine parses a PostgreSQL log line into a LogEntry.
// If the line cannot be parsed, it returns an entry with only Raw populated
// and Level set to LevelLog.
func ParseLogLine(line string) LogEntry {
	entry := LogEntry{
		Raw:   line,
		Level: LevelLog,
	}

	// Check for continuation line (starts with whitespace or tab).
	if len(line) > 0 && (line[0] == ' ' || line[0] == '\t') {
		entry.IsContinuation = true
		entry.Message = strings.TrimSpace(line)
		return entry
	}

	// Try primary pattern first (with PID).
	matches := logPattern.FindStringSubmatch(line)
	if matches == nil {
		// Try simpler pattern (with PID, no timezone).
		matches = simpleLogPattern.FindStringSubmatch(line)
	}

	if matches != nil {
		entry.Timestamp = matches[1]
		if pid, err := strconv.Atoi(matches[2]); err == nil {
			entry.PID = pid
		}
		if level, ok := ParseLogLevel(matches[3]); ok {
			entry.Level = level
		}
		entry.Message = matches[4]
		return entry
	}

	// Try pattern without PID (common on Windows).
	matches = noPidPattern.FindStringSubmatch(line)
	if matches != nil {
		entry.Timestamp = matches[1]
		if level, ok := ParseLogLevel(matches[2]); ok {
			entry.Level = level
		}
		entry.Message = matches[3]
		return entry
	}

	// Unparseable line; return as-is with default level.
	entry.Message = line
	return entry
}
