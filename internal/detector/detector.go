package detector

import (
	"path/filepath"
	"strings"

	"github.com/willibrandon/pgtail/internal/instance"
)

// DetectionResult holds the results of instance detection.
type DetectionResult struct {
	Instances []*instance.Instance
	Errors    []DetectionError
}

// DetectionError represents an error that occurred during detection.
type DetectionError struct {
	Source  string
	Path    string
	Message string
}

// DetectInstances scans for all PostgreSQL instances using multiple detection methods.
// Detection priority order:
// 1. Running processes (highest confidence)
// 2. pgrx directories (~/.pgrx/data-*)
// 3. PGDATA environment variable
// 4. Platform-specific known paths
//
// Instances are deduplicated by normalized data directory path.
func DetectInstances() DetectionResult {
	result := DetectionResult{
		Instances: make([]*instance.Instance, 0),
		Errors:    make([]DetectionError, 0),
	}

	seen := make(map[string]bool)

	// 1. Running processes (highest priority).
	processInstances := detectFromProcesses()
	for _, inst := range processInstances {
		normalizedPath := normalizePath(inst.DataDir)
		if !seen[normalizedPath] {
			seen[normalizedPath] = true
			result.Instances = append(result.Instances, inst)
		}
	}

	// 2. pgrx directories.
	pgrxPaths := ScanPgrxPaths()
	for _, path := range pgrxPaths {
		normalizedPath := normalizePath(path)
		if seen[normalizedPath] {
			continue
		}

		inst := buildInstance(path, instance.SourcePgrx)
		if inst != nil {
			seen[normalizedPath] = true
			result.Instances = append(result.Instances, inst)
		}
	}

	// 3. PGDATA environment variable.
	pgdataPaths := ScanPGDATA()
	for _, path := range pgdataPaths {
		normalizedPath := normalizePath(path)
		if seen[normalizedPath] {
			continue
		}

		inst := buildInstance(path, instance.SourceEnvVar)
		if inst != nil {
			seen[normalizedPath] = true
			result.Instances = append(result.Instances, inst)
		}
	}

	// 4. Platform-specific known paths.
	knownPaths := ScanKnownPaths()
	for _, path := range knownPaths {
		normalizedPath := normalizePath(path)
		if seen[normalizedPath] {
			continue
		}

		inst := buildInstance(path, instance.SourceKnownPath)
		if inst != nil {
			seen[normalizedPath] = true
			result.Instances = append(result.Instances, inst)
		}
	}

	return result
}

// detectFromProcesses detects instances from running postgres processes.
func detectFromProcesses() []*instance.Instance {
	var instances []*instance.Instance

	processInfos := FindRunningPostgres()
	for _, pinfo := range processInfos {
		if !IsValidDataDir(pinfo.DataDir) {
			continue
		}

		inst := buildInstance(pinfo.DataDir, instance.SourceProcess)
		if inst != nil {
			inst.Running = true
			instances = append(instances, inst)
		}
	}

	return instances
}

// buildInstance creates an Instance from a data directory path.
// Returns nil if the directory is not a valid PostgreSQL data directory.
func buildInstance(dataDir string, source instance.DetectionSource) *instance.Instance {
	if !IsValidDataDir(dataDir) {
		return nil
	}

	// Read version.
	version := ReadPGVersion(dataDir)
	if version == "" {
		return nil
	}

	// Parse config.
	config := ParsePostgresConfig(dataDir)

	// Resolve log directory.
	logDir := ResolveLogDir(dataDir, config.LogDirectory)

	// Check if running via postmaster.pid.
	running := false
	port := config.Port
	pmInfo := ParsePostmasterPID(dataDir)
	if pmInfo != nil {
		if IsProcessRunning(pmInfo.PID) {
			running = true
			if pmInfo.Port > 0 {
				port = pmInfo.Port
			}
		}
	}

	return &instance.Instance{
		DataDir:        dataDir,
		Version:        version,
		Port:           port,
		Running:        running,
		LogDir:         logDir,
		LogPattern:     config.LogFilename,
		Source:         source,
		LoggingEnabled: config.LoggingCollector,
	}
}

// normalizePath normalizes a path for deduplication.
// Converts to absolute path, cleans it, and lowercases on case-insensitive filesystems.
func normalizePath(path string) string {
	// Convert to absolute path.
	absPath, err := filepath.Abs(path)
	if err != nil {
		absPath = path
	}

	// Clean the path.
	absPath = filepath.Clean(absPath)

	// On macOS and Windows, paths are case-insensitive by default.
	// Lowercase for comparison.
	// Note: This is a simplification; some mounted filesystems may be case-sensitive.
	absPath = strings.ToLower(absPath)

	return absPath
}

// Refresh re-detects all instances.
// This is a convenience function that wraps DetectInstances.
func Refresh() DetectionResult {
	return DetectInstances()
}
