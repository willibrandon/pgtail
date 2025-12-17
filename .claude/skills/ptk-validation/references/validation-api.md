# Validation API Reference

Complete API for prompt_toolkit validation system.

## Validator Base Class

```python
from abc import ABCMeta, abstractmethod

class Validator(metaclass=ABCMeta):
    @abstractmethod
    def validate(self, document: Document) -> None:
        """
        Validate the document.
        Raise ValidationError if invalid.
        """
        pass

    async def validate_async(self, document: Document) -> None:
        """
        Async validation (optional).
        Default implementation calls sync validate().
        """
        self.validate(document)
```

## ValidationError

```python
class ValidationError(Exception):
    def __init__(
        self,
        cursor_position: int = 0,
        message: str = "",
    ):
        self.cursor_position = cursor_position
        self.message = message
```

**Parameters:**
- `cursor_position` - Where to place cursor (0 = start of text)
- `message` - Error message to display

## Validator.from_callable

```python
Validator.from_callable(
    validate_func: Callable[[str], bool],
    error_message: str = "Invalid input",
    move_cursor_to_end: bool = False,
) -> Validator
```

**Example:**
```python
validator = Validator.from_callable(
    lambda text: '@' in text,
    error_message='Must contain @',
    move_cursor_to_end=True,
)
```

## ThreadedValidator

```python
from prompt_toolkit.validation import ThreadedValidator

threaded = ThreadedValidator(SlowValidator())
```

Runs validation in a background thread to prevent UI blocking.

## ConditionalValidator

```python
from prompt_toolkit.validation import ConditionalValidator
from prompt_toolkit.filters import Condition

validator = ConditionalValidator(
    base_validator,
    filter=Condition(lambda: validation_enabled),
)
```

## DynamicValidator

```python
from prompt_toolkit.validation import DynamicValidator

def get_validator():
    if mode == 'email':
        return email_validator
    return default_validator

validator = DynamicValidator(get_validator)
```

## DummyValidator

```python
from prompt_toolkit.validation import DummyValidator

validator = DummyValidator()  # Always passes
```

## ValidationState

```python
from prompt_toolkit.validation import ValidationState

# Enum values
ValidationState.VALID      # Validation passed
ValidationState.INVALID    # Validation failed
ValidationState.UNKNOWN    # Not yet validated
```

## Buffer Integration

```python
buffer = Buffer(
    validator=my_validator,
    validate_while_typing=False,  # Validate only on accept
)

# Check validation state
state = buffer.validation_state  # ValidationState enum
error = buffer.validation_error  # ValidationError or None

# Manual validation
is_valid = buffer.validate(set_cursor=True)

# Async validation
is_valid = await buffer.validate_async(set_cursor=True)
```

## Custom Validators

### Multi-Field Validator

```python
class MultiFieldValidator(Validator):
    def __init__(self, field_validators: dict):
        """
        field_validators = {
            'name': name_validator,
            'email': email_validator,
        }
        """
        self.field_validators = field_validators

    def validate(self, document):
        # Parse fields from document
        fields = self._parse_fields(document.text)

        for field_name, validator in self.field_validators.items():
            if field_name in fields:
                field_doc = Document(fields[field_name])
                try:
                    validator.validate(field_doc)
                except ValidationError as e:
                    raise ValidationError(
                        message=f'{field_name}: {e.message}'
                    )
```

### Composite Validator

```python
class CompositeValidator(Validator):
    def __init__(self, validators: list):
        self.validators = validators

    def validate(self, document):
        errors = []
        for validator in self.validators:
            try:
                validator.validate(document)
            except ValidationError as e:
                errors.append(e.message)

        if errors:
            raise ValidationError(
                message='; '.join(errors),
                cursor_position=len(document.text),
            )
```

### Pattern-Based Validator

```python
import re

class PatternValidator(Validator):
    PATTERNS = {
        'email': r'^[\w.-]+@[\w.-]+\.\w+$',
        'phone': r'^\+?[\d\s-]{10,}$',
        'url': r'^https?://[\w.-]+(?:/[\w.-]*)*$',
        'ip': r'^(?:\d{1,3}\.){3}\d{1,3}$',
    }

    def __init__(self, pattern_name: str):
        if pattern_name not in self.PATTERNS:
            raise ValueError(f'Unknown pattern: {pattern_name}')
        self.pattern = re.compile(self.PATTERNS[pattern_name])
        self.pattern_name = pattern_name

    def validate(self, document):
        if not self.pattern.match(document.text):
            raise ValidationError(
                message=f'Invalid {self.pattern_name} format',
                cursor_position=len(document.text),
            )
```

### Async Remote Validator

```python
class RemoteValidator(Validator):
    def __init__(self, api_url):
        self.api_url = api_url
        self._cache = {}

    async def validate_async(self, document):
        text = document.text

        # Check cache first
        if text in self._cache:
            if not self._cache[text]:
                raise ValidationError(message='Already exists')
            return

        # Call remote API
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.api_url}/check/{text}') as resp:
                data = await resp.json()
                is_valid = data.get('available', False)
                self._cache[text] = is_valid

                if not is_valid:
                    raise ValidationError(message='Already exists')

    def validate(self, document):
        # Sync fallback - use cache only
        text = document.text
        if text in self._cache and not self._cache[text]:
            raise ValidationError(message='Already exists')
```

## Validation Display

### Validation Toolbar

```python
from prompt_toolkit.layout import Window, ConditionalContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.filters import has_validation_error

def create_validation_toolbar(buffer):
    def get_text():
        if buffer.validation_error:
            return [('class:validation.error', buffer.validation_error.message)]
        return []

    return ConditionalContainer(
        content=Window(
            FormattedTextControl(get_text),
            height=1,
            style='class:validation-toolbar',
        ),
        filter=has_validation_error,
    )
```

### Inline Validation Display

```python
from prompt_toolkit.layout.processors import Processor, Transformation

class ValidationProcessor(Processor):
    def __init__(self, buffer):
        self.buffer = buffer

    def apply_transformation(self, transformation_input):
        if self.buffer.validation_error:
            # Add error indicator at cursor position
            error_pos = self.buffer.validation_error.cursor_position
            # ... add visual indicator
        return Transformation(transformation_input.fragments)
```

## Best Practices

1. **Keep validation fast** - Use ThreadedValidator for slow checks
2. **Provide clear messages** - Include what's wrong and how to fix
3. **Position cursor helpfully** - Point to the error location
4. **Use validate_while_typing carefully** - Can be annoying for complex rules
5. **Cache async validation results** - Avoid repeated API calls
6. **Combine validators** - Use CompositeValidator for multiple rules

```python
# Production validator pattern
class ProductionValidator(Validator):
    def __init__(self):
        self.validators = [
            self._check_not_empty,
            self._check_length,
            self._check_format,
        ]

    def validate(self, document):
        for check in self.validators:
            error = check(document.text)
            if error:
                raise ValidationError(**error)

    def _check_not_empty(self, text):
        if not text.strip():
            return {'message': 'Input required', 'cursor_position': 0}

    def _check_length(self, text):
        if len(text) < 3:
            return {
                'message': f'Minimum 3 characters (currently {len(text)})',
                'cursor_position': len(text),
            }

    def _check_format(self, text):
        if not text.isalnum():
            return {'message': 'Only letters and numbers allowed'}
```
