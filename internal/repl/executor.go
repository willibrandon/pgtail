// Package repl provides the interactive REPL for pgtail.
package repl

import (
	"context"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/willibrandon/pgtail/internal/detector"
	"github.com/willibrandon/pgtail/internal/instance"
	"github.com/willibrandon/pgtail/internal/tailer"
	"github.com/willibrandon/pgtail/internal/ui"
)

// AppState represents the runtime state for the REPL session.
type AppState struct {
	// Instances is the list of detected PostgreSQL instances (indexed 0-N).
	Instances []*instance.Instance

	// CurrentIndex is the selected instance index (-1 if none selected).
	CurrentIndex int

	// Filter is the active log level filter.
	Filter *tailer.Filter

	// Tailing indicates whether we are actively tailing logs.
	Tailing bool

	// TailCancel is the function to stop the current tail operation.
	TailCancel context.CancelFunc
}

// NewAppState creates a new AppState with default values.
func NewAppState() *AppState {
	return &AppState{
		Instances:    make([]*instance.Instance, 0),
		CurrentIndex: -1,
		Filter:       tailer.NewFilter(),
		Tailing:      false,
		TailCancel:   nil,
	}
}

// CurrentInstance returns the currently selected instance, or nil if none.
func (s *AppState) CurrentInstance() *instance.Instance {
	if s.CurrentIndex < 0 || s.CurrentIndex >= len(s.Instances) {
		return nil
	}
	return s.Instances[s.CurrentIndex]
}

// SelectInstance sets the current instance by index.
// Returns true if the index is valid, false otherwise.
func (s *AppState) SelectInstance(index int) bool {
	if index < 0 || index >= len(s.Instances) {
		return false
	}
	s.CurrentIndex = index
	return true
}

// ClearSelection clears the current instance selection.
func (s *AppState) ClearSelection() {
	s.CurrentIndex = -1
}

// StopTailing stops any active tail operation.
func (s *AppState) StopTailing() {
	if s.TailCancel != nil {
		s.TailCancel()
		s.TailCancel = nil
	}
	s.Tailing = false
}

// SetInstances updates the list of detected instances and clears selection.
func (s *AppState) SetInstances(instances []*instance.Instance) {
	s.Instances = instances
	s.CurrentIndex = -1
}

// Executor handles command execution for the REPL.
type Executor struct {
	State  *AppState
	Output io.Writer
}

// NewExecutor creates a new command executor.
func NewExecutor(state *AppState) *Executor {
	return &Executor{
		State:  state,
		Output: os.Stdout,
	}
}

// Execute runs a command and returns the output.
func (e *Executor) Execute(input string) string {
	input = strings.TrimSpace(input)
	if input == "" {
		return ""
	}

	parts := strings.Fields(input)
	cmd := strings.ToLower(parts[0])
	args := parts[1:]

	// Suppress unused variable warning for now (will be used for tail, levels commands)
	_ = args

	switch cmd {
	case "list":
		return e.cmdList()
	case "refresh":
		return e.cmdRefresh()
	case "help":
		return e.cmdHelp()
	case "quit", "exit":
		return e.cmdQuit()
	case "clear":
		return e.cmdClear()
	default:
		return fmt.Sprintf("Unknown command: %s. Type 'help' for available commands.", cmd)
	}
}

// cmdList displays all detected PostgreSQL instances.
func (e *Executor) cmdList() string {
	if len(e.State.Instances) == 0 {
		return e.noInstancesMessage()
	}

	return e.formatInstanceTable()
}

// cmdRefresh re-scans for PostgreSQL instances.
func (e *Executor) cmdRefresh() string {
	fmt.Fprintln(e.Output, ui.RenderInfo("Scanning for PostgreSQL instances..."))

	result := detector.Detect()
	e.State.SetInstances(result.Instances)

	if result.HasErrors() {
		for _, err := range result.Errors {
			fmt.Fprintln(e.Output, ui.RenderWarning(err.Error()))
		}
	}

	return ui.RenderInfo(fmt.Sprintf("Found %d instance(s)", len(result.Instances)))
}

// cmdHelp displays available commands.
func (e *Executor) cmdHelp() string {
	return `pgtail - PostgreSQL log tailer

Commands:
  list              Show detected PostgreSQL instances
  tail <id|path>    Tail logs for an instance (alias: follow)
  levels [LEVEL...] Set log level filter (no args = clear)
  refresh           Re-scan for instances
  stop              Stop current tail
  clear             Clear screen
  help              Show this help
  quit              Exit pgtail (alias: exit)

Keyboard Shortcuts:
  Tab       Autocomplete
  Up/Down   Command history
  Ctrl+C    Stop tail / Clear input
  Ctrl+D    Exit (when input empty)
  Ctrl+L    Clear screen

Log Levels (for 'levels' command):
  PANIC FATAL ERROR WARNING NOTICE LOG INFO DEBUG1-5`
}

// cmdQuit signals the REPL to exit.
func (e *Executor) cmdQuit() string {
	os.Exit(0)
	return ""
}

// cmdClear clears the terminal screen.
func (e *Executor) cmdClear() string {
	// ANSI escape sequence to clear screen and move cursor to top
	fmt.Fprint(e.Output, "\033[2J\033[H")
	return ""
}

// formatInstanceTable formats instances as a table.
func (e *Executor) formatInstanceTable() string {
	var sb strings.Builder

	// Header
	sb.WriteString(fmt.Sprintf("  %s  %s  %s  %s  %s  %s\n",
		ui.TableHeader.Render(fmt.Sprintf("%-3s", "#")),
		ui.TableHeader.Render(fmt.Sprintf("%-8s", "VERSION")),
		ui.TableHeader.Render(fmt.Sprintf("%6s", "PORT")),
		ui.TableHeader.Render(fmt.Sprintf("%-8s", "STATUS")),
		ui.TableHeader.Render(fmt.Sprintf("%-8s", "SOURCE")),
		ui.TableHeader.Render("DATA DIRECTORY")))

	// Rows
	for i, inst := range e.State.Instances {
		portStr := ui.Muted.Render("-")
		if inst.Port > 0 {
			portStr = fmt.Sprintf("%d", inst.Port)
		}

		// Shorten home directory to ~
		dataDir := shortenPath(inst.DataDir)

		sb.WriteString(fmt.Sprintf("  %s  %-8s  %6s  %s  %-8s  %s\n",
			ui.TableIndex.Render(fmt.Sprintf("%-3d", i)),
			inst.Version,
			portStr,
			fmt.Sprintf("%-8s", ui.RenderStatus(inst.Running)),
			inst.DisplaySource(),
			dataDir))
	}

	return sb.String()
}

// noInstancesMessage returns a helpful message when no instances are found.
func (e *Executor) noInstancesMessage() string {
	return `No PostgreSQL instances found.

Suggestions:
  - If PostgreSQL is running, check that the process is visible
  - Check if PGDATA environment variable is set correctly
  - For pgrx users: ensure ~/.pgrx/data-*/ directories exist
  - For Homebrew users: check /opt/homebrew/var/postgresql@*/
  - Run 'refresh' to re-scan after starting PostgreSQL

Common installation paths checked:
  - ~/.pgrx/data-*/           (pgrx development)
  - /opt/homebrew/var/postgres*  (Homebrew on Apple Silicon)
  - /usr/local/var/postgres*     (Homebrew on Intel)
  - /var/lib/postgresql/*/main   (Debian/Ubuntu)
  - /var/lib/pgsql/*/data        (RHEL/CentOS)`
}

// shortenPath replaces home directory with ~ for display.
func shortenPath(path string) string {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return path
	}

	if strings.HasPrefix(path, homeDir) {
		return "~" + path[len(homeDir):]
	}

	return path
}

// DetectAndSetInstances runs detection and updates state.
func (e *Executor) DetectAndSetInstances() *detector.DetectionResult {
	result := detector.Detect()
	e.State.SetInstances(result.Instances)
	return result
}
