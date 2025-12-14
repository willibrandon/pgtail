// Package tailer provides log file tailing and parsing functionality.
package tailer

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

	// IsContinuation indicates this is a continuation of a previous entry.
	IsContinuation bool
}
