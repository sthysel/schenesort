"""Tests for filename sanitization functionality."""

from schenesort.cli import sanitize_filename


class TestSanitizeFilename:
    """Tests for the sanitize_filename function."""

    # Basic whitespace handling
    def test_replaces_single_space_with_underscore(self):
        assert sanitize_filename("hello world.jpg") == "hello_world.jpg"

    def test_replaces_multiple_spaces_with_single_underscore(self):
        assert sanitize_filename("hello   world.jpg") == "hello_world.jpg"

    def test_handles_tabs_as_whitespace(self):
        assert sanitize_filename("hello\tworld.jpg") == "hello_world.jpg"

    def test_handles_mixed_whitespace(self):
        assert sanitize_filename("hello \t world.jpg") == "hello_world.jpg"

    # Case conversion
    def test_converts_uppercase_to_lowercase(self):
        assert sanitize_filename("HelloWorld.JPG") == "helloworld.jpg"

    def test_handles_mixed_case_and_spaces(self):
        assert sanitize_filename("My Cool Wallpaper.PNG") == "my_cool_wallpaper.png"

    def test_uppercase_extension(self):
        assert sanitize_filename("image.JPEG") == "image.jpeg"

    def test_mixed_case_extension(self):
        assert sanitize_filename("image.JpEg") == "image.jpeg"

    # Underscore handling
    def test_preserves_single_underscores(self):
        assert sanitize_filename("already_has_underscores.jpg") == "already_has_underscores.jpg"

    def test_collapses_multiple_underscores(self):
        assert sanitize_filename("too___many___underscores.jpg") == "too_many_underscores.jpg"

    def test_strips_leading_underscore(self):
        assert sanitize_filename("_leading.jpg") == "leading.jpg"

    def test_strips_trailing_underscore(self):
        assert sanitize_filename("trailing_.jpg") == "trailing.jpg"

    def test_leading_space_becomes_stripped(self):
        assert sanitize_filename(" leading.jpg") == "leading.jpg"

    def test_trailing_space_becomes_stripped(self):
        assert sanitize_filename("trailing .jpg") == "trailing.jpg"

    # Hyphen handling
    def test_preserves_hyphens(self):
        assert sanitize_filename("image-with-dashes.jpg") == "image-with-dashes.jpg"

    def test_collapses_multiple_hyphens(self):
        assert sanitize_filename("too---many---hyphens.jpg") == "too-many-hyphens.jpg"

    def test_strips_leading_hyphen(self):
        assert sanitize_filename("-leading.jpg") == "leading.jpg"

    def test_strips_trailing_hyphen(self):
        assert sanitize_filename("trailing-.jpg") == "trailing.jpg"

    # Punctuation removal
    def test_removes_exclamation(self):
        assert sanitize_filename("wow!.jpg") == "wow.jpg"

    def test_removes_question_mark(self):
        assert sanitize_filename("what?.jpg") == "what.jpg"

    def test_removes_at_symbol(self):
        assert sanitize_filename("user@home.jpg") == "userhome.jpg"

    def test_removes_hash(self):
        assert sanitize_filename("file#1.jpg") == "file1.jpg"

    def test_removes_dollar(self):
        assert sanitize_filename("money$.jpg") == "money.jpg"

    def test_removes_percent(self):
        assert sanitize_filename("100%.jpg") == "100.jpg"

    def test_removes_ampersand(self):
        assert sanitize_filename("this&that.jpg") == "thisthat.jpg"

    def test_removes_parentheses(self):
        assert sanitize_filename("file(1).jpg") == "file1.jpg"

    def test_removes_brackets(self):
        assert sanitize_filename("file[1].jpg") == "file1.jpg"

    def test_removes_braces(self):
        assert sanitize_filename("file{1}.jpg") == "file1.jpg"

    def test_removes_quotes(self):
        assert sanitize_filename('it\'s "quoted".jpg') == "its_quoted.jpg"

    def test_removes_comma(self):
        assert sanitize_filename("one, two.jpg") == "one_two.jpg"

    def test_removes_semicolon(self):
        assert sanitize_filename("one;two.jpg") == "onetwo.jpg"

    def test_removes_colon(self):
        assert sanitize_filename("time:12.jpg") == "time12.jpg"

    def test_removes_plus(self):
        assert sanitize_filename("a+b.jpg") == "ab.jpg"

    def test_removes_equals(self):
        assert sanitize_filename("a=b.jpg") == "ab.jpg"

    def test_complex_punctuation_removal(self):
        assert sanitize_filename("Hello! World? (2024).jpg") == "hello_world_2024.jpg"

    # Dots in filename
    def test_preserves_extension_dot(self):
        assert sanitize_filename("simple.jpg") == "simple.jpg"

    def test_removes_dots_in_stem(self):
        assert sanitize_filename("file.backup.jpg") == "filebackup.jpg"

    def test_multiple_dots_only_last_kept(self):
        assert sanitize_filename("my.file.name.jpg") == "myfilename.jpg"

    # Numbers
    def test_numbers_preserved(self):
        assert sanitize_filename("Image 001.jpg") == "image_001.jpg"

    def test_numbers_only_filename(self):
        assert sanitize_filename("12345.jpg") == "12345.jpg"

    # Edge cases
    def test_no_change_needed(self):
        assert sanitize_filename("already_clean.jpg") == "already_clean.jpg"

    def test_empty_string(self):
        assert sanitize_filename("") == ""

    def test_only_spaces_becomes_unnamed(self):
        assert sanitize_filename("   .jpg") == "unnamed.jpg"

    def test_only_punctuation_becomes_unnamed(self):
        assert sanitize_filename("!@#$.jpg") == "unnamed.jpg"

    def test_hidden_file_preserved(self):
        assert sanitize_filename(".hidden") == ".hidden"

    def test_no_extension(self):
        assert sanitize_filename("README") == "readme"

    # Unicode
    def test_unicode_letters_preserved(self):
        assert sanitize_filename("café.jpg") == "café.jpg"

    def test_unicode_with_spaces(self):
        assert sanitize_filename("schöne tapete.jpg") == "schöne_tapete.jpg"

    # Mixed underscore and hyphen sequences
    def test_mixed_underscore_hyphen_collapsed(self):
        assert sanitize_filename("file_-_name.jpg") == "file_name.jpg"

    def test_hyphen_underscore_sequence(self):
        assert sanitize_filename("a-_-b.jpg") == "a_b.jpg"

    # Trailing dot (AI descriptions often end with a period)
    def test_trailing_dot_stripped(self):
        assert sanitize_filename("a description.") == "a_description"

    def test_trailing_dot_with_extension(self):
        assert sanitize_filename("a description..jpg") == "a_description.jpg"
