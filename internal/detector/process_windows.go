//go:build windows

// Package detector provides PostgreSQL instance detection functionality.
package detector

// Platform-specific process detection for Windows systems.
// Currently uses the shared gopsutil implementation which works on Windows.
// This file exists to allow for Windows-specific handling if needed.

// DetectFromProcessesWindows is a Windows-specific wrapper around DetectFromProcesses.
// On Windows, the process name may be "postgres.exe" instead of "postgres".
// gopsutil handles this transparently.
func DetectFromProcessesWindows() error {
	// The shared implementation in process.go handles Windows via gopsutil.
	// This function exists as a hook for future Windows-specific optimizations.
	return nil
}
