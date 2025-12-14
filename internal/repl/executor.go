// Package repl provides the interactive REPL for pgtail.
package repl

import (
	"context"

	"github.com/willibrandon/pgtail/internal/instance"
	"github.com/willibrandon/pgtail/internal/tailer"
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
