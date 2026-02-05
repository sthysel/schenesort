"""Thumbnail cache management for gallery view."""

import hashlib
import os
from pathlib import Path

from PIL import Image

APP_NAME = "schenesort"

# Thumbnail dimensions - larger for better quality when rendered in terminal
# Terminal cells are ~32x14 chars, but textual-image benefits from more source pixels
THUMBNAIL_WIDTH = 320
THUMBNAIL_HEIGHT = 200


def get_cache_dir() -> Path:
    """Get the XDG cache directory for schenesort thumbnails."""
    xdg_cache = os.environ.get("XDG_CACHE_HOME", "")
    if xdg_cache:
        cache_dir = Path(xdg_cache) / APP_NAME / "thumbnails"
    else:
        cache_dir = Path.home() / ".cache" / APP_NAME / "thumbnails"
    return cache_dir


def get_thumbnail_path(image_path: Path) -> Path:
    """Get the thumbnail path for an image.

    Uses MD5 hash of the absolute path to create a unique filename.
    """
    # Use absolute path for consistent hashing
    abs_path = str(image_path.resolve())
    path_hash = hashlib.md5(abs_path.encode()).hexdigest()
    return get_cache_dir() / f"{path_hash}.jpg"


def thumbnail_exists(image_path: Path) -> bool:
    """Check if a thumbnail exists for the given image."""
    thumb_path = get_thumbnail_path(image_path)
    if not thumb_path.exists():
        return False

    # Check if thumbnail is newer than original
    try:
        orig_mtime = image_path.stat().st_mtime
        thumb_mtime = thumb_path.stat().st_mtime
        return thumb_mtime >= orig_mtime
    except OSError:
        return False


def generate_thumbnail(image_path: Path, force: bool = False) -> Path | None:
    """Generate a thumbnail for the given image.

    Args:
        image_path: Path to the original image
        force: If True, regenerate even if thumbnail exists

    Returns:
        Path to the thumbnail, or None if generation failed
    """
    if not force and thumbnail_exists(image_path):
        return get_thumbnail_path(image_path)

    thumb_path = get_thumbnail_path(image_path)

    try:
        # Ensure cache directory exists
        thumb_path.parent.mkdir(parents=True, exist_ok=True)

        with Image.open(image_path) as img:
            # Convert to RGB if necessary (handles RGBA, palette, etc.)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Calculate size preserving aspect ratio
            img.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS)

            # Save as JPEG with high quality for better terminal rendering
            img.save(thumb_path, "JPEG", quality=95, optimize=True)

        return thumb_path

    except Exception:
        # Clean up partial file if it exists
        if thumb_path.exists():
            thumb_path.unlink()
        return None


def clear_cache() -> int:
    """Clear all cached thumbnails.

    Returns:
        Number of thumbnails deleted
    """
    cache_dir = get_cache_dir()
    if not cache_dir.exists():
        return 0

    count = 0
    for thumb in cache_dir.glob("*.jpg"):
        try:
            thumb.unlink()
            count += 1
        except OSError:
            pass

    return count


def get_cache_stats() -> dict:
    """Get statistics about the thumbnail cache."""
    cache_dir = get_cache_dir()
    if not cache_dir.exists():
        return {"count": 0, "size_bytes": 0, "path": str(cache_dir)}

    thumbnails = list(cache_dir.glob("*.jpg"))
    total_size = sum(t.stat().st_size for t in thumbnails)

    return {
        "count": len(thumbnails),
        "size_bytes": total_size,
        "size_mb": total_size / (1024 * 1024),
        "path": str(cache_dir),
    }
