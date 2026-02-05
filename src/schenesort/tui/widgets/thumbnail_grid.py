"""Thumbnail grid widget for gallery view."""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer
from textual.message import Message
from textual.widgets import Static


class ThumbnailCell(Static):
    """A single thumbnail cell in the grid showing filename."""

    DEFAULT_CSS = """
    ThumbnailCell {
        width: 24;
        height: 4;
        border: solid $background-lighten-2;
        content-align: center middle;
        text-align: center;
        overflow: hidden;
    }

    ThumbnailCell.selected {
        border: double $primary;
        background: $primary-darken-3;
    }
    """

    def __init__(self, image_path: Path, index: int, **kwargs) -> None:
        # Show truncated filename
        name = image_path.stem
        if len(name) > 20:
            name = name[:17] + "..."
        super().__init__(name, **kwargs)
        self.image_path = image_path
        self.index = index


class ThumbnailGrid(ScrollableContainer, can_focus=True):
    """Scrollable grid of image thumbnails with keyboard navigation."""

    BINDINGS = [
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("left", "move_left", "Left", show=False),
        Binding("right", "move_right", "Right", show=False),
        Binding("k", "move_up", "Up", show=False),
        Binding("j", "move_down", "Down", show=False),
        Binding("h", "move_left", "Left", show=False),
        Binding("l", "move_right", "Right", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("home", "first", "First", show=False),
        Binding("end", "last", "Last", show=False),
        Binding("g", "first", "First", show=False),
        Binding("G", "last", "Last", show=False, key_display="shift+g"),
    ]

    class ImageSelected(Message):
        """Emitted when an image is selected (Enter pressed)."""

        def __init__(self, image_path: Path, index: int) -> None:
            self.image_path = image_path
            self.index = index
            super().__init__()

    class SelectionChanged(Message):
        """Emitted when the selection changes."""

        def __init__(self, image_path: Path, index: int) -> None:
            self.image_path = image_path
            self.index = index
            super().__init__()

    DEFAULT_CSS = """
    ThumbnailGrid {
        width: 100%;
        height: 100%;
        background: $background;
        padding: 1;
    }

    ThumbnailGrid:focus {
        border: solid $accent;
    }

    ThumbnailGrid #grid-container {
        layout: grid;
        grid-gutter: 1;
        width: 100%;
        height: auto;
    }

    ThumbnailGrid .empty-message {
        color: $text-disabled;
        text-style: italic;
        text-align: center;
        width: 100%;
        padding: 4;
    }
    """

    CELL_WIDTH = 24
    CELL_HEIGHT = 12

    def __init__(self, images: list[Path] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._images: list[Path] = images or []
        self._selected_index: int = 0
        self._columns: int = 1
        self._cells: list[ThumbnailCell] = []

    def compose(self) -> ComposeResult:
        yield Container(id="grid-container")

    def on_mount(self) -> None:
        """Initialize the grid on mount."""
        self._calculate_columns()
        self._rebuild_grid()

    def on_resize(self) -> None:
        """Recalculate columns when resized."""
        old_columns = self._columns
        self._calculate_columns()
        if old_columns != self._columns:
            self._rebuild_grid()

    def _calculate_columns(self) -> None:
        """Calculate number of columns based on container width."""
        # Account for padding and borders
        available_width = max(self.size.width - 4, self.CELL_WIDTH)
        self._columns = max(1, available_width // (self.CELL_WIDTH + 1))

    def _rebuild_grid(self) -> None:
        """Rebuild the grid with current images and column count."""
        container = self.query_one("#grid-container", Container)

        # Clear all children from container
        container.remove_children()
        self._cells.clear()

        if not self._images:
            container.mount(Static("No images to display", classes="empty-message"))
            return

        # Update grid columns CSS
        container.styles.grid_size_columns = self._columns

        # Create cells (no IDs to avoid duplicate ID issues on resize)
        for idx, image_path in enumerate(self._images):
            cell = ThumbnailCell(image_path, idx)
            self._cells.append(cell)
            container.mount(cell)

        # Update selection
        self._update_selection()

    def set_images(self, images: list[Path]) -> None:
        """Update the images displayed in the grid."""
        self._images = images
        self._selected_index = 0 if images else -1
        self._rebuild_grid()

    def _update_selection(self) -> None:
        """Update the visual selection state."""
        for idx, cell in enumerate(self._cells):
            if idx == self._selected_index:
                cell.add_class("selected")
            else:
                cell.remove_class("selected")

        # Scroll selected cell into view
        if 0 <= self._selected_index < len(self._cells):
            self._cells[self._selected_index].scroll_visible()

    def _move_selection(self, delta: int) -> None:
        """Move selection by delta amount."""
        if not self._images:
            return

        new_index = self._selected_index + delta
        new_index = max(0, min(len(self._images) - 1, new_index))

        if new_index != self._selected_index:
            self._selected_index = new_index
            self._update_selection()
            self.post_message(
                self.SelectionChanged(self._images[self._selected_index], self._selected_index)
            )

    def action_move_up(self) -> None:
        """Move selection up by one row."""
        self._move_selection(-self._columns)

    def action_move_down(self) -> None:
        """Move selection down by one row."""
        self._move_selection(self._columns)

    def action_move_left(self) -> None:
        """Move selection left by one cell."""
        self._move_selection(-1)

    def action_move_right(self) -> None:
        """Move selection right by one cell."""
        self._move_selection(1)

    def action_first(self) -> None:
        """Move selection to first image."""
        if self._images:
            self._selected_index = 0
            self._update_selection()
            self.post_message(
                self.SelectionChanged(self._images[self._selected_index], self._selected_index)
            )

    def action_last(self) -> None:
        """Move selection to last image."""
        if self._images:
            self._selected_index = len(self._images) - 1
            self._update_selection()
            self.post_message(
                self.SelectionChanged(self._images[self._selected_index], self._selected_index)
            )

    def action_select(self) -> None:
        """Select the current image (open in detail view)."""
        if 0 <= self._selected_index < len(self._images):
            self.post_message(
                self.ImageSelected(self._images[self._selected_index], self._selected_index)
            )

    @property
    def selected_image(self) -> Path | None:
        """Get the currently selected image path."""
        if 0 <= self._selected_index < len(self._images):
            return self._images[self._selected_index]
        return None

    @property
    def selected_index(self) -> int:
        """Get the currently selected index."""
        return self._selected_index

    @property
    def image_count(self) -> int:
        """Get the number of images in the grid."""
        return len(self._images)
