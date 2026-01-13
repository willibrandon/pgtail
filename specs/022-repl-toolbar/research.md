# Research: REPL Bottom Toolbar

**Feature**: 022-repl-toolbar
**Date**: 2026-01-12

## Executive Summary

This document captures research findings for implementing a bottom toolbar in pgtail's REPL using prompt_toolkit's native `bottom_toolbar` parameter. All technical unknowns have been resolved through source code analysis of prompt_toolkit.

## Research Topics

### 1. prompt_toolkit `bottom_toolbar` Parameter

**Decision**: Use callable returning `list[tuple[str, str]]` (StyleAndTextTuples)

**Rationale**:
- The `bottom_toolbar` parameter in `PromptSession` accepts `AnyFormattedText`, which includes:
  - Plain strings
  - `list[tuple[str, str]]` (style, text tuples)
  - Callables returning any of the above
  - `None` to hide the toolbar
- A callable is required for dynamic content that reflects changing state
- Style tuples provide fine-grained control over individual text segments

**Alternatives Considered**:
- Plain string: Too limited, no styling
- HTML formatted text: More complex, less performant
- Custom Control: Overkill, prompt_toolkit already provides toolbar support

**Source Reference**: `/Users/brandon/src/python-prompt-toolkit/src/prompt_toolkit/shortcuts/prompt.py` lines 584-596

### 2. Dynamic Toolbar Updates

**Decision**: Pass callable that reads from AppState; toolbar updates automatically on each prompt

**Rationale**:
- `FormattedTextControl` wraps the callable in a lambda (`lambda: self.bottom_toolbar`)
- The callable is invoked on every render cycle
- When state changes (filters, theme, instances), the next render reflects the new values
- No explicit invalidation needed - prompt_toolkit handles this

**Implementation Pattern**:
```python
def create_toolbar_func(state: AppState):
    def get_toolbar() -> list[tuple[str, str]]:
        parts: list[tuple[str, str]] = []
        # Read from state, build tuple list
        return parts
    return get_toolbar

# In PromptSession initialization:
session = PromptSession(
    bottom_toolbar=create_toolbar_func(state),
    ...
)
```

**Source Reference**: `/Users/brandon/src/python-prompt-toolkit/src/prompt_toolkit/formatted_text/base.py` lines 80-81

### 3. Toolbar Styling with Style Classes

**Decision**: Define custom style classes (`toolbar`, `toolbar.dim`, `toolbar.filter`, `toolbar.warning`, `toolbar.shell`) and integrate with ThemeManager

**Rationale**:
- prompt_toolkit applies two default classes: `bottom-toolbar` (container) and `bottom-toolbar.text` (content)
- Custom classes can be defined and used via `class:classname` prefix in tuples
- Integrating with ThemeManager allows theme-aware toolbar colors
- Adding toolbar styles to Theme.ui follows existing pattern for other UI elements

**Style Integration**:
```python
# In Theme.ui dictionary:
{
    "toolbar": ColorStyle(bg="#1a1a1a", fg="#cccccc"),
    "toolbar.dim": ColorStyle(bg="#1a1a1a", fg="#666666"),
    "toolbar.filter": ColorStyle(bg="#1a1a1a", fg="#55ffff"),
    "toolbar.warning": ColorStyle(bg="#1a1a1a", fg="#ffff55"),
    "toolbar.shell": ColorStyle(bg="#1a1a1a", fg="#ffffff", bold=True),
}

# In FormattedText tuples:
[("class:toolbar.filter", "levels:ERROR,FATAL")]
```

**Source Reference**: `/Users/brandon/src/python-prompt-toolkit/src/prompt_toolkit/styles/defaults.py` line 129

### 4. Conditionally Hiding the Toolbar

**Decision**: Set `bottom_toolbar=None` when `display.show_toolbar=false`

**Rationale**:
- Returning `None` from the callable does NOT hide the toolbar (empty space remains)
- The `bottom_toolbar` parameter must be set to `None` to completely hide
- A `ConditionalContainer` filter hides when `self.bottom_toolbar is None`

**Implementation Pattern**:
```python
# In PromptSession initialization:
session = PromptSession(
    bottom_toolbar=create_toolbar_func(state) if state.config.display.show_toolbar else None,
    ...
)
```

**Source Reference**: `/Users/brandon/src/python-prompt-toolkit/src/prompt_toolkit/shortcuts/prompt.py` lines 590-593

### 5. Existing Codebase Patterns

**Decision**: Follow existing patterns from `colors.py` and `theme.py`

**Key Findings**:
- `ThemeManager.generate_style()` builds `Style(rules)` from theme definitions
- UI styles are defined in `Theme.ui` dictionary with string keys
- Style rules use format `(class_name, style_string)` where style_string is like `"bg:#1a1a1a #cccccc"`
- `ColorStyle.to_style_string()` converts dataclass to prompt_toolkit format
- `get_style(theme_manager)` returns current theme's Style object

**Integration Points**:
1. Add toolbar style keys to `Theme.ui` in built-in themes
2. Use `get_style(state.theme_manager)` when creating PromptSession
3. Reference styles via `class:toolbar.xxx` in FormattedText tuples

**Source Reference**: `/Users/brandon/src/pgtail/pgtail_py/theme.py` lines 660-691

### 6. NO_COLOR Environment Variable

**Decision**: Check `is_color_disabled()` utility before applying styles

**Rationale**:
- Existing `utils.py` has `is_color_disabled()` function
- When NO_COLOR is set, return plain text without style classes
- Toolbar content remains visible, just without colors

**Implementation Pattern**:
```python
from pgtail_py.utils import is_color_disabled

def get_toolbar() -> list[tuple[str, str]]:
    if is_color_disabled():
        # Return plain text without style classes
        return [("", "3 instances • Theme: dark")]
    else:
        return [("class:toolbar", " 3 instances "), ...]
```

**Source Reference**: `/Users/brandon/src/pgtail/pgtail_py/utils.py`

### 7. Filter Formatting Patterns

**Decision**: Reuse existing format methods where available

**Key Methods**:
- `TimeFilter.format_description()` - Already returns human-readable time filter string
- `FilterState.filters[0].pattern` - Access first regex pattern
- `LogLevel.all_levels()` - Compare to detect if levels are filtered

**Example Filter Display**:
```
levels:ERROR,FATAL,PANIC filter:/deadlock/i since:1h ago slow:>200ms
```

**Source Reference**: `/Users/brandon/src/pgtail/pgtail_py/time_filter.py` line 246

## Resolved Clarifications

| Unknown | Resolution |
|---------|------------|
| How to update toolbar dynamically? | Callable is re-invoked on each render cycle |
| How to integrate with existing themes? | Add style keys to Theme.ui, use generate_style() |
| How to hide toolbar completely? | Set bottom_toolbar=None, not return None from callable |
| How to handle NO_COLOR? | Check is_color_disabled() utility |
| How to format filters? | Reuse existing format_description() methods |

## Next Steps

1. Generate `data-model.md` with toolbar state and config schema
2. Generate `quickstart.md` with implementation guide
3. Proceed to `/speckit.tasks` for task breakdown
