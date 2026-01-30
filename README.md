# Schenesort v1.0.0

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

# AI-powered renaming (requires Ollama with a vision model)
schenesort describe ~/wallpapers --dry-run
schenesort describe ~/wallpapers -m llava:13b
```

## Commands

| Command    | Description                               |
|------------|-------------------------------------------|
| `sanitize` | Rename files to Unix-friendly format      |
| `validate` | Check image extensions match file content |
| `info`     | Show collection statistics                |
| `describe` | AI-rename images based on content (Ollama)|
| `metadata` | Manage XMP sidecar metadata               |

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

## AI-Powered Renaming

The `describe` command uses Ollama with a vision model to analyze images and generate descriptive filenames.

### Ollama Setup (Arch Linux)

```bash
# Install from AUR
yay -S ollama

# Enable and start the service
sudo systemctl enable ollama
sudo systemctl start ollama

# Pull a vision model
ollama pull llava           # Default, ~4GB
ollama pull llava:13b       # Larger/better, ~8GB

# Verify it works
ollama run llava "hello"
```

**GPU Support (NVIDIA):**
```bash
yay -S cuda cudnn
```
Ollama automatically detects and uses the GPU.

### Usage

```bash
# Preview what would be renamed
schenesort describe ~/wallpapers --dry-run

# Rename with a specific model
schenesort describe ~/wallpapers -m llava:13b

# Process subdirectories
schenesort describe ~/wallpapers -r
```

The generated description is automatically sanitized to create Unix-friendly filenames.

## Metadata Management

Store metadata in XMP sidecar files (`.xmp`) alongside images without modifying the original files.

```bash
# Show metadata for images
schenesort metadata show ~/wallpapers
schenesort metadata show image.jpg

# Set metadata manually
schenesort metadata set image.jpg -d "Mountain sunset landscape"
schenesort metadata set image.jpg -t "nature,sunset,mountains"
schenesort metadata set image.jpg -a "peaceful"  # add tag
schenesort metadata set image.jpg -s "https://unsplash.com/..."

# Generate metadata with AI
schenesort metadata generate ~/wallpapers --dry-run
schenesort metadata generate ~/wallpapers -m llava
schenesort metadata generate ~/wallpapers --overwrite  # replace existing
```

### XMP Sidecar Format

```
~/wallpapers/
├── mountain_sunset.jpg
├── mountain_sunset.jpg.xmp   ← metadata stored here
├── cyberpunk_city.png
└── cyberpunk_city.png.xmp
```

Metadata is stored in standard XMP format, compatible with photo managers like digiKam, darktable, and Lightroom.
