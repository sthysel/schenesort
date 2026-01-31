"""Image preview widget using textual-image."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static
from textual_image.widget import Image


class ImagePreview(Container):
    """Widget for displaying image preview with zoom support."""

    DEFAULT_CSS = """
    ImagePreview {
        width: 100%;
        height: 100%;
        background: $background;
        align: center middle;
    }

    ImagePreview Image {
        width: 100%;
        height: 100%;
    }

    ImagePreview .no-image {
        color: $text-disabled;
        text-style: italic;
        text-align: center;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._image_path: Path | None = None
        self._zoom_level: float = 1.0
        self._image_widget: Image | None = None

    def compose(self) -> ComposeResult:
        yield Static("No image selected", classes="no-image", id="placeholder")

    def load_image(self, path: Path | None) -> None:
        """Load and display an image."""
        self._image_path = path
        self._zoom_level = 1.0

        # Remove existing image widget if present
        if self._image_widget is not None:
            self._image_widget.remove()
            self._image_widget = None

        placeholder = self.query_one("#placeholder", Static)

        if path is None or not path.exists():
            placeholder.update("No image selected")
            placeholder.display = True
            return

        try:
            placeholder.display = False
            self._image_widget = Image(path)
            self.mount(self._image_widget)
        except Exception as e:
            placeholder.update(f"Error loading image: {e}")
            placeholder.display = True

    def zoom_in(self) -> None:
        """Zoom in on the image."""
        self._zoom_level = min(4.0, self._zoom_level * 1.25)
        self._apply_zoom()

    def zoom_out(self) -> None:
        """Zoom out of the image."""
        self._zoom_level = max(0.25, self._zoom_level / 1.25)
        self._apply_zoom()

    def reset_zoom(self) -> None:
        """Reset zoom to 100%."""
        self._zoom_level = 1.0
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        """Apply current zoom level to the image widget."""
        # textual-image handles scaling internally based on container size
        # For now, zoom is a placeholder for future enhancement
        pass

    @property
    def current_path(self) -> Path | None:
        """Get the currently displayed image path."""
        return self._image_path

    @property
    def zoom_level(self) -> float:
        """Get the current zoom level."""
        return self._zoom_level
