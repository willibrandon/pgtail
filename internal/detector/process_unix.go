//go:build !windows

package detector

import (
	"os"
	"syscall"
)

// IsProcessRunning checks if a process with the given PID is running on Unix systems.
func IsProcessRunning(pid int) bool {
	if pid <= 0 {
		return false
	}

	proc, err := os.FindProcess(pid)
	if err != nil {
		return false
	}

	// On Unix, FindProcess always succeeds. Use Signal(0) to check if process exists.
	err = proc.Signal(syscall.Signal(0))
	return err == nil
}
