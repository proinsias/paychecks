# paychecks Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-22

## Active Technologies

- Python 3.12 + Typer (CLI), Rich (terminal output), pdfplumber (PDF extraction), (001-paycheck-w2-validator)

## Project Structure

```text
src/
tests/
```

## Commands

```bash
# Install
uv pip install -e .

# Run tests with coverage
uv run pytest --cov=src/paychecks --cov-report=term-missing

# Unit tests only
uv run pytest tests/unit/ -v

# Lint
uv run ruff check .
uv run ruff format --check .

# CLI entry point
paychecks --help
```

## Code Style

Python 3.12: Follow standard conventions

## Recent Changes

- 001-paycheck-w2-validator: Added Python 3.12 + Typer (CLI), Rich (terminal output), pdfplumber (PDF extraction),

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
