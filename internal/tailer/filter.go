// Package tailer provides log file tailing and filtering functionality.
package tailer

import (
	"strings"
)

// LogLevel represents PostgreSQL log severity levels.
type LogLevel int

const (
	LevelDebug5 LogLevel = iota
	LevelDebug4
	LevelDebug3
	LevelDebug2
	LevelDebug1
	LevelInfo
	LevelNotice
	LevelWarning
	LevelError
	LevelLog
	LevelFatal
	LevelPanic
)

// String returns the display string for a LogLevel.
func (l LogLevel) String() string {
	switch l {
	case LevelDebug5:
		return "DEBUG5"
	case LevelDebug4:
		return "DEBUG4"
	case LevelDebug3:
		return "DEBUG3"
	case LevelDebug2:
		return "DEBUG2"
	case LevelDebug1:
		return "DEBUG1"
	case LevelInfo:
		return "INFO"
	case LevelNotice:
		return "NOTICE"
	case LevelWarning:
		return "WARNING"
	case LevelError:
		return "ERROR"
	case LevelLog:
		return "LOG"
	case LevelFatal:
		return "FATAL"
	case LevelPanic:
		return "PANIC"
	default:
		return "UNKNOWN"
	}
}

// Short returns a short display string for prompt display.
func (l LogLevel) Short() string {
	switch l {
	case LevelDebug5, LevelDebug4, LevelDebug3, LevelDebug2, LevelDebug1:
		return "DBG"
	case LevelInfo:
		return "INFO"
	case LevelNotice:
		return "NTCE"
	case LevelWarning:
		return "WARN"
	case LevelError:
		return "ERR"
	case LevelLog:
		return "LOG"
	case LevelFatal:
		return "FATL"
	case LevelPanic:
		return "PANC"
	default:
		return "UNK"
	}
}

// AllLevels returns all valid log levels.
func AllLevels() []LogLevel {
	return []LogLevel{
		LevelDebug5, LevelDebug4, LevelDebug3, LevelDebug2, LevelDebug1,
		LevelInfo, LevelNotice, LevelWarning, LevelError, LevelLog,
		LevelFatal, LevelPanic,
	}
}

// ParseLevel parses a log level string (case-insensitive).
// Returns the level and true if valid, or LevelLog and false if invalid.
func ParseLevel(s string) (LogLevel, bool) {
	switch strings.ToUpper(strings.TrimSpace(s)) {
	case "DEBUG5":
		return LevelDebug5, true
	case "DEBUG4":
		return LevelDebug4, true
	case "DEBUG3":
		return LevelDebug3, true
	case "DEBUG2":
		return LevelDebug2, true
	case "DEBUG1":
		return LevelDebug1, true
	case "INFO":
		return LevelInfo, true
	case "NOTICE":
		return LevelNotice, true
	case "WARNING":
		return LevelWarning, true
	case "ERROR":
		return LevelError, true
	case "LOG":
		return LevelLog, true
	case "FATAL":
		return LevelFatal, true
	case "PANIC":
		return LevelPanic, true
	default:
		return LevelLog, false
	}
}

// Filter represents a user-configured set of log levels to display.
type Filter struct {
	// Levels maps each level to whether it should be shown.
	// Empty or nil means show all levels.
	Levels map[LogLevel]bool
}

// NewFilter creates a new empty filter (shows all levels).
func NewFilter() *Filter {
	return &Filter{
		Levels: make(map[LogLevel]bool),
	}
}

// Allow returns true if the given level should be displayed.
// An empty filter allows all levels.
func (f *Filter) Allow(level LogLevel) bool {
	if f == nil || len(f.Levels) == 0 {
		return true
	}
	return f.Levels[level]
}

// Set configures the filter to show only the specified levels.
func (f *Filter) Set(levels ...LogLevel) {
	f.Levels = make(map[LogLevel]bool)
	for _, l := range levels {
		f.Levels[l] = true
	}
}

// Clear removes all filtering (show all levels).
func (f *Filter) Clear() {
	f.Levels = make(map[LogLevel]bool)
}

// IsEmpty returns true if no filter is set.
func (f *Filter) IsEmpty() bool {
	return f == nil || len(f.Levels) == 0
}

// String returns a formatted string for prompt display (e.g., "ERR,WARN").
func (f *Filter) String() string {
	if f.IsEmpty() {
		return ""
	}

	var parts []string
	for _, level := range AllLevels() {
		if f.Levels[level] {
			parts = append(parts, level.Short())
		}
	}
	return strings.Join(parts, ",")
}
