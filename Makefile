.PHONY: help run test test-perf lint format build build-test msi clean shell docs docs-serve

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
	@echo "  build      Build standalone executable with Nuitka"
	@echo "  build-test Verify build works (runs --version)"
	@echo "  msi        Build Windows MSI installer (Windows only, requires WiX)"
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
ifeq ($(DETECTED_OS),Windows)
	bash scripts/build-nuitka.sh
else
	./scripts/build-nuitka.sh
endif

build-test:
ifeq ($(DETECTED_OS),Windows)
	@echo "Testing build..."
	@dist\pgtail-windows-x86_64\pgtail.exe --version
	@echo.
	@echo "Testing list-instances command help..."
	@dist\pgtail-windows-x86_64\pgtail.exe list-instances --help
	@echo.
	@echo "Build test passed!"
else
	@echo "Testing build..."
	@./dist/pgtail-*/pgtail --version
	@echo ""
	@echo "Testing list-instances command help..."
	@./dist/pgtail-*/pgtail list-instances --help | head -5
	@echo ""
	@echo "Build test passed!"
endif

msi:
ifeq ($(DETECTED_OS),Windows)
	@echo "Building MSI installer..."
	@bash -c 'VERSION=$$(python -c "import tomllib; print(tomllib.load(open(\"pyproject.toml\",\"rb\"))[\"project\"][\"version\"])") && wix build wix/pgtail.wxs -d SourceDir=../dist/pgtail-windows-x86_64 -d Version=$$VERSION -arch x64 -out dist/pgtail-windows-x86_64.msi'
	@echo "MSI created: dist\pgtail-windows-x86_64.msi"
else
	@echo "Error: MSI build is only supported on Windows"
	@exit 1
endif

clean:
ifeq ($(DETECTED_OS),Windows)
	-@if exist build rd /s /q build
	-@if exist dist rd /s /q dist
	-@if exist .pytest_cache rd /s /q .pytest_cache
	-@if exist .ruff_cache rd /s /q .ruff_cache
	-@if exist pgtail_py\__pycache__ rd /s /q pgtail_py\__pycache__
	-@if exist tests\__pycache__ rd /s /q tests\__pycache__
	-@if exist site rd /s /q site
	-@if exist pgtail.build rd /s /q pgtail.build
	-@if exist pgtail.dist rd /s /q pgtail.dist
	-@if exist pgtail.onefile-build rd /s /q pgtail.onefile-build
else
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/ site/
	rm -rf pgtail.build/ pgtail.dist/ *.onefile-build/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
endif

docs:
	$(UV) run --extra docs mkdocs build

docs-serve:
	$(UV) run --extra docs mkdocs serve
