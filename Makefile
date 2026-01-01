.PHONY: help run test test-perf lint format build clean shell docs docs-serve

# Detect OS for platform-specific commands
ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
    UV := $(USERPROFILE)\.local\bin\uv.exe
else
    DETECTED_OS := $(shell uname -s)
    UV := uv
endif

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  run        Run pgtail from source"
	@echo "  test       Run pytest (excludes performance tests)"
	@echo "  test-perf  Run performance tests only"
	@echo "  lint       Run ruff linter"
	@echo "  format     Format code with ruff"
	@echo "  build      Build standalone executable"
	@echo "  clean      Remove build artifacts"
	@echo "  shell      Enter virtual environment shell"
	@echo "  docs       Build documentation site"
	@echo "  docs-serve Serve documentation locally"

shell:
ifeq ($(DETECTED_OS),Windows)
	@echo "Entering venv shell (type 'exit' to leave)"
	@cmd /k ".venv\Scripts\activate.bat"
else
	@echo "Entering venv shell (type 'exit' to leave)"
	@bash -c "source .venv/bin/activate && exec bash"
endif

run:
	$(UV) run python -m pgtail_py

test:
	$(UV) run python -m pytest tests/ -v -m "not performance"

test-perf:
	$(UV) run python -m pytest tests/ -v -m "performance"

lint:
	$(UV) run ruff check pgtail_py/

format:
	$(UV) run ruff format pgtail_py/

build:
	$(UV) run pyinstaller --onefile --name pgtail pgtail_py/__main__.py

clean:
ifeq ($(DETECTED_OS),Windows)
	-@if exist build rd /s /q build
	-@if exist dist rd /s /q dist
	-@if exist .pytest_cache rd /s /q .pytest_cache
	-@if exist .ruff_cache rd /s /q .ruff_cache
	-@if exist pgtail_py\__pycache__ rd /s /q pgtail_py\__pycache__
	-@if exist tests\__pycache__ rd /s /q tests\__pycache__
	-@if exist site rd /s /q site
else
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/ site/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
endif

docs:
	$(UV) run --extra docs mkdocs build

docs-serve:
	$(UV) run --extra docs mkdocs serve
