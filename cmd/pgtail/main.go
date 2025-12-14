// Package main provides the entry point for the pgtail CLI tool.
package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/c-bata/go-prompt"
	"github.com/willibrandon/pgtail/internal/repl"
)

// Version is set at build time.
var Version = "0.1.0"

func main() {
	// Handle --help and --version flags.
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "--help", "-h":
			printHelp()
			os.Exit(0)
		case "--version", "-v":
			fmt.Printf("pgtail version %s\n", Version)
			os.Exit(0)
		default:
			fmt.Fprintf(os.Stderr, "Unknown flag: %s\nRun 'pgtail --help' for usage.\n", os.Args[1])
			os.Exit(1)
		}
	}

	// Initialize application state.
	state := repl.NewAppState()

	// Create the REPL with go-prompt.
	p := prompt.New(
		makeExecutor(state),
		makeCompleter(state),
		prompt.OptionPrefix("pgtail> "),
		prompt.OptionLivePrefix(makeLivePrefix(state)),
		prompt.OptionTitle("pgtail"),
		prompt.OptionPrefixTextColor(prompt.Cyan),
		prompt.OptionPreviewSuggestionTextColor(prompt.Blue),
		prompt.OptionSelectedSuggestionBGColor(prompt.LightGray),
		prompt.OptionSuggestionBGColor(prompt.DarkGray),
	)

	// Run the REPL.
	p.Run()
}

func printHelp() {
	fmt.Println(`pgtail - PostgreSQL log tailer

Usage:
  pgtail [flags]

Flags:
  -h, --help      Show this help message
  -v, --version   Show version information

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
  Ctrl+L    Clear screen`)
}

func makeExecutor(state *repl.AppState) func(string) {
	return func(input string) {
		input = strings.TrimSpace(input)
		if input == "" {
			return
		}

		parts := strings.Fields(input)
		cmd := strings.ToLower(parts[0])
		args := parts[1:]

		switch cmd {
		case "quit", "exit":
			fmt.Println("Goodbye!")
			os.Exit(0)

		case "help":
			printREPLHelp()

		case "clear":
			// Clear screen using ANSI escape codes.
			fmt.Print("\033[H\033[2J")

		case "list":
			executeList(state)

		case "tail", "follow":
			executeTail(state, args)

		case "levels":
			executeLevels(state, args)

		case "refresh":
			executeRefresh(state)

		case "stop":
			executeStop(state)

		default:
			fmt.Printf("Unknown command: %s. Type 'help' for available commands.\n", cmd)
		}
	}
}

func printREPLHelp() {
	fmt.Println(`pgtail - PostgreSQL log tailer

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
  PANIC FATAL ERROR WARNING NOTICE LOG INFO DEBUG1-5`)
}

func makeCompleter(state *repl.AppState) func(prompt.Document) []prompt.Suggest {
	return func(d prompt.Document) []prompt.Suggest {
		// Get the text before the cursor.
		text := d.TextBeforeCursor()
		if text == "" {
			return nil
		}

		// Split into words.
		words := strings.Fields(text)
		if len(words) == 0 {
			return nil
		}

		// If we're still typing the first word, suggest commands.
		if len(words) == 1 && !strings.HasSuffix(text, " ") {
			commands := []prompt.Suggest{
				{Text: "list", Description: "Show detected PostgreSQL instances"},
				{Text: "tail", Description: "Tail logs for an instance"},
				{Text: "follow", Description: "Alias for tail"},
				{Text: "levels", Description: "Set log level filter"},
				{Text: "refresh", Description: "Re-scan for instances"},
				{Text: "stop", Description: "Stop current tail"},
				{Text: "clear", Description: "Clear screen"},
				{Text: "help", Description: "Show help"},
				{Text: "quit", Description: "Exit pgtail"},
				{Text: "exit", Description: "Exit pgtail"},
			}
			return prompt.FilterHasPrefix(commands, words[0], true)
		}

		// Context-aware suggestions based on the command.
		cmd := strings.ToLower(words[0])
		switch cmd {
		case "tail", "follow":
			return suggestInstances(state)
		case "levels":
			return suggestLevels(words[1:])
		}

		return nil
	}
}

func suggestInstances(state *repl.AppState) []prompt.Suggest {
	var suggestions []prompt.Suggest
	for i, inst := range state.Instances {
		suggestions = append(suggestions, prompt.Suggest{
			Text:        fmt.Sprintf("%d", i),
			Description: inst.DataDir,
		})
	}
	return suggestions
}

func suggestLevels(alreadyUsed []string) []prompt.Suggest {
	used := make(map[string]bool)
	for _, l := range alreadyUsed {
		used[strings.ToUpper(l)] = true
	}

	allLevels := []prompt.Suggest{
		{Text: "PANIC", Description: "Critical: System panic"},
		{Text: "FATAL", Description: "Critical: Fatal error"},
		{Text: "ERROR", Description: "High: Error condition"},
		{Text: "WARNING", Description: "Medium: Warning condition"},
		{Text: "NOTICE", Description: "Low: Notice"},
		{Text: "LOG", Description: "Info: General log"},
		{Text: "INFO", Description: "Info: Informational"},
		{Text: "DEBUG1", Description: "Verbose: Debug level 1"},
		{Text: "DEBUG2", Description: "Verbose: Debug level 2"},
		{Text: "DEBUG3", Description: "Verbose: Debug level 3"},
		{Text: "DEBUG4", Description: "Verbose: Debug level 4"},
		{Text: "DEBUG5", Description: "Verbose: Debug level 5"},
	}

	var suggestions []prompt.Suggest
	for _, s := range allLevels {
		if !used[s.Text] {
			suggestions = append(suggestions, s)
		}
	}
	return suggestions
}

func makeLivePrefix(state *repl.AppState) func() (string, bool) {
	return func() (string, bool) {
		prefix := "pgtail"

		// Add instance index if selected.
		if state.CurrentIndex >= 0 {
			prefix += fmt.Sprintf("[%d", state.CurrentIndex)

			// Add filter if set.
			if !state.Filter.IsEmpty() {
				prefix += ":" + state.Filter.String()
			}

			prefix += "]"
		} else if !state.Filter.IsEmpty() {
			prefix += "[:" + state.Filter.String() + "]"
		}

		prefix += "> "
		return prefix, true
	}
}

// Placeholder command implementations - to be completed in Phase 3+.

func executeList(state *repl.AppState) {
	if len(state.Instances) == 0 {
		fmt.Println("No PostgreSQL instances found.")
		fmt.Println("")
		fmt.Println("Suggestions:")
		fmt.Println("  - Start a PostgreSQL instance")
		fmt.Println("  - Check PGDATA environment variable")
		fmt.Println("  - Run 'refresh' after starting PostgreSQL")
		return
	}

	fmt.Println("  #  VERSION  PORT   STATUS   SOURCE  DATA DIRECTORY")
	for i, inst := range state.Instances {
		status := "stopped"
		if inst.Running {
			status = "running"
		}
		port := "-"
		if inst.Port > 0 {
			port = fmt.Sprintf("%d", inst.Port)
		}
		fmt.Printf("  %d  %-8s %-6s %-8s %-7s %s\n",
			i, inst.Version, port, status, inst.Source.String(), inst.DataDir)
	}
}

func executeTail(state *repl.AppState, args []string) {
	if len(args) == 0 {
		fmt.Println("Error: Missing instance identifier.")
		fmt.Println("Usage: tail <index|path>")
		fmt.Println("Run 'list' to see available instances.")
		return
	}

	// TODO: Implement in Phase 4 (User Story 2).
	fmt.Printf("Tailing logs for: %s (not yet implemented)\n", args[0])
}

func executeLevels(state *repl.AppState, args []string) {
	if len(args) == 0 {
		state.Filter.Clear()
		fmt.Println("[Filter cleared - showing all levels]")
		return
	}

	// TODO: Implement in Phase 5 (User Story 3).
	fmt.Printf("[Filter set: %s] (not yet implemented)\n", strings.Join(args, ", "))
}

func executeRefresh(state *repl.AppState) {
	fmt.Println("[Scanning for PostgreSQL instances...]")
	// TODO: Implement detection in Phase 3 (User Story 1).
	state.Instances = nil
	state.ClearSelection()
	fmt.Printf("[Found %d instances]\n", len(state.Instances))
}

func executeStop(state *repl.AppState) {
	state.StopTailing()
	// Returns to prompt silently.
}
