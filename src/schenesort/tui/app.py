"""Wallpaper Browser TUI application."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Static

from schenesort.tui.widgets.image_preview import ImagePreview
from schenesort.tui.widgets.metadata_panel import MetadataPanel
from schenesort.xmp import read_xmp

VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}


class WallpaperBrowser(App):
    """A TUI application for browsing wallpapers with metadata display."""

    TITLE = "Schenesort - Wallpaper Browser"

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        width: 100%;
        height: 1fr;
    }

    #image-panel {
        width: 60%;
        height: 100%;
        border: solid $primary;
    }

    #metadata-panel {
        width: 40%;
        height: 100%;
        border: solid $secondary;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text;
        padding: 0 1;
    }

    #status-left {
        width: 1fr;
    }

    #status-right {
        width: auto;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("j", "next_image", "Next", show=True),
        Binding("k", "prev_image", "Previous", show=True),
        Binding("g", "first_image", "First", show=True),
        Binding("G", "last_image", "Last", show=True, key_display="shift+g"),
        Binding("+", "zoom_in", "Zoom In", show=True),
        Binding("-", "zoom_out", "Zoom Out", show=True),
        Binding("0", "reset_zoom", "Reset Zoom", show=False),
        Binding("down", "next_image", "Next", show=False),
        Binding("up", "prev_image", "Previous", show=False),
        Binding("home", "first_image", "First", show=False),
        Binding("end", "last_image", "Last", show=False),
    ]

    def __init__(self, path: Path, recursive: bool = False) -> None:
        super().__init__()
        self._base_path = path
        self._recursive = recursive
        self._images: list[Path] = []
        self._current_index: int = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-container"):
            yield ImagePreview(id="image-panel")
            yield MetadataPanel(id="metadata-panel")
        with Horizontal(id="status-bar"):
            yield Static("", id="status-left")
            yield Static("", id="status-right")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the browser when mounted."""
        self._load_images()
        if self._images:
            self._show_current_image()
        else:
            self._update_status("No images found", "")

    def _load_images(self) -> None:
        """Load list of images from the specified path."""
        if self._base_path.is_file():
            if self._base_path.suffix.lower() in VALID_IMAGE_EXTENSIONS:
                self._images = [self._base_path]
        else:
            pattern = "**/*" if self._recursive else "*"
            self._images = sorted(
                f
                for f in self._base_path.glob(pattern)
                if f.is_file() and f.suffix.lower() in VALID_IMAGE_EXTENSIONS
            )

    def _show_current_image(self) -> None:
        """Display the current image and its metadata."""
        if not self._images:
            return

        current_image = self._images[self._current_index]

        # Load image
        preview = self.query_one("#image-panel", ImagePreview)
        preview.load_image(current_image)

        # Load metadata
        metadata = read_xmp(current_image)
        panel = self.query_one("#metadata-panel", MetadataPanel)
        panel.update_metadata(metadata, current_image.name)

        # Update status
        self._update_status(
            str(current_image.relative_to(self._base_path))
            if current_image.is_relative_to(self._base_path)
            else current_image.name,
            f"{self._current_index + 1}/{len(self._images)}",
        )

    def _update_status(self, left: str, right: str) -> None:
        """Update the status bar."""
        self.query_one("#status-left", Static).update(left)
        self.query_one("#status-right", Static).update(right)

    def action_next_image(self) -> None:
        """Navigate to the next image."""
        if self._images and self._current_index < len(self._images) - 1:
            self._current_index += 1
            self._show_current_image()

    def action_prev_image(self) -> None:
        """Navigate to the previous image."""
        if self._images and self._current_index > 0:
            self._current_index -= 1
            self._show_current_image()

    def action_first_image(self) -> None:
        """Navigate to the first image."""
        if self._images:
            self._current_index = 0
            self._show_current_image()

    def action_last_image(self) -> None:
        """Navigate to the last image."""
        if self._images:
            self._current_index = len(self._images) - 1
            self._show_current_image()

    def action_zoom_in(self) -> None:
        """Zoom in on the current image."""
        preview = self.query_one("#image-panel", ImagePreview)
        preview.zoom_in()

    def action_zoom_out(self) -> None:
        """Zoom out of the current image."""
        preview = self.query_one("#image-panel", ImagePreview)
        preview.zoom_out()

    def action_reset_zoom(self) -> None:
        """Reset the zoom level."""
        preview = self.query_one("#image-panel", ImagePreview)
        preview.reset_zoom()
