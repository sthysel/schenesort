# Schenesort Yazi Plugin

A [Yazi](https://yazi-rs.github.io/) previewer plugin that displays XMP metadata from Schenesort sidecar files alongside image previews.

## Features

- Displays image metadata (description, scene, tags, mood, style, colors, etc.) in the preview pane
- Renders image in top 70% of preview, metadata in bottom 30%
- Falls back to standard image preview when no XMP sidecar exists
- Uses exiftool for metadata extraction

## Requirements

- [Yazi](https://yazi-rs.github.io/) file manager
- [ExifTool](https://exiftool.org/) for reading XMP metadata
  ```bash
  # Arch Linux
  sudo pacman -S perl-image-exiftool

  # Debian/Ubuntu
  sudo apt install libimage-exiftool-perl

  # macOS
  brew install exiftool
  ```

## Installation

1. **Copy the plugin:**
   ```bash
   mkdir -p ~/.config/yazi/plugins/schenesort.yazi
   cp main.lua ~/.config/yazi/plugins/schenesort.yazi/
   ```

2. **Install ExifTool config for custom namespace:**
   ```bash
   mkdir -p ~/.config/ExifTool
   cp schenesort.config ~/.config/ExifTool/
   ```

3. **Configure Yazi to use the plugin:**

   Add to `~/.config/yazi/yazi.toml`:
   ```toml
   [plugin]
   prepend_previewers = [
       { mime = "image/*", run = "schenesort" },
   ]
   ```

## Usage

Navigate to any image file in Yazi. If the image has a `.xmp` sidecar file (e.g., `photo.jpg.xmp` for `photo.jpg`), the plugin will display the metadata below the image preview.

### Metadata Fields Displayed

| Field | Description |
|-------|-------------|
| Description | Short AI-generated description |
| Scene | Detailed scene description |
| Tags | Keywords/tags |
| Mood | Visual mood (peaceful, dramatic, etc.) |
| Style | Art style (photography, digital art, etc.) |
| Colors | Dominant colors |
| Time | Time of day depicted |
| Subject | Primary subject category |
| AI Model | Model used for metadata generation |

## How It Works

1. When previewing an image, the plugin checks for a corresponding `.xmp` sidecar file
2. If found, it uses exiftool to extract the Schenesort metadata
3. The preview area is split: image on top, metadata below
4. If no sidecar exists, standard Yazi image preview is used

## Troubleshooting

### Metadata not showing

1. Verify the XMP sidecar exists:
   ```bash
   ls -la image.jpg.xmp
   ```

2. Check exiftool can read the file:
   ```bash
   exiftool image.jpg.xmp
   ```

3. Verify the exiftool config is installed:
   ```bash
   exiftool -config ~/.config/ExifTool/schenesort.config -XMP-schenesort:all image.jpg.xmp
   ```

### Plugin not loading

Check Yazi's plugin path:
```bash
ls ~/.config/yazi/plugins/schenesort.yazi/main.lua
```

Verify `yazi.toml` configuration is correct and restart Yazi.

## License

Same as Schenesort - see main project repository.
