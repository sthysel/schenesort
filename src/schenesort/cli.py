"""Schenesort CLI - Wallpaper collection management tool."""

import re
from pathlib import Path
from typing import Annotated

import filetype
import typer

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


if __name__ == "__main__":
    app()
