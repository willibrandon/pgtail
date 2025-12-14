// Package tailer provides PostgreSQL log file tailing and parsing functionality.
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

// String returns the PostgreSQL log level name.
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

// Short returns a short display string for the log level.
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
		return "PNKC"
	default:
		return "UNK"
	}
}

// ParseLogLevel parses a string into a LogLevel (case-insensitive).
// Returns LevelLog and false if the string is not recognized.
func ParseLogLevel(s string) (LogLevel, bool) {
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

// AllLogLevels returns all valid log level names for autocomplete.
func AllLogLevels() []string {
	return []string{
		"DEBUG5", "DEBUG4", "DEBUG3", "DEBUG2", "DEBUG1",
		"INFO", "NOTICE", "WARNING", "ERROR", "LOG", "FATAL", "PANIC",
	}
}

// Filter manages a set of log levels to display.
type Filter struct {
	levels map[LogLevel]bool
}

// NewFilter creates a new empty filter (shows all levels).
func NewFilter() *Filter {
	return &Filter{
		levels: make(map[LogLevel]bool),
	}
}

// Allow returns true if the given level should be displayed.
// An empty filter allows all levels.
func (f *Filter) Allow(level LogLevel) bool {
	if f == nil || len(f.levels) == 0 {
		return true
	}
	return f.levels[level]
}

// Set configures the filter to show only the specified levels.
func (f *Filter) Set(levels ...LogLevel) {
	f.levels = make(map[LogLevel]bool)
	for _, l := range levels {
		f.levels[l] = true
	}
}

// Clear removes all filtering (shows all levels).
func (f *Filter) Clear() {
	f.levels = make(map[LogLevel]bool)
}

// IsEmpty returns true if no filter is set (showing all levels).
func (f *Filter) IsEmpty() bool {
	return f == nil || len(f.levels) == 0
}

// String returns a formatted string for prompt display (e.g., "ERR,WARN").
func (f *Filter) String() string {
	if f.IsEmpty() {
		return ""
	}

	var parts []string
	// Order by severity (highest first for display)
	order := []LogLevel{
		LevelPanic, LevelFatal, LevelError, LevelWarning,
		LevelNotice, LevelLog, LevelInfo,
		LevelDebug1, LevelDebug2, LevelDebug3, LevelDebug4, LevelDebug5,
	}
	for _, l := range order {
		if f.levels[l] {
			parts = append(parts, l.Short())
		}
	}

	return strings.Join(parts, ",")
}

// Levels returns the currently filtered levels.
func (f *Filter) Levels() []LogLevel {
	if f.IsEmpty() {
		return nil
	}
	var result []LogLevel
	for l, enabled := range f.levels {
		if enabled {
			result = append(result, l)
		}
	}
	return result
}
