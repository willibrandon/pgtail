package tailer

import (
	"testing"
)

func TestFilter_New(t *testing.T) {
	f := NewFilter()
	if f == nil {
		t.Fatal("NewFilter returned nil")
	}
	if f.levels == nil {
		t.Error("levels map should be initialized")
	}
	if !f.IsEmpty() {
		t.Error("new filter should be empty")
	}
}

func TestFilter_AllowEmptyFilter(t *testing.T) {
	f := NewFilter()
	// An empty filter should allow all levels.
	levels := []LogLevel{
		LevelDebug5, LevelDebug4, LevelDebug3, LevelDebug2, LevelDebug1,
		LevelInfo, LevelNotice, LevelWarning, LevelError, LevelLog,
		LevelFatal, LevelPanic,
	}
	for _, level := range levels {
		if !f.Allow(level) {
			t.Errorf("Empty filter should allow %v", level)
		}
	}
}

func TestFilter_AllowNilFilter(t *testing.T) {
	var f *Filter
	// A nil filter should allow all levels.
	if !f.Allow(LevelError) {
		t.Error("Nil filter should allow ERROR")
	}
	if !f.Allow(LevelWarning) {
		t.Error("Nil filter should allow WARNING")
	}
	if !f.Allow(LevelInfo) {
		t.Error("Nil filter should allow INFO")
	}
}

func TestFilter_Set(t *testing.T) {
	tests := []struct {
		name      string
		setLevels []LogLevel
		allow     []LogLevel
		deny      []LogLevel
	}{
		{
			name:      "single level",
			setLevels: []LogLevel{LevelError},
			allow:     []LogLevel{LevelError},
			deny:      []LogLevel{LevelWarning, LevelInfo, LevelLog, LevelFatal},
		},
		{
			name:      "multiple levels",
			setLevels: []LogLevel{LevelError, LevelWarning, LevelFatal},
			allow:     []LogLevel{LevelError, LevelWarning, LevelFatal},
			deny:      []LogLevel{LevelInfo, LevelLog, LevelDebug1},
		},
		{
			name:      "all levels",
			setLevels: []LogLevel{LevelDebug5, LevelDebug4, LevelDebug3, LevelDebug2, LevelDebug1, LevelInfo, LevelNotice, LevelWarning, LevelError, LevelLog, LevelFatal, LevelPanic},
			allow:     []LogLevel{LevelDebug1, LevelInfo, LevelWarning, LevelError, LevelFatal, LevelPanic},
			deny:      []LogLevel{},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := NewFilter()
			f.Set(tt.setLevels...)

			for _, level := range tt.allow {
				if !f.Allow(level) {
					t.Errorf("Should allow %v", level)
				}
			}
			for _, level := range tt.deny {
				if f.Allow(level) {
					t.Errorf("Should deny %v", level)
				}
			}
		})
	}
}

func TestFilter_SetReplacesExisting(t *testing.T) {
	f := NewFilter()
	f.Set(LevelError, LevelWarning)

	// First set should work.
	if !f.Allow(LevelError) {
		t.Error("Should allow ERROR after first Set")
	}

	// Setting again should replace, not add.
	f.Set(LevelInfo)
	if f.Allow(LevelError) {
		t.Error("Should not allow ERROR after second Set")
	}
	if f.Allow(LevelWarning) {
		t.Error("Should not allow WARNING after second Set")
	}
	if !f.Allow(LevelInfo) {
		t.Error("Should allow INFO after second Set")
	}
}

func TestFilter_Clear(t *testing.T) {
	f := NewFilter()
	f.Set(LevelError, LevelWarning)

	// Verify filter is active.
	if f.IsEmpty() {
		t.Error("Filter should not be empty before clear")
	}
	if f.Allow(LevelInfo) {
		t.Error("Should not allow INFO before clear")
	}

	// Clear the filter.
	f.Clear()

	// Verify filter is cleared.
	if !f.IsEmpty() {
		t.Error("Filter should be empty after clear")
	}
	if !f.Allow(LevelInfo) {
		t.Error("Should allow INFO after clear")
	}
	if !f.Allow(LevelError) {
		t.Error("Should allow ERROR after clear")
	}
}

func TestFilter_IsEmpty(t *testing.T) {
	tests := []struct {
		name    string
		setup   func(*Filter)
		isEmpty bool
	}{
		{
			name:    "new filter",
			setup:   func(f *Filter) {},
			isEmpty: true,
		},
		{
			name:    "after Set",
			setup:   func(f *Filter) { f.Set(LevelError) },
			isEmpty: false,
		},
		{
			name:    "after Set then Clear",
			setup:   func(f *Filter) { f.Set(LevelError); f.Clear() },
			isEmpty: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := NewFilter()
			tt.setup(f)
			if f.IsEmpty() != tt.isEmpty {
				t.Errorf("IsEmpty() = %v, want %v", f.IsEmpty(), tt.isEmpty)
			}
		})
	}

	// Test nil filter.
	var nilFilter *Filter
	if !nilFilter.IsEmpty() {
		t.Error("Nil filter should be considered empty")
	}
}

func TestFilter_String(t *testing.T) {
	tests := []struct {
		name      string
		setLevels []LogLevel
		want      string
	}{
		{
			name:      "empty filter",
			setLevels: []LogLevel{},
			want:      "",
		},
		{
			name:      "single level",
			setLevels: []LogLevel{LevelError},
			want:      "ERR",
		},
		{
			name:      "ERROR and WARNING",
			setLevels: []LogLevel{LevelError, LevelWarning},
			want:      "ERR,WARN",
		},
		{
			name:      "high severity levels",
			setLevels: []LogLevel{LevelPanic, LevelFatal, LevelError},
			want:      "PNKC,FATL,ERR",
		},
		{
			name:      "debug levels",
			setLevels: []LogLevel{LevelDebug1, LevelDebug2},
			want:      "DBG,DBG",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := NewFilter()
			if len(tt.setLevels) > 0 {
				f.Set(tt.setLevels...)
			}
			if got := f.String(); got != tt.want {
				t.Errorf("String() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestFilter_Levels(t *testing.T) {
	t.Run("empty filter returns nil", func(t *testing.T) {
		f := NewFilter()
		if levels := f.Levels(); levels != nil {
			t.Errorf("Levels() = %v, want nil", levels)
		}
	})

	t.Run("returns set levels", func(t *testing.T) {
		f := NewFilter()
		f.Set(LevelError, LevelWarning)
		levels := f.Levels()
		if len(levels) != 2 {
			t.Errorf("Levels() returned %d levels, want 2", len(levels))
		}
		// Check that both levels are present (order doesn't matter).
		hasError := false
		hasWarning := false
		for _, l := range levels {
			if l == LevelError {
				hasError = true
			}
			if l == LevelWarning {
				hasWarning = true
			}
		}
		if !hasError {
			t.Error("Levels() should contain ERROR")
		}
		if !hasWarning {
			t.Error("Levels() should contain WARNING")
		}
	})
}

func TestParseLogLevel_CaseInsensitive(t *testing.T) {
	tests := []struct {
		input string
		want  LogLevel
	}{
		{"error", LevelError},
		{"ERROR", LevelError},
		{"Error", LevelError},
		{"eRrOr", LevelError},
		{"warning", LevelWarning},
		{"WARNING", LevelWarning},
		{"Warning", LevelWarning},
		{"log", LevelLog},
		{"LOG", LevelLog},
		{"fatal", LevelFatal},
		{"FATAL", LevelFatal},
		{"panic", LevelPanic},
		{"PANIC", LevelPanic},
		{"info", LevelInfo},
		{"INFO", LevelInfo},
		{"notice", LevelNotice},
		{"NOTICE", LevelNotice},
		{"debug1", LevelDebug1},
		{"DEBUG1", LevelDebug1},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got, ok := ParseLogLevel(tt.input)
			if !ok {
				t.Errorf("ParseLogLevel(%q) should return ok=true", tt.input)
			}
			if got != tt.want {
				t.Errorf("ParseLogLevel(%q) = %v, want %v", tt.input, got, tt.want)
			}
		})
	}
}

func TestParseLogLevel_Invalid(t *testing.T) {
	tests := []string{
		"invalid",
		"INVALID",
		"",
		"  ",
		"err",
		"warn",
		"debug",
		"critical",
		"trace",
	}

	for _, input := range tests {
		t.Run(input, func(t *testing.T) {
			_, ok := ParseLogLevel(input)
			if ok {
				t.Errorf("ParseLogLevel(%q) should return ok=false", input)
			}
		})
	}
}

func TestParseLogLevel_WithWhitespace(t *testing.T) {
	tests := []struct {
		input string
		want  LogLevel
	}{
		{"  ERROR  ", LevelError},
		{"\tWARNING\t", LevelWarning},
		{" LOG", LevelLog},
		{"FATAL ", LevelFatal},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got, ok := ParseLogLevel(tt.input)
			if !ok {
				t.Errorf("ParseLogLevel(%q) should return ok=true", tt.input)
			}
			if got != tt.want {
				t.Errorf("ParseLogLevel(%q) = %v, want %v", tt.input, got, tt.want)
			}
		})
	}
}

func TestAllLogLevels(t *testing.T) {
	levels := AllLogLevels()

	// Should contain all 12 levels.
	if len(levels) != 12 {
		t.Errorf("AllLogLevels() returned %d levels, want 12", len(levels))
	}

	// Check that all expected levels are present.
	expected := map[string]bool{
		"DEBUG5": false, "DEBUG4": false, "DEBUG3": false, "DEBUG2": false, "DEBUG1": false,
		"INFO": false, "NOTICE": false, "WARNING": false, "ERROR": false,
		"LOG": false, "FATAL": false, "PANIC": false,
	}
	for _, level := range levels {
		if _, ok := expected[level]; !ok {
			t.Errorf("Unexpected level %q in AllLogLevels()", level)
		}
		expected[level] = true
	}
	for level, found := range expected {
		if !found {
			t.Errorf("Missing level %q in AllLogLevels()", level)
		}
	}
}
