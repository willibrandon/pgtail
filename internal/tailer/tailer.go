package tailer

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"time"

	"github.com/fsnotify/fsnotify"
)

// Tailer watches a PostgreSQL log file and streams new entries.
type Tailer struct {
	logDir     string
	logPattern string
	filter     *Filter

	// Output channel for log entries.
	entries chan LogEntry

	// Error channel for reporting issues.
	errors chan error

	// Current file being tailed.
	currentFile *os.File
	currentPath string

	// Watcher for file changes.
	watcher *fsnotify.Watcher

	// Polling interval for fallback mode.
	pollInterval time.Duration

	// useFsnotify indicates whether to use fsnotify or polling.
	useFsnotify bool
}

// TailerConfig holds configuration for creating a Tailer.
type TailerConfig struct {
	LogDir       string
	LogPattern   string
	Filter       *Filter
	PollInterval time.Duration
}

// NewTailer creates a new Tailer for the given configuration.
func NewTailer(cfg TailerConfig) (*Tailer, error) {
	if cfg.LogDir == "" {
		return nil, fmt.Errorf("log directory is required")
	}

	// Check if log directory exists.
	info, err := os.Stat(cfg.LogDir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("log directory does not exist: %s", cfg.LogDir)
		}
		return nil, fmt.Errorf("cannot access log directory: %w", err)
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("log path is not a directory: %s", cfg.LogDir)
	}

	pollInterval := cfg.PollInterval
	if pollInterval == 0 {
		pollInterval = 500 * time.Millisecond
	}

	t := &Tailer{
		logDir:       cfg.LogDir,
		logPattern:   cfg.LogPattern,
		filter:       cfg.Filter,
		entries:      make(chan LogEntry, 100),
		errors:       make(chan error, 10),
		pollInterval: pollInterval,
		useFsnotify:  runtime.GOOS != "windows", // Use polling on Windows
	}

	// Try to create fsnotify watcher (only on non-Windows).
	if t.useFsnotify {
		watcher, err := fsnotify.NewWatcher()
		if err != nil {
			// Fallback to polling if fsnotify fails.
			t.useFsnotify = false
		} else {
			t.watcher = watcher
		}
	}

	return t, nil
}

// Entries returns the channel for receiving log entries.
func (t *Tailer) Entries() <-chan LogEntry {
	return t.entries
}

// Errors returns the channel for receiving errors.
func (t *Tailer) Errors() <-chan error {
	return t.errors
}

// Start begins tailing the log file. It runs until the context is cancelled.
func (t *Tailer) Start(ctx context.Context) error {
	// Find the most recent log file.
	logFile, err := t.findMostRecentLogFile()
	if err != nil {
		return err
	}

	// Open the file.
	t.currentPath = logFile
	t.currentFile, err = os.Open(logFile)
	if err != nil {
		return fmt.Errorf("cannot open log file: %w", err)
	}

	// Seek to end of file to only show new entries.
	_, err = t.currentFile.Seek(0, io.SeekEnd)
	if err != nil {
		_ = t.currentFile.Close()
		return fmt.Errorf("cannot seek to end of file: %w", err)
	}

	// Start the appropriate tailing method.
	if t.useFsnotify {
		go t.tailWithFsnotify(ctx)
	} else {
		go t.tailWithPolling(ctx)
	}

	return nil
}

// Stop stops the tailer and cleans up resources.
func (t *Tailer) Stop() {
	if t.currentFile != nil {
		_ = t.currentFile.Close()
		t.currentFile = nil
	}
	if t.watcher != nil {
		_ = t.watcher.Close()
		t.watcher = nil
	}
	close(t.entries)
	close(t.errors)
}

// CurrentFile returns the path of the currently tailed file.
func (t *Tailer) CurrentFile() string {
	return t.currentPath
}

// findMostRecentLogFile finds the most recently modified log file matching the pattern.
func (t *Tailer) findMostRecentLogFile() (string, error) {
	pattern := t.logPattern
	if pattern == "" {
		// Default PostgreSQL log pattern.
		pattern = "postgresql-*.log"
	}

	// Convert PostgreSQL strftime pattern to glob pattern.
	globPattern := convertLogPatternToGlob(pattern)
	searchPath := filepath.Join(t.logDir, globPattern)

	matches, err := filepath.Glob(searchPath)
	if err != nil {
		return "", fmt.Errorf("invalid log pattern: %w", err)
	}

	if len(matches) == 0 {
		// Try some common alternative patterns.
		alternatives := []string{
			filepath.Join(t.logDir, "postgresql-*.log"),
			filepath.Join(t.logDir, "postgres-*.log"),
			filepath.Join(t.logDir, "*.log"),
		}
		for _, alt := range alternatives {
			matches, err = filepath.Glob(alt)
			if err == nil && len(matches) > 0 {
				break
			}
		}
	}

	if len(matches) == 0 {
		return "", fmt.Errorf("no log files found in %s", t.logDir)
	}

	// Sort by modification time (most recent first).
	type fileInfo struct {
		path    string
		modTime time.Time
	}
	files := make([]fileInfo, 0, len(matches))
	for _, path := range matches {
		info, err := os.Stat(path)
		if err != nil {
			continue
		}
		if info.IsDir() {
			continue
		}
		files = append(files, fileInfo{path: path, modTime: info.ModTime()})
	}

	if len(files) == 0 {
		return "", fmt.Errorf("no readable log files found in %s", t.logDir)
	}

	sort.Slice(files, func(i, j int) bool {
		return files[i].modTime.After(files[j].modTime)
	})

	return files[0].path, nil
}

// convertLogPatternToGlob converts PostgreSQL log_filename strftime patterns to glob patterns.
func convertLogPatternToGlob(pattern string) string {
	// PostgreSQL uses strftime patterns like %Y-%m-%d_%H%M%S
	// Convert to glob wildcards.
	replacements := map[string]string{
		"%Y": "????", // 4-digit year
		"%m": "??",   // 2-digit month
		"%d": "??",   // 2-digit day
		"%H": "??",   // 2-digit hour
		"%M": "??",   // 2-digit minute
		"%S": "??",   // 2-digit second
		"%j": "???",  // 3-digit day of year
		"%W": "??",   // 2-digit week number
		"%w": "?",    // 1-digit day of week
		"%a": "???",  // abbreviated weekday name
		"%A": "*",    // full weekday name
		"%b": "???",  // abbreviated month name
		"%B": "*",    // full month name
	}

	result := pattern
	for from, to := range replacements {
		result = strings.ReplaceAll(result, from, to)
	}
	// Replace any remaining % sequences with wildcard.
	for strings.Contains(result, "%") {
		idx := strings.Index(result, "%")
		if idx >= 0 && idx+1 < len(result) {
			result = result[:idx] + "*" + result[idx+2:]
		} else {
			break
		}
	}

	return result
}

// tailWithFsnotify tails the file using fsnotify for file change notifications.
func (t *Tailer) tailWithFsnotify(ctx context.Context) {
	defer t.cleanup()

	// Watch the log directory for changes.
	err := t.watcher.Add(t.logDir)
	if err != nil {
		// Fall back to polling.
		t.tailWithPolling(ctx)
		return
	}

	reader := bufio.NewReader(t.currentFile)

	for {
		select {
		case <-ctx.Done():
			return
		case event, ok := <-t.watcher.Events:
			if !ok {
				return
			}
			// Check if this is a write to our file or a new log file.
			// Use case-insensitive comparison for Windows compatibility.
			if event.Has(fsnotify.Write) && pathsEqual(event.Name, t.currentPath) {
				t.readNewLines(reader)
			} else if event.Has(fsnotify.Create) && isLogFile(event.Name) {
				// A new log file was created; switch to it.
				t.switchToNewFile(event.Name, reader)
			}
		case err, ok := <-t.watcher.Errors:
			if !ok {
				return
			}
			select {
			case t.errors <- err:
			default:
			}
		}
	}
}

// tailWithPolling tails the file using periodic polling.
func (t *Tailer) tailWithPolling(ctx context.Context) {
	defer t.cleanup()

	reader := bufio.NewReader(t.currentFile)
	ticker := time.NewTicker(t.pollInterval)
	defer ticker.Stop()

	// Track file stats for rotation detection.
	lastStat, _ := t.currentFile.Stat()
	lastSize := int64(0)
	if lastStat != nil {
		lastSize = lastStat.Size()
	}

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			// Check for file rotation.
			newStat, err := os.Stat(t.currentPath)
			if err != nil || newStat.Size() < lastSize {
				// File was rotated; try to find the new log file.
				newFile, err := t.findMostRecentLogFile()
				if err == nil && newFile != t.currentPath {
					t.switchToNewFile(newFile, reader)
				}
			}
			if newStat != nil {
				lastSize = newStat.Size()
			}

			// Read new lines.
			t.readNewLines(reader)
		}
	}
}

// readNewLines reads and processes any new lines from the current file.
func (t *Tailer) readNewLines(reader *bufio.Reader) {
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			if err != io.EOF {
				select {
				case t.errors <- err:
				default:
				}
			}
			return
		}

		// Trim newline.
		line = strings.TrimRight(line, "\n\r")
		if line == "" {
			continue
		}

		// Parse the log line.
		entry := ParseLogLine(line)

		// Apply filter.
		if t.filter != nil && !t.filter.Allow(entry.Level) {
			continue
		}

		// Send to channel.
		select {
		case t.entries <- entry:
		default:
			// Channel full; drop oldest entry.
			select {
			case <-t.entries:
			default:
			}
			select {
			case t.entries <- entry:
			default:
			}
		}
	}
}

// switchToNewFile switches to tailing a new log file.
func (t *Tailer) switchToNewFile(newPath string, reader *bufio.Reader) {
	// Read remaining lines from current file.
	t.readNewLines(reader)

	// Close current file.
	if t.currentFile != nil {
		_ = t.currentFile.Close()
	}

	// Open new file.
	newFile, err := os.Open(newPath)
	if err != nil {
		select {
		case t.errors <- fmt.Errorf("cannot open new log file: %w", err):
		default:
		}
		return
	}

	t.currentFile = newFile
	t.currentPath = newPath

	// Reset reader for new file.
	reader.Reset(newFile)
}

// cleanup releases resources.
func (t *Tailer) cleanup() {
	if t.currentFile != nil {
		_ = t.currentFile.Close()
		t.currentFile = nil
	}
}

// isLogFile checks if a file path looks like a PostgreSQL log file.
func isLogFile(path string) bool {
	base := filepath.Base(path)
	return strings.HasSuffix(base, ".log") &&
		(strings.HasPrefix(base, "postgresql") || strings.HasPrefix(base, "postgres"))
}

// pathsEqual compares two file paths for equality.
// On Windows, this is case-insensitive and normalizes path separators.
func pathsEqual(a, b string) bool {
	// Clean and normalize paths.
	a = filepath.Clean(a)
	b = filepath.Clean(b)

	// Case-insensitive comparison for Windows.
	return strings.EqualFold(a, b)
}

// ResolveLogFile resolves the log file path for an instance.
// Returns the path and any error encountered.
func ResolveLogFile(logDir, logPattern string) (string, error) {
	cfg := TailerConfig{
		LogDir:     logDir,
		LogPattern: logPattern,
	}

	t, err := NewTailer(cfg)
	if err != nil {
		return "", err
	}

	logFile, err := t.findMostRecentLogFile()
	if err != nil {
		return "", err
	}

	return logFile, nil
}
