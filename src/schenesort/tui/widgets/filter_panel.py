"""Filter panel widget for gallery grid view."""

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widgets import Input, Label, Static


@dataclass
class FilterValues:
    """Container for all filter values."""

    search: str = ""
    tag: str = ""
    mood: str = ""
    color: str = ""
    style: str = ""
    subject: str = ""
    time: str = ""
    screen: str = ""
    min_width: int | None = None
    min_height: int | None = None

    def is_empty(self) -> bool:
        """Check if all filters are empty."""
        return (
            not self.search
            and not self.tag
            and not self.mood
            and not self.color
            and not self.style
            and not self.subject
            and not self.time
            and not self.screen
            and self.min_width is None
            and self.min_height is None
        )


class FilterPanel(VerticalScroll):
    """Sidebar panel with filter inputs for gallery view."""

    class FiltersChanged(Message):
        """Emitted when any filter value changes."""

        def __init__(self, filters: FilterValues) -> None:
            self.filters = filters
            super().__init__()

    DEFAULT_CSS = """
    FilterPanel {
        width: 100%;
        height: 100%;
        background: $surface;
        padding: 1;
    }

    FilterPanel .filter-title {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
        text-align: center;
    }

    FilterPanel .filter-label {
        color: $text-muted;
        margin-top: 1;
    }

    FilterPanel Input {
        margin-bottom: 0;
    }

    FilterPanel Input:focus {
        border: tall $accent;
    }

    FilterPanel .filter-section {
        margin-top: 1;
    }

    FilterPanel .filter-hint {
        color: $text-disabled;
        text-style: italic;
        margin-top: 1;
    }
    """

    def __init__(self, initial_filters: FilterValues | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._filters = initial_filters or FilterValues()
        self._pending_change: int = 0

    def compose(self) -> ComposeResult:
        yield Static("Filters", classes="filter-title")

        yield Label("Search", classes="filter-label")
        yield Input(
            value=self._filters.search,
            placeholder="description, scene...",
            id="filter-search",
        )

        yield Label("Tag", classes="filter-label")
        yield Input(
            value=self._filters.tag,
            placeholder="e.g. nature",
            id="filter-tag",
        )

        yield Label("Mood", classes="filter-label")
        yield Input(
            value=self._filters.mood,
            placeholder="e.g. peaceful",
            id="filter-mood",
        )

        yield Label("Color", classes="filter-label")
        yield Input(
            value=self._filters.color,
            placeholder="e.g. blue",
            id="filter-color",
        )

        yield Label("Style", classes="filter-label")
        yield Input(
            value=self._filters.style,
            placeholder="e.g. photography",
            id="filter-style",
        )

        yield Label("Subject", classes="filter-label")
        yield Input(
            value=self._filters.subject,
            placeholder="e.g. landscape",
            id="filter-subject",
        )

        yield Label("Time", classes="filter-label")
        yield Input(
            value=self._filters.time,
            placeholder="e.g. sunset",
            id="filter-time",
        )

        yield Label("Screen", classes="filter-label")
        yield Input(
            value=self._filters.screen,
            placeholder="e.g. 4K, 1440p",
            id="filter-screen",
        )

        yield Label("Min Width", classes="filter-label")
        yield Input(
            value=str(self._filters.min_width) if self._filters.min_width else "",
            placeholder="pixels",
            id="filter-min-width",
        )

        yield Label("Min Height", classes="filter-label")
        yield Input(
            value=str(self._filters.min_height) if self._filters.min_height else "",
            placeholder="pixels",
            id="filter-min-height",
        )

        yield Static("Press Tab to switch to grid", classes="filter-hint")

    def on_input_changed(self, event: Input.Changed) -> None:  # noqa: ARG002
        """Handle input changes with debouncing."""
        # Increment counter to track which change this is
        self._pending_change += 1
        current_change = self._pending_change

        # Schedule the filter update with a small delay
        self.set_timer(0.3, lambda: self._emit_filter_change(current_change))

    def _emit_filter_change(self, change_id: int) -> None:
        """Gather all filter values and emit the change message."""
        # Only process if this is the most recent change
        if change_id != self._pending_change:
            return

        # Read all input values
        search = self.query_one("#filter-search", Input).value.strip()
        tag = self.query_one("#filter-tag", Input).value.strip()
        mood = self.query_one("#filter-mood", Input).value.strip()
        color = self.query_one("#filter-color", Input).value.strip()
        style = self.query_one("#filter-style", Input).value.strip()
        subject = self.query_one("#filter-subject", Input).value.strip()
        time = self.query_one("#filter-time", Input).value.strip()
        screen = self.query_one("#filter-screen", Input).value.strip()

        # Parse numeric values
        min_width_str = self.query_one("#filter-min-width", Input).value.strip()
        min_height_str = self.query_one("#filter-min-height", Input).value.strip()

        min_width = None
        min_height = None
        try:
            if min_width_str:
                min_width = int(min_width_str)
        except ValueError:
            pass
        try:
            if min_height_str:
                min_height = int(min_height_str)
        except ValueError:
            pass

        self._filters = FilterValues(
            search=search,
            tag=tag,
            mood=mood,
            color=color,
            style=style,
            subject=subject,
            time=time,
            screen=screen,
            min_width=min_width,
            min_height=min_height,
        )

        self.post_message(self.FiltersChanged(self._filters))

    @property
    def filters(self) -> FilterValues:
        """Get the current filter values."""
        return self._filters

    def clear_filters(self) -> None:
        """Clear all filter inputs."""
        for input_id in [
            "#filter-search",
            "#filter-tag",
            "#filter-mood",
            "#filter-color",
            "#filter-style",
            "#filter-subject",
            "#filter-time",
            "#filter-screen",
            "#filter-min-width",
            "#filter-min-height",
        ]:
            self.query_one(input_id, Input).value = ""
        self._filters = FilterValues()
        self.post_message(self.FiltersChanged(self._filters))
