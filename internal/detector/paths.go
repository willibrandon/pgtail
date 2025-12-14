// Package detector provides PostgreSQL instance detection functionality.
package detector

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/willibrandon/pgtail/internal/instance"
)

// DetectFromPgrx finds PostgreSQL instances in ~/.pgrx/data-*/ directories.
// These are created by the pgrx framework for PostgreSQL extension development.
func DetectFromPgrx() ([]*instance.Instance, []error) {
	var instances []*instance.Instance
	var errors []error

	homeDir, err := os.UserHomeDir()
	if err != nil {
		return nil, []error{err}
	}

	pgrxDir := filepath.Join(homeDir, ".pgrx")

	// Check if .pgrx directory exists
	info, err := os.Stat(pgrxDir)
	if err != nil || !info.IsDir() {
		return nil, nil
	}

	// Look for data-* directories
	entries, err := os.ReadDir(pgrxDir)
	if err != nil {
		return nil, []error{err}
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		name := entry.Name()
		if !strings.HasPrefix(name, "data-") {
			continue
		}

		dataDir := filepath.Join(pgrxDir, name)
		if !IsValidDataDir(dataDir) {
			continue
		}

		inst, err := instanceFromDataDir(dataDir, instance.SourcePgrx, "pgrx")
		if err != nil {
			errors = append(errors, err)
			continue
		}

		instances = append(instances, inst)
	}

	return instances, errors
}

// DetectFromKnownPaths finds PostgreSQL instances in platform-specific known locations.
func DetectFromKnownPaths() ([]*instance.Instance, []error) {
	var instances []*instance.Instance
	var errors []error

	paths := getKnownPaths()

	for _, pathInfo := range paths {
		// Expand glob patterns
		matches, err := filepath.Glob(pathInfo.Pattern)
		if err != nil {
			errors = append(errors, err)
			continue
		}

		for _, match := range matches {
			if !IsValidDataDir(match) {
				continue
			}

			inst, err := instanceFromDataDir(match, instance.SourceKnownPath, pathInfo.SourceDetail)
			if err != nil {
				errors = append(errors, err)
				continue
			}

			instances = append(instances, inst)
		}
	}

	return instances, errors
}

// DetectFromEnvVar finds a PostgreSQL instance from the PGDATA environment variable.
func DetectFromEnvVar() (*instance.Instance, error) {
	pgdata := os.Getenv("PGDATA")
	if pgdata == "" {
		return nil, nil
	}

	// Expand ~ if present
	if strings.HasPrefix(pgdata, "~") {
		homeDir, err := os.UserHomeDir()
		if err != nil {
			return nil, err
		}
		pgdata = filepath.Join(homeDir, pgdata[1:])
	}

	if !IsValidDataDir(pgdata) {
		return nil, nil
	}

	return instanceFromDataDir(pgdata, instance.SourceEnvVar, "env")
}

// PathInfo describes a known PostgreSQL installation path pattern.
type PathInfo struct {
	// Pattern is a glob pattern to match data directories.
	Pattern string

	// SourceDetail is the display name for this source (e.g., "brew", "apt").
	SourceDetail string
}

// getKnownPaths returns platform-specific known PostgreSQL installation paths.
func getKnownPaths() []PathInfo {
	switch runtime.GOOS {
	case "darwin":
		return getDarwinPaths()
	case "linux":
		return getLinuxPaths()
	case "windows":
		return getWindowsPaths()
	default:
		return nil
	}
}

// getDarwinPaths returns macOS-specific PostgreSQL paths.
func getDarwinPaths() []PathInfo {
	homeDir, _ := os.UserHomeDir()

	paths := []PathInfo{
		// Homebrew on Apple Silicon
		{Pattern: "/opt/homebrew/var/postgresql@*/", SourceDetail: "brew"},
		{Pattern: "/opt/homebrew/var/postgres/", SourceDetail: "brew"},

		// Homebrew on Intel
		{Pattern: "/usr/local/var/postgresql@*/", SourceDetail: "brew"},
		{Pattern: "/usr/local/var/postgres/", SourceDetail: "brew"},
	}

	// Postgres.app
	if homeDir != "" {
		paths = append(paths, PathInfo{
			Pattern:      filepath.Join(homeDir, "Library/Application Support/Postgres/var-*"),
			SourceDetail: "app",
		})
	}

	return paths
}

// getLinuxPaths returns Linux-specific PostgreSQL paths.
func getLinuxPaths() []PathInfo {
	return []PathInfo{
		// Debian/Ubuntu
		{Pattern: "/var/lib/postgresql/*/main", SourceDetail: "apt"},
		{Pattern: "/etc/postgresql/*/main", SourceDetail: "apt"},

		// RHEL/CentOS
		{Pattern: "/var/lib/pgsql/*/data", SourceDetail: "yum"},
		{Pattern: "/var/lib/pgsql/data", SourceDetail: "yum"},
	}
}

// getWindowsPaths returns Windows-specific PostgreSQL paths.
func getWindowsPaths() []PathInfo {
	programData := os.Getenv("PROGRAMDATA")
	if programData == "" {
		programData = "C:\\ProgramData"
	}

	return []PathInfo{
		// Standard installer locations
		{Pattern: "C:\\Program Files\\PostgreSQL\\*\\data", SourceDetail: "installer"},
		{Pattern: "C:\\Program Files (x86)\\PostgreSQL\\*\\data", SourceDetail: "installer"},
		{Pattern: filepath.Join(programData, "PostgreSQL\\*\\data"), SourceDetail: "installer"},
	}
}

// instanceFromDataDir creates an Instance from a data directory path.
func instanceFromDataDir(dataDir string, source instance.DetectionSource, sourceDetail string) (*instance.Instance, error) {
	version, err := ReadPGVersion(dataDir)
	if err != nil {
		return nil, err
	}

	inst := &instance.Instance{
		DataDir:      dataDir,
		Version:      version,
		Source:       source,
		SourceDetail: sourceDetail,
	}

	// Parse config for additional info
	config, _ := ParsePostgresConfig(dataDir)
	if config != nil {
		inst.Port = config.Port
		inst.LogDir = config.ResolveLogDir(dataDir)
		inst.LogPattern = config.LogFilename
	}

	// Check if running by looking for postmaster.pid
	if pmInfo, err := ParsePostmasterPID(dataDir); err == nil {
		inst.Running = pmInfo.PID > 0 && isProcessRunning(pmInfo.PID)
		if pmInfo.Port > 0 {
			inst.Port = pmInfo.Port
		}
	}

	return inst, nil
}

// isProcessRunning checks if a process with the given PID exists.
func isProcessRunning(pid int) bool {
	proc, err := os.FindProcess(pid)
	if err != nil {
		return false
	}

	// On Unix, FindProcess always succeeds. We need to send signal 0 to check.
	// On Windows, FindProcess returns an error if the process doesn't exist.
	if runtime.GOOS == "windows" {
		return true
	}

	// Send signal 0 to check if process exists
	err = proc.Signal(nil)
	return err == nil
}
