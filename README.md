# Schenesort v0.0.6

A CLI tool for managing wallpaper collections.

## Installation

```bash
uv sync
```

## Usage

```bash
# Show collection info
schenesort info ~/wallpapers

# Sanitize filenames (preview)
schenesort sanitize ~/wallpapers --dry-run

# Sanitize filenames
schenesort sanitize ~/wallpapers -r

# Validate image extensions
schenesort validate ~/wallpapers --fix
```

## Commands

| Command    | Description                               |
|------------|-------------------------------------------|
| `sanitize` | Rename files to Unix-friendly format      |
| `validate` | Check image extensions match file content |
| `info`     | Show collection statistics                |

## Filename Sanitization Rules

The `sanitize` command applies these rules to make filenames Unix-friendly:

| Rule                        | Example                              |
|-----------------------------|--------------------------------------|
| Lowercase                   | `HelloWorld.JPG` → `helloworld.jpg`  |
| Spaces → underscore         | `my file.jpg` → `my_file.jpg`        |
| Remove punctuation          | `file(1)!.jpg` → `file1.jpg`         |
| Collapse underscores        | `a___b.jpg` → `a_b.jpg`              |
| Collapse hyphens            | `a---b.jpg` → `a-b.jpg`              |
| Strip leading/trailing `_-` | `_file_.jpg` → `file.jpg`            |
| Remove dots in stem         | `file.backup.jpg` → `filebackup.jpg` |
| Preserve hidden files       | `.hidden` → `.hidden`                |
| Empty stem fallback         | `!@#$.jpg` → `unnamed.jpg`           |

**Preserved characters:** alphanumeric, underscore, hyphen, extension dot, unicode letters
