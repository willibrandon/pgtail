package detector

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParsePostgresConfig(t *testing.T) {
	tests := []struct {
		name     string
		content  string
		expected Config
	}{
		{
			name: "basic config",
			content: `
port = 5433
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_destination = 'stderr'
`,
			expected: Config{
				Port:           5433,
				LogDirectory:   "pg_log",
				LogFilename:    "postgresql-%Y-%m-%d_%H%M%S.log",
				LogDestination: "stderr",
			},
		},
		{
			name: "config with comments",
			content: `
# This is a comment
port = 5432 # inline comment
log_directory = 'log'
# log_filename = 'ignored.log'
`,
			expected: Config{
				Port:         5432,
				LogDirectory: "log",
			},
		},
		{
			name: "config with double quotes",
			content: `
port = 5434
log_directory = "custom_logs"
`,
			expected: Config{
				Port:         5434,
				LogDirectory: "custom_logs",
			},
		},
		{
			name: "empty config",
			content: `
# all comments
`,
			expected: Config{
				Port: 5432, // default
			},
		},
		{
			name: "config without spaces",
			content: `
port=5435
log_directory='logs'
`,
			expected: Config{
				Port:         5435,
				LogDirectory: "logs",
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Create a temporary directory with postgresql.conf.
			tmpDir := t.TempDir()
			configPath := filepath.Join(tmpDir, "postgresql.conf")
			if err := os.WriteFile(configPath, []byte(tt.content), 0644); err != nil {
				t.Fatalf("failed to write config: %v", err)
			}

			config := ParsePostgresConfig(tmpDir)

			if config.Port != tt.expected.Port {
				t.Errorf("Port = %d, want %d", config.Port, tt.expected.Port)
			}
			if config.LogDirectory != tt.expected.LogDirectory {
				t.Errorf("LogDirectory = %q, want %q", config.LogDirectory, tt.expected.LogDirectory)
			}
			if config.LogFilename != tt.expected.LogFilename {
				t.Errorf("LogFilename = %q, want %q", config.LogFilename, tt.expected.LogFilename)
			}
			if config.LogDestination != tt.expected.LogDestination {
				t.Errorf("LogDestination = %q, want %q", config.LogDestination, tt.expected.LogDestination)
			}
		})
	}
}

func TestParsePostgresConfig_MissingFile(t *testing.T) {
	config := ParsePostgresConfig("/nonexistent/path")

	// Should return default config.
	if config.Port != 5432 {
		t.Errorf("Port = %d, want 5432 (default)", config.Port)
	}
}

func TestReadPGVersion(t *testing.T) {
	tests := []struct {
		name     string
		content  string
		expected string
	}{
		{
			name:     "major version only",
			content:  "16\n",
			expected: "16",
		},
		{
			name:     "major.minor version",
			content:  "15.4\n",
			expected: "15.4",
		},
		{
			name:     "version with trailing newline",
			content:  "14\n",
			expected: "14",
		},
		{
			name:     "version without newline",
			content:  "13",
			expected: "13",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tmpDir := t.TempDir()
			versionPath := filepath.Join(tmpDir, "PG_VERSION")
			if err := os.WriteFile(versionPath, []byte(tt.content), 0644); err != nil {
				t.Fatalf("failed to write version: %v", err)
			}

			version := ReadPGVersion(tmpDir)

			if version != tt.expected {
				t.Errorf("ReadPGVersion() = %q, want %q", version, tt.expected)
			}
		})
	}
}

func TestReadPGVersion_MissingFile(t *testing.T) {
	version := ReadPGVersion("/nonexistent/path")
	if version != "" {
		t.Errorf("ReadPGVersion() = %q, want empty string", version)
	}
}

func TestParsePostmasterPID(t *testing.T) {
	tests := []struct {
		name     string
		content  string
		expected *PostmasterInfo
	}{
		{
			name: "full postmaster.pid",
			content: `12345
/var/lib/postgresql/16/main
1699123456
5432
/var/run/postgresql
localhost
main
`,
			expected: &PostmasterInfo{
				PID:       12345,
				DataDir:   "/var/lib/postgresql/16/main",
				StartTime: 1699123456,
				Port:      5432,
				SocketDir: "/var/run/postgresql",
				Host:      "localhost",
				Cluster:   "main",
			},
		},
		{
			name: "minimal postmaster.pid",
			content: `67890
/data
0
5433
`,
			expected: &PostmasterInfo{
				PID:       67890,
				DataDir:   "/data",
				StartTime: 0,
				Port:      5433,
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tmpDir := t.TempDir()
			pidPath := filepath.Join(tmpDir, "postmaster.pid")
			if err := os.WriteFile(pidPath, []byte(tt.content), 0644); err != nil {
				t.Fatalf("failed to write pid file: %v", err)
			}

			info := ParsePostmasterPID(tmpDir)

			if info == nil {
				t.Fatal("ParsePostmasterPID() returned nil")
			}
			if info.PID != tt.expected.PID {
				t.Errorf("PID = %d, want %d", info.PID, tt.expected.PID)
			}
			if info.Port != tt.expected.Port {
				t.Errorf("Port = %d, want %d", info.Port, tt.expected.Port)
			}
		})
	}
}

func TestParsePostmasterPID_MissingFile(t *testing.T) {
	info := ParsePostmasterPID("/nonexistent/path")
	if info != nil {
		t.Errorf("ParsePostmasterPID() = %v, want nil", info)
	}
}

func TestParsePostmasterPID_InvalidPID(t *testing.T) {
	tmpDir := t.TempDir()
	pidPath := filepath.Join(tmpDir, "postmaster.pid")
	if err := os.WriteFile(pidPath, []byte("not-a-number\n"), 0644); err != nil {
		t.Fatalf("failed to write pid file: %v", err)
	}

	info := ParsePostmasterPID(tmpDir)
	if info != nil {
		t.Errorf("ParsePostmasterPID() = %v, want nil for invalid PID", info)
	}
}

func TestResolveLogDir(t *testing.T) {
	tests := []struct {
		name     string
		dataDir  string
		logDir   string
		expected string
	}{
		{
			name:     "empty log dir uses default",
			dataDir:  "/data",
			logDir:   "",
			expected: "/data/log",
		},
		{
			name:     "absolute log dir unchanged",
			dataDir:  "/data",
			logDir:   "/var/log/postgresql",
			expected: "/var/log/postgresql",
		},
		{
			name:     "relative log dir resolved against data dir",
			dataDir:  "/data",
			logDir:   "pg_log",
			expected: "/data/pg_log",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := ResolveLogDir(tt.dataDir, tt.logDir)
			if result != tt.expected {
				t.Errorf("ResolveLogDir(%q, %q) = %q, want %q",
					tt.dataDir, tt.logDir, result, tt.expected)
			}
		})
	}
}

func TestIsValidDataDir(t *testing.T) {
	// Create a valid data dir with PG_VERSION.
	validDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(validDir, "PG_VERSION"), []byte("16\n"), 0644); err != nil {
		t.Fatalf("failed to create PG_VERSION: %v", err)
	}

	// Create an invalid dir without PG_VERSION.
	invalidDir := t.TempDir()

	tests := []struct {
		name     string
		path     string
		expected bool
	}{
		{
			name:     "valid data dir",
			path:     validDir,
			expected: true,
		},
		{
			name:     "invalid data dir - no PG_VERSION",
			path:     invalidDir,
			expected: false,
		},
		{
			name:     "nonexistent dir",
			path:     "/nonexistent/path",
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := IsValidDataDir(tt.path)
			if result != tt.expected {
				t.Errorf("IsValidDataDir(%q) = %v, want %v", tt.path, result, tt.expected)
			}
		})
	}
}
