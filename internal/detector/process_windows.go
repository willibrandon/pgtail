//go:build windows

package detector

import (
	"github.com/shirou/gopsutil/v3/process"
)

// IsProcessRunning checks if a process with the given PID is running on Windows.
func IsProcessRunning(pid int) bool {
	if pid <= 0 {
		return false
	}

	exists, err := process.PidExists(int32(pid))
	if err != nil {
		return false
	}
	return exists
}
