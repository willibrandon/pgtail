// Package detector provides PostgreSQL instance detection functionality.
package detector

import (
	"bufio"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// Config holds parsed postgresql.conf settings relevant to pgtail.
type Config struct {
	LogDirectory     string // log_directory setting
	LogFilename      string // log_filename setting
	Port             int    // port setting
	LogDestination   string // log_destination setting
	LoggingCollector bool   // logging_collector setting
}

// ParsePostgresConfig reads postgresql.conf and extracts relevant settings.
// Returns an empty Config if the file cannot be read.
func ParsePostgresConfig(dataDir string) Config {
	config := Config{
		Port: 5432, // Default PostgreSQL port
	}

	configPath := filepath.Join(dataDir, "postgresql.conf")
	file, err := os.Open(configPath)
	if err != nil {
		return config
	}
	defer func() { _ = file.Close() }()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())

		// Skip comments and empty lines.
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		// Parse key = value format.
		idx := strings.Index(line, "=")
		if idx < 0 {
			continue
		}

		key := strings.TrimSpace(line[:idx])
		value := strings.TrimSpace(line[idx+1:])

		// Remove trailing comments.
		if commentIdx := strings.Index(value, "#"); commentIdx >= 0 {
			value = strings.TrimSpace(value[:commentIdx])
		}

		// Remove quotes.
		value = strings.Trim(value, "'\"")

		switch key {
		case "log_directory":
			config.LogDirectory = value
		case "log_filename":
			config.LogFilename = value
		case "port":
			if port, err := strconv.Atoi(value); err == nil {
				config.Port = port
			}
		case "log_destination":
			config.LogDestination = value
		case "logging_collector":
			config.LoggingCollector = value == "on" || value == "true" || value == "1"
		}
	}

	return config
}

// ReadPGVersion reads the PG_VERSION file and returns the PostgreSQL version.
// Returns an empty string if the file cannot be read.
func ReadPGVersion(dataDir string) string {
	versionPath := filepath.Join(dataDir, "PG_VERSION")
	data, err := os.ReadFile(versionPath)
	if err != nil {
		return ""
	}

	version := strings.TrimSpace(string(data))
	return version
}

// PostmasterInfo holds information parsed from postmaster.pid.
type PostmasterInfo struct {
	PID       int
	DataDir   string
	StartTime int64
	Port      int
	SocketDir string
	Host      string
	Cluster   string
}

// ParsePostmasterPID reads postmaster.pid and extracts process information.
// Returns nil if the file cannot be read or parsed.
func ParsePostmasterPID(dataDir string) *PostmasterInfo {
	pidPath := filepath.Join(dataDir, "postmaster.pid")
	file, err := os.Open(pidPath)
	if err != nil {
		return nil
	}
	defer func() { _ = file.Close() }()

	info := &PostmasterInfo{
		DataDir: dataDir,
	}

	scanner := bufio.NewScanner(file)
	lineNum := 0

	// postmaster.pid format:
	// Line 1: PID
	// Line 2: Data directory path
	// Line 3: Start timestamp
	// Line 4: Port number
	// Line 5: Socket directory (Unix) or empty (Windows)
	// Line 6: Hostname or empty
	// Line 7: Cluster name (optional)
	for scanner.Scan() {
		lineNum++
		line := strings.TrimSpace(scanner.Text())

		switch lineNum {
		case 1:
			if pid, err := strconv.Atoi(line); err == nil {
				info.PID = pid
			}
		case 2:
			info.DataDir = line
		case 3:
			if ts, err := strconv.ParseInt(line, 10, 64); err == nil {
				info.StartTime = ts
			}
		case 4:
			if port, err := strconv.Atoi(line); err == nil {
				info.Port = port
			}
		case 5:
			info.SocketDir = line
		case 6:
			info.Host = line
		case 7:
			info.Cluster = line
		}
	}

	// Verify we got at least the PID.
	if info.PID == 0 {
		return nil
	}

	return info
}

// ResolveLogDir resolves the log directory path.
// If logDir is relative, it's resolved against dataDir.
// Returns the resolved path or dataDir/log as default.
func ResolveLogDir(dataDir, logDir string) string {
	if logDir == "" {
		// Default log directory.
		return filepath.Join(dataDir, "log")
	}

	if filepath.IsAbs(logDir) {
		return logDir
	}

	return filepath.Join(dataDir, logDir)
}

// IsValidDataDir checks if a directory appears to be a valid PostgreSQL data directory.
// It checks for the presence of PG_VERSION file.
func IsValidDataDir(path string) bool {
	versionPath := filepath.Join(path, "PG_VERSION")
	info, err := os.Stat(versionPath)
	if err != nil {
		return false
	}
	return !info.IsDir()
}
