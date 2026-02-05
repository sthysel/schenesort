"""Gallery Grid Browser TUI application."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from schenesort.db import WallpaperDB
from schenesort.tui.widgets.filter_panel import FilterPanel, FilterValues
from schenesort.tui.widgets.image_preview import ImagePreview
from schenesort.tui.widgets.metadata_panel import MetadataPanel
from schenesort.tui.widgets.thumbnail_grid import ThumbnailGrid
from schenesort.xmp import read_xmp


class DetailScreen(Screen):
    """Screen for viewing a single image with metadata."""

    BINDINGS = [
        Binding("escape", "pop_screen", "Back", show=True),
        Binding("q", "pop_screen", "Back", show=False),
        Binding("j", "next_image", "Next", show=True),
        Binding("k", "prev_image", "Previous", show=True),
        Binding("down", "next_image", "Next", show=False),
        Binding("up", "prev_image", "Previous", show=False),
    ]

    CSS = """
    DetailScreen {
        layout: vertical;
    }

    DetailScreen #detail-container {
        width: 100%;
        height: 1fr;
    }

    DetailScreen #image-panel {
        width: 60%;
        height: 100%;
        border: solid $primary;
    }

    DetailScreen #metadata-panel {
        width: 40%;
        height: 100%;
        border: solid $secondary;
    }

    DetailScreen #detail-status {
        dock: bottom;
        height: 1;
        background: $surface;
        padding: 0 1;
    }
    """

    def __init__(self, images: list[Path], start_index: int = 0, **kwargs) -> None:
        super().__init__(**kwargs)
        self._images = images
        self._current_index = start_index

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="detail-container"):
            yield ImagePreview(id="image-panel")
            yield MetadataPanel(id="metadata-panel")
        yield Static("", id="detail-status")
        yield Footer()

    def on_mount(self) -> None:
        """Show the initial image."""
        self._show_current_image()

    def _show_current_image(self) -> None:
        """Display the current image and metadata."""
        if not self._images or not (0 <= self._current_index < len(self._images)):
            return

        current = self._images[self._current_index]

        # Update image
        preview = self.query_one("#image-panel", ImagePreview)
        preview.load_image(current)

        # Update metadata
        metadata = read_xmp(current)
        panel = self.query_one("#metadata-panel", MetadataPanel)
        panel.update_metadata(metadata, current.name)

        # Update status
        status = self.query_one("#detail-status", Static)
        status.update(f"{current.name}  [{self._current_index + 1}/{len(self._images)}]")

    def action_next_image(self) -> None:
        """Show next image."""
        if self._current_index < len(self._images) - 1:
            self._current_index += 1
            self._show_current_image()

    def action_prev_image(self) -> None:
        """Show previous image."""
        if self._current_index > 0:
            self._current_index -= 1
            self._show_current_image()

    def action_pop_screen(self) -> None:
        """Return to the grid view."""
        self.app.pop_screen()


class GridBrowser(App):
    """A TUI application for browsing wallpapers in a thumbnail grid with filters."""

    TITLE = "Schenesort - Gallery"

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        width: 100%;
        height: 1fr;
    }

    #filter-panel {
        width: 22;
        height: 100%;
        border: solid $secondary;
    }

    #grid-panel {
        width: 1fr;
        height: 100%;
        border: solid $primary;
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
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
        Binding("ctrl+q", "quit", "Quit", show=False, priority=True),
        Binding("tab", "focus_next_panel", "Switch Panel", show=True),
        Binding("shift+tab", "focus_prev_panel", "Switch Panel", show=False),
        Binding("enter", "open_detail", "Open", show=True),
        Binding("escape", "clear_filters", "Clear Filters", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    def __init__(self, initial_filters: FilterValues | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._initial_filters = initial_filters or FilterValues()
        self._images: list[Path] = []
        self._db_path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-container"):
            yield FilterPanel(initial_filters=self._initial_filters, id="filter-panel")
            yield ThumbnailGrid(id="grid-panel")
        with Horizontal(id="status-bar"):
            yield Static("Loading...", id="status-left")
            yield Static("", id="status-right")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the browser when mounted."""
        # Set initial focus to the grid
        self.query_one("#grid-panel", ThumbnailGrid).focus()
        # Load initial data
        self._query_database(self._initial_filters)

    def _query_database(self, filters: FilterValues) -> None:
        """Query the database with the given filters."""
        try:
            with WallpaperDB() as db:
                self._db_path = db.db_path
                results = db.query(
                    search=filters.search or None,
                    tag=filters.tag or None,
                    mood=filters.mood or None,
                    color=filters.color or None,
                    style=filters.style or None,
                    subject=filters.subject or None,
                    time_of_day=filters.time or None,
                    screen=filters.screen or None,
                    min_width=filters.min_width,
                    min_height=filters.min_height,
                )

            # Extract paths and filter for existing files
            self._images = [Path(r["path"]) for r in results if Path(r["path"]).exists()]

            # Update grid
            grid = self.query_one("#grid-panel", ThumbnailGrid)
            grid.set_images(self._images)

            # Update status
            self._update_status()

        except Exception as e:
            self._update_status(error=str(e))

    def _update_status(self, error: str | None = None) -> None:
        """Update the status bar."""
        left_status = self.query_one("#status-left", Static)
        right_status = self.query_one("#status-right", Static)

        if error:
            left_status.update(f"[red]Error: {error}[/red]")
            right_status.update("")
        else:
            count = len(self._images)
            if count == 0:
                left_status.update("[dim]No images matching filters[/dim]")
            else:
                left_status.update(f"{count} image{'s' if count != 1 else ''} matching")

            grid = self.query_one("#grid-panel", ThumbnailGrid)
            if grid.image_count > 0:
                right_status.update(f"{grid.selected_index + 1}/{grid.image_count}")
            else:
                right_status.update("")

    def on_filter_panel_filters_changed(self, event: FilterPanel.FiltersChanged) -> None:
        """Handle filter changes from the filter panel."""
        self._query_database(event.filters)

    def on_thumbnail_grid_selection_changed(
        self,
        event: ThumbnailGrid.SelectionChanged,  # noqa: ARG002
    ) -> None:
        """Handle selection changes in the grid."""
        self._update_status()

    def on_thumbnail_grid_image_selected(self, event: ThumbnailGrid.ImageSelected) -> None:
        """Handle image selection (Enter pressed) - open detail view."""
        self._open_detail_view(event.index)

    def _open_detail_view(self, start_index: int = 0) -> None:
        """Open the detail view with the current image list."""
        if not self._images:
            return

        # Push detail screen onto the stack
        self.push_screen(DetailScreen(self._images, start_index))

    def action_focus_next_panel(self) -> None:
        """Switch focus to the next panel."""
        current = self.focused
        filter_panel = self.query_one("#filter-panel", FilterPanel)
        grid_panel = self.query_one("#grid-panel", ThumbnailGrid)

        # Check if focus is in the filter panel area
        if current is not None and filter_panel in current.ancestors_with_self:
            grid_panel.focus()
        else:
            # Focus the first input in the filter panel
            try:
                first_input = filter_panel.query("Input").first()
                first_input.focus()
            except Exception:
                filter_panel.focus()

    def action_focus_prev_panel(self) -> None:
        """Switch focus to the previous panel (reverse of next)."""
        self.action_focus_next_panel()

    def action_open_detail(self) -> None:
        """Open detail view for the selected image."""
        grid = self.query_one("#grid-panel", ThumbnailGrid)
        self._open_detail_view(grid.selected_index)

    def action_clear_filters(self) -> None:
        """Clear all filters."""
        filter_panel = self.query_one("#filter-panel", FilterPanel)
        filter_panel.clear_filters()

    def action_refresh(self) -> None:
        """Refresh the grid with current filters."""
        filter_panel = self.query_one("#filter-panel", FilterPanel)
        self._query_database(filter_panel.filters)
