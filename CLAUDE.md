# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Schenesort is a CLI tool for managing wallpaper collections. It sanitizes filenames (lowercase, spaces to underscores), validates image file extensions against actual content, and can rename images based on AI-generated descriptions using Ollama.

## Commands

```bash
# Run the CLI
uv run schenesort --help
uv run schenesort sanitize <path> --dry-run
uv run schenesort validate <path> --fix
uv run schenesort info <path>
uv run schenesort describe <path> --dry-run -m llava

# Testing
uv run pytest tests/ -v              # Run all tests
uv run pytest tests/test_sanitize.py -v  # Run specific test file
uv run pytest -k "test_sanitize_dry"     # Run tests matching pattern

# Linting
uv run ruff check src/ tests/        # Check for issues
uv run ruff check src/ tests/ --fix  # Auto-fix issues
uv run ruff format src/ tests/       # Format code

# Pre-commit
uv run pre-commit run --all-files    # Run all hooks manually
```

## Architecture

- `src/schenesort/cli.py` - All CLI commands using Typer. Contains `sanitize`, `validate`, `info`, and `describe` commands plus helper functions `sanitize_filename()`, `get_actual_image_type()`, `validate_extension()`, and `describe_image()`.
- `tests/test_sanitize.py` - Unit tests for `sanitize_filename()` function
- `tests/test_cli.py` - Integration tests for CLI commands using `typer.testing.CliRunner`

Image type detection uses the `filetype` library to read file headers (Python 3.13 removed `imghdr`). AI image description uses the `ollama` library to communicate with a local Ollama instance running a vision model (default: llava).
