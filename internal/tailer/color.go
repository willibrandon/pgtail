package tailer

import (
	"os"

	"github.com/charmbracelet/lipgloss"
	"golang.org/x/term"
)

// colorEnabled tracks whether colors should be used.
var colorEnabled bool

// Color styles for each log level.
var (
	stylePanic   lipgloss.Style
	styleFatal   lipgloss.Style
	styleError   lipgloss.Style
	styleWarning lipgloss.Style
	styleNotice  lipgloss.Style
	styleLog     lipgloss.Style
	styleInfo    lipgloss.Style
	styleDebug   lipgloss.Style

	// styleTimestamp is used for timestamp display.
	styleTimestamp lipgloss.Style

	// stylePID is used for process ID display.
	stylePID lipgloss.Style
)

func init() {
	initColors()
}

// initColors initializes color styles based on environment and terminal capabilities.
func initColors() {
	colorEnabled = detectColorSupport()

	if colorEnabled {
		// High severity - Red tones
		stylePanic = lipgloss.NewStyle().Foreground(lipgloss.Color("196")).Bold(true)   // Bright red, bold
		styleFatal = lipgloss.NewStyle().Foreground(lipgloss.Color("160")).Bold(true)   // Dark red, bold
		styleError = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))              // Bright red

		// Medium severity - Yellow/Orange tones
		styleWarning = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))            // Orange
		styleNotice = lipgloss.NewStyle().Foreground(lipgloss.Color("227"))             // Yellow

		// Low severity - Blue/Cyan/Green tones
		styleLog = lipgloss.NewStyle().Foreground(lipgloss.Color("250"))                // Light gray
		styleInfo = lipgloss.NewStyle().Foreground(lipgloss.Color("39"))                // Cyan
		styleDebug = lipgloss.NewStyle().Foreground(lipgloss.Color("245"))              // Gray

		// Metadata styles
		styleTimestamp = lipgloss.NewStyle().Foreground(lipgloss.Color("243"))          // Dim gray
		stylePID = lipgloss.NewStyle().Foreground(lipgloss.Color("245"))                // Gray
	} else {
		// No colors - use empty styles
		stylePanic = lipgloss.NewStyle()
		styleFatal = lipgloss.NewStyle()
		styleError = lipgloss.NewStyle()
		styleWarning = lipgloss.NewStyle()
		styleNotice = lipgloss.NewStyle()
		styleLog = lipgloss.NewStyle()
		styleInfo = lipgloss.NewStyle()
		styleDebug = lipgloss.NewStyle()
		styleTimestamp = lipgloss.NewStyle()
		stylePID = lipgloss.NewStyle()
	}
}

// detectColorSupport determines if color output should be enabled.
// Checks NO_COLOR env var and terminal capabilities.
func detectColorSupport() bool {
	// NO_COLOR standard: https://no-color.org/
	// If NO_COLOR is set (to any value), disable colors.
	if _, exists := os.LookupEnv("NO_COLOR"); exists {
		return false
	}

	// FORCE_COLOR overrides detection.
	if _, exists := os.LookupEnv("FORCE_COLOR"); exists {
		return true
	}

	// Check if stdout is a terminal.
	if !term.IsTerminal(int(os.Stdout.Fd())) {
		return false
	}

	// Check TERM environment variable.
	termEnv := os.Getenv("TERM")
	if termEnv == "dumb" {
		return false
	}

	return true
}

// ColorEnabled returns whether colors are currently enabled.
func ColorEnabled() bool {
	return colorEnabled
}

// SetColorEnabled allows programmatic control of color output.
func SetColorEnabled(enabled bool) {
	colorEnabled = enabled
	initColors()
}

// ColorizeLevel returns the log level string with appropriate coloring.
func ColorizeLevel(level LogLevel) string {
	levelStr := level.String()

	if !colorEnabled {
		return levelStr
	}

	style := levelStyle(level)
	return style.Render(levelStr)
}

// ColorizeEntry returns a fully colorized log entry string.
func ColorizeEntry(entry LogEntry) string {
	if entry.IsContinuation {
		return "    " + entry.Message
	}

	if entry.Timestamp == "" {
		return entry.Raw
	}

	if !colorEnabled {
		return entry.Raw
	}

	// Build colorized output: TIMESTAMP [PID] LEVEL: MESSAGE
	timestamp := styleTimestamp.Render(entry.Timestamp)
	pid := stylePID.Render("[" + itoa(entry.PID) + "]")
	level := ColorizeLevel(entry.Level)

	// Message uses the level's color for high severity, plain for others
	var message string
	switch entry.Level {
	case LevelPanic, LevelFatal, LevelError:
		message = levelStyle(entry.Level).Render(entry.Message)
	default:
		message = entry.Message
	}

	return timestamp + " " + pid + " " + level + ": " + message
}

// levelStyle returns the lipgloss style for a log level.
func levelStyle(level LogLevel) lipgloss.Style {
	switch level {
	case LevelPanic:
		return stylePanic
	case LevelFatal:
		return styleFatal
	case LevelError:
		return styleError
	case LevelWarning:
		return styleWarning
	case LevelNotice:
		return styleNotice
	case LevelLog:
		return styleLog
	case LevelInfo:
		return styleInfo
	case LevelDebug5, LevelDebug4, LevelDebug3, LevelDebug2, LevelDebug1:
		return styleDebug
	default:
		return styleLog
	}
}

// itoa is a simple int-to-string conversion to avoid importing strconv.
func itoa(i int) string {
	if i == 0 {
		return "0"
	}

	neg := false
	if i < 0 {
		neg = true
		i = -i
	}

	var b [20]byte
	idx := len(b)
	for i > 0 {
		idx--
		b[idx] = byte('0' + i%10)
		i /= 10
	}

	if neg {
		idx--
		b[idx] = '-'
	}

	return string(b[idx:])
}
