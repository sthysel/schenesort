"""Integration tests for the CLI commands."""

import pytest
from typer.testing import CliRunner

from schenesort.cli import app

runner = CliRunner()


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory with test files."""
    return tmp_path


class TestSanitizeCommand:
    """Tests for the sanitise CLI command."""

    def test_sanitise_dry_run(self, temp_dir):
        """Test dry-run mode shows what would be renamed."""
        test_file = temp_dir / "Hello World.jpg"
        test_file.touch()

        result = runner.invoke(app, ["sanitise", str(temp_dir), "--dry-run"])

        assert result.exit_code == 0
        assert "Would rename" in result.stdout
        assert "hello_world.jpg" in result.stdout
        assert test_file.exists()  # Original should still exist

    def test_sanitise_actual_rename(self, temp_dir):
        """Test actual file renaming."""
        test_file = temp_dir / "Hello World.jpg"
        test_file.touch()

        result = runner.invoke(app, ["sanitise", str(temp_dir)])

        assert result.exit_code == 0
        assert "Renamed" in result.stdout
        assert not test_file.exists()
        assert (temp_dir / "hello_world.jpg").exists()

    def test_sanitise_multiple_files(self, temp_dir):
        """Test renaming multiple files."""
        (temp_dir / "File One.jpg").touch()
        (temp_dir / "File Two.png").touch()
        (temp_dir / "already_clean.gif").touch()

        result = runner.invoke(app, ["sanitise", str(temp_dir)])

        assert result.exit_code == 0
        assert "Renamed 2 file(s)" in result.stdout
        assert (temp_dir / "file_one.jpg").exists()
        assert (temp_dir / "file_two.png").exists()
        assert (temp_dir / "already_clean.gif").exists()

    def test_sanitise_recursive(self, temp_dir):
        """Test recursive directory processing."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (temp_dir / "Root File.jpg").touch()
        (subdir / "Sub File.png").touch()

        result = runner.invoke(app, ["sanitise", str(temp_dir), "--recursive"])

        assert result.exit_code == 0
        assert "Renamed 2 file(s)" in result.stdout
        assert (temp_dir / "root_file.jpg").exists()
        assert (subdir / "sub_file.png").exists()

    def test_sanitise_nonexistent_path(self):
        """Test error handling for nonexistent path."""
        result = runner.invoke(app, ["sanitise", "/nonexistent/path"])

        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_sanitise_skip_existing_target(self, temp_dir):
        """Test skipping when target already exists."""
        (temp_dir / "Hello World.jpg").touch()
        (temp_dir / "hello_world.jpg").touch()

        result = runner.invoke(app, ["sanitise", str(temp_dir)])

        assert result.exit_code == 0
        assert "Skipping" in result.output
        assert "already exists" in result.output

    def test_sanitise_single_file(self, temp_dir):
        """Test sanitizing a single file."""
        test_file = temp_dir / "Single File.jpg"
        test_file.touch()

        result = runner.invoke(app, ["sanitise", str(test_file)])

        assert result.exit_code == 0
        assert "Renamed 1 file(s)" in result.stdout
        assert (temp_dir / "single_file.jpg").exists()

    def test_sanitise_uppercase_extension(self, temp_dir):
        """Test that uppercase extensions are lowercased."""
        test_file = temp_dir / "Image.JPG"
        test_file.touch()

        result = runner.invoke(app, ["sanitise", str(temp_dir)])

        assert result.exit_code == 0
        assert (temp_dir / "image.jpg").exists()

    def test_sanitise_no_changes_needed(self, temp_dir):
        """Test when no files need renaming."""
        (temp_dir / "already_clean.jpg").touch()

        result = runner.invoke(app, ["sanitise", str(temp_dir)])

        assert result.exit_code == 0
        assert "Renamed 0 file(s)" in result.stdout


class TestInfoCommand:
    """Tests for the info CLI command."""

    def test_info_basic(self, temp_dir):
        """Test basic info output."""
        (temp_dir / "image1.jpg").write_bytes(b"x" * 1024)
        (temp_dir / "image2.png").write_bytes(b"x" * 2048)

        result = runner.invoke(app, ["info", str(temp_dir)])

        assert result.exit_code == 0
        assert "Total files: 2" in result.stdout
        assert ".jpg: 1" in result.stdout
        assert ".png: 1" in result.stdout

    def test_info_counts_spaces_in_names(self, temp_dir):
        """Test that files with spaces are counted."""
        (temp_dir / "has spaces.jpg").touch()
        (temp_dir / "no_spaces.jpg").touch()

        result = runner.invoke(app, ["info", str(temp_dir)])

        assert result.exit_code == 0
        assert "Files with spaces in name: 1" in result.stdout

    def test_info_nonexistent_path(self):
        """Test error handling for nonexistent path."""
        result = runner.invoke(app, ["info", "/nonexistent/path"])

        assert result.exit_code == 1
        assert "does not exist" in result.output
