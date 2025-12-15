// Package main provides the entry point for the pgtail CLI tool.
package main

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"

	"github.com/c-bata/go-prompt"
	"github.com/willibrandon/pgtail/internal/detector"
	"github.com/willibrandon/pgtail/internal/repl"
	"github.com/willibrandon/pgtail/internal/tailer"
)

var shellMode bool

// Version is set at build time.
var Version = "0.1.0"

// historyFile is the path to the command history file.
var historyFile string

// historyMaxLines is the maximum number of history entries to keep.
const historyMaxLines = 1000

// lastHistoryCmd tracks the last command to skip consecutive duplicates.
var lastHistoryCmd string

// historyIgnore contains commands that should not be saved to history.
var historyIgnore = map[string]bool{
	"q": true, "quit": true, "exit": true,
	"": true,
}

func init() {
	home, err := os.UserHomeDir()
	if err != nil {
		return
	}
	historyFile = filepath.Join(home, ".pgtail.hist")
}

// loadHistory reads command history from the history file.
func loadHistory() []string {
	if historyFile == "" {
		return nil
	}
	file, err := os.Open(historyFile)
	if err != nil {
		return nil
	}
	defer file.Close()

	var history []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		if line := scanner.Text(); line != "" {
			history = append(history, line)
		}
	}

	// Track last command for duplicate detection.
	if len(history) > 0 {
		lastHistoryCmd = history[len(history)-1]
	}

	return history
}

// saveHistory appends a command to the history file.
func saveHistory(cmd string) {
	if historyFile == "" || cmd == "" {
		return
	}

	// Ignore certain commands.
	cmdLower := strings.ToLower(strings.Fields(cmd)[0])
	if historyIgnore[cmdLower] {
		return
	}

	// Skip single-character commands.
	if len(strings.TrimSpace(cmd)) == 1 {
		return
	}

	// Skip consecutive duplicates.
	if cmd == lastHistoryCmd {
		return
	}
	lastHistoryCmd = cmd

	// Append to file.
	file, err := os.OpenFile(historyFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0600)
	if err != nil {
		return
	}
	file.WriteString(cmd + "\n")
	file.Close()

	// Trim history if needed.
	trimHistory()
}

// trimHistory keeps only the last historyMaxLines entries.
func trimHistory() {
	if historyFile == "" {
		return
	}

	// Read current history.
	file, err := os.Open(historyFile)
	if err != nil {
		return
	}

	var lines []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	file.Close()

	// Only trim if over limit.
	if len(lines) <= historyMaxLines {
		return
	}

	// Keep last N lines.
	lines = lines[len(lines)-historyMaxLines:]

	// Rewrite file.
	file, err = os.OpenFile(historyFile, os.O_TRUNC|os.O_CREATE|os.O_WRONLY, 0600)
	if err != nil {
		return
	}
	defer file.Close()
	for _, line := range lines {
		file.WriteString(line + "\n")
	}
}

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

	// Auto-detect instances on startup.
	fmt.Println("[Scanning for PostgreSQL instances...]")
	result := detector.DetectInstances()
	state.Instances = result.Instances
	fmt.Printf("[Found %d instance(s)]\n", len(state.Instances))
	fmt.Println()

	// Create the REPL with go-prompt.
	p := prompt.New(
		makeExecutor(state),
		makeCompleter(state),
		prompt.OptionPrefix("pgtail> "),
		prompt.OptionLivePrefix(makeLivePrefix(state)),
		prompt.OptionTitle("pgtail"),
		prompt.OptionHistory(loadHistory()),
		prompt.OptionPrefixTextColor(prompt.Cyan),
		prompt.OptionPreviewSuggestionTextColor(prompt.Blue),
		prompt.OptionSelectedSuggestionBGColor(prompt.LightGray),
		prompt.OptionSuggestionBGColor(prompt.DarkGray),
		prompt.OptionAddASCIICodeBind(
			prompt.ASCIICodeBind{
				ASCIICode: []byte{'!'},
				Fn: func(buf *prompt.Buffer) {
					if buf.Text() == "" {
						shellMode = true
					} else {
						buf.InsertText("!", false, true)
					}
				},
			},
		),
		prompt.OptionAddKeyBind(
			prompt.KeyBind{
				Key: prompt.Escape,
				Fn: func(buf *prompt.Buffer) {
					shellMode = false
				},
			},
			prompt.KeyBind{
				Key: prompt.Backspace,
				Fn: func(buf *prompt.Buffer) {
					if shellMode && buf.Text() == "" {
						shellMode = false
					}
					// Otherwise let default handler do the delete
				},
			},
		),
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

		// Empty input or 'q' stops tailing if active.
		if input == "" {
			shellMode = false
			if state.Tailing {
				stopTailing(state)
			}
			return
		}

		// Save to history.
		saveHistory(input)

		if shellMode {
			shellMode = false
			runShell(input)
			return
		}

		parts := strings.Fields(input)
		cmd := strings.ToLower(parts[0])
		args := parts[1:]

		// 'q' stops tailing (like less/top).
		if cmd == "q" && state.Tailing {
			stopTailing(state)
			return
		}

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

		case "stop", "q":
			if state.Tailing {
				stopTailing(state)
			}

		case "enable-logging":
			executeEnableLogging(state, args)

		default:
			fmt.Printf("Unknown command: %s. Type 'help' for available commands.\n", cmd)
		}
	}
}

func printREPLHelp() {
	fmt.Println(`pgtail - PostgreSQL log tailer

Commands:
  list               Show detected PostgreSQL instances
  tail <id|path>     Tail logs for an instance (alias: follow)
  levels [LEVEL...]  Set log level filter (no args = clear)
  enable-logging <id> Enable logging_collector for an instance
  refresh            Re-scan for instances
  stop               Stop current tail
  clear              Clear screen
  help               Show this help
  quit               Exit pgtail (alias: exit)

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
				{Text: "enable-logging", Description: "Enable logging for an instance"},
				{Text: "refresh", Description: "Re-scan for instances"},
				{Text: "stop", Description: "Stop current tail"},
				{Text: "q", Description: "Stop current tail"},
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
		case "tail", "follow", "enable-logging":
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
		if shellMode {
			return "! ", true
		}

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

func executeList(state *repl.AppState) {
	if len(state.Instances) == 0 {
		fmt.Println("No PostgreSQL instances found.")
		fmt.Println("")
		fmt.Println("Suggestions:")
		fmt.Println("  - Start a PostgreSQL instance")
		fmt.Println("  - Set PGDATA environment variable to your data directory")
		fmt.Println("  - Run 'refresh' after starting PostgreSQL")
		fmt.Println("  - Check ~/.pgrx/ for pgrx development instances")
		return
	}

	fmt.Println("  #  VERSION  PORT   STATUS   LOG  SOURCE  DATA DIRECTORY")
	for i, inst := range state.Instances {
		status := "stopped"
		if inst.Running {
			status = "running"
		}
		port := "-"
		if inst.Port > 0 {
			port = fmt.Sprintf("%d", inst.Port)
		}
		logStatus := "off"
		if inst.LoggingEnabled {
			logStatus = "on"
		}
		// Shorten home directory to ~ for display.
		dataDir := shortenPath(inst.DataDir)
		fmt.Printf("  %d  %-8s %-6s %-8s %-4s %-7s %s\n",
			i, inst.Version, port, status, logStatus, inst.Source.String(), dataDir)
	}
}

// shortenPath replaces the home directory with ~ for display.
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

// activeTailer holds the current tailer for background tailing.
var activeTailer *tailer.Tailer

func executeTail(state *repl.AppState, args []string) {
	if len(args) == 0 {
		fmt.Println("Error: Missing instance identifier.")
		fmt.Println("Usage: tail <index|path>")
		fmt.Println("Run 'list' to see available instances.")
		return
	}

	if len(state.Instances) == 0 {
		fmt.Println("Error: No instances available.")
		fmt.Println("Run 'refresh' to scan for PostgreSQL instances.")
		return
	}

	// Stop any existing tail first.
	if state.Tailing {
		stopTailing(state)
	}

	// Find the instance by index or path substring.
	instIndex := findInstanceIndex(state, args[0])
	if instIndex < 0 {
		fmt.Printf("Error: Instance not found: %s\n", args[0])
		fmt.Println("Use a numeric index (0, 1, ...) or a path substring.")
		fmt.Println("Run 'list' to see available instances.")
		return
	}

	inst := state.Instances[instIndex]

	// Check if instance has a log directory.
	if inst.LogDir == "" {
		fmt.Printf("Error: Instance has no log directory configured.\n")
		fmt.Printf("Check postgresql.conf for log_directory setting.\n")
		return
	}

	// Create tailer configuration.
	cfg := tailer.TailerConfig{
		LogDir:     inst.LogDir,
		LogPattern: inst.LogPattern,
		Filter:     state.Filter,
	}

	// Create tailer.
	t, err := tailer.NewTailer(cfg)
	if err != nil {
		fmt.Printf("Error: %s\n", err.Error())
		if strings.Contains(err.Error(), "does not exist") {
			fmt.Println("The log directory may not exist because logging_collector is disabled.")
			fmt.Println("Enable logging in postgresql.conf and restart PostgreSQL.")
		} else if strings.Contains(err.Error(), "permission") {
			fmt.Println("Check file permissions on the log directory.")
		}
		return
	}

	// Create context for cancellation.
	ctx, cancel := context.WithCancel(context.Background())
	state.StartTailing(cancel)
	state.SelectInstance(instIndex)
	activeTailer = t

	// Start tailing.
	err = t.Start(ctx)
	if err != nil {
		state.StopTailing()
		activeTailer = nil
		fmt.Printf("Error: %s\n", err.Error())
		if strings.Contains(err.Error(), "no log files") {
			fmt.Println("No log files found matching the pattern.")
			fmt.Println("PostgreSQL may not have written any logs yet.")
		}
		return
	}

	fmt.Printf("[Tailing %s]\n", t.CurrentFile())
	fmt.Println("[Press 'q' or Enter to stop]")

	// Read and display log entries in background.
	go func() {
		for {
			select {
			case entry, ok := <-t.Entries():
				if !ok {
					return
				}
				displayLogEntry(entry)
			case err, ok := <-t.Errors():
				if !ok {
					return
				}
				fmt.Printf("[Error: %s]\n", err.Error())
			case <-ctx.Done():
				return
			}
		}
	}()

	// Non-blocking - return to prompt immediately.
	// User types 'q', 'stop', or Enter to stop.
}

func stopTailing(state *repl.AppState) {
	if activeTailer != nil {
		activeTailer.Stop()
		activeTailer = nil
	}
	state.StopTailing()
	state.ClearSelection()
	fmt.Println("[Stopped]")
}

// findInstanceIndex finds an instance by numeric index or path substring.
// Returns -1 if not found.
func findInstanceIndex(state *repl.AppState, identifier string) int {
	// Try numeric index first.
	if idx, err := strconv.Atoi(identifier); err == nil {
		if idx >= 0 && idx < len(state.Instances) {
			return idx
		}
		return -1
	}

	// Try path substring match (case-insensitive).
	identifier = strings.ToLower(identifier)
	for i, inst := range state.Instances {
		if strings.Contains(strings.ToLower(inst.DataDir), identifier) {
			return i
		}
	}

	return -1
}

// displayLogEntry prints a log entry to stdout with color coding.
func displayLogEntry(entry tailer.LogEntry) {
	fmt.Println(tailer.ColorizeEntry(entry))
}

func executeLevels(state *repl.AppState, args []string) {
	// No arguments: clear the filter.
	if len(args) == 0 {
		state.Filter.Clear()
		fmt.Println("[Filter cleared - showing all levels]")
		return
	}

	// Parse level arguments.
	var levels []tailer.LogLevel
	var invalidLevels []string

	for _, arg := range args {
		level, valid := tailer.ParseLogLevel(arg)
		if valid {
			levels = append(levels, level)
		} else {
			invalidLevels = append(invalidLevels, arg)
		}
	}

	// Report invalid levels.
	if len(invalidLevels) > 0 {
		fmt.Printf("Error: Invalid log level(s): %s\n", strings.Join(invalidLevels, ", "))
		fmt.Println("Valid levels: PANIC FATAL ERROR WARNING NOTICE LOG INFO DEBUG1-5")
		return
	}

	// Set the filter.
	state.Filter.Set(levels...)
	fmt.Printf("[Filter set: %s]\n", state.Filter.String())
}

func executeRefresh(state *repl.AppState) {
	fmt.Println("[Scanning for PostgreSQL instances...]")
	result := detector.DetectInstances()
	state.Instances = result.Instances
	state.ClearSelection()
	fmt.Printf("[Found %d instance(s)]\n", len(state.Instances))
}

func executeEnableLogging(state *repl.AppState, args []string) {
	if len(args) == 0 {
		fmt.Println("Error: Missing instance identifier.")
		fmt.Println("Usage: enable-logging <index|path>")
		fmt.Println("Run 'list' to see available instances.")
		return
	}

	if len(state.Instances) == 0 {
		fmt.Println("Error: No instances available.")
		fmt.Println("Run 'refresh' to scan for PostgreSQL instances.")
		return
	}

	// Find the instance.
	instIndex := findInstanceIndex(state, args[0])
	if instIndex < 0 {
		fmt.Printf("Error: Instance not found: %s\n", args[0])
		fmt.Println("Use a numeric index (0, 1, ...) or a path substring.")
		fmt.Println("Run 'list' to see available instances.")
		return
	}

	inst := state.Instances[instIndex]

	if inst.LoggingEnabled {
		fmt.Println("Logging is already enabled for this instance.")
		return
	}

	configPath := inst.DataDir + "/postgresql.conf"

	// Read current config.
	content, err := os.ReadFile(configPath)
	if err != nil {
		fmt.Printf("Error: Cannot read %s: %s\n", configPath, err.Error())
		return
	}

	// Prepare the settings to add/modify.
	settings := map[string]string{
		"logging_collector": "on",
		"log_directory":     "'log'",
		"log_filename":      "'postgresql-%Y-%m-%d_%H%M%S.log'",
	}

	lines := strings.Split(string(content), "\n")
	modified := make(map[string]bool)

	// Update existing settings or uncomment them.
	for i, line := range lines {
		trimmed := strings.TrimSpace(line)
		for key, value := range settings {
			// Check for commented or uncommented setting.
			if strings.HasPrefix(trimmed, "#"+key) || strings.HasPrefix(trimmed, key) {
				lines[i] = key + " = " + value
				modified[key] = true
				break
			}
		}
	}

	// Append any settings that weren't found.
	var toAppend []string
	for key, value := range settings {
		if !modified[key] {
			toAppend = append(toAppend, key+" = "+value)
		}
	}

	if len(toAppend) > 0 {
		lines = append(lines, "")
		lines = append(lines, "# Added by pgtail")
		lines = append(lines, toAppend...)
	}

	// Write back.
	newContent := strings.Join(lines, "\n")
	err = os.WriteFile(configPath, []byte(newContent), 0644)
	if err != nil {
		fmt.Printf("Error: Cannot write %s: %s\n", configPath, err.Error())
		return
	}

	fmt.Println("[Logging enabled in postgresql.conf]")
	fmt.Println()
	fmt.Println("Settings added:")
	fmt.Println("  logging_collector = on")
	fmt.Println("  log_directory = 'log'")
	logFilenameExample := "  log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'"
	fmt.Println(logFilenameExample)
	fmt.Println()

	if inst.Running {
		fmt.Println("Restart PostgreSQL for changes to take effect:")
		fmt.Printf("  pg_ctl restart -D %s\n", inst.DataDir)
	} else {
		fmt.Println("Start PostgreSQL to begin logging.")
	}

	// Update instance state.
	inst.LoggingEnabled = true
}

func runShell(cmdLine string) {
	if cmdLine == "" {
		return
	}
	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		cmd = exec.Command("cmd", "/c", cmdLine)
	} else {
		cmd = exec.Command("sh", "-c", cmdLine)
	}
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Run()
}
