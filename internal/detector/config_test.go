package detector

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParsePostgresConfig(t *testing.T) {
	// Create a temporary directory for test files
	tmpDir := t.TempDir()

	tests := []struct {
		name           string
		configContent  string
		wantPort       int
		wantLogDir     string
		wantLogFile    string
		wantLogDest    string
		wantErr        bool
	}{
		{
			name: "basic config with all settings",
			configContent: `
# PostgreSQL configuration file
port = 5433
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_destination = 'stderr'
`,
			wantPort:    5433,
			wantLogDir:  "pg_log",
			wantLogFile: "postgresql-%Y-%m-%d.log",
			wantLogDest: "stderr",
			wantErr:     false,
		},
		{
			name: "config with double quotes",
			configContent: `
port = 5434
log_directory = "custom_logs"
log_filename = "server.log"
`,
			wantPort:    5434,
			wantLogDir:  "custom_logs",
			wantLogFile: "server.log",
			wantErr:     false,
		},
		{
			name: "config with inline comments",
			configContent: `
port = 5435 # custom port
log_directory = 'logs' # log location
`,
			wantPort:   5435,
			wantLogDir: "logs",
			wantErr:    false,
		},
		{
			name: "config with no spaces around equals",
			configContent: `
port=5436
log_directory='nospace'
`,
			wantPort:   5436,
			wantLogDir: "nospace",
			wantErr:    false,
		},
		{
			name: "empty config uses defaults",
			configContent: `
# Only comments
# Nothing configured
`,
			wantPort: 5432, // default
			wantErr:  false,
		},
		{
			name:          "completely empty config",
			configContent: "",
			wantPort:      5432, // default
			wantErr:       false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Create test data directory
			dataDir := filepath.Join(tmpDir, tt.name)
			if err := os.MkdirAll(dataDir, 0755); err != nil {
				t.Fatalf("failed to create test dir: %v", err)
			}

			// Write config file
			configPath := filepath.Join(dataDir, "postgresql.conf")
			if err := os.WriteFile(configPath, []byte(tt.configContent), 0644); err != nil {
				t.Fatalf("failed to write config: %v", err)
			}

			// Parse config
			config, err := ParsePostgresConfig(dataDir)
			if (err != nil) != tt.wantErr {
				t.Errorf("ParsePostgresConfig() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if config.Port != tt.wantPort {
				t.Errorf("Port = %d, want %d", config.Port, tt.wantPort)
			}
			if config.LogDirectory != tt.wantLogDir {
				t.Errorf("LogDirectory = %q, want %q", config.LogDirectory, tt.wantLogDir)
			}
			if config.LogFilename != tt.wantLogFile {
				t.Errorf("LogFilename = %q, want %q", config.LogFilename, tt.wantLogFile)
			}
			if config.LogDestination != tt.wantLogDest {
				t.Errorf("LogDestination = %q, want %q", config.LogDestination, tt.wantLogDest)
			}
		})
	}
}

func TestParsePostgresConfig_FileNotFound(t *testing.T) {
	_, err := ParsePostgresConfig("/nonexistent/path")
	if err == nil {
		t.Error("expected error for nonexistent file, got nil")
	}
}

func TestResolveLogDir(t *testing.T) {
	tmpDir := t.TempDir()

	// Create log subdirectory
	logDir := filepath.Join(tmpDir, "log")
	if err := os.MkdirAll(logDir, 0755); err != nil {
		t.Fatalf("failed to create log dir: %v", err)
	}

	tests := []struct {
		name         string
		logDirectory string
		dataDir      string
		want         string
	}{
		{
			name:         "absolute path",
			logDirectory: "/var/log/postgresql",
			dataDir:      tmpDir,
			want:         "/var/log/postgresql",
		},
		{
			name:         "relative path",
			logDirectory: "pg_log",
			dataDir:      tmpDir,
			want:         filepath.Join(tmpDir, "pg_log"),
		},
		{
			name:         "empty uses default log dir",
			logDirectory: "",
			dataDir:      tmpDir,
			want:         logDir, // should find existing "log" directory
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			config := &PostgresConfig{LogDirectory: tt.logDirectory}
			got := config.ResolveLogDir(tt.dataDir)
			if got != tt.want {
				t.Errorf("ResolveLogDir() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestReadPGVersion(t *testing.T) {
	tmpDir := t.TempDir()

	tests := []struct {
		name    string
		content string
		want    string
		wantErr bool
	}{
		{
			name:    "version 16",
			content: "16\n",
			want:    "16",
			wantErr: false,
		},
		{
			name:    "version 15.4",
			content: "15\n",
			want:    "15",
			wantErr: false,
		},
		{
			name:    "version with extra whitespace",
			content: "  14  \n",
			want:    "14",
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dataDir := filepath.Join(tmpDir, tt.name)
			if err := os.MkdirAll(dataDir, 0755); err != nil {
				t.Fatalf("failed to create test dir: %v", err)
			}

			versionPath := filepath.Join(dataDir, "PG_VERSION")
			if err := os.WriteFile(versionPath, []byte(tt.content), 0644); err != nil {
				t.Fatalf("failed to write PG_VERSION: %v", err)
			}

			got, err := ReadPGVersion(dataDir)
			if (err != nil) != tt.wantErr {
				t.Errorf("ReadPGVersion() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if got != tt.want {
				t.Errorf("ReadPGVersion() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestReadPGVersion_FileNotFound(t *testing.T) {
	_, err := ReadPGVersion("/nonexistent/path")
	if err == nil {
		t.Error("expected error for nonexistent file, got nil")
	}
}

func TestParsePostmasterPID(t *testing.T) {
	tmpDir := t.TempDir()

	tests := []struct {
		name      string
		content   string
		wantPID   int
		wantPort  int
		wantErr   bool
	}{
		{
			name: "standard postmaster.pid",
			content: `12345
/var/lib/postgresql/16/main
1702500000
5432
/var/run/postgresql
*
`,
			wantPID:  12345,
			wantPort: 5432,
			wantErr:  false,
		},
		{
			name: "custom port",
			content: `54321
/home/user/.pgrx/data-16
1702500000
5433
/tmp
`,
			wantPID:  54321,
			wantPort: 5433,
			wantErr:  false,
		},
		{
			name: "minimal content",
			content: `1234
/data
0
5434
`,
			wantPID:  1234,
			wantPort: 5434,
			wantErr:  false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dataDir := filepath.Join(tmpDir, tt.name)
			if err := os.MkdirAll(dataDir, 0755); err != nil {
				t.Fatalf("failed to create test dir: %v", err)
			}

			pidPath := filepath.Join(dataDir, "postmaster.pid")
			if err := os.WriteFile(pidPath, []byte(tt.content), 0644); err != nil {
				t.Fatalf("failed to write postmaster.pid: %v", err)
			}

			info, err := ParsePostmasterPID(dataDir)
			if (err != nil) != tt.wantErr {
				t.Errorf("ParsePostmasterPID() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if info.PID != tt.wantPID {
				t.Errorf("PID = %d, want %d", info.PID, tt.wantPID)
			}
			if info.Port != tt.wantPort {
				t.Errorf("Port = %d, want %d", info.Port, tt.wantPort)
			}
		})
	}
}

func TestParsePostmasterPID_FileNotFound(t *testing.T) {
	_, err := ParsePostmasterPID("/nonexistent/path")
	if err == nil {
		t.Error("expected error for nonexistent file, got nil")
	}
}

func TestIsValidDataDir(t *testing.T) {
	tmpDir := t.TempDir()

	// Create a valid data directory
	validDir := filepath.Join(tmpDir, "valid")
	if err := os.MkdirAll(validDir, 0755); err != nil {
		t.Fatalf("failed to create valid dir: %v", err)
	}
	if err := os.WriteFile(filepath.Join(validDir, "PG_VERSION"), []byte("16\n"), 0644); err != nil {
		t.Fatalf("failed to write PG_VERSION: %v", err)
	}

	// Create an invalid data directory (no PG_VERSION)
	invalidDir := filepath.Join(tmpDir, "invalid")
	if err := os.MkdirAll(invalidDir, 0755); err != nil {
		t.Fatalf("failed to create invalid dir: %v", err)
	}

	tests := []struct {
		name string
		path string
		want bool
	}{
		{
			name: "valid data directory",
			path: validDir,
			want: true,
		},
		{
			name: "invalid data directory",
			path: invalidDir,
			want: false,
		},
		{
			name: "nonexistent directory",
			path: "/nonexistent/path",
			want: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := IsValidDataDir(tt.path)
			if got != tt.want {
				t.Errorf("IsValidDataDir(%q) = %v, want %v", tt.path, got, tt.want)
			}
		})
	}
}
