//go:build !windows

// Package detector provides PostgreSQL instance detection functionality.
package detector

// Platform-specific process detection for Unix systems.
// Currently uses the shared gopsutil implementation which works on Unix.
// This file exists to allow for Unix-specific optimizations if needed.

// DetectFromProcessesUnix is a Unix-specific wrapper around DetectFromProcesses.
// On Unix, we can potentially use more efficient methods like reading /proc directly,
// but gopsutil already handles this well.
func DetectFromProcessesUnix() error {
	// The shared implementation in process.go handles Unix via gopsutil.
	// This function exists as a hook for future Unix-specific optimizations.
	return nil
}
