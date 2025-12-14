// Package instance provides PostgreSQL instance representation and detection sources.
package instance

// DetectionSource indicates how a PostgreSQL instance was discovered.
type DetectionSource int

const (
	// SourceProcess indicates the instance was found via a running postgres process.
	SourceProcess DetectionSource = iota
	// SourcePgrx indicates the instance was found in ~/.pgrx/data-*/.
	SourcePgrx
	// SourceEnvVar indicates the instance was found via PGDATA environment variable.
	SourceEnvVar
	// SourceKnownPath indicates the instance was found in platform-specific known paths.
	SourceKnownPath
	// SourceService indicates the instance was found via system service registration.
	SourceService
)

// String returns the display string for a DetectionSource.
func (s DetectionSource) String() string {
	switch s {
	case SourceProcess:
		return "process"
	case SourcePgrx:
		return "pgrx"
	case SourceEnvVar:
		return "env"
	case SourceKnownPath:
		return "path"
	case SourceService:
		return "service"
	default:
		return "unknown"
	}
}

// Instance represents a detected PostgreSQL installation.
type Instance struct {
	// DataDir is the absolute path to the data directory.
	DataDir string

	// Version is the PostgreSQL version (e.g., "16.1").
	Version string

	// Port is the listening port (0 if unknown).
	Port int

	// Running indicates whether postmaster is currently running.
	Running bool

	// LogDir is the resolved log directory path.
	LogDir string

	// LogPattern is the log filename pattern (e.g., "postgresql-%Y-%m-%d_%H%M%S.log").
	LogPattern string

	// Source indicates how this instance was detected.
	Source DetectionSource
}
