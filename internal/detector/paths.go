package detector

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

// ScanPgrxPaths scans for PostgreSQL data directories in ~/.pgrx/data-*/.
func ScanPgrxPaths() []string {
	var paths []string

	homeDir, err := os.UserHomeDir()
	if err != nil {
		return paths
	}

	pgrxDir := filepath.Join(homeDir, ".pgrx")

	entries, err := os.ReadDir(pgrxDir)
	if err != nil {
		return paths
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		name := entry.Name()
		if !strings.HasPrefix(name, "data-") {
			continue
		}

		dataPath := filepath.Join(pgrxDir, name)
		if IsValidDataDir(dataPath) {
			paths = append(paths, dataPath)
		}
	}

	return paths
}

// ScanPGDATA checks the PGDATA environment variable for a data directory.
func ScanPGDATA() []string {
	var paths []string

	pgdata := os.Getenv("PGDATA")
	if pgdata == "" {
		return paths
	}

	if IsValidDataDir(pgdata) {
		paths = append(paths, pgdata)
	}

	return paths
}

// ScanKnownPaths scans platform-specific known PostgreSQL installation paths.
func ScanKnownPaths() []string {
	switch runtime.GOOS {
	case "darwin":
		return scanMacOSPaths()
	case "linux":
		return scanLinuxPaths()
	case "windows":
		return scanWindowsPaths()
	default:
		return nil
	}
}

// scanMacOSPaths scans macOS-specific PostgreSQL paths.
func scanMacOSPaths() []string {
	var paths []string

	homeDir, _ := os.UserHomeDir()

	// Homebrew paths (ARM64 and Intel).
	homebrewPaths := []string{
		"/opt/homebrew/var/postgresql@17",
		"/opt/homebrew/var/postgresql@16",
		"/opt/homebrew/var/postgresql@15",
		"/opt/homebrew/var/postgresql@14",
		"/opt/homebrew/var/postgresql@13",
		"/opt/homebrew/var/postgres",
		"/usr/local/var/postgresql@17",
		"/usr/local/var/postgresql@16",
		"/usr/local/var/postgresql@15",
		"/usr/local/var/postgresql@14",
		"/usr/local/var/postgresql@13",
		"/usr/local/var/postgres",
	}

	for _, p := range homebrewPaths {
		if IsValidDataDir(p) {
			paths = append(paths, p)
		}
	}

	// Postgres.app paths.
	if homeDir != "" {
		postgresAppBase := filepath.Join(homeDir, "Library", "Application Support", "Postgres")
		entries, err := os.ReadDir(postgresAppBase)
		if err == nil {
			for _, entry := range entries {
				if entry.IsDir() && strings.HasPrefix(entry.Name(), "var-") {
					dataPath := filepath.Join(postgresAppBase, entry.Name())
					if IsValidDataDir(dataPath) {
						paths = append(paths, dataPath)
					}
				}
			}
		}
	}

	return paths
}

// scanLinuxPaths scans Linux-specific PostgreSQL paths.
func scanLinuxPaths() []string {
	var paths []string

	// Debian/Ubuntu paths.
	debianPaths := []string{
		"/var/lib/postgresql/17/main",
		"/var/lib/postgresql/16/main",
		"/var/lib/postgresql/15/main",
		"/var/lib/postgresql/14/main",
		"/var/lib/postgresql/13/main",
	}

	for _, p := range debianPaths {
		if IsValidDataDir(p) {
			paths = append(paths, p)
		}
	}

	// RHEL/CentOS paths.
	rhelPaths := []string{
		"/var/lib/pgsql/17/data",
		"/var/lib/pgsql/16/data",
		"/var/lib/pgsql/15/data",
		"/var/lib/pgsql/14/data",
		"/var/lib/pgsql/13/data",
		"/var/lib/pgsql/data",
	}

	for _, p := range rhelPaths {
		if IsValidDataDir(p) {
			paths = append(paths, p)
		}
	}

	// Also scan /etc/postgresql for config dirs that might point to data dirs.
	etcBase := "/etc/postgresql"
	entries, err := os.ReadDir(etcBase)
	if err == nil {
		for _, entry := range entries {
			if !entry.IsDir() {
				continue
			}
			// /etc/postgresql/16/main/ etc.
			subEntries, err := os.ReadDir(filepath.Join(etcBase, entry.Name()))
			if err != nil {
				continue
			}
			for _, subEntry := range subEntries {
				if subEntry.IsDir() {
					configPath := filepath.Join(etcBase, entry.Name(), subEntry.Name())
					// Check if postgresql.conf exists to read data_directory.
					confPath := filepath.Join(configPath, "postgresql.conf")
					if _, err := os.Stat(confPath); err == nil {
						// Try to read data_directory from config.
						config := ParsePostgresConfig(configPath)
						if config.LogDirectory != "" {
							// This means we found a config dir, check corresponding data dir.
							dataDir := filepath.Join("/var/lib/postgresql", entry.Name(), subEntry.Name())
							if IsValidDataDir(dataDir) {
								paths = append(paths, dataDir)
							}
						}
					}
				}
			}
		}
	}

	return paths
}

// scanWindowsPaths scans Windows-specific PostgreSQL paths.
func scanWindowsPaths() []string {
	var paths []string

	// Standard PostgreSQL installer paths.
	basePaths := []string{
		"C:\\Program Files\\PostgreSQL",
		"C:\\Program Files (x86)\\PostgreSQL",
	}

	// Also check PROGRAMDATA.
	programData := os.Getenv("PROGRAMDATA")
	if programData != "" {
		basePaths = append(basePaths, filepath.Join(programData, "PostgreSQL"))
	}

	// Also check user home for pgrx (Windows style).
	homeDir, _ := os.UserHomeDir()
	if homeDir != "" {
		pgrxDir := filepath.Join(homeDir, ".pgrx")
		entries, err := os.ReadDir(pgrxDir)
		if err == nil {
			for _, entry := range entries {
				if entry.IsDir() && strings.HasPrefix(entry.Name(), "data-") {
					dataPath := filepath.Join(pgrxDir, entry.Name())
					if IsValidDataDir(dataPath) {
						paths = append(paths, dataPath)
					}
				}
			}
		}
	}

	versions := []string{"17", "16", "15", "14", "13", "12", "11", "10"}

	for _, base := range basePaths {
		for _, ver := range versions {
			dataPath := filepath.Join(base, ver, "data")
			if IsValidDataDir(dataPath) {
				paths = append(paths, dataPath)
			}
		}
	}

	return paths
}

// GetSourceForPath returns the detection source type based on the path.
func GetSourceForPath(path string) string {
	homeDir, _ := os.UserHomeDir()

	// Check if it's a pgrx path.
	if homeDir != "" {
		pgrxDir := filepath.Join(homeDir, ".pgrx")
		if strings.HasPrefix(path, pgrxDir) {
			return "pgrx"
		}
	}

	// Check platform-specific paths.
	switch runtime.GOOS {
	case "darwin":
		if strings.Contains(path, "homebrew") || strings.Contains(path, "/usr/local/var") {
			return "brew"
		}
		if strings.Contains(path, "Application Support/Postgres") {
			return "app"
		}
	case "linux":
		if strings.HasPrefix(path, "/var/lib/postgresql") || strings.HasPrefix(path, "/var/lib/pgsql") {
			return "pkg"
		}
	case "windows":
		if strings.Contains(path, "Program Files") {
			return "installer"
		}
	}

	return "path"
}
