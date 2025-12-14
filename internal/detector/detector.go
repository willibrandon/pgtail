// Package detector provides PostgreSQL instance detection functionality.
package detector

import (
	"path/filepath"
	"runtime"
	"strings"

	"github.com/willibrandon/pgtail/internal/instance"
)

// DetectionResult holds the results of a detection scan.
type DetectionResult struct {
	// Instances is the list of unique detected instances.
	Instances []*instance.Instance

	// Errors contains any errors encountered during detection.
	// Detection continues even when individual sources fail.
	Errors []error

	// SkippedSources lists detection sources that were skipped due to errors.
	SkippedSources []string
}

// Detect scans for PostgreSQL instances using all available detection methods.
// Detection sources are tried in priority order:
//  1. Running processes (highest confidence)
//  2. pgrx directories (~/.pgrx/data-*)
//  3. PGDATA environment variable
//  4. Platform-specific known paths
//
// Instances are deduplicated by normalized data directory path.
// Errors are collected but do not stop detection from other sources.
func Detect() *DetectionResult {
	result := &DetectionResult{
		Instances: make([]*instance.Instance, 0),
	}

	seen := make(map[string]bool)

	// 1. Running processes (highest priority)
	if processInstances, errs := DetectFromProcesses(); errs != nil {
		for _, err := range errs {
			result.Errors = append(result.Errors, err)
		}
		result.SkippedSources = append(result.SkippedSources, "processes")
	} else {
		for _, inst := range processInstances {
			key := normalizeDataDir(inst.DataDir)
			if !seen[key] {
				seen[key] = true
				result.Instances = append(result.Instances, inst)
			}
		}
	}

	// 2. pgrx directories
	if pgrxInstances, errs := DetectFromPgrx(); errs != nil {
		for _, err := range errs {
			result.Errors = append(result.Errors, err)
		}
		result.SkippedSources = append(result.SkippedSources, "pgrx")
	} else {
		for _, inst := range pgrxInstances {
			key := normalizeDataDir(inst.DataDir)
			if !seen[key] {
				seen[key] = true
				result.Instances = append(result.Instances, inst)
			}
		}
	}

	// 3. PGDATA environment variable
	if envInst, err := DetectFromEnvVar(); err != nil {
		result.Errors = append(result.Errors, err)
		result.SkippedSources = append(result.SkippedSources, "PGDATA")
	} else if envInst != nil {
		key := normalizeDataDir(envInst.DataDir)
		if !seen[key] {
			seen[key] = true
			result.Instances = append(result.Instances, envInst)
		}
	}

	// 4. Known paths
	if knownInstances, errs := DetectFromKnownPaths(); errs != nil {
		for _, err := range errs {
			result.Errors = append(result.Errors, err)
		}
		result.SkippedSources = append(result.SkippedSources, "known paths")
	} else {
		for _, inst := range knownInstances {
			key := normalizeDataDir(inst.DataDir)
			if !seen[key] {
				seen[key] = true
				result.Instances = append(result.Instances, inst)
			}
		}
	}

	return result
}

// normalizeDataDir normalizes a data directory path for deduplication.
// - Converts to absolute path
// - Cleans the path (removes ., .., trailing slashes)
// - On case-insensitive filesystems, converts to lowercase
func normalizeDataDir(path string) string {
	// Convert to absolute path
	absPath, err := filepath.Abs(path)
	if err != nil {
		absPath = path
	}

	// Clean the path
	absPath = filepath.Clean(absPath)

	// On macOS and Windows (typically case-insensitive), normalize to lowercase
	if runtime.GOOS == "darwin" || runtime.GOOS == "windows" {
		absPath = strings.ToLower(absPath)
	}

	return absPath
}

// HasErrors returns true if any errors occurred during detection.
func (r *DetectionResult) HasErrors() bool {
	return len(r.Errors) > 0
}

// InstanceCount returns the number of detected instances.
func (r *DetectionResult) InstanceCount() int {
	return len(r.Instances)
}
