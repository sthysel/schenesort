"""Schenesort CLI - Wallpaper collection management tool."""

import base64
import re
from pathlib import Path
from typing import Annotated

import filetype
import ollama
import typer

from schenesort.config import load_config
from schenesort.xmp import get_recommended_screen, get_xmp_path, read_xmp, write_xmp

app = typer.Typer(
    name="schenesort",
    help="Wallpaper collection management CLI tool.",
    no_args_is_help=True,
)

VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}


def sanitise_filename(name: str) -> str:
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


def get_image_dimensions(filepath: Path) -> tuple[int, int]:
    """Get image width and height using PIL."""
    try:
        from PIL import Image

        with Image.open(filepath) as img:
            return img.size  # (width, height)
    except Exception:
        return 0, 0


@app.command()
def sanitise(
    path: Annotated[Path, typer.Argument(help="Directory or file to sanitise")],
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
        new_name = sanitise_filename(old_name)

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
def cleanup(
    path: Annotated[Path, typer.Argument(help="Directory to clean up")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Show what would be deleted")
    ] = False,
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Process directories recursively")
    ] = False,
) -> None:
    """Delete orphaned XMP sidecar files that have no corresponding image."""
    path = path.resolve()

    if not path.exists():
        typer.echo(f"Error: Path '{path}' does not exist.", err=True)
        raise typer.Exit(1)

    if not path.is_dir():
        typer.echo(f"Error: Path '{path}' is not a directory.", err=True)
        raise typer.Exit(1)

    pattern = "**/*.xmp" if recursive else "*.xmp"
    xmp_files = list(path.glob(pattern))

    if not xmp_files:
        typer.echo("No XMP sidecar files found.")
        raise typer.Exit(0)

    orphaned_count = 0
    total_size = 0

    for xmp_path in xmp_files:
        # The image path is the XMP path without the .xmp suffix
        # e.g., "image.jpg.xmp" -> "image.jpg"
        image_path = xmp_path.parent / xmp_path.stem

        if not image_path.exists():
            size = xmp_path.stat().st_size
            total_size += size

            if dry_run:
                typer.echo(f"Would delete: {xmp_path}")
            else:
                xmp_path.unlink()
                typer.echo(f"Deleted: {xmp_path}")

            orphaned_count += 1

    if orphaned_count == 0:
        typer.echo("No orphaned XMP sidecars found.")
    else:
        action = "Would delete" if dry_run else "Deleted"
        size_kb = total_size / 1024
        typer.echo(f"\n{action} {orphaned_count} orphaned sidecar(s) ({size_kb:.1f} KB).")


@app.command()
def index(
    path: Annotated[Path, typer.Argument(help="Directory to index")],
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Process directories recursively")
    ] = True,
    prune: Annotated[
        bool, typer.Option("--prune", "-p", help="Remove entries for deleted files")
    ] = False,
    rebuild: Annotated[bool, typer.Option("--rebuild", help="Rebuild index from scratch")] = False,
) -> None:
    """Build or update the SQLite index of wallpaper metadata."""
    from schenesort.db import WallpaperDB

    path = path.resolve()

    if not path.exists():
        typer.echo(f"Error: Path '{path}' does not exist.", err=True)
        raise typer.Exit(1)

    if not path.is_dir():
        typer.echo(f"Error: Path '{path}' is not a directory.", err=True)
        raise typer.Exit(1)

    with WallpaperDB() as db:
        if rebuild:
            typer.echo("Rebuilding index from scratch...")
            db.clear()

        pattern = "**/*" if recursive else "*"
        image_files = [
            f
            for f in path.glob(pattern)
            if f.is_file() and f.suffix.lower() in VALID_IMAGE_EXTENSIONS
        ]

        typer.echo(f"Indexing {len(image_files)} image(s)...")

        indexed = 0
        for filepath in image_files:
            xmp_path = get_xmp_path(filepath)
            if xmp_path.exists():
                metadata = read_xmp(filepath)
                db.index_image(filepath, metadata)
                indexed += 1

        db.commit()

        if prune:
            valid_paths = {str(f) for f in image_files}
            pruned = db.prune(valid_paths)
            if pruned:
                typer.echo(f"Pruned {pruned} removed file(s) from index.")

        typer.echo(f"Indexed {indexed} wallpaper(s) with metadata.")

        # Show stats
        stats = db.stats()
        typer.echo(f"\nDatabase: {db.db_path}")
        typer.echo(f"Total indexed: {stats.get('total_wallpapers', 0)}")
        typer.echo(f"With metadata: {stats.get('with_metadata', 0)}")


@app.command()
def get(
    tag: Annotated[str | None, typer.Option("--tag", "-t", help="Filter by tag")] = None,
    mood: Annotated[str | None, typer.Option("--mood", "-m", help="Filter by mood")] = None,
    color: Annotated[str | None, typer.Option("--color", "-c", help="Filter by color")] = None,
    style: Annotated[str | None, typer.Option("--style", "-s", help="Filter by style")] = None,
    subject: Annotated[str | None, typer.Option("--subject", help="Filter by subject")] = None,
    time: Annotated[str | None, typer.Option("--time", help="Filter by time of day")] = None,
    screen: Annotated[
        str | None, typer.Option("--screen", help="Filter by recommended screen (4K, 1440p, etc)")
    ] = None,
    min_width: Annotated[
        int | None, typer.Option("--min-width", help="Minimum width in pixels")
    ] = None,
    min_height: Annotated[
        int | None, typer.Option("--min-height", help="Minimum height in pixels")
    ] = None,
    search: Annotated[
        str | None, typer.Option("--search", "-q", help="Search description, scene, style, subject")
    ] = None,
    limit: Annotated[
        int | None, typer.Option("--limit", "-n", help="Maximum number of results")
    ] = None,
    random: Annotated[
        bool, typer.Option("--random", "-R", help="Return results in random order")
    ] = False,
    one: Annotated[
        bool, typer.Option("--one", "-1", help="Return single random result (shortcut for -R -n1)")
    ] = False,
    paths_only: Annotated[
        bool, typer.Option("--paths-only", "-p", help="Output only file paths (for scripting)")
    ] = False,
    browse: Annotated[
        bool, typer.Option("--browse", "-b", help="Open results in TUI browser")
    ] = False,
) -> None:
    """Query wallpapers by metadata attributes."""
    from schenesort.db import WallpaperDB

    if one:
        random = True
        limit = 1

    with WallpaperDB() as db:
        results = db.query(
            tag=tag,
            mood=mood,
            color=color,
            style=style,
            subject=subject,
            time_of_day=time,
            screen=screen,
            min_width=min_width,
            min_height=min_height,
            search=search,
            limit=limit,
            random=random,
        )

        if not results:
            typer.echo("No wallpapers found matching criteria.", err=True)
            raise typer.Exit(1)

        if browse:
            from schenesort.tui import WallpaperBrowser

            files = [Path(r["path"]) for r in results]
            app_instance = WallpaperBrowser(files=files)
            app_instance.run()
        elif paths_only:
            for r in results:
                typer.echo(r["path"])
        else:
            typer.echo(f"Found {len(results)} wallpaper(s):\n")
            for r in results:
                typer.echo(f"{r['path']}")
                if r.get("description"):
                    typer.echo(f"  {r['description']}")
                details = []
                if r.get("style"):
                    details.append(r["style"])
                if r.get("subject"):
                    details.append(r["subject"])
                if r.get("recommended_screen"):
                    details.append(r["recommended_screen"])
                if details:
                    typer.echo(f"  [{', '.join(details)}]")
                typer.echo()


@app.command()
def stats() -> None:
    """Show statistics about the indexed wallpaper collection."""
    from schenesort.db import WallpaperDB

    with WallpaperDB() as db:
        s = db.stats()

        if not s.get("total_wallpapers"):
            typer.echo("No wallpapers indexed. Run 'schenesort index <path>' first.")
            raise typer.Exit(1)

        typer.echo(f"Database: {db.db_path}\n")
        typer.echo(f"Total wallpapers: {s['total_wallpapers']}")
        typer.echo(f"With metadata: {s['with_metadata']}")

        if s.get("by_screen"):
            typer.echo("\nBy screen size:")
            for screen, count in s["by_screen"].items():
                typer.echo(f"  {screen}: {count}")

        if s.get("by_style"):
            typer.echo("\nBy style:")
            for style, count in s["by_style"].items():
                typer.echo(f"  {style}: {count}")

        if s.get("by_subject"):
            typer.echo("\nBy subject:")
            for subject, count in s["by_subject"].items():
                typer.echo(f"  {subject}: {count}")

        if s.get("top_tags"):
            typer.echo("\nTop tags:")
            for tag, count in list(s["top_tags"].items())[:10]:
                typer.echo(f"  {tag}: {count}")

        if s.get("top_moods"):
            typer.echo("\nTop moods:")
            for mood, count in s["top_moods"].items():
                typer.echo(f"  {mood}: {count}")

        if s.get("top_colors"):
            typer.echo("\nTop colors:")
            for color, count in s["top_colors"].items():
                typer.echo(f"  {color}: {count}")


@app.command()
def browse(
    path: Annotated[
        Path | None,
        typer.Argument(help="Directory or file to browse (default: config wallpaper path)"),
    ] = None,
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Browse directories recursively")
    ] = False,
) -> None:
    """Browse wallpapers in a terminal UI with image preview and metadata display."""
    from schenesort.tui import WallpaperBrowser

    if path is None:
        cfg = load_config()
        if cfg.wallpaper_path:
            path = Path(cfg.wallpaper_path).expanduser()
        else:
            typer.echo("Error: No path provided and no wallpaper path configured.", err=True)
            typer.echo("Set paths.wallpaper in config or provide a path argument.", err=True)
            raise typer.Exit(1)

    path = path.resolve()

    if not path.exists():
        typer.echo(f"Error: Path '{path}' does not exist.", err=True)
        raise typer.Exit(1)

    app_instance = WallpaperBrowser(path, recursive=recursive)
    app_instance.run()


@app.command()
def config(
    create: Annotated[
        bool, typer.Option("--create", "-c", help="Create default config file if missing")
    ] = False,
) -> None:
    """Show or create the configuration file."""
    from schenesort.config import create_default_config, get_config_path

    config_path = get_config_path()

    if create:
        already_existed = config_path.exists()
        path = create_default_config()
        typer.echo(f"Config file: {path}")
        typer.echo("(already existed)" if already_existed else "(created)")

    if config_path.exists():
        typer.echo(f"Config file: {config_path}\n")
        typer.echo(config_path.read_text())
    elif not create:
        typer.echo(f"Config file: {config_path}")
        typer.echo("(file does not exist, use --create to create)")


DEFAULT_MODEL = "llava"


def get_ollama_settings(
    host: str | None = None, model: str | None = None
) -> tuple[str | None, str]:
    """Get Ollama host and model, using config defaults if not specified."""
    config = load_config()
    effective_host = host if host is not None else (config.ollama_host or None)
    effective_model = model if model is not None else config.ollama_model
    return effective_host, effective_model


@app.command()
def models(
    host: Annotated[
        str | None,
        typer.Option("--host", "-H", help="Ollama server URL (e.g., http://server:11434)"),
    ] = None,
) -> None:
    """List available models on the Ollama server."""
    effective_host, _ = get_ollama_settings(host=host)
    try:
        client = ollama.Client(host=effective_host) if effective_host else ollama
        response = client.list()

        if not response.models:
            typer.echo("No models found.")
            raise typer.Exit(0)

        server_info = effective_host or "localhost:11434"
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
        str | None, typer.Option("--model", "-m", help="Ollama vision model to use")
    ] = None,
    cpu: Annotated[bool, typer.Option("--cpu", help="Use CPU only (no GPU acceleration)")] = False,
    host: Annotated[
        str | None,
        typer.Option("--host", "-H", help="Ollama server URL (e.g., http://server:11434)"),
    ] = None,
) -> None:
    """Rename images based on AI-generated descriptions using Ollama."""
    effective_host, effective_model = get_ollama_settings(host=host, model=model)

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

    typer.echo(f"Processing {len(image_files)} image(s) with model '{effective_model}'...\n")

    renamed_count = 0
    skipped_count = 0

    for filepath in image_files:
        typer.echo(f"Analyzing: {filepath.name}...", nl=False)

        description = describe_image(filepath, effective_model, use_cpu=cpu, host=effective_host)
        if not description:
            typer.echo(" [FAILED]")
            skipped_count += 1
            continue

        # Create new filename from description
        new_stem = sanitise_filename(description)
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
            # Rename any existing XMP sidecar first
            old_xmp = get_xmp_path(filepath)
            if old_xmp.exists():
                new_xmp = get_xmp_path(new_path)
                old_xmp.rename(new_xmp)

            filepath.rename(new_path)
            typer.echo(f"  Renamed: {filepath.name} -> {new_name}")

            # Save description to XMP sidecar
            metadata = read_xmp(new_path)
            metadata.description = description
            metadata.ai_model = effective_model

            # Add image dimensions
            width, height = get_image_dimensions(new_path)
            if width and height:
                metadata.width = width
                metadata.height = height
                metadata.recommended_screen = get_recommended_screen(width, height)

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
            if metadata.width and metadata.height:
                typer.echo(f"  Dimensions: {metadata.width} x {metadata.height}")
                if metadata.recommended_screen:
                    typer.echo(f"  Best for: {metadata.recommended_screen}")
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
        str | None, typer.Option("--model", "-m", help="Ollama vision model to use")
    ] = None,
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
    effective_host, effective_model = get_ollama_settings(host=host, model=model)

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

    typer.echo(f"Generating metadata for {len(image_files)} image(s) with '{effective_model}'...\n")

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

        result = analyze_image(filepath, effective_model, use_cpu=cpu, host=effective_host)
        if not result:
            typer.echo(" [FAILED]")
            skipped_count += 1
            continue

        description = result.get("description", "")
        typer.echo(f" -> {description}")

        if dry_run:
            if rename:
                new_stem = sanitise_filename(str(description))
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
                new_stem = sanitise_filename(str(description))
                new_name = new_stem + filepath.suffix.lower()

                if filepath.name != new_name:
                    new_path = filepath.parent / new_name

                    # Handle filename collisions
                    counter = 1
                    while new_path.exists() and new_path != filepath:
                        new_name = f"{new_stem}_{counter}{filepath.suffix.lower()}"
                        new_path = filepath.parent / new_name
                        counter += 1

                    # Rename any existing XMP sidecar first
                    old_xmp = get_xmp_path(filepath)
                    if old_xmp.exists():
                        new_xmp = get_xmp_path(new_path)
                        old_xmp.rename(new_xmp)

                    filepath.rename(new_path)
                    target_path = new_path
                    typer.echo(f"  Renamed: {filepath.name} -> {new_name}")

            # Build and save metadata
            metadata = existing
            metadata.description = str(description)
            metadata.ai_model = effective_model
            scene = result.get("scene")
            if isinstance(scene, str):
                metadata.scene = scene
            tags = result.get("tags")
            if isinstance(tags, list):
                metadata.tags = tags
            mood = result.get("mood")
            if isinstance(mood, list):
                metadata.mood = mood
            style = result.get("style")
            if isinstance(style, str):
                metadata.style = style
            colors = result.get("colors")
            if isinstance(colors, list):
                metadata.colors = colors
            time_val = result.get("time")
            if isinstance(time_val, str):
                metadata.time_of_day = time_val
            subject = result.get("subject")
            if isinstance(subject, str):
                metadata.subject = subject

            # Add image dimensions
            width, height = get_image_dimensions(target_path)
            if width and height:
                metadata.width = width
                metadata.height = height
                metadata.recommended_screen = get_recommended_screen(width, height)

            write_xmp(target_path, metadata)
            typer.echo(f"  Saved to {get_xmp_path(target_path).name}")

        generated_count += 1

    action = "Would generate" if dry_run else "Generated"
    typer.echo(f"\n{action} metadata for {generated_count} file(s), skipped {skipped_count}.")


@metadata_app.command("update-dimensions")
def metadata_update_dimensions(
    path: Annotated[Path, typer.Argument(help="Image file or directory")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Show what would be updated")
    ] = False,
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Process directories recursively")
    ] = False,
) -> None:
    """Update existing XMP sidecars with image dimensions (no AI inference)."""
    path = path.resolve()

    if not path.exists():
        typer.echo(f"Error: Path '{path}' does not exist.", err=True)
        raise typer.Exit(1)

    if path.is_file():
        files = [path]
    else:
        pattern = "**/*" if recursive else "*"
        files = [f for f in path.glob(pattern) if f.is_file()]

    # Filter to image files that have existing sidecars
    image_files = [
        f for f in files if f.suffix.lower() in VALID_IMAGE_EXTENSIONS and get_xmp_path(f).exists()
    ]

    if not image_files:
        typer.echo("No image files with existing XMP sidecars found.")
        raise typer.Exit(0)

    typer.echo(f"Updating dimensions for {len(image_files)} image(s)...\n")

    updated_count = 0
    skipped_count = 0

    for filepath in image_files:
        width, height = get_image_dimensions(filepath)

        if not width or not height:
            typer.echo(f"Skipping: {filepath.name} (could not read dimensions)")
            skipped_count += 1
            continue

        recommended = get_recommended_screen(width, height)

        if dry_run:
            typer.echo(f"Would update: {filepath.name} -> {width}x{height} ({recommended})")
        else:
            metadata = read_xmp(filepath)
            metadata.width = width
            metadata.height = height
            metadata.recommended_screen = recommended
            write_xmp(filepath, metadata)
            typer.echo(f"Updated: {filepath.name} -> {width}x{height} ({recommended})")

        updated_count += 1

    action = "Would update" if dry_run else "Updated"
    typer.echo(f"\n{action} {updated_count} sidecar(s), skipped {skipped_count}.")


@app.command()
def collage(
    output: Annotated[Path, typer.Argument(help="Output PNG file path")],
    tag: Annotated[str | None, typer.Option("--tag", "-t", help="Filter by tag")] = None,
    mood: Annotated[str | None, typer.Option("--mood", "-m", help="Filter by mood")] = None,
    color: Annotated[str | None, typer.Option("--color", "-c", help="Filter by color")] = None,
    style: Annotated[str | None, typer.Option("--style", "-s", help="Filter by style")] = None,
    subject: Annotated[str | None, typer.Option("--subject", help="Filter by subject")] = None,
    time: Annotated[str | None, typer.Option("--time", help="Filter by time of day")] = None,
    screen: Annotated[
        str | None, typer.Option("--screen", help="Filter by recommended screen (4K, 1440p, etc)")
    ] = None,
    min_width: Annotated[
        int | None, typer.Option("--min-width", help="Minimum width in pixels")
    ] = None,
    min_height: Annotated[
        int | None, typer.Option("--min-height", help="Minimum height in pixels")
    ] = None,
    search: Annotated[
        str | None, typer.Option("--search", "-q", help="Search description, scene, style, subject")
    ] = None,
    cols: Annotated[int, typer.Option("--cols", help="Number of columns (1-4)")] = 2,
    rows: Annotated[int, typer.Option("--rows", help="Number of rows (1-4)")] = 2,
    tile_width: Annotated[
        int, typer.Option("--tile-width", "-w", help="Width of each tile in pixels")
    ] = 480,
    tile_height: Annotated[
        int, typer.Option("--tile-height", "-h", help="Height of each tile in pixels")
    ] = 270,
    random: Annotated[bool, typer.Option("--random", "-R", help="Select images randomly")] = True,
) -> None:
    """Create a collage of wallpapers matching the given criteria (max 4x4 grid)."""
    from PIL import Image

    from schenesort.db import WallpaperDB

    # Validate grid size
    if cols < 1 or cols > 4:
        typer.echo("Error: --cols must be between 1 and 4.", err=True)
        raise typer.Exit(1)
    if rows < 1 or rows > 4:
        typer.echo("Error: --rows must be between 1 and 4.", err=True)
        raise typer.Exit(1)

    num_images = cols * rows

    with WallpaperDB() as db:
        results = db.query(
            tag=tag,
            mood=mood,
            color=color,
            style=style,
            subject=subject,
            time_of_day=time,
            screen=screen,
            min_width=min_width,
            min_height=min_height,
            search=search,
            limit=num_images,
            random=random,
        )

        if not results:
            typer.echo("No wallpapers found matching criteria.", err=True)
            raise typer.Exit(1)

        if len(results) < num_images:
            typer.echo(
                f"Warning: Only found {len(results)} image(s), "
                f"need {num_images} for {cols}x{rows} grid."
            )

        # Create collage canvas
        collage_width = cols * tile_width
        collage_height = rows * tile_height
        collage_img = Image.new("RGB", (collage_width, collage_height), color=(0, 0, 0))

        typer.echo(f"Creating {cols}x{rows} collage ({collage_width}x{collage_height})...")

        for idx, r in enumerate(results):
            if idx >= num_images:
                break

            filepath = Path(r["path"])
            row = idx // cols
            col = idx % cols

            try:
                with Image.open(filepath) as img:
                    # Convert to RGB if necessary (handles RGBA, palette, etc.)
                    if img.mode != "RGB":
                        img = img.convert("RGB")

                    # Resize to fit tile while preserving aspect ratio, then crop to fill
                    img_ratio = img.width / img.height
                    tile_ratio = tile_width / tile_height

                    if img_ratio > tile_ratio:
                        # Image is wider - fit by height, crop width
                        new_height = tile_height
                        new_width = int(tile_height * img_ratio)
                    else:
                        # Image is taller - fit by width, crop height
                        new_width = tile_width
                        new_height = int(tile_width / img_ratio)

                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # Center crop to tile size
                    left = (new_width - tile_width) // 2
                    top = (new_height - tile_height) // 2
                    img = img.crop((left, top, left + tile_width, top + tile_height))

                    # Paste into collage
                    x = col * tile_width
                    y = row * tile_height
                    collage_img.paste(img, (x, y))

                    typer.echo(f"  [{row},{col}] {filepath.name}")

            except Exception as e:
                typer.echo(f"  [{row},{col}] Failed to load {filepath.name}: {e}", err=True)

        # Save collage
        output = output.resolve()
        if not output.suffix.lower() == ".png":
            output = output.with_suffix(".png")

        collage_img.save(output, "PNG")
        typer.echo(f"\nSaved collage to: {output}")


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
