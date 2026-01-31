"""SQLite database for wallpaper collection indexing."""

import os
import sqlite3
from pathlib import Path

from schenesort.xmp import ImageMetadata, get_xmp_path

APP_NAME = "schenesort"


def get_data_dir() -> Path:
    """Get the XDG data directory for schenesort."""
    xdg_data = os.environ.get("XDG_DATA_HOME", "")
    if xdg_data:
        data_dir = Path(xdg_data) / APP_NAME
    else:
        data_dir = Path.home() / ".local" / "share" / APP_NAME
    return data_dir


def get_default_db_path() -> Path:
    """Get the default database path."""
    return get_data_dir() / "index.db"


DEFAULT_DB_PATH = get_default_db_path()

SCHEMA = """
CREATE TABLE IF NOT EXISTS wallpapers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    description TEXT,
    scene TEXT,
    style TEXT,
    time_of_day TEXT,
    subject TEXT,
    source TEXT,
    ai_model TEXT,
    width INTEGER,
    height INTEGER,
    recommended_screen TEXT,
    mtime REAL
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallpaper_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY (wallpaper_id) REFERENCES wallpapers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS moods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallpaper_id INTEGER NOT NULL,
    mood TEXT NOT NULL,
    FOREIGN KEY (wallpaper_id) REFERENCES wallpapers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS colors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallpaper_id INTEGER NOT NULL,
    color TEXT NOT NULL,
    FOREIGN KEY (wallpaper_id) REFERENCES wallpapers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wallpapers_description ON wallpapers(description);
CREATE INDEX IF NOT EXISTS idx_wallpapers_style ON wallpapers(style);
CREATE INDEX IF NOT EXISTS idx_wallpapers_subject ON wallpapers(subject);
CREATE INDEX IF NOT EXISTS idx_wallpapers_time_of_day ON wallpapers(time_of_day);
CREATE INDEX IF NOT EXISTS idx_wallpapers_recommended_screen ON wallpapers(recommended_screen);
CREATE INDEX IF NOT EXISTS idx_wallpapers_width ON wallpapers(width);
CREATE INDEX IF NOT EXISTS idx_wallpapers_height ON wallpapers(height);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
CREATE INDEX IF NOT EXISTS idx_moods_mood ON moods(mood);
CREATE INDEX IF NOT EXISTS idx_colors_color ON colors(color);
"""


class WallpaperDB:
    """SQLite database for wallpaper metadata."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: sqlite3.Connection | None = None

    def __enter__(self) -> "WallpaperDB":
        self.connect()
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def connect(self) -> None:
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def clear(self) -> None:
        """Clear all data from the database."""
        if not self.conn:
            return
        self.conn.execute("DELETE FROM colors")
        self.conn.execute("DELETE FROM moods")
        self.conn.execute("DELETE FROM tags")
        self.conn.execute("DELETE FROM wallpapers")
        self.conn.commit()

    def index_image(self, image_path: Path, metadata: ImageMetadata) -> None:
        """Add or update an image in the index."""
        if not self.conn:
            return

        xmp_path = get_xmp_path(image_path)
        mtime = xmp_path.stat().st_mtime if xmp_path.exists() else 0

        # Check if already indexed with same mtime
        cursor = self.conn.execute(
            "SELECT id, mtime FROM wallpapers WHERE path = ?", (str(image_path),)
        )
        row = cursor.fetchone()

        if row and row["mtime"] == mtime:
            return  # Already up to date

        # Delete existing entry if present
        if row:
            self.conn.execute("DELETE FROM wallpapers WHERE id = ?", (row["id"],))

        # Insert new entry
        cursor = self.conn.execute(
            """INSERT INTO wallpapers
               (path, filename, extension, description, scene, style, time_of_day,
                subject, source, ai_model, width, height, recommended_screen, mtime)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(image_path),
                image_path.name,
                image_path.suffix.lower(),
                metadata.description or None,
                metadata.scene or None,
                metadata.style or None,
                metadata.time_of_day or None,
                metadata.subject or None,
                metadata.source or None,
                metadata.ai_model or None,
                metadata.width or None,
                metadata.height or None,
                metadata.recommended_screen or None,
                mtime,
            ),
        )
        wallpaper_id = cursor.lastrowid

        # Insert tags
        for tag in metadata.tags:
            self.conn.execute(
                "INSERT INTO tags (wallpaper_id, tag) VALUES (?, ?)", (wallpaper_id, tag)
            )

        # Insert moods
        for mood in metadata.mood:
            self.conn.execute(
                "INSERT INTO moods (wallpaper_id, mood) VALUES (?, ?)", (wallpaper_id, mood)
            )

        # Insert colors
        for color in metadata.colors:
            self.conn.execute(
                "INSERT INTO colors (wallpaper_id, color) VALUES (?, ?)", (wallpaper_id, color)
            )

    def commit(self) -> None:
        if self.conn:
            self.conn.commit()

    def query(
        self,
        description: str | None = None,
        tag: str | None = None,
        mood: str | None = None,
        color: str | None = None,
        style: str | None = None,
        subject: str | None = None,
        time_of_day: str | None = None,
        screen: str | None = None,
        min_width: int | None = None,
        min_height: int | None = None,
        search: str | None = None,
        limit: int | None = None,
        random: bool = False,
    ) -> list[dict]:
        """Query wallpapers with filters."""
        if not self.conn:
            return []

        conditions = []
        params: list = []

        if description:
            conditions.append("w.description LIKE ?")
            params.append(f"%{description}%")

        if style:
            conditions.append("w.style LIKE ?")
            params.append(f"%{style}%")

        if subject:
            conditions.append("w.subject LIKE ?")
            params.append(f"%{subject}%")

        if time_of_day:
            conditions.append("w.time_of_day LIKE ?")
            params.append(f"%{time_of_day}%")

        if screen:
            conditions.append("w.recommended_screen LIKE ?")
            params.append(f"%{screen}%")

        if min_width:
            conditions.append("w.width >= ?")
            params.append(min_width)

        if min_height:
            conditions.append("w.height >= ?")
            params.append(min_height)

        if search:
            conditions.append(
                "(w.description LIKE ? OR w.scene LIKE ? OR w.style LIKE ? OR w.subject LIKE ?)"
            )
            params.extend([f"%{search}%"] * 4)

        if tag:
            conditions.append(
                "EXISTS (SELECT 1 FROM tags t WHERE t.wallpaper_id = w.id AND t.tag LIKE ?)"
            )
            params.append(f"%{tag}%")

        if mood:
            conditions.append(
                "EXISTS (SELECT 1 FROM moods m WHERE m.wallpaper_id = w.id AND m.mood LIKE ?)"
            )
            params.append(f"%{mood}%")

        if color:
            conditions.append(
                "EXISTS (SELECT 1 FROM colors c WHERE c.wallpaper_id = w.id AND c.color LIKE ?)"
            )
            params.append(f"%{color}%")

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        order_clause = "ORDER BY RANDOM()" if random else "ORDER BY w.filename"
        limit_clause = f"LIMIT {limit}" if limit else ""

        query = f"""
            SELECT DISTINCT w.path, w.filename, w.description, w.style, w.subject,
                   w.time_of_day, w.recommended_screen, w.width, w.height
            FROM wallpapers w
            WHERE {where_clause}
            {order_clause}
            {limit_clause}
        """

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def stats(self) -> dict:
        """Get database statistics."""
        if not self.conn:
            return {}

        stats = {}

        cursor = self.conn.execute("SELECT COUNT(*) as count FROM wallpapers")
        stats["total_wallpapers"] = cursor.fetchone()["count"]

        cursor = self.conn.execute(
            "SELECT COUNT(*) as count FROM wallpapers WHERE description IS NOT NULL"
        )
        stats["with_metadata"] = cursor.fetchone()["count"]

        cursor = self.conn.execute(
            "SELECT recommended_screen, COUNT(*) as count FROM wallpapers "
            "WHERE recommended_screen IS NOT NULL GROUP BY recommended_screen ORDER BY count DESC"
        )
        stats["by_screen"] = {row["recommended_screen"]: row["count"] for row in cursor.fetchall()}

        cursor = self.conn.execute(
            "SELECT style, COUNT(*) as count FROM wallpapers "
            "WHERE style IS NOT NULL GROUP BY style ORDER BY count DESC"
        )
        stats["by_style"] = {row["style"]: row["count"] for row in cursor.fetchall()}

        cursor = self.conn.execute(
            "SELECT subject, COUNT(*) as count FROM wallpapers "
            "WHERE subject IS NOT NULL GROUP BY subject ORDER BY count DESC"
        )
        stats["by_subject"] = {row["subject"]: row["count"] for row in cursor.fetchall()}

        cursor = self.conn.execute(
            "SELECT tag, COUNT(*) as count FROM tags GROUP BY tag ORDER BY count DESC LIMIT 20"
        )
        stats["top_tags"] = {row["tag"]: row["count"] for row in cursor.fetchall()}

        cursor = self.conn.execute(
            "SELECT mood, COUNT(*) as count FROM moods GROUP BY mood ORDER BY count DESC LIMIT 10"
        )
        stats["top_moods"] = {row["mood"]: row["count"] for row in cursor.fetchall()}

        cursor = self.conn.execute(
            "SELECT color, COUNT(*) as count FROM colors "
            "GROUP BY color ORDER BY count DESC LIMIT 10"
        )
        stats["top_colors"] = {row["color"]: row["count"] for row in cursor.fetchall()}

        return stats

    def prune(self, valid_paths: set[str]) -> int:
        """Remove entries for files that no longer exist."""
        if not self.conn:
            return 0

        cursor = self.conn.execute("SELECT id, path FROM wallpapers")
        to_delete = [row["id"] for row in cursor.fetchall() if row["path"] not in valid_paths]

        for wallpaper_id in to_delete:
            self.conn.execute("DELETE FROM wallpapers WHERE id = ?", (wallpaper_id,))

        self.conn.commit()
        return len(to_delete)
