"""Metadata panel widget for displaying image metadata."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from schenesort.xmp import ImageMetadata


class MetadataPanel(VerticalScroll):
    """Panel displaying image metadata from XMP sidecar."""

    DEFAULT_CSS = """
    MetadataPanel {
        width: 100%;
        height: 100%;
        background: $surface;
        padding: 1 2;
    }

    MetadataPanel .metadata-title {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    MetadataPanel .metadata-label {
        color: $text-muted;
        margin-top: 1;
    }

    MetadataPanel .metadata-value {
        color: $text;
        margin-left: 2;
    }

    MetadataPanel .metadata-empty {
        color: $text-disabled;
        text-style: italic;
    }

    MetadataPanel .metadata-tags {
        color: $primary;
    }

    MetadataPanel .metadata-colors {
        color: $secondary;
    }

    MetadataPanel .metadata-scene {
        color: $text;
        margin-left: 2;
        text-style: italic;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._metadata: ImageMetadata | None = None
        self._filename: str = ""

    def compose(self) -> ComposeResult:
        yield Static("No image selected", classes="metadata-empty", id="content")

    def update_metadata(self, metadata: ImageMetadata | None, filename: str = "") -> None:
        """Update the displayed metadata."""
        self._metadata = metadata
        self._filename = filename
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Refresh the metadata display."""
        content = self.query_one("#content", Static)

        if self._metadata is None or self._metadata.is_empty():
            if self._filename:
                content.update(
                    f"[bold]{self._filename}[/bold]\n\n[dim italic]No metadata[/dim italic]"
                )
            else:
                content.update("[dim italic]No image selected[/dim italic]")
            return

        lines = []

        # Filename as title
        if self._filename:
            lines.append(f"[bold]{self._filename}[/bold]")
            lines.append("")

        # Description
        if self._metadata.description:
            lines.append("[dim]Description[/dim]")
            lines.append(f"  {self._metadata.description}")

        # Scene (detailed description)
        if self._metadata.scene:
            lines.append("")
            lines.append("[dim]Scene[/dim]")
            lines.append(f"  [italic]{self._metadata.scene}[/italic]")

        # Tags
        if self._metadata.tags:
            lines.append("")
            lines.append("[dim]Tags[/dim]")
            tags_str = ", ".join(f"[cyan]{tag}[/cyan]" for tag in self._metadata.tags)
            lines.append(f"  {tags_str}")

        # Mood
        if self._metadata.mood:
            lines.append("")
            lines.append("[dim]Mood[/dim]")
            mood_str = ", ".join(f"[magenta]{m}[/magenta]" for m in self._metadata.mood)
            lines.append(f"  {mood_str}")

        # Style
        if self._metadata.style:
            lines.append("")
            lines.append("[dim]Style[/dim]")
            lines.append(f"  [yellow]{self._metadata.style}[/yellow]")

        # Colors
        if self._metadata.colors:
            lines.append("")
            lines.append("[dim]Colors[/dim]")
            colors_str = ", ".join(f"[green]{c}[/green]" for c in self._metadata.colors)
            lines.append(f"  {colors_str}")

        # Time of day
        if self._metadata.time_of_day:
            lines.append("")
            lines.append("[dim]Time[/dim]")
            lines.append(f"  {self._metadata.time_of_day}")

        # Subject
        if self._metadata.subject:
            lines.append("")
            lines.append("[dim]Subject[/dim]")
            lines.append(f"  {self._metadata.subject}")

        # Dimensions
        if self._metadata.width and self._metadata.height:
            lines.append("")
            lines.append("[dim]Dimensions[/dim]")
            lines.append(f"  {self._metadata.width} x {self._metadata.height}")
            if self._metadata.recommended_screen:
                lines.append(f"  [green]Best for: {self._metadata.recommended_screen}[/green]")

        # Source
        if self._metadata.source:
            lines.append("")
            lines.append("[dim]Source[/dim]")
            lines.append(f"  [blue]{self._metadata.source}[/blue]")

        # AI Model
        if self._metadata.ai_model:
            lines.append("")
            lines.append("[dim]AI Model[/dim]")
            lines.append(f"  [dim]{self._metadata.ai_model}[/dim]")

        content.update("\n".join(lines))
