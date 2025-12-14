// Package ui provides terminal styling for pgtail.
package ui

import (
	"github.com/charmbracelet/lipgloss"
)

// Color palette using ANSI 256 colors for broad terminal support
var (
	// Brand colors
	ColorPrimary   = lipgloss.Color("12")  // bright blue
	ColorSecondary = lipgloss.Color("14")  // cyan
	ColorMuted     = lipgloss.Color("8")   // gray
	ColorSuccess   = lipgloss.Color("10")  // green
	ColorWarning   = lipgloss.Color("11")  // yellow
	ColorError     = lipgloss.Color("9")   // red

	// Status colors
	ColorRunning = lipgloss.Color("10") // green
	ColorStopped = lipgloss.Color("8")  // gray
)

// Base styles
var (
	// Title is for main headings
	Title = lipgloss.NewStyle().
		Bold(true).
		Foreground(ColorPrimary)

	// Subtitle is for secondary headings
	Subtitle = lipgloss.NewStyle().
			Foreground(ColorSecondary)

	// Muted is for less important text
	Muted = lipgloss.NewStyle().
		Foreground(ColorMuted)

	// Success is for positive messages
	Success = lipgloss.NewStyle().
		Foreground(ColorSuccess)

	// Warning is for warning messages
	Warning = lipgloss.NewStyle().
		Foreground(ColorWarning)

	// Error is for error messages
	Error = lipgloss.NewStyle().
		Foreground(ColorError)

	// Bold is for emphasis
	Bold = lipgloss.NewStyle().
		Bold(true)
)

// Table styles
var (
	// TableHeader is for table column headers
	TableHeader = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorPrimary)

	// TableCell is the base style for table cells
	TableCell = lipgloss.NewStyle()

	// TableIndex is for row index numbers
	TableIndex = lipgloss.NewStyle().
			Foreground(ColorMuted)
)

// Status styles
var (
	// StatusRunning is for "running" status text
	StatusRunning = lipgloss.NewStyle().
			Foreground(ColorRunning)

	// StatusStopped is for "stopped" status text
	StatusStopped = lipgloss.NewStyle().
			Foreground(ColorStopped)
)

// Message styles
var (
	// Info is for informational messages like "[Scanning...]"
	Info = lipgloss.NewStyle().
		Foreground(ColorSecondary)

	// Prompt is for the REPL prompt
	Prompt = lipgloss.NewStyle().
		Foreground(ColorPrimary).
		Bold(true)
)

// Log level styles (for future use in tail output)
var (
	LogPanic   = lipgloss.NewStyle().Foreground(ColorError).Bold(true)
	LogFatal   = lipgloss.NewStyle().Foreground(ColorError).Bold(true)
	LogError   = lipgloss.NewStyle().Foreground(ColorError)
	LogWarning = lipgloss.NewStyle().Foreground(ColorWarning)
	LogNotice  = lipgloss.NewStyle().Foreground(ColorSecondary)
	LogLog     = lipgloss.NewStyle()
	LogInfo    = lipgloss.NewStyle().Foreground(ColorSuccess)
	LogDebug   = lipgloss.NewStyle().Foreground(ColorMuted)
)

// Helper functions

// RenderStatus returns styled status text based on running state.
func RenderStatus(running bool) string {
	if running {
		return StatusRunning.Render("running")
	}
	return StatusStopped.Render("stopped")
}

// RenderInfo wraps text in info style with brackets.
func RenderInfo(text string) string {
	return Info.Render("[" + text + "]")
}

// RenderError wraps text in error style.
func RenderError(text string) string {
	return Error.Render("Error: " + text)
}

// RenderWarning wraps text in warning style.
func RenderWarning(text string) string {
	return Warning.Render("Warning: " + text)
}
