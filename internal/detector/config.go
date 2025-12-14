// Package detector provides PostgreSQL instance detection functionality.
package detector

import (
	"bufio"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// PostgresConfig holds parsed postgresql.conf values relevant to pgtail.
type PostgresConfig struct {
	// LogDirectory is the log_directory setting (may be relative or absolute).
	LogDirectory string

	// LogFilename is the log_filename pattern.
	LogFilename string

	// Port is the configured port number.
	Port int

	// LogDestination is the log_destination setting.
	LogDestination string
}

// ParsePostgresConfig reads and parses a postgresql.conf file.
// Returns parsed config and any error encountered.
func ParsePostgresConfig(dataDir string) (*PostgresConfig, error) {
	configPath := filepath.Join(dataDir, "postgresql.conf")
	file, err := os.Open(configPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	config := &PostgresConfig{
		Port: 5432, // default
	}

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())

		// Skip comments and empty lines
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		// Parse key = value
		idx := strings.Index(line, "=")
		if idx <= 0 {
			continue
		}

		key := strings.TrimSpace(line[:idx])
		value := strings.TrimSpace(line[idx+1:])

		// Remove inline comments
		if commentIdx := strings.Index(value, "#"); commentIdx > 0 {
			value = strings.TrimSpace(value[:commentIdx])
		}

		// Remove quotes
		value = strings.Trim(value, "'\"")

		switch key {
		case "log_directory":
			config.LogDirectory = value
		case "log_filename":
			config.LogFilename = value
		case "port":
			if p, err := strconv.Atoi(value); err == nil {
				config.Port = p
			}
		case "log_destination":
			config.LogDestination = value
		}
	}

	if err := scanner.Err(); err != nil {
		return config, err
	}

	return config, nil
}

// ResolveLogDir resolves the log directory path.
// If LogDirectory is relative, it's resolved against the data directory.
// If LogDirectory is empty, returns default log locations to check.
func (c *PostgresConfig) ResolveLogDir(dataDir string) string {
	if c.LogDirectory == "" {
		// Check default locations
		for _, dir := range []string{"log", "pg_log"} {
			path := filepath.Join(dataDir, dir)
			if info, err := os.Stat(path); err == nil && info.IsDir() {
				return path
			}
		}
		return ""
	}

	if filepath.IsAbs(c.LogDirectory) {
		return c.LogDirectory
	}

	return filepath.Join(dataDir, c.LogDirectory)
}

// ReadPGVersion reads the PostgreSQL version from PG_VERSION file.
func ReadPGVersion(dataDir string) (string, error) {
	versionPath := filepath.Join(dataDir, "PG_VERSION")
	data, err := os.ReadFile(versionPath)
	if err != nil {
		return "", err
	}

	version := strings.TrimSpace(string(data))
	return version, nil
}

// PostmasterInfo holds parsed postmaster.pid information.
type PostmasterInfo struct {
	// PID is the postmaster process ID.
	PID int

	// DataDir is the data directory path.
	DataDir string

	// Port is the listening port.
	Port int

	// SocketDir is the Unix socket directory.
	SocketDir string
}

// ParsePostmasterPID reads and parses the postmaster.pid file.
// The file format is:
//
//	Line 1: PID
//	Line 2: Data directory
//	Line 3: Start timestamp
//	Line 4: Port
//	Line 5: Socket directory
//	Line 6: Listen addresses
//	Line 7: Shared memory key (older versions)
func ParsePostmasterPID(dataDir string) (*PostmasterInfo, error) {
	pidPath := filepath.Join(dataDir, "postmaster.pid")
	file, err := os.Open(pidPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	info := &PostmasterInfo{}
	scanner := bufio.NewScanner(file)
	lineNum := 0

	for scanner.Scan() {
		lineNum++
		line := strings.TrimSpace(scanner.Text())

		switch lineNum {
		case 1: // PID
			if pid, err := strconv.Atoi(line); err == nil {
				info.PID = pid
			}
		case 2: // Data directory
			info.DataDir = line
		case 4: // Port
			if port, err := strconv.Atoi(line); err == nil {
				info.Port = port
			}
		case 5: // Socket directory
			info.SocketDir = line
		}

		if lineNum >= 5 {
			break
		}
	}

	if err := scanner.Err(); err != nil {
		return info, err
	}

	return info, nil
}

// IsValidDataDir checks if a directory is a valid PostgreSQL data directory.
// A valid data directory contains at least a PG_VERSION file.
func IsValidDataDir(path string) bool {
	versionPath := filepath.Join(path, "PG_VERSION")
	_, err := os.Stat(versionPath)
	return err == nil
}
