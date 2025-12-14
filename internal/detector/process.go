package detector

import (
	"strings"

	"github.com/shirou/gopsutil/v3/process"
)

// ProcessInfo holds information about a running PostgreSQL process.
type ProcessInfo struct {
	PID     int32
	DataDir string
	Cmdline string
}

// FindRunningPostgres finds all running PostgreSQL processes and extracts their data directories.
func FindRunningPostgres() []ProcessInfo {
	var results []ProcessInfo

	procs, err := process.Processes()
	if err != nil {
		return results
	}

	for _, p := range procs {
		name, err := p.Name()
		if err != nil {
			continue
		}

		// Look for postgres or postmaster processes.
		nameLower := strings.ToLower(name)
		if !strings.Contains(nameLower, "postgres") && !strings.Contains(nameLower, "postmaster") {
			continue
		}

		// Get command line to extract -D flag.
		cmdline, err := p.Cmdline()
		if err != nil {
			continue
		}

		// Extract data directory from command line.
		dataDir := extractDataDir(cmdline)
		if dataDir == "" {
			continue
		}

		results = append(results, ProcessInfo{
			PID:     p.Pid,
			DataDir: dataDir,
			Cmdline: cmdline,
		})
	}

	return results
}

// extractDataDir extracts the -D data directory path from a postgres command line.
func extractDataDir(cmdline string) string {
	// Split by spaces, handling quoted paths.
	args := splitCommandLine(cmdline)

	for i, arg := range args {
		if arg == "-D" && i+1 < len(args) {
			return args[i+1]
		}
		if strings.HasPrefix(arg, "-D") {
			// Handle -D/path/to/data format.
			return strings.TrimPrefix(arg, "-D")
		}
		// Some systems use --data or PGDATA in cmdline.
		if arg == "--data" && i+1 < len(args) {
			return args[i+1]
		}
		if strings.HasPrefix(arg, "--data=") {
			return strings.TrimPrefix(arg, "--data=")
		}
	}

	return ""
}

// splitCommandLine splits a command line string into arguments.
// Handles quoted strings.
func splitCommandLine(cmdline string) []string {
	var args []string
	var current strings.Builder
	inQuote := false
	quoteChar := rune(0)

	for _, r := range cmdline {
		switch {
		case r == '"' || r == '\'':
			if inQuote && r == quoteChar {
				inQuote = false
				quoteChar = 0
			} else if !inQuote {
				inQuote = true
				quoteChar = r
			} else {
				current.WriteRune(r)
			}
		case r == ' ' || r == '\t':
			if inQuote {
				current.WriteRune(r)
			} else if current.Len() > 0 {
				args = append(args, current.String())
				current.Reset()
			}
		default:
			current.WriteRune(r)
		}
	}

	if current.Len() > 0 {
		args = append(args, current.String())
	}

	return args
}
