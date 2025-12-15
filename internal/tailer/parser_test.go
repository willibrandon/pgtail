package tailer

import (
	"testing"
)

func TestParseLogLine_StandardFormat(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		wantTS   string
		wantPID  int
		wantLvl  LogLevel
		wantMsg  string
		wantCont bool
	}{
		{
			name:    "standard LOG entry",
			input:   "2024-01-15 10:23:45.123 PST [12345] LOG: database system is ready to accept connections",
			wantTS:  "2024-01-15 10:23:45.123 PST",
			wantPID: 12345,
			wantLvl: LevelLog,
			wantMsg: "database system is ready to accept connections",
		},
		{
			name:    "ERROR entry",
			input:   "2024-01-15 10:23:45.123 PST [99999] ERROR: relation \"users\" does not exist",
			wantTS:  "2024-01-15 10:23:45.123 PST",
			wantPID: 99999,
			wantLvl: LevelError,
			wantMsg: "relation \"users\" does not exist",
		},
		{
			name:    "WARNING entry",
			input:   "2024-01-15 10:23:45.999 UTC [1] WARNING: connection limit exceeded",
			wantTS:  "2024-01-15 10:23:45.999 UTC",
			wantPID: 1,
			wantLvl: LevelWarning,
			wantMsg: "connection limit exceeded",
		},
		{
			name:    "FATAL entry",
			input:   "2024-01-15 10:23:45.000 EST [42] FATAL: password authentication failed",
			wantTS:  "2024-01-15 10:23:45.000 EST",
			wantPID: 42,
			wantLvl: LevelFatal,
			wantMsg: "password authentication failed",
		},
		{
			name:    "INFO entry",
			input:   "2024-01-15 10:23:45.500 PST [123] INFO: autovacuum launcher started",
			wantTS:  "2024-01-15 10:23:45.500 PST",
			wantPID: 123,
			wantLvl: LevelInfo,
			wantMsg: "autovacuum launcher started",
		},
		{
			name:    "NOTICE entry",
			input:   "2024-01-15 10:23:45.100 PST [456] NOTICE: index \"idx_test\" was not created because it already exists",
			wantTS:  "2024-01-15 10:23:45.100 PST",
			wantPID: 456,
			wantLvl: LevelNotice,
			wantMsg: "index \"idx_test\" was not created because it already exists",
		},
		{
			name:    "DEBUG1 entry",
			input:   "2024-01-15 10:23:45.200 PST [789] DEBUG1: StartTransaction(1) name: unnamed",
			wantTS:  "2024-01-15 10:23:45.200 PST",
			wantPID: 789,
			wantLvl: LevelDebug1,
			wantMsg: "StartTransaction(1) name: unnamed",
		},
		{
			name:    "PANIC entry",
			input:   "2024-01-15 10:23:45.300 PST [111] PANIC: could not write to file \"pg_xact/0000\"",
			wantTS:  "2024-01-15 10:23:45.300 PST",
			wantPID: 111,
			wantLvl: LevelPanic,
			wantMsg: "could not write to file \"pg_xact/0000\"",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			entry := ParseLogLine(tt.input)

			if entry.Timestamp != tt.wantTS {
				t.Errorf("Timestamp = %q, want %q", entry.Timestamp, tt.wantTS)
			}
			if entry.PID != tt.wantPID {
				t.Errorf("PID = %d, want %d", entry.PID, tt.wantPID)
			}
			if entry.Level != tt.wantLvl {
				t.Errorf("Level = %v, want %v", entry.Level, tt.wantLvl)
			}
			if entry.Message != tt.wantMsg {
				t.Errorf("Message = %q, want %q", entry.Message, tt.wantMsg)
			}
			if entry.IsContinuation != tt.wantCont {
				t.Errorf("IsContinuation = %v, want %v", entry.IsContinuation, tt.wantCont)
			}
			if entry.Raw != tt.input {
				t.Errorf("Raw = %q, want %q", entry.Raw, tt.input)
			}
		})
	}
}

func TestParseLogLine_SimpleFormat(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		wantTS   string
		wantPID  int
		wantLvl  LogLevel
		wantMsg  string
	}{
		{
			name:    "simple format without timezone",
			input:   "2024-01-15 10:23:45 [12345] LOG: startup message",
			wantTS:  "2024-01-15 10:23:45",
			wantPID: 12345,
			wantLvl: LevelLog,
			wantMsg: "startup message",
		},
		{
			name:    "simple format with milliseconds",
			input:   "2024-01-15 10:23:45.123 [999] ERROR: simple error",
			wantTS:  "2024-01-15 10:23:45.123",
			wantPID: 999,
			wantLvl: LevelError,
			wantMsg: "simple error",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			entry := ParseLogLine(tt.input)

			if entry.Timestamp != tt.wantTS {
				t.Errorf("Timestamp = %q, want %q", entry.Timestamp, tt.wantTS)
			}
			if entry.PID != tt.wantPID {
				t.Errorf("PID = %d, want %d", entry.PID, tt.wantPID)
			}
			if entry.Level != tt.wantLvl {
				t.Errorf("Level = %v, want %v", entry.Level, tt.wantLvl)
			}
			if entry.Message != tt.wantMsg {
				t.Errorf("Message = %q, want %q", entry.Message, tt.wantMsg)
			}
		})
	}
}

func TestParseLogLine_ContinuationLines(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		wantMsg  string
		wantCont bool
	}{
		{
			name:     "tab-indented continuation",
			input:    "\t\tQuery: SELECT * FROM users WHERE id = 1",
			wantMsg:  "Query: SELECT * FROM users WHERE id = 1",
			wantCont: true,
		},
		{
			name:     "space-indented continuation",
			input:    "        DETAIL: Key (id)=(1) already exists",
			wantMsg:  "DETAIL: Key (id)=(1) already exists",
			wantCont: true,
		},
		{
			name:     "mixed whitespace continuation",
			input:    "  \tStatement: INSERT INTO test VALUES (1)",
			wantMsg:  "Statement: INSERT INTO test VALUES (1)",
			wantCont: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			entry := ParseLogLine(tt.input)

			if entry.IsContinuation != tt.wantCont {
				t.Errorf("IsContinuation = %v, want %v", entry.IsContinuation, tt.wantCont)
			}
			if entry.Message != tt.wantMsg {
				t.Errorf("Message = %q, want %q", entry.Message, tt.wantMsg)
			}
		})
	}
}

func TestParseLogLine_UnparseableLines(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		wantMsg string
		wantLvl LogLevel
	}{
		{
			name:    "random text",
			input:   "This is not a log line",
			wantMsg: "This is not a log line",
			wantLvl: LevelLog,
		},
		{
			name:    "incomplete timestamp",
			input:   "2024-01-15 LOG: incomplete",
			wantMsg: "2024-01-15 LOG: incomplete",
			wantLvl: LevelLog,
		},
		{
			name:    "missing brackets",
			input:   "2024-01-15 10:23:45 PST 12345 LOG: no brackets",
			wantMsg: "2024-01-15 10:23:45 PST 12345 LOG: no brackets",
			wantLvl: LevelLog,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			entry := ParseLogLine(tt.input)

			if entry.Message != tt.wantMsg {
				t.Errorf("Message = %q, want %q", entry.Message, tt.wantMsg)
			}
			if entry.Level != tt.wantLvl {
				t.Errorf("Level = %v, want %v", entry.Level, tt.wantLvl)
			}
			if entry.IsContinuation {
				t.Error("IsContinuation should be false for unparseable line")
			}
		})
	}
}

func TestParseLogLevel(t *testing.T) {
	tests := []struct {
		input   string
		want    LogLevel
		wantOK  bool
	}{
		{"DEBUG5", LevelDebug5, true},
		{"DEBUG4", LevelDebug4, true},
		{"DEBUG3", LevelDebug3, true},
		{"DEBUG2", LevelDebug2, true},
		{"DEBUG1", LevelDebug1, true},
		{"INFO", LevelInfo, true},
		{"NOTICE", LevelNotice, true},
		{"WARNING", LevelWarning, true},
		{"ERROR", LevelError, true},
		{"LOG", LevelLog, true},
		{"FATAL", LevelFatal, true},
		{"PANIC", LevelPanic, true},
		// Case insensitivity
		{"error", LevelError, true},
		{"Error", LevelError, true},
		{"warning", LevelWarning, true},
		{"log", LevelLog, true},
		// Invalid
		{"INVALID", LevelLog, false},
		{"", LevelLog, false},
		{"  ", LevelLog, false},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got, ok := ParseLogLevel(tt.input)
			if got != tt.want {
				t.Errorf("ParseLogLevel(%q) level = %v, want %v", tt.input, got, tt.want)
			}
			if ok != tt.wantOK {
				t.Errorf("ParseLogLevel(%q) ok = %v, want %v", tt.input, ok, tt.wantOK)
			}
		})
	}
}

func TestLogLevel_String(t *testing.T) {
	tests := []struct {
		level LogLevel
		want  string
	}{
		{LevelDebug5, "DEBUG5"},
		{LevelDebug4, "DEBUG4"},
		{LevelDebug3, "DEBUG3"},
		{LevelDebug2, "DEBUG2"},
		{LevelDebug1, "DEBUG1"},
		{LevelInfo, "INFO"},
		{LevelNotice, "NOTICE"},
		{LevelWarning, "WARNING"},
		{LevelError, "ERROR"},
		{LevelLog, "LOG"},
		{LevelFatal, "FATAL"},
		{LevelPanic, "PANIC"},
		{LogLevel(999), "UNKNOWN"},
	}

	for _, tt := range tests {
		t.Run(tt.want, func(t *testing.T) {
			if got := tt.level.String(); got != tt.want {
				t.Errorf("LogLevel(%d).String() = %q, want %q", tt.level, got, tt.want)
			}
		})
	}
}

func TestLogLevel_Short(t *testing.T) {
	tests := []struct {
		level LogLevel
		want  string
	}{
		{LevelDebug5, "DBG"},
		{LevelDebug4, "DBG"},
		{LevelDebug3, "DBG"},
		{LevelDebug2, "DBG"},
		{LevelDebug1, "DBG"},
		{LevelInfo, "INFO"},
		{LevelNotice, "NTCE"},
		{LevelWarning, "WARN"},
		{LevelError, "ERR"},
		{LevelLog, "LOG"},
		{LevelFatal, "FATL"},
		{LevelPanic, "PNKC"},
		{LogLevel(999), "UNK"},
	}

	for _, tt := range tests {
		t.Run(tt.want, func(t *testing.T) {
			if got := tt.level.Short(); got != tt.want {
				t.Errorf("LogLevel(%d).Short() = %q, want %q", tt.level, got, tt.want)
			}
		})
	}
}

func TestFilter(t *testing.T) {
	t.Run("empty filter allows all", func(t *testing.T) {
		f := NewFilter()
		for _, level := range []LogLevel{LevelDebug1, LevelInfo, LevelWarning, LevelError, LevelFatal} {
			if !f.Allow(level) {
				t.Errorf("Empty filter should allow %v", level)
			}
		}
		if !f.IsEmpty() {
			t.Error("Filter should be empty")
		}
	})

	t.Run("set filters specific levels", func(t *testing.T) {
		f := NewFilter()
		f.Set(LevelError, LevelWarning)

		if !f.Allow(LevelError) {
			t.Error("Should allow ERROR")
		}
		if !f.Allow(LevelWarning) {
			t.Error("Should allow WARNING")
		}
		if f.Allow(LevelInfo) {
			t.Error("Should not allow INFO")
		}
		if f.Allow(LevelLog) {
			t.Error("Should not allow LOG")
		}
		if f.IsEmpty() {
			t.Error("Filter should not be empty")
		}
	})

	t.Run("clear removes filter", func(t *testing.T) {
		f := NewFilter()
		f.Set(LevelError)
		f.Clear()

		if !f.Allow(LevelInfo) {
			t.Error("Should allow INFO after clear")
		}
		if !f.IsEmpty() {
			t.Error("Filter should be empty after clear")
		}
	})

	t.Run("nil filter allows all", func(t *testing.T) {
		var f *Filter
		if !f.Allow(LevelError) {
			t.Error("Nil filter should allow all levels")
		}
		if !f.IsEmpty() {
			t.Error("Nil filter should be considered empty")
		}
	})

	t.Run("String returns short format", func(t *testing.T) {
		f := NewFilter()
		f.Set(LevelError, LevelWarning)

		s := f.String()
		if s != "ERR,WARN" {
			t.Errorf("Filter.String() = %q, want %q", s, "ERR,WARN")
		}
	})

	t.Run("empty filter String returns empty", func(t *testing.T) {
		f := NewFilter()
		if f.String() != "" {
			t.Errorf("Empty filter String() = %q, want empty", f.String())
		}
	})
}
