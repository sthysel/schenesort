"""Schenesort CLI - Wallpaper collection management tool."""

import base64
import re
from pathlib import Path
from typing import Annotated

import filetype
import ollama
import typer

from schenesort.xmp import get_xmp_path, read_xmp, write_xmp

app = typer.Typer(
    name="schenesort",
    help="Wallpaper collection management CLI tool.",
    no_args_is_help=True,
)

VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}


def sanitize_filename(name: str) -> str:
    """
    Sanitize filename to be Unix-friendly.

    Rules:
    - Convert to lowercase
    - Replace whitespace with underscores
    - Remove punctuation except underscore, hyphen, dot
    - Collapse consecutive underscores/hyphens
    - Remove leading/trailing underscores/hyphens from name (not extension)
    - Preserve hidden file prefix (leading dot)
    """
    if not name:
        return name

    # Handle hidden files (start with dot)
    hidden_prefix = ""
    if name.startswith("."):
        hidden_prefix = "."
        name = name[1:]
        if not name:
            return hidden_prefix

    # Split into stem and extension
    if "." in name:
        # Find the last dot for extension
        last_dot = name.rfind(".")
        stem = name[:last_dot]
        ext = name[last_dot:]
        # If ext is just a dot (no actual extension), treat as part of stem
        if ext == ".":
            stem = name
            ext = ""
    else:
        stem = name
        ext = ""

    # Lowercase
    stem = stem.lower()
    ext = ext.lower()

    # Replace whitespace with underscore
    stem = re.sub(r"\s+", "_", stem)

    # Remove unwanted punctuation (keep alphanumeric, underscore, hyphen)
    stem = re.sub(r"[^\w\-]", "", stem)

    # Collapse multiple underscores or hyphens
    stem = re.sub(r"_+", "_", stem)
    stem = re.sub(r"-+", "-", stem)
    stem = re.sub(r"[-_]{2,}", "_", stem)  # mixed sequences become single underscore

    # Remove leading/trailing underscores and hyphens
    stem = stem.strip("_-")

    # Handle edge case where stem becomes empty
    if not stem:
        stem = "unnamed"

    return hidden_prefix + stem + ext


def get_actual_image_type(filepath: Path) -> str | None:
    """Detect actual image type by reading file header."""
    kind = filetype.guess(filepath)
    if kind is None:
        return None
    if kind.mime.startswith("image/"):
        ext = kind.extension
        if ext == "jpeg":
            return ".jpg"
        return f".{ext}"
    return None


def validate_extension(filepath: Path) -> tuple[bool, str | None]:
    """
    Validate that a file's extension matches its actual content type.

    Returns:
        Tuple of (is_valid, actual_extension or None if not an image)
    """
    actual_type = get_actual_image_type(filepath)
    if actual_type is None:
        return False, None

    current_ext = filepath.suffix.lower()
    if current_ext in (".jpg", ".jpeg") and actual_type in (".jpg", ".jpeg"):
        return True, actual_type

    return current_ext == actual_type, actual_type


@app.command()
def sanitize(
    path: Annotated[Path, typer.Argument(help="Directory or file to sanitize")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Show what would be renamed")
    ] = False,
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Process directories recursively")
    ] = False,
) -> None:
    """Convert filenames to lowercase and replace spaces with underscores."""
    path = path.resolve()

    if not path.exists():
        typer.echo(f"Error: Path '{path}' does not exist.", err=True)
        raise typer.Exit(1)

    if path.is_file():
        files = [path]
    else:
        pattern = "**/*" if recursive else "*"
        files = [f for f in path.glob(pattern) if f.is_file()]

    renamed_count = 0
    for filepath in files:
        # Skip .xmp sidecar files - they follow their parent image
        if filepath.suffix.lower() == ".xmp":
            continue

        old_name = filepath.name
        new_name = sanitize_filename(old_name)

        if old_name != new_name:
            new_path = filepath.parent / new_name
            if dry_run:
                typer.echo(f"Would rename: {filepath} -> {new_path}")
            else:
                if new_path.exists():
                    typer.echo(
                        f"Skipping: {filepath} (target '{new_path}' already exists)",
                        err=True,
                    )
                    continue
                filepath.rename(new_path)
                typer.echo(f"Renamed: {old_name} -> {new_name}")

            # Handle associated XMP sidecar file
            old_xmp = get_xmp_path(filepath)
            if old_xmp.exists():
                new_xmp = get_xmp_path(new_path)
                if dry_run:
                    typer.echo(f"Would rename: {old_xmp} -> {new_xmp}")
                else:
                    if new_xmp.exists():
                        typer.echo(
                            f"Skipping: {old_xmp} (target '{new_xmp}' already exists)",
                            err=True,
                        )
                    else:
                        old_xmp.rename(new_xmp)
                        typer.echo(f"Renamed: {old_xmp.name} -> {new_xmp.name}")
                renamed_count += 1

            renamed_count += 1

    action = "Would rename" if dry_run else "Renamed"
    typer.echo(f"\n{action} {renamed_count} file(s).")


@app.command()
def validate(
    path: Annotated[Path, typer.Argument(help="Directory or file to validate")],
    fix: Annotated[bool, typer.Option("--fix", "-f", help="Fix incorrect extensions")] = False,
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Process directories recursively")
    ] = False,
) -> None:
    """Validate that image file extensions match their actual content type."""
    path = path.resolve()

    if not path.exists():
        typer.echo(f"Error: Path '{path}' does not exist.", err=True)
        raise typer.Exit(1)

    if path.is_file():
        files = [path]
    else:
        pattern = "**/*" if recursive else "*"
        files = [f for f in path.glob(pattern) if f.is_file()]

    valid_count = 0
    invalid_count = 0
    non_image_count = 0
    fixed_count = 0

    for filepath in files:
        if filepath.suffix.lower() not in VALID_IMAGE_EXTENSIONS:
            continue

        is_valid, actual_ext = validate_extension(filepath)

        if actual_ext is None:
            typer.echo(f"[NOT IMAGE] {filepath}")
            non_image_count += 1
        elif is_valid:
            valid_count += 1
        else:
            typer.echo(f"[INVALID] {filepath} (actual: {actual_ext})")
            invalid_count += 1

            if fix:
                new_path = filepath.with_suffix(actual_ext)
                if new_path.exists():
                    typer.echo(f"  Cannot fix: target '{new_path}' already exists", err=True)
                else:
                    filepath.rename(new_path)
                    typer.echo(f"  Fixed: {filepath.name} -> {new_path.name}")
                    fixed_count += 1

    typer.echo("\nValidation complete:")
    typer.echo(f"  Valid: {valid_count}")
    typer.echo(f"  Invalid: {invalid_count}")
    typer.echo(f"  Not images: {non_image_count}")
    if fix:
        typer.echo(f"  Fixed: {fixed_count}")


@app.command()
def info(
    path: Annotated[Path, typer.Argument(help="Directory to analyze")],
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Process directories recursively")
    ] = False,
) -> None:
    """Show information about wallpaper collection."""
    path = path.resolve()

    if not path.exists():
        typer.echo(f"Error: Path '{path}' does not exist.", err=True)
        raise typer.Exit(1)

    if not path.is_dir():
        typer.echo(f"Error: Path '{path}' is not a directory.", err=True)
        raise typer.Exit(1)

    pattern = "**/*" if recursive else "*"
    files = [f for f in path.glob(pattern) if f.is_file()]

    ext_counts: dict[str, int] = {}
    total_size = 0
    files_with_spaces = 0

    for filepath in files:
        ext = filepath.suffix.lower() or "(no extension)"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
        total_size += filepath.stat().st_size
        if " " in filepath.name:
            files_with_spaces += 1

    typer.echo(f"Collection: {path}")
    typer.echo(f"Total files: {len(files)}")
    typer.echo(f"Total size: {total_size / (1024 * 1024):.2f} MB")
    typer.echo(f"Files with spaces in name: {files_with_spaces}")
    typer.echo("\nExtensions:")
    for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]):
        typer.echo(f"  {ext}: {count}")


@app.command()
def browse(
    path: Annotated[Path, typer.Argument(help="Directory or file to browse")],
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Browse directories recursively")
    ] = False,
) -> None:
    """Browse wallpapers in a terminal UI with image preview and metadata display."""
    from schenesort.tui import WallpaperBrowser

    path = path.resolve()

    if not path.exists():
        typer.echo(f"Error: Path '{path}' does not exist.", err=True)
        raise typer.Exit(1)

    app_instance = WallpaperBrowser(path, recursive=recursive)
    app_instance.run()


DEFAULT_MODEL = "llava"


@app.command()
def models(
    host: Annotated[
        str | None,
        typer.Option("--host", "-H", help="Ollama server URL (e.g., http://server:11434)"),
    ] = None,
) -> None:
    """List available models on the Ollama server."""
    try:
        client = ollama.Client(host=host) if host else ollama
        response = client.list()

        if not response.models:
            typer.echo("No models found.")
            raise typer.Exit(0)

        server_info = host or "localhost:11434"
        typer.echo(f"Models on {server_info}:\n")

        for model in response.models:
            name = model.model
            size_gb = (model.size or 0) / (1024**3)
            param_size = model.details.parameter_size if model.details else ""
            typer.echo(f"  {name} ({size_gb:.1f} GB, {param_size})")

    except ollama.ResponseError as e:
        typer.echo(f"Ollama error: {e}", err=True)
        raise typer.Exit(1) from None
    except Exception as e:
        typer.echo(f"Error connecting to Ollama: {e}", err=True)
        raise typer.Exit(1) from None


DESCRIBE_PROMPT = """Describe this image in 3-5 words suitable for a filename.
Focus on the main subject and style. Be concise and specific.
Output ONLY the description, no punctuation, no explanation.
Example outputs: mountain sunset landscape, cyberpunk city night, abstract blue waves"""

ANALYZE_PROMPT = """Analyze this image and provide metadata in the following exact format.
Each field on its own line, use commas to separate multiple values.
Be concise and specific. Use lowercase.

Description: [3-5 word description for filename]
Scene: [1-3 sentence description of what the image depicts, including composition and atmosphere]
Tags: [comma-separated keywords, 3-6 tags]
Mood: [comma-separated moods like peaceful, dramatic, mysterious, vibrant, melancholic]
Style: [one of: photography, digital art, illustration, 3d render, anime, painting, pixel art]
Colors: [comma-separated dominant colors, 2-4 colors]
Time: [one of: day, night, sunset, sunrise, golden hour, overcast, or unknown]
Subject: [landscape, portrait, architecture, wildlife, abstract, space, urban, nature, fantasy]

Example output:
Description: neon cyberpunk city night
Tags: cyberpunk, city, neon, futuristic, rain
Mood: mysterious, vibrant
Style: digital art
Colors: purple, cyan, pink
Time: night
Subject: urban"""


def describe_image(
    filepath: Path,
    model: str = DEFAULT_MODEL,
    use_cpu: bool = False,
    host: str | None = None,
) -> str | None:
    """Use Ollama vision model to describe an image (simple description only)."""
    try:
        with open(filepath, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        options = {"num_gpu": 0} if use_cpu else {}
        client = ollama.Client(host=host) if host else ollama

        response = client.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": DESCRIBE_PROMPT,
                    "images": [image_data],
                }
            ],
            options=options,
        )
        return response["message"]["content"].strip()
    except ollama.ResponseError as e:
        typer.echo(f"Ollama error: {e}", err=True)
        return None
    except Exception as e:
        typer.echo(f"Error describing image: {e}", err=True)
        return None


def parse_metadata_response(response: str) -> dict[str, str | list[str]]:
    """Parse structured metadata response from vision model."""
    result: dict[str, str | list[str]] = {}

    for line in response.strip().split("\n"):
        if ":" not in line:
            continue

        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if not value:
            continue

        # Fields that should be lists
        if key in ("tags", "mood", "colors"):
            result[key] = [v.strip().lower() for v in value.split(",") if v.strip()]
        # Scene keeps original case (it's a sentence)
        elif key == "scene":
            result[key] = value
        else:
            result[key] = value.lower()

    return result


def analyze_image(
    filepath: Path,
    model: str = DEFAULT_MODEL,
    use_cpu: bool = False,
    host: str | None = None,
) -> dict[str, str | list[str]] | None:
    """Use Ollama vision model to analyze an image and extract full metadata."""
    try:
        with open(filepath, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        options = {"num_gpu": 0} if use_cpu else {}
        client = ollama.Client(host=host) if host else ollama

        response = client.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": ANALYZE_PROMPT,
                    "images": [image_data],
                }
            ],
            options=options,
        )
        return parse_metadata_response(response["message"]["content"])
    except ollama.ResponseError as e:
        typer.echo(f"Ollama error: {e}", err=True)
        return None
    except Exception as e:
        typer.echo(f"Error analyzing image: {e}", err=True)
        return None


@app.command()
@app.command("rename", hidden=True)
def describe(
    path: Annotated[Path, typer.Argument(help="Directory or file to describe and rename")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Show what would be renamed")
    ] = False,
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Process directories recursively")
    ] = False,
    model: Annotated[
        str, typer.Option("--model", "-m", help="Ollama vision model to use")
    ] = DEFAULT_MODEL,
    cpu: Annotated[bool, typer.Option("--cpu", help="Use CPU only (no GPU acceleration)")] = False,
    host: Annotated[
        str | None,
        typer.Option("--host", "-H", help="Ollama server URL (e.g., http://server:11434)"),
    ] = None,
) -> None:
    """Rename images based on AI-generated descriptions using Ollama."""
    path = path.resolve()

    if not path.exists():
        typer.echo(f"Error: Path '{path}' does not exist.", err=True)
        raise typer.Exit(1)

    if path.is_file():
        files = [path]
    else:
        pattern = "**/*" if recursive else "*"
        files = [f for f in path.glob(pattern) if f.is_file()]

    # Filter to only image files
    image_files = [f for f in files if f.suffix.lower() in VALID_IMAGE_EXTENSIONS]

    if not image_files:
        typer.echo("No image files found.")
        raise typer.Exit(0)

    typer.echo(f"Processing {len(image_files)} image(s) with model '{model}'...\n")

    renamed_count = 0
    skipped_count = 0

    for filepath in image_files:
        typer.echo(f"Analyzing: {filepath.name}...", nl=False)

        description = describe_image(filepath, model, use_cpu=cpu, host=host)
        if not description:
            typer.echo(" [FAILED]")
            skipped_count += 1
            continue

        # Create new filename from description
        new_stem = sanitize_filename(description)
        new_name = new_stem + filepath.suffix.lower()

        typer.echo(f" -> {description}")

        if filepath.name == new_name:
            typer.echo("  (no change needed)")
            continue

        new_path = filepath.parent / new_name

        # Handle filename collisions by adding a number
        counter = 1
        while new_path.exists() and new_path != filepath:
            new_name = f"{new_stem}_{counter}{filepath.suffix.lower()}"
            new_path = filepath.parent / new_name
            counter += 1

        if dry_run:
            typer.echo(f"  Would rename: {filepath.name} -> {new_name}")
        else:
            filepath.rename(new_path)
            typer.echo(f"  Renamed: {filepath.name} -> {new_name}")

            # Save description to XMP sidecar
            metadata = read_xmp(new_path)
            metadata.description = description
            metadata.ai_model = model
            write_xmp(new_path, metadata)
            typer.echo(f"  Saved metadata to {get_xmp_path(new_path).name}")
        renamed_count += 1

    action = "Would rename" if dry_run else "Renamed"
    typer.echo(f"\n{action} {renamed_count} file(s), skipped {skipped_count}.")


# Metadata subcommand group
metadata_app = typer.Typer(help="Manage image metadata in XMP sidecar files.")
app.add_typer(metadata_app, name="metadata")


@metadata_app.command("show")
def metadata_show(
    path: Annotated[Path, typer.Argument(help="Image file or directory")],
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Process directories recursively")
    ] = False,
) -> None:
    """Display metadata for image(s)."""
    path = path.resolve()

    if not path.exists():
        typer.echo(f"Error: Path '{path}' does not exist.", err=True)
        raise typer.Exit(1)

    if path.is_file():
        files = [path]
    else:
        pattern = "**/*" if recursive else "*"
        files = [f for f in path.glob(pattern) if f.is_file()]

    image_files = [f for f in files if f.suffix.lower() in VALID_IMAGE_EXTENSIONS]

    if not image_files:
        typer.echo("No image files found.")
        raise typer.Exit(0)

    for filepath in image_files:
        metadata = read_xmp(filepath)
        xmp_path = get_xmp_path(filepath)

        typer.echo(f"\n{filepath.name}")
        typer.echo(f"  XMP: {xmp_path.name if xmp_path.exists() else '(not found)'}")

        if metadata.is_empty():
            typer.echo("  (no metadata)")
        else:
            if metadata.description:
                typer.echo(f"  Description: {metadata.description}")
            if metadata.scene:
                typer.echo(f"  Scene: {metadata.scene}")
            if metadata.tags:
                typer.echo(f"  Tags: {', '.join(metadata.tags)}")
            if metadata.mood:
                typer.echo(f"  Mood: {', '.join(metadata.mood)}")
            if metadata.style:
                typer.echo(f"  Style: {metadata.style}")
            if metadata.colors:
                typer.echo(f"  Colors: {', '.join(metadata.colors)}")
            if metadata.time_of_day:
                typer.echo(f"  Time: {metadata.time_of_day}")
            if metadata.subject:
                typer.echo(f"  Subject: {metadata.subject}")
            if metadata.source:
                typer.echo(f"  Source: {metadata.source}")
            if metadata.ai_model:
                typer.echo(f"  AI Model: {metadata.ai_model}")


@metadata_app.command("set")
def metadata_set(
    path: Annotated[Path, typer.Argument(help="Image file")],
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Set description")
    ] = None,
    tags: Annotated[
        str | None, typer.Option("--tags", "-t", help="Set tags (comma-separated)")
    ] = None,
    add_tags: Annotated[
        str | None, typer.Option("--add-tags", "-a", help="Add tags (comma-separated)")
    ] = None,
    source: Annotated[
        str | None, typer.Option("--source", "-s", help="Set source URL/info")
    ] = None,
) -> None:
    """Set metadata fields for an image."""
    path = path.resolve()

    if not path.exists():
        typer.echo(f"Error: Path '{path}' does not exist.", err=True)
        raise typer.Exit(1)

    if not path.is_file():
        typer.echo("Error: Path must be a file.", err=True)
        raise typer.Exit(1)

    if path.suffix.lower() not in VALID_IMAGE_EXTENSIONS:
        typer.echo(f"Error: '{path.name}' is not a supported image format.", err=True)
        raise typer.Exit(1)

    # Read existing metadata
    metadata = read_xmp(path)

    # Update fields
    if description is not None:
        metadata.description = description

    if tags is not None:
        metadata.tags = [t.strip() for t in tags.split(",") if t.strip()]

    if add_tags is not None:
        new_tags = [t.strip() for t in add_tags.split(",") if t.strip()]
        for tag in new_tags:
            if tag not in metadata.tags:
                metadata.tags.append(tag)

    if source is not None:
        metadata.source = source

    # Write metadata
    write_xmp(path, metadata)
    typer.echo(f"Updated metadata for {path.name}")


@metadata_app.command("generate")
def metadata_generate(
    path: Annotated[Path, typer.Argument(help="Image file or directory")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Show what would be generated")
    ] = False,
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Process directories recursively")
    ] = False,
    model: Annotated[
        str, typer.Option("--model", "-m", help="Ollama vision model to use")
    ] = DEFAULT_MODEL,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Overwrite existing descriptions")
    ] = False,
    rename: Annotated[
        bool, typer.Option("--rename/--no-rename", help="Rename files based on description")
    ] = True,
    cpu: Annotated[bool, typer.Option("--cpu", help="Use CPU only (no GPU acceleration)")] = False,
    host: Annotated[
        str | None,
        typer.Option("--host", "-H", help="Ollama server URL (e.g., http://server:11434)"),
    ] = None,
) -> None:
    """Generate metadata using AI vision model and optionally rename files."""
    path = path.resolve()

    if not path.exists():
        typer.echo(f"Error: Path '{path}' does not exist.", err=True)
        raise typer.Exit(1)

    if path.is_file():
        files = [path]
    else:
        pattern = "**/*" if recursive else "*"
        files = [f for f in path.glob(pattern) if f.is_file()]

    image_files = [f for f in files if f.suffix.lower() in VALID_IMAGE_EXTENSIONS]

    if not image_files:
        typer.echo("No image files found.")
        raise typer.Exit(0)

    typer.echo(f"Generating metadata for {len(image_files)} image(s) with '{model}'...\n")

    generated_count = 0
    skipped_count = 0

    for filepath in image_files:
        # Check if metadata already exists
        existing = read_xmp(filepath)
        if existing.description and not overwrite:
            typer.echo(f"Skipping: {filepath.name} (already has description)")
            skipped_count += 1
            continue

        typer.echo(f"Analyzing: {filepath.name}...", nl=False)

        result = analyze_image(filepath, model, use_cpu=cpu, host=host)
        if not result:
            typer.echo(" [FAILED]")
            skipped_count += 1
            continue

        description = result.get("description", "")
        typer.echo(f" -> {description}")

        if dry_run:
            if rename:
                new_stem = sanitize_filename(str(description))
                new_name = new_stem + filepath.suffix.lower()
                typer.echo(f"  Would rename: {filepath.name} -> {new_name}")
            if result.get("scene"):
                typer.echo(f"  Scene: {result['scene']}")
            if result.get("tags"):
                typer.echo(f"  Tags: {', '.join(result['tags'])}")
            if result.get("mood"):
                typer.echo(f"  Mood: {', '.join(result['mood'])}")
            if result.get("style"):
                typer.echo(f"  Style: {result['style']}")
            if result.get("colors"):
                typer.echo(f"  Colors: {', '.join(result['colors'])}")
            if result.get("time"):
                typer.echo(f"  Time: {result['time']}")
            if result.get("subject"):
                typer.echo(f"  Subject: {result['subject']}")
            typer.echo("  (dry run, not saving)")
        else:
            # Rename file if requested
            target_path = filepath
            if rename:
                new_stem = sanitize_filename(str(description))
                new_name = new_stem + filepath.suffix.lower()

                if filepath.name != new_name:
                    new_path = filepath.parent / new_name

                    # Handle filename collisions
                    counter = 1
                    while new_path.exists() and new_path != filepath:
                        new_name = f"{new_stem}_{counter}{filepath.suffix.lower()}"
                        new_path = filepath.parent / new_name
                        counter += 1

                    filepath.rename(new_path)
                    target_path = new_path
                    typer.echo(f"  Renamed: {filepath.name} -> {new_name}")

            # Build and save metadata
            metadata = existing
            metadata.description = str(description)
            metadata.ai_model = model
            if isinstance(result.get("scene"), str):
                metadata.scene = result["scene"]
            if isinstance(result.get("tags"), list):
                metadata.tags = result["tags"]
            if isinstance(result.get("mood"), list):
                metadata.mood = result["mood"]
            if isinstance(result.get("style"), str):
                metadata.style = result["style"]
            if isinstance(result.get("colors"), list):
                metadata.colors = result["colors"]
            if isinstance(result.get("time"), str):
                metadata.time_of_day = result["time"]
            if isinstance(result.get("subject"), str):
                metadata.subject = result["subject"]
            write_xmp(target_path, metadata)
            typer.echo(f"  Saved to {get_xmp_path(target_path).name}")

        generated_count += 1

    action = "Would generate" if dry_run else "Generated"
    typer.echo(f"\n{action} metadata for {generated_count} file(s), skipped {skipped_count}.")


@metadata_app.command("embed")
def metadata_embed(
    path: Annotated[Path, typer.Argument(help="Image file or directory")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Show what would be embedded")
    ] = False,
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Process directories recursively")
    ] = False,
) -> None:
    """Embed XMP sidecar metadata into image files using exiftool."""
    import shutil
    import subprocess

    # Check for exiftool
    if not shutil.which("exiftool"):
        typer.echo("Error: exiftool not found. Install it first:", err=True)
        typer.echo("  Arch: pacman -S perl-image-exiftool", err=True)
        typer.echo("  Debian: apt install libimage-exiftool-perl", err=True)
        raise typer.Exit(1)

    path = path.resolve()

    if not path.exists():
        typer.echo(f"Error: Path '{path}' does not exist.", err=True)
        raise typer.Exit(1)

    if path.is_file():
        files = [path]
    else:
        pattern = "**/*" if recursive else "*"
        files = [f for f in path.glob(pattern) if f.is_file()]

    # Filter to image files that have sidecars
    image_files = [
        f for f in files if f.suffix.lower() in VALID_IMAGE_EXTENSIONS and get_xmp_path(f).exists()
    ]

    if not image_files:
        typer.echo("No image files with XMP sidecars found.")
        raise typer.Exit(0)

    typer.echo(f"Embedding metadata into {len(image_files)} image(s)...\n")

    embedded_count = 0
    skipped_count = 0

    for filepath in image_files:
        metadata = read_xmp(filepath)

        if metadata.is_empty():
            typer.echo(f"Skipping: {filepath.name} (empty sidecar)")
            skipped_count += 1
            continue

        # Build exiftool arguments
        args = ["exiftool", "-overwrite_original"]

        # Description: combine short description and scene for full context
        full_description = metadata.description
        if metadata.scene:
            full_description = f"{metadata.description}. {metadata.scene}"

        if full_description:
            args.extend([f"-IPTC:Caption-Abstract={full_description}"])
            args.extend([f"-XMP:Description={full_description}"])

        # Tags/Keywords
        if metadata.tags:
            for tag in metadata.tags:
                args.extend([f"-IPTC:Keywords={tag}"])
                args.extend([f"-XMP:Subject={tag}"])

        # Only description and tags have standard fields
        # Log what custom fields exist but can't be embedded in standard fields
        custom_fields = []
        if metadata.mood:
            custom_fields.append(f"mood: {', '.join(metadata.mood)}")
        if metadata.style:
            custom_fields.append(f"style: {metadata.style}")
        if metadata.colors:
            custom_fields.append(f"colors: {', '.join(metadata.colors)}")
        if metadata.time_of_day:
            custom_fields.append(f"time: {metadata.time_of_day}")
        if metadata.subject:
            custom_fields.append(f"subject: {metadata.subject}")

        args.append(str(filepath))

        if dry_run:
            typer.echo(f"Would embed: {filepath.name}")
            if full_description:
                ellipsis = "..." if len(full_description) > 80 else ""
                typer.echo(f"  Description: {full_description[:80]}{ellipsis}")
            if metadata.tags:
                typer.echo(f"  Keywords: {', '.join(metadata.tags)}")
            if custom_fields:
                typer.echo(f"  (sidecar-only: {'; '.join(custom_fields)})")
        else:
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode == 0:
                typer.echo(f"Embedded: {filepath.name}")
                embedded_count += 1
            else:
                typer.echo(f"Failed: {filepath.name} - {result.stderr.strip()}", err=True)
                skipped_count += 1
                continue

        if not dry_run:
            pass  # already counted above
        else:
            embedded_count += 1

    action = "Would embed" if dry_run else "Embedded"
    typer.echo(f"\n{action} metadata in {embedded_count} file(s), skipped {skipped_count}.")


if __name__ == "__main__":
    app()
