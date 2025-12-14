package detector

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/willibrandon/pgtail/internal/instance"
)

func TestNormalizeDataDir(t *testing.T) {
	tests := []struct {
		name  string
		input string
	}{
		{
			name:  "removes trailing slash",
			input: "/var/lib/postgresql/",
		},
		{
			name:  "cleans double slashes",
			input: "/var//lib/postgresql",
		},
		{
			name:  "handles dot components",
			input: "/var/lib/../lib/postgresql",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := normalizeDataDir(tt.input)

			// Should not have trailing slash
			if strings.HasSuffix(result, "/") && result != "/" {
				t.Errorf("normalizeDataDir(%q) has trailing slash: %q", tt.input, result)
			}

			// Should not have double slashes
			if strings.Contains(result, "//") {
				t.Errorf("normalizeDataDir(%q) has double slashes: %q", tt.input, result)
			}

			// Should not have . or .. components (except at start for relative paths)
			if strings.Contains(result, "/./") || strings.Contains(result, "/../") {
				t.Errorf("normalizeDataDir(%q) has unresolved path components: %q", tt.input, result)
			}
		})
	}
}

func TestNormalizeDataDir_CaseHandling(t *testing.T) {
	path := "/Var/Lib/PostgreSQL"
	result := normalizeDataDir(path)

	// On case-insensitive systems (macOS, Windows), should be lowercased
	if runtime.GOOS == "darwin" || runtime.GOOS == "windows" {
		if result != strings.ToLower(result) {
			t.Errorf("on %s, normalizeDataDir(%q) should be lowercase, got %q", runtime.GOOS, path, result)
		}
	}
}

func TestDetectionResult_HasErrors(t *testing.T) {
	tests := []struct {
		name   string
		errors []error
		want   bool
	}{
		{
			name:   "no errors",
			errors: nil,
			want:   false,
		},
		{
			name:   "empty errors slice",
			errors: []error{},
			want:   false,
		},
		{
			name:   "with errors",
			errors: []error{os.ErrNotExist},
			want:   true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			r := &DetectionResult{Errors: tt.errors}
			if got := r.HasErrors(); got != tt.want {
				t.Errorf("HasErrors() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestDetectionResult_InstanceCount(t *testing.T) {
	tests := []struct {
		name      string
		instances []*instance.Instance
		want      int
	}{
		{
			name:      "no instances",
			instances: nil,
			want:      0,
		},
		{
			name:      "one instance",
			instances: []*instance.Instance{{}},
			want:      1,
		},
		{
			name:      "multiple instances",
			instances: []*instance.Instance{{}, {}, {}},
			want:      3,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			r := &DetectionResult{Instances: tt.instances}
			if got := r.InstanceCount(); got != tt.want {
				t.Errorf("InstanceCount() = %v, want %v", got, tt.want)
			}
		})
	}
}

// createMockDataDir creates a mock PostgreSQL data directory for testing.
func createMockDataDir(t *testing.T, baseDir, name, version string, port int) string {
	t.Helper()

	dataDir := filepath.Join(baseDir, name)
	if err := os.MkdirAll(dataDir, 0755); err != nil {
		t.Fatalf("failed to create mock data dir: %v", err)
	}

	// Write PG_VERSION
	if err := os.WriteFile(filepath.Join(dataDir, "PG_VERSION"), []byte(version+"\n"), 0644); err != nil {
		t.Fatalf("failed to write PG_VERSION: %v", err)
	}

	// Write postgresql.conf
	configContent := ""
	if port > 0 {
		configContent = "port = " + itoa(port) + "\n"
	}
	if err := os.WriteFile(filepath.Join(dataDir, "postgresql.conf"), []byte(configContent), 0644); err != nil {
		t.Fatalf("failed to write postgresql.conf: %v", err)
	}

	// Create log directory
	logDir := filepath.Join(dataDir, "log")
	if err := os.MkdirAll(logDir, 0755); err != nil {
		t.Fatalf("failed to create log dir: %v", err)
	}

	return dataDir
}

// itoa converts int to string without importing strconv
func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	var digits []byte
	for n > 0 {
		digits = append([]byte{byte('0' + n%10)}, digits...)
		n /= 10
	}
	return string(digits)
}

func TestDetectFromPgrx(t *testing.T) {
	// Skip if we can't create temp directories
	tmpDir := t.TempDir()

	// Create a mock .pgrx directory structure
	pgrxDir := filepath.Join(tmpDir, ".pgrx")
	if err := os.MkdirAll(pgrxDir, 0755); err != nil {
		t.Fatalf("failed to create .pgrx dir: %v", err)
	}

	// Create mock data directories
	createMockDataDir(t, pgrxDir, "data-16", "16", 5432)
	createMockDataDir(t, pgrxDir, "data-15", "15", 5433)

	// Create a non-data directory (should be skipped)
	if err := os.MkdirAll(filepath.Join(pgrxDir, "not-data"), 0755); err != nil {
		t.Fatalf("failed to create non-data dir: %v", err)
	}

	// Temporarily override home directory
	oldHome := os.Getenv("HOME")
	os.Setenv("HOME", tmpDir)
	defer os.Setenv("HOME", oldHome)

	instances, errs := DetectFromPgrx()

	if len(errs) > 0 {
		t.Errorf("DetectFromPgrx() returned errors: %v", errs)
	}

	if len(instances) != 2 {
		t.Errorf("DetectFromPgrx() found %d instances, want 2", len(instances))
	}

	// Verify instances have correct source
	for _, inst := range instances {
		if inst.Source != instance.SourcePgrx {
			t.Errorf("instance source = %v, want SourcePgrx", inst.Source)
		}
		if inst.SourceDetail != "pgrx" {
			t.Errorf("instance source detail = %q, want %q", inst.SourceDetail, "pgrx")
		}
	}
}

func TestDetectFromEnvVar(t *testing.T) {
	tmpDir := t.TempDir()

	// Create a mock data directory
	dataDir := createMockDataDir(t, tmpDir, "pgdata", "16", 5432)

	// Set PGDATA environment variable
	oldPGDATA := os.Getenv("PGDATA")
	os.Setenv("PGDATA", dataDir)
	defer os.Setenv("PGDATA", oldPGDATA)

	inst, err := DetectFromEnvVar()
	if err != nil {
		t.Fatalf("DetectFromEnvVar() error = %v", err)
	}

	if inst == nil {
		t.Fatal("DetectFromEnvVar() returned nil instance")
	}

	if inst.Source != instance.SourceEnvVar {
		t.Errorf("instance source = %v, want SourceEnvVar", inst.Source)
	}

	if inst.Version != "16" {
		t.Errorf("instance version = %q, want %q", inst.Version, "16")
	}
}

func TestDetectFromEnvVar_NotSet(t *testing.T) {
	// Unset PGDATA
	oldPGDATA := os.Getenv("PGDATA")
	os.Unsetenv("PGDATA")
	defer func() {
		if oldPGDATA != "" {
			os.Setenv("PGDATA", oldPGDATA)
		}
	}()

	inst, err := DetectFromEnvVar()
	if err != nil {
		t.Fatalf("DetectFromEnvVar() error = %v", err)
	}

	if inst != nil {
		t.Errorf("DetectFromEnvVar() = %v, want nil when PGDATA not set", inst)
	}
}

func TestDetectFromEnvVar_InvalidPath(t *testing.T) {
	// Set PGDATA to a nonexistent path
	oldPGDATA := os.Getenv("PGDATA")
	os.Setenv("PGDATA", "/nonexistent/path/to/data")
	defer os.Setenv("PGDATA", oldPGDATA)

	inst, err := DetectFromEnvVar()
	if err != nil {
		t.Fatalf("DetectFromEnvVar() error = %v", err)
	}

	// Should return nil for invalid path, not error
	if inst != nil {
		t.Errorf("DetectFromEnvVar() = %v, want nil for invalid path", inst)
	}
}

func TestInstanceDeduplication(t *testing.T) {
	tmpDir := t.TempDir()

	// Create a single data directory
	dataDir := createMockDataDir(t, tmpDir, "data", "16", 5432)

	// Simulate detecting the same instance from multiple sources
	seen := make(map[string]bool)

	// First detection
	key1 := normalizeDataDir(dataDir)
	if seen[key1] {
		t.Error("instance should not be seen on first detection")
	}
	seen[key1] = true

	// Second detection of same path (should be deduplicated)
	key2 := normalizeDataDir(dataDir)
	if !seen[key2] {
		t.Error("instance should be seen on second detection (deduplication)")
	}

	// Different path should not be seen
	key3 := normalizeDataDir(filepath.Join(tmpDir, "other"))
	if seen[key3] {
		t.Error("different path should not be seen")
	}
}

func TestExtractDataDir(t *testing.T) {
	tests := []struct {
		name    string
		cmdline string
		want    string
	}{
		{
			name:    "standard -D flag",
			cmdline: "/usr/lib/postgresql/16/bin/postgres -D /var/lib/postgresql/16/main",
			want:    "/var/lib/postgresql/16/main",
		},
		{
			name:    "-D flag with other args",
			cmdline: "postgres -D /data -c shared_buffers=256MB",
			want:    "/data",
		},
		{
			name:    "--pgdata= style",
			cmdline: "postgres --pgdata=/var/lib/pgsql/data",
			want:    "/var/lib/pgsql/data",
		},
		{
			name:    "-D attached to value",
			cmdline: "postgres -D/data/postgresql",
			want:    "/data/postgresql",
		},
		{
			name:    "no data directory",
			cmdline: "postgres -c log_connections=on",
			want:    "",
		},
		{
			name:    "empty cmdline",
			cmdline: "",
			want:    "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := extractDataDir(tt.cmdline)
			if got != tt.want {
				t.Errorf("extractDataDir(%q) = %q, want %q", tt.cmdline, got, tt.want)
			}
		})
	}
}
