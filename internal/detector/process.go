// Package detector provides PostgreSQL instance detection functionality.
package detector

import (
	"strings"

	"github.com/shirou/gopsutil/v3/process"
	"github.com/willibrandon/pgtail/internal/instance"
)

// DetectFromProcesses finds PostgreSQL instances by scanning running processes.
// Returns a slice of instances found and any errors encountered.
func DetectFromProcesses() ([]*instance.Instance, []error) {
	var instances []*instance.Instance
	var errors []error

	procs, err := process.Processes()
	if err != nil {
		return nil, []error{err}
	}

	for _, p := range procs {
		inst, err := checkProcess(p)
		if err != nil {
			// Silently skip processes we can't inspect
			continue
		}
		if inst != nil {
			instances = append(instances, inst)
		}
	}

	return instances, errors
}

// checkProcess examines a single process to see if it's a PostgreSQL postmaster.
func checkProcess(p *process.Process) (*instance.Instance, error) {
	name, err := p.Name()
	if err != nil {
		return nil, err
	}

	// Check if this is a postgres process
	nameLower := strings.ToLower(name)
	if !strings.Contains(nameLower, "postgres") {
		return nil, nil
	}

	// Get command line to extract data directory
	cmdline, err := p.Cmdline()
	if err != nil {
		return nil, err
	}

	dataDir := extractDataDir(cmdline)
	if dataDir == "" {
		return nil, nil
	}

	// Validate it's a real data directory
	if !IsValidDataDir(dataDir) {
		return nil, nil
	}

	// Read version
	version, err := ReadPGVersion(dataDir)
	if err != nil {
		return nil, err
	}

	// Parse config for additional info
	config, _ := ParsePostgresConfig(dataDir)

	inst := &instance.Instance{
		DataDir: dataDir,
		Version: version,
		Running: true,
		Source:  instance.SourceProcess,
	}

	if config != nil {
		inst.Port = config.Port
		inst.LogDir = config.ResolveLogDir(dataDir)
		inst.LogPattern = config.LogFilename
	}

	// Try to get port from postmaster.pid if not in config
	if inst.Port == 0 {
		if pmInfo, err := ParsePostmasterPID(dataDir); err == nil && pmInfo.Port > 0 {
			inst.Port = pmInfo.Port
		}
	}

	return inst, nil
}

// extractDataDir extracts the -D data directory argument from a command line.
func extractDataDir(cmdline string) string {
	// Split on whitespace
	parts := strings.Fields(cmdline)

	for i, part := range parts {
		// Check for -D flag
		if part == "-D" && i+1 < len(parts) {
			return parts[i+1]
		}
		// Check for --pgdata or --data-dir
		if strings.HasPrefix(part, "--pgdata=") {
			return strings.TrimPrefix(part, "--pgdata=")
		}
		if strings.HasPrefix(part, "-D") && len(part) > 2 {
			return part[2:]
		}
	}

	return ""
}
