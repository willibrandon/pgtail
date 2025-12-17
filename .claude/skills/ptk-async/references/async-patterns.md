# Async Patterns for prompt_toolkit

Production patterns for async prompt_toolkit applications.

## Basic Async Application

```python
import asyncio
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl

class AsyncApp:
    def __init__(self):
        self.data = "Loading..."
        self.kb = KeyBindings()
        self._setup_bindings()

    def _setup_bindings(self):
        @self.kb.add('c-c')
        def exit_(event):
            event.app.exit()

        @self.kb.add('r')
        async def refresh(event):
            self.data = "Refreshing..."
            event.app.invalidate()
            self.data = await self._fetch_data()
            event.app.invalidate()

    async def _fetch_data(self):
        await asyncio.sleep(1)  # Simulate API call
        return f"Data loaded at {asyncio.get_event_loop().time()}"

    def _get_text(self):
        return self.data

    def create_app(self):
        return Application(
            layout=Layout(Window(FormattedTextControl(self._get_text))),
            key_bindings=self.kb,
            full_screen=True,
        )

    async def run(self):
        app = self.create_app()
        # Load data before showing UI
        self.data = await self._fetch_data()
        return await app.run_async()


if __name__ == '__main__':
    async_app = AsyncApp()
    asyncio.run(async_app.run())
```

## Real-Time Updates

### Clock/Timer Pattern

```python
class RealtimeApp:
    def __init__(self):
        self.time_str = ""
        self._running = True

    async def _update_time(self, app):
        import datetime
        while self._running:
            self.time_str = datetime.datetime.now().strftime('%H:%M:%S')
            app.invalidate()
            await asyncio.sleep(1)

    async def run(self):
        app = Application(
            layout=Layout(Window(FormattedTextControl(lambda: self.time_str))),
            full_screen=True,
        )

        # Start background task
        update_task = asyncio.create_task(self._update_time(app))

        try:
            await app.run_async()
        finally:
            self._running = False
            update_task.cancel()
            try:
                await update_task
            except asyncio.CancelledError:
                pass
```

### Progress Bar Pattern

```python
class ProgressApp:
    def __init__(self):
        self.progress = 0
        self.total = 100
        self.status = "Idle"

    def _get_progress_bar(self):
        filled = int(self.progress / self.total * 50)
        bar = '█' * filled + '░' * (50 - filled)
        return [
            ('class:progress.bar', f'[{bar}]'),
            ('', f' {self.progress}/{self.total}'),
            ('', f'\n{self.status}'),
        ]

    async def _process_items(self, app):
        self.status = "Processing..."
        for i in range(self.total + 1):
            self.progress = i
            app.invalidate()
            await asyncio.sleep(0.05)  # Simulate work
        self.status = "Complete!"
        app.invalidate()

    async def run(self):
        kb = KeyBindings()

        @kb.add('s')
        async def start(event):
            await self._process_items(event.app)

        @kb.add('c-c')
        def exit_(event):
            event.app.exit()

        app = Application(
            layout=Layout(Window(FormattedTextControl(self._get_progress_bar))),
            key_bindings=kb,
            full_screen=True,
        )
        await app.run_async()
```

## Concurrent Operations

### Parallel Data Loading

```python
class DashboardApp:
    def __init__(self):
        self.users = None
        self.orders = None
        self.metrics = None

    async def _load_all_data(self):
        # Load all data concurrently
        self.users, self.orders, self.metrics = await asyncio.gather(
            self._fetch_users(),
            self._fetch_orders(),
            self._fetch_metrics(),
        )

    async def _fetch_users(self):
        await asyncio.sleep(0.5)
        return ["Alice", "Bob", "Charlie"]

    async def _fetch_orders(self):
        await asyncio.sleep(0.8)
        return [{"id": 1}, {"id": 2}]

    async def _fetch_metrics(self):
        await asyncio.sleep(0.3)
        return {"revenue": 1000, "visitors": 500}

    async def run(self):
        # Show loading state
        app = Application(
            layout=Layout(Window(FormattedTextControl("Loading..."))),
            full_screen=True,
        )

        async def init_and_run():
            await self._load_all_data()
            # Update layout with data
            app.invalidate()
            await app.run_async()

        await init_and_run()
```

### Producer-Consumer Pattern

```python
class StreamingApp:
    def __init__(self):
        self.messages = []
        self.queue = asyncio.Queue()

    async def _producer(self):
        """Simulate incoming messages"""
        import random
        while True:
            await asyncio.sleep(random.uniform(0.5, 2))
            await self.queue.put(f"Message at {asyncio.get_event_loop().time():.2f}")

    async def _consumer(self, app):
        """Process messages and update UI"""
        while True:
            message = await self.queue.get()
            self.messages.append(message)
            self.messages = self.messages[-10:]  # Keep last 10
            app.invalidate()
            self.queue.task_done()

    def _get_messages(self):
        if not self.messages:
            return "Waiting for messages..."
        return '\n'.join(self.messages)

    async def run(self):
        kb = KeyBindings()

        @kb.add('c-c')
        def exit_(event):
            event.app.exit()

        app = Application(
            layout=Layout(Window(FormattedTextControl(self._get_messages))),
            key_bindings=kb,
            full_screen=True,
        )

        producer = asyncio.create_task(self._producer())
        consumer = asyncio.create_task(self._consumer(app))

        try:
            await app.run_async()
        finally:
            producer.cancel()
            consumer.cancel()
```

## Debouncing and Throttling

### Debounced Search

```python
class SearchApp:
    def __init__(self):
        self.query = ""
        self.results = []
        self._search_task = None

    async def _search(self, query):
        # Debounce: wait before searching
        await asyncio.sleep(0.3)

        # Perform search
        self.results = await self._fetch_results(query)

    async def _fetch_results(self, query):
        await asyncio.sleep(0.2)  # Simulate API
        return [f"Result for '{query}' #{i}" for i in range(5)]

    def _on_text_changed(self, buffer):
        self.query = buffer.text

        # Cancel previous search
        if self._search_task:
            self._search_task.cancel()

        # Start new debounced search
        if self.query:
            self._search_task = asyncio.create_task(self._search(self.query))
```

### Throttled Updates

```python
class ThrottledApp:
    def __init__(self):
        self._last_update = 0
        self._min_interval = 0.1  # Max 10 updates/second

    def _throttled_invalidate(self, app):
        import time
        now = time.time()
        if now - self._last_update >= self._min_interval:
            self._last_update = now
            app.invalidate()
```

## External Command Execution

### Using run_in_terminal

```python
from prompt_toolkit.application import run_in_terminal
import subprocess

class ShellApp:
    async def _run_command(self, event, command):
        def execute():
            print(f"Running: {command}")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
            )
            print(result.stdout)
            if result.stderr:
                print(f"Errors: {result.stderr}")
            input("Press Enter to continue...")

        await run_in_terminal(execute)

    def create_app(self):
        kb = KeyBindings()

        @kb.add('!')
        async def run_shell(event):
            await self._run_command(event, 'ls -la')

        @kb.add('c-c')
        def exit_(event):
            event.app.exit()

        return Application(
            layout=Layout(Window(FormattedTextControl("Press ! to run shell"))),
            key_bindings=kb,
            full_screen=True,
        )
```

### Async Subprocess

```python
class AsyncSubprocessApp:
    def __init__(self):
        self.output = ""

    async def _run_async_command(self, command):
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()
        self.output = stdout.decode() + stderr.decode()
```

## Error Handling

### Graceful Error Recovery

```python
class RobustApp:
    def __init__(self):
        self.error = None
        self.data = None

    async def _safe_fetch(self, app):
        try:
            self.data = await self._fetch_data()
            self.error = None
        except Exception as e:
            self.error = str(e)
            self.data = None
        finally:
            app.invalidate()

    async def _fetch_data(self):
        await asyncio.sleep(0.5)
        import random
        if random.random() < 0.3:
            raise ConnectionError("Network error")
        return "Data loaded successfully"

    def _get_display(self):
        if self.error:
            return [('class:error', f"Error: {self.error}")]
        if self.data:
            return [('class:success', self.data)]
        return "Loading..."
```

### Timeout Handling

```python
class TimeoutApp:
    async def _fetch_with_timeout(self, timeout=5.0):
        try:
            return await asyncio.wait_for(
                self._slow_operation(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return "Operation timed out"

    async def _slow_operation(self):
        await asyncio.sleep(10)  # Simulate slow operation
        return "Done"
```

## Cleanup Patterns

### Proper Resource Cleanup

```python
class CleanupApp:
    def __init__(self):
        self._tasks = []
        self._connections = []

    async def run(self):
        app = self._create_app()

        try:
            await app.run_async()
        finally:
            await self._cleanup()

    async def _cleanup(self):
        # Cancel all background tasks
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Close connections
        for conn in self._connections:
            await conn.close()

        print("Cleanup complete")
```

### Context Manager Pattern

```python
class ContextApp:
    async def __aenter__(self):
        await self._initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._cleanup()
        return False

    async def _initialize(self):
        self.connection = await self._connect()

    async def _cleanup(self):
        await self.connection.close()


async def main():
    async with ContextApp() as app:
        await app.run()
```

## Testing Async Apps

```python
import pytest

@pytest.mark.asyncio
async def test_data_loading():
    app = AsyncApp()
    data = await app._fetch_data()
    assert data is not None

@pytest.mark.asyncio
async def test_concurrent_loading():
    app = DashboardApp()
    await app._load_all_data()
    assert app.users is not None
    assert app.orders is not None
    assert app.metrics is not None
```

## Best Practices

1. **Always use `async def` for I/O operations** in key handlers
2. **Cancel background tasks** on app exit to prevent leaks
3. **Use `asyncio.gather`** for parallel operations
4. **Debounce** expensive operations triggered by typing
5. **Handle errors gracefully** - don't let exceptions crash the UI
6. **Use `run_in_terminal`** for blocking operations that need stdout
7. **Throttle `invalidate()`** calls for high-frequency updates
8. **Set appropriate timeouts** for network operations
9. **Clean up resources** in finally blocks or context managers
10. **Test async code** with pytest-asyncio
