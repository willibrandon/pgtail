package detector

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestNormalizePath(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "absolute path",
			input:    "/var/lib/postgresql/16/main",
			expected: strings.ToLower("/var/lib/postgresql/16/main"),
		},
		{
			name:     "path with trailing slash",
			input:    "/var/lib/postgresql/16/main/",
			expected: strings.ToLower("/var/lib/postgresql/16/main"),
		},
		{
			name:     "path with dot components",
			input:    "/var/lib/postgresql/../postgresql/16/main",
			expected: strings.ToLower("/var/lib/postgresql/16/main"),
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := normalizePath(tt.input)
			if result != tt.expected {
				t.Errorf("normalizePath(%q) = %q, want %q", tt.input, result, tt.expected)
			}
		})
	}
}

func TestBuildInstance(t *testing.T) {
	// Create a mock PostgreSQL data directory.
	dataDir := t.TempDir()

	// Create required files.
	if err := os.WriteFile(filepath.Join(dataDir, "PG_VERSION"), []byte("16\n"), 0644); err != nil {
		t.Fatalf("failed to create PG_VERSION: %v", err)
	}

	configContent := `
port = 5433
log_directory = 'log'
`
	if err := os.WriteFile(filepath.Join(dataDir, "postgresql.conf"), []byte(configContent), 0644); err != nil {
		t.Fatalf("failed to create postgresql.conf: %v", err)
	}

	// Create log directory.
	if err := os.MkdirAll(filepath.Join(dataDir, "log"), 0755); err != nil {
		t.Fatalf("failed to create log dir: %v", err)
	}

	// Test building instance.
	inst := buildInstance(dataDir, 0) // SourceProcess = 0

	if inst == nil {
		t.Fatal("buildInstance() returned nil")
	}

	if inst.DataDir != dataDir {
		t.Errorf("DataDir = %q, want %q", inst.DataDir, dataDir)
	}

	if inst.Version != "16" {
		t.Errorf("Version = %q, want %q", inst.Version, "16")
	}

	if inst.Port != 5433 {
		t.Errorf("Port = %d, want 5433", inst.Port)
	}

	expectedLogDir := filepath.Join(dataDir, "log")
	if inst.LogDir != expectedLogDir {
		t.Errorf("LogDir = %q, want %q", inst.LogDir, expectedLogDir)
	}
}

func TestBuildInstance_InvalidDataDir(t *testing.T) {
	// Test with non-existent directory.
	inst := buildInstance("/nonexistent/path", 0)
	if inst != nil {
		t.Errorf("buildInstance() = %v, want nil for invalid data dir", inst)
	}

	// Test with directory without PG_VERSION.
	emptyDir := t.TempDir()
	inst = buildInstance(emptyDir, 0)
	if inst != nil {
		t.Errorf("buildInstance() = %v, want nil for dir without PG_VERSION", inst)
	}
}

func TestDetectInstances_Deduplication(t *testing.T) {
	// Create two "different" paths that resolve to the same location.
	dataDir := t.TempDir()

	// Create required files.
	if err := os.WriteFile(filepath.Join(dataDir, "PG_VERSION"), []byte("16\n"), 0644); err != nil {
		t.Fatalf("failed to create PG_VERSION: %v", err)
	}
	if err := os.WriteFile(filepath.Join(dataDir, "postgresql.conf"), []byte("port = 5432\n"), 0644); err != nil {
		t.Fatalf("failed to create postgresql.conf: %v", err)
	}

	// Test that normalizePath handles deduplication correctly.
	path1 := dataDir
	path2 := dataDir + "/" // With trailing slash.
	path3 := dataDir + "/." // With dot component.

	normalized1 := normalizePath(path1)
	normalized2 := normalizePath(path2)
	normalized3 := normalizePath(path3)

	if normalized1 != normalized2 {
		t.Errorf("Paths not deduplicated: %q != %q", normalized1, normalized2)
	}
	if normalized1 != normalized3 {
		t.Errorf("Paths not deduplicated: %q != %q", normalized1, normalized3)
	}
}

func TestSplitCommandLine(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected []string
	}{
		{
			name:     "simple args",
			input:    "postgres -D /data -p 5432",
			expected: []string{"postgres", "-D", "/data", "-p", "5432"},
		},
		{
			name:     "quoted path with spaces",
			input:    `postgres -D "/path/with spaces/data" -p 5432`,
			expected: []string{"postgres", "-D", "/path/with spaces/data", "-p", "5432"},
		},
		{
			name:     "single quoted path",
			input:    `postgres -D '/path/with spaces/data' -p 5432`,
			expected: []string{"postgres", "-D", "/path/with spaces/data", "-p", "5432"},
		},
		{
			name:     "multiple spaces",
			input:    "postgres   -D   /data",
			expected: []string{"postgres", "-D", "/data"},
		},
		{
			name:     "empty string",
			input:    "",
			expected: nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := splitCommandLine(tt.input)
			if len(result) != len(tt.expected) {
				t.Errorf("splitCommandLine(%q) = %v (len %d), want %v (len %d)",
					tt.input, result, len(result), tt.expected, len(tt.expected))
				return
			}
			for i, arg := range result {
				if arg != tt.expected[i] {
					t.Errorf("splitCommandLine(%q)[%d] = %q, want %q",
						tt.input, i, arg, tt.expected[i])
				}
			}
		})
	}
}

func TestExtractDataDir(t *testing.T) {
	tests := []struct {
		name     string
		cmdline  string
		expected string
	}{
		{
			name:     "-D with space",
			cmdline:  "/usr/lib/postgresql/16/bin/postgres -D /var/lib/postgresql/16/main",
			expected: "/var/lib/postgresql/16/main",
		},
		{
			name:     "-D without space",
			cmdline:  "/usr/bin/postgres -D/data",
			expected: "/data",
		},
		{
			name:     "--data flag",
			cmdline:  "postgres --data /data -p 5432",
			expected: "/data",
		},
		{
			name:     "--data= format",
			cmdline:  "postgres --data=/data -p 5432",
			expected: "/data",
		},
		{
			name:     "no data dir",
			cmdline:  "postgres -p 5432",
			expected: "",
		},
		{
			name:     "quoted path",
			cmdline:  `postgres -D "/path/with spaces"`,
			expected: "/path/with spaces",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := extractDataDir(tt.cmdline)
			if result != tt.expected {
				t.Errorf("extractDataDir(%q) = %q, want %q", tt.cmdline, result, tt.expected)
			}
		})
	}
}
