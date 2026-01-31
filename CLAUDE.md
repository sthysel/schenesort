# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Schenesort is a CLI tool for managing wallpaper collections. It sanitises filenames (lowercase, spaces to underscores), validates image file extensions against actual content, indexes metadata into SQLite for fast querying, provides a terminal UI browser, and can rename images based on AI-generated descriptions using Ollama.

## Commands

```bash
# Run the CLI
uv run schenesort --help
uv run schenesort sanitise <path> --dry-run
uv run schenesort validate <path> --fix
uv run schenesort info <path>
uv run schenesort describe <path> --dry-run -m llava
uv run schenesort browse <path>
uv run schenesort index <path>
uv run schenesort get --mood peaceful --screen 4K
uv run schenesort stats
uv run schenesort cleanup <path> --dry-run
uv run schenesort config --create

# Testing
uv run pytest tests/ -v              # Run all tests
uv run pytest tests/test_sanitise.py -v  # Run specific test file
uv run pytest -k "test_sanitise_dry"     # Run tests matching pattern

# Linting
uv run ruff check src/ tests/        # Check for issues
uv run ruff check src/ tests/ --fix  # Auto-fix issues
uv run ruff format src/ tests/       # Format code

# Pre-commit
uv run pre-commit run --all-files    # Run all hooks manually
```

## Architecture

- `src/schenesort/cli.py` - All CLI commands using Typer. Contains `sanitise`, `validate`, `info`, `browse`, `index`, `get`, `stats`, `cleanup`, `config`, `describe` commands plus helper functions `sanitise_filename()`, `get_actual_image_type()`, `validate_extension()`, `get_image_dimensions()`, and `describe_image()`.
- `src/schenesort/config.py` - Configuration file handling. Loads settings from `~/.config/schenesort/config.toml`.
- `src/schenesort/xmp.py` - XMP sidecar file handling. Contains `ImageMetadata` dataclass, `read_xmp()`, `write_xmp()`, and `get_recommended_screen()`.
- `src/schenesort/db.py` - SQLite database for collection indexing. Contains `WallpaperDB` class with query and stats methods.
- `src/schenesort/tui/` - Terminal UI browser using Textual.
  - `app.py` - `WallpaperBrowser` main application
  - `widgets/image_preview.py` - Image display widget using textual-image
  - `widgets/metadata_panel.py` - Metadata display panel
- `schenesort.yazi/` - Yazi file manager plugin for previewing metadata
- `tests/test_sanitise.py` - Unit tests for `sanitise_filename()` function
- `tests/test_cli.py` - Integration tests for CLI commands using `typer.testing.CliRunner`

Image type detection uses the `filetype` library to read file headers (Python 3.13 removed `imghdr`). AI image description uses the `ollama` library to communicate with a local Ollama instance running a vision model (default: llava).
