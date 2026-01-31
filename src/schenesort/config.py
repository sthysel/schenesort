"""Configuration file handling for Schenesort."""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "schenesort"


def get_config_dir() -> Path:
    """Get the XDG config directory for schenesort."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg_config:
        config_dir = Path(xdg_config) / APP_NAME
    else:
        config_dir = Path.home() / ".config" / APP_NAME
    return config_dir


def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_config_dir() / "config.toml"


@dataclass
class Config:
    """Schenesort configuration."""

    # Ollama settings
    ollama_host: str = ""
    ollama_model: str = "llava"

    # Collection paths (optional defaults)
    wallpaper_path: str = ""

    # Database settings
    db_path: str = ""

    # Additional settings as needed
    extra: dict = field(default_factory=dict)


def load_config() -> Config:
    """Load configuration from file."""
    config_path = get_config_path()

    if not config_path.exists():
        return Config()

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        config = Config()

        # Ollama section
        ollama = data.get("ollama", {})
        if ollama.get("host"):
            config.ollama_host = ollama["host"]
        if ollama.get("model"):
            config.ollama_model = ollama["model"]

        # Paths section
        paths = data.get("paths", {})
        if paths.get("wallpaper"):
            config.wallpaper_path = paths["wallpaper"]
        if paths.get("database"):
            config.db_path = paths["database"]

        # Store any extra settings
        config.extra = data

        return config

    except Exception:
        return Config()


def create_default_config() -> Path:
    """Create a default config file if it doesn't exist."""
    config_path = get_config_path()

    if config_path.exists():
        return config_path

    config_path.parent.mkdir(parents=True, exist_ok=True)

    default_config = """\
# Schenesort configuration file

[ollama]
# Ollama server URL (leave empty for localhost:11434)
# host = "http://server:11434"

# Default vision model
model = "llava"

[paths]
# Default wallpaper collection path
# wallpaper = "~/wallpapers"

# Database path (default: ~/.local/share/schenesort/index.db)
# database = ""
"""

    config_path.write_text(default_config)
    return config_path
