.PHONY: help run test lint format build clean shell

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  run     Run pgtail from source"
	@echo "  test    Run pytest"
	@echo "  lint    Run ruff linter"
	@echo "  format  Format code with ruff"
	@echo "  build   Build standalone executable"
	@echo "  clean   Remove build artifacts"
	@echo "  shell   Enter virtual environment shell"

shell:
	@echo "Entering venv shell (type 'exit' to leave)"
	@bash -c "source .venv/bin/activate && exec bash"

run:
	uv run python -m pgtail_py

test:
	uv run python -m pytest tests/ -v

lint:
	uv run ruff check pgtail_py/

format:
	uv run ruff format pgtail_py/

build:
	uv run pyinstaller --onefile --name pgtail pgtail_py/__main__.py

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
