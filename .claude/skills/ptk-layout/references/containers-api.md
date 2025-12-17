# Container API Reference

Complete API signatures for prompt_toolkit layout containers.

## HSplit

```python
HSplit(
    children: Sequence[AnyContainer],
    align: VerticalAlign = VerticalAlign.JUSTIFY,
    padding: AnyDimension = 0,
    padding_char: str | None = None,
    padding_style: str = "",
    width: AnyDimension = None,
    height: AnyDimension = None,
    z_index: int | None = None,
    modal: bool = False,
    key_bindings: KeyBindingsBase | None = None,
    style: str | Callable[[], str] = "",
)
```

**Parameters:**
- `children` - Sequence of containers to stack vertically
- `align` - `VerticalAlign.TOP`, `CENTER`, `BOTTOM`, or `JUSTIFY`
- `padding` - Space between children
- `modal` - If True, key bindings are isolated to this container
- `style` - CSS-like style string applied to container

## VSplit

```python
VSplit(
    children: Sequence[AnyContainer],
    align: HorizontalAlign = HorizontalAlign.JUSTIFY,
    padding: AnyDimension = 0,
    padding_char: str | None = None,
    padding_style: str = "",
    width: AnyDimension = None,
    height: AnyDimension = None,
    z_index: int | None = None,
    modal: bool = False,
    key_bindings: KeyBindingsBase | None = None,
    style: str | Callable[[], str] = "",
)
```

**Parameters:** Same as HSplit but with `HorizontalAlign`.

## Window

```python
Window(
    content: UIControl | None = None,
    width: AnyDimension = None,
    height: AnyDimension = None,
    z_index: int | None = None,
    dont_extend_width: bool = False,
    dont_extend_height: bool = False,
    ignore_content_width: bool = False,
    ignore_content_height: bool = False,
    left_margins: Sequence[Margin] | None = None,
    right_margins: Sequence[Margin] | None = None,
    scroll_offsets: ScrollOffsets | None = None,
    allow_scroll_beyond_bottom: bool = False,
    wrap_lines: bool = False,
    get_vertical_scroll: Callable[..., int] | None = None,
    get_horizontal_scroll: Callable[..., int] | None = None,
    always_hide_cursor: bool = False,
    cursorline: bool = False,
    cursorcolumn: bool = False,
    colorcolumns: Callable[[], list[ColorColumn]] | list[ColorColumn] | None = None,
    align: WindowAlign = WindowAlign.LEFT,
    style: str | Callable[[], str] = "",
    char: str | Callable[[], str] | None = None,
    get_line_prefix: GetLinePrefixCallable | None = None,
)
```

**Key Parameters:**
- `content` - UIControl to display (BufferControl, FormattedTextControl, etc.)
- `char` - Character to fill empty space
- `wrap_lines` - Enable line wrapping
- `cursorline` - Highlight current line
- `left_margins`/`right_margins` - Margin controls (line numbers, scroll bars)

## FloatContainer

```python
FloatContainer(
    content: AnyContainer,
    floats: list[Float],
    modal: bool = False,
    key_bindings: KeyBindingsBase | None = None,
    style: str | Callable[[], str] = "",
    z_index: int | None = None,
)
```

## Float

```python
Float(
    content: AnyContainer,
    top: int | None = None,
    right: int | None = None,
    bottom: int | None = None,
    left: int | None = None,
    width: int | Callable[[], int] | None = None,
    height: int | Callable[[], int] | None = None,
    xcursor: bool = False,
    ycursor: bool = False,
    attach_to_window: AnyContainer | None = None,
    hide_when_covering_content: bool = False,
    allow_cover_cursor: bool = False,
    z_index: int | None = None,
    transparent: bool = False,
)
```

**Positioning:**
- Use `top`/`bottom`/`left`/`right` for absolute positioning
- Use `xcursor=True` to follow cursor horizontally
- Use `ycursor=True` to follow cursor vertically

## ConditionalContainer

```python
ConditionalContainer(
    content: AnyContainer,
    filter: FilterOrBool,
)
```

## DynamicContainer

```python
DynamicContainer(
    get_container: Callable[[], AnyContainer],
)
```

## ScrollablePane

```python
ScrollablePane(
    content: AnyContainer,
    scroll_offsets: ScrollOffsets | None = None,
    keep_cursor_visible: bool = True,
    keep_focused_window_visible: bool = True,
    max_available_height: int = 10000,
    display_arrows: bool = False,
    up_arrow_symbol: str = "^",
    down_arrow_symbol: str = "v",
)
```

## Dimension

```python
Dimension(
    min: int | None = None,
    max: int | None = None,
    weight: int | None = None,
    preferred: int | None = None,
)

# Class methods
Dimension.exact(value: int) -> Dimension
Dimension.zero() -> Dimension
```

**Weight distribution:** When multiple containers have `weight`, space is distributed proportionally.

## Layout

```python
Layout(
    container: AnyContainer,
    focused_element: FocusableElement | None = None,
)
```

**Methods:**
- `focus(element)` - Focus specific element
- `focus_next()` - Focus next focusable
- `focus_previous()` - Focus previous focusable
- `focus_last()` - Focus last used element
- `has_focus(element)` - Check if element has focus
- `get_focusable_windows()` - List of focusable windows
- `find_all_windows()` - All windows in layout

**Properties:**
- `current_window` - Currently focused Window
- `current_buffer` - Buffer of focused window (if any)
- `current_control` - UIControl of focused window
- `is_searching` - True if in search mode
- `search_buffer` - Search Buffer if searching
