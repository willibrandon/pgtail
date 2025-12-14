// Package main provides the entry point for the pgtail CLI tool.
package main

import (
	"bufio"
	"flag"
	"fmt"
	"os"
	"strings"

	"github.com/willibrandon/pgtail/internal/repl"
	"github.com/willibrandon/pgtail/internal/ui"
)

// Version is the current version of pgtail.
// This is typically set at build time via ldflags.
var Version = "0.1.0"

func main() {
	// Define flags
	helpFlag := flag.Bool("help", false, "Show help and exit")
	hFlag := flag.Bool("h", false, "Show help and exit")
	versionFlag := flag.Bool("version", false, "Show version and exit")
	vFlag := flag.Bool("v", false, "Show version and exit")

	flag.Parse()

	// Handle --help / -h
	if *helpFlag || *hFlag {
		printHelp()
		os.Exit(0)
	}

	// Handle --version / -v
	if *versionFlag || *vFlag {
		fmt.Printf("pgtail version %s\n", Version)
		os.Exit(0)
	}

	// Initialize state and executor
	state := repl.NewAppState()
	executor := repl.NewExecutor(state)

	// Run initial detection
	fmt.Println(ui.Title.Render("pgtail") + ui.Muted.Render(" - PostgreSQL log tailer"))
	fmt.Println(ui.RenderInfo("Scanning for PostgreSQL instances..."))
	result := executor.DetectAndSetInstances()
	fmt.Println(ui.RenderInfo(fmt.Sprintf("Found %d instance(s)", result.InstanceCount())))
	if result.HasErrors() {
		for _, err := range result.Errors {
			fmt.Println(ui.RenderWarning(err.Error()))
		}
	}
	fmt.Println()

	// Start REPL
	scanner := bufio.NewScanner(os.Stdin)
	for {
		// Print prompt
		fmt.Print(ui.Prompt.Render("pgtail> "))

		// Read input
		if !scanner.Scan() {
			// EOF (Ctrl+D)
			fmt.Println()
			break
		}

		input := strings.TrimSpace(scanner.Text())
		if input == "" {
			continue
		}

		// Execute command
		output := executor.Execute(input)
		if output != "" {
			fmt.Println(output)
		}
	}
}

func printHelp() {
	fmt.Println(`pgtail - PostgreSQL log tailer

Usage: pgtail [flags]

Flags:
  --help, -h       Show this help and exit
  --version, -v    Show version and exit

Commands (in REPL):
  list              Show detected PostgreSQL instances
  tail <id|path>    Tail logs for an instance (alias: follow)
  levels [LEVEL...] Set log level filter (no args = clear)
  refresh           Re-scan for instances
  stop              Stop current tail
  clear             Clear screen
  help              Show command help
  quit              Exit pgtail (alias: exit)

Keyboard Shortcuts:
  Tab       Autocomplete
  Up/Down   Command history
  Ctrl+C    Stop tail / Clear input
  Ctrl+D    Exit (when input empty)
  Ctrl+L    Clear screen

Log Levels (for 'levels' command):
  PANIC FATAL ERROR WARNING NOTICE LOG INFO DEBUG1-5`)
}
