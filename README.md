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
| `metadata show` | Display XMP sidecar metadata         |
| `metadata set` | Manually set metadata fields          |
| `metadata generate` | Generate metadata with AI (Ollama) |
| `metadata embed` | Embed sidecar data into image files  |

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

## Local model renaming

The `describe` command uses Ollama with a vision model to analyze images and generate descriptive filenames.

### Ollama Setup (Arch Linux)

```bash
# Install from AUR (CPU only)
yay -S ollama

# For NVIDIA GPU support, also install:
yay -S ollama-cuda

# Enable and start the service
sudo systemctl enable ollama
sudo systemctl start ollama

# Pull a vision model
ollama pull llava           # Default, ~4GB
ollama pull llava:13b       # Larger/better, ~8GB

# Verify it works
ollama run llava "hello"

# Verify GPU is being used
ollama ps
# Should show "100% GPU" not "100% CPU"
```

**Note:** On Arch, you need **both** `ollama` and `ollama-cuda` packages for GPU acceleration. The `ollama-cuda` package provides the CUDA library that the base `ollama` package loads at runtime. After installing `ollama-cuda`, restart the service:

```bash
sudo systemctl restart ollama
```

**Known Issue:** There's a CUDA bug where API-based image processing crashes while interactive mode works. If you see "model runner has unexpectedly stopped" errors, workarounds:

```bash
# Option 1: Prefix schenesort commands (temporary)
CUDA_VISIBLE_DEVICES="" schenesort describe ~/wallpapers

# Option 2: Run Ollama in CPU mode (permanent)
sudo systemctl edit ollama
# Add: Environment="CUDA_VISIBLE_DEVICES="
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

See [ollama-setup.md](ollama-setup.md) for details.

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

# Generate using remote Ollama server
schenesort metadata generate ~/wallpaper --host http://promaxgb10-6dbe:11434 --model llava:13b --overwrite
```

### Re-inference Behavior

When running `metadata generate`, existing descriptions are preserved by default:

| Sidecar exists? | Description populated? | Will re-inference? | Will rename? |
|-----------------|------------------------|--------------------|--------------|
| No              | N/A                    | Yes                | Yes          |
| Yes             | No/empty               | Yes                | Yes          |
| Yes             | Yes                    | No (skipped)       | No           |

By default, files are renamed based on the AI-generated description. The sidecar follows the image (e.g., `mountain.jpg` → `sunset_over_peaks.jpg` with `sunset_over_peaks.jpg.xmp`).

Options:
- `--overwrite` - force re-inference for all images regardless of existing metadata
- `--no-rename` - generate metadata only, keep original filenames

### XMP Sidecar Format

```
~/wallpapers/
├── mountain_sunset.jpg
├── mountain_sunset.jpg.xmp   ← metadata stored here
├── cyberpunk_city.png
└── cyberpunk_city.png.xmp
```

Metadata is stored in standard XMP format, compatible with photo managers like digiKam, darktable, and Lightroom.

### Embedding Metadata into Image Files

Use `metadata embed` to write sidecar metadata directly into image files (requires `exiftool`):

```bash
# Preview what would be embedded
schenesort metadata embed ~/wallpapers --dry-run

# Embed metadata into images
schenesort metadata embed ~/wallpapers

# Process recursively
schenesort metadata embed ~/wallpapers -r
```

This writes to standard IPTC/XMP fields that photo managers understand:

| Sidecar Field | Embedded As |
|---------------|-------------|
| description + scene | IPTC:Caption-Abstract, XMP:Description |
| tags | IPTC:Keywords, XMP:Subject |
| mood, style, colors, time, subject | Sidecar only (no standard field) |

The sidecar remains the source of truth for all fields; embedding copies compatible fields into the image for broader tool compatibility.
