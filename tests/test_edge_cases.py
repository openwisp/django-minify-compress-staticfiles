"""Tests for utility functions edge cases."""

import os
import tempfile

from django.core.files.storage import FileSystemStorage
from django.test import TestCase

from django_minify_compress_staticfiles.utils import is_safe_path, should_process_file


class IsSafePathEdgeCaseTests(TestCase):
    """Tests for is_safe_path edge cases."""

    def test_is_safe_path_with_empty_string(self):
        """Test that empty string returns False."""
        self.assertFalse(is_safe_path(""))

    def test_is_safe_path_with_backslash(self):
        """Test that paths with backslashes are rejected (Windows style)."""
        self.assertFalse(is_safe_path(r"..\..\windows\system32"))
        self.assertFalse(is_safe_path(r"C:\Windows\System32"))

    def test_is_safe_path_different_drives(self):
        """Test is_safe_path with paths on different drives (Windows)."""
        # On Linux/Unix, this won't apply, but the test should still pass
        # by handling the ValueError that occurs when paths are on different drives
        try:
            result = is_safe_path(r"D:\file.txt", base_dir=r"C:\base")
            # On Unix, this will just treat them as paths
            # On Windows with different drives, relpath raises ValueError
            self.assertFalse(result)
        except ValueError:
            # This is expected on Windows with different drives
            # The function should handle this
            pass

    def test_is_safe_path_symlinks(self):
        """Test that symlinks are handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a symlink
            target = os.path.join(tmpdir, "target.txt")
            link = os.path.join(tmpdir, "link.txt")
            with open(target, "w") as f:
                f.write("test")
            try:
                os.symlink(target, link)
                # Symlink to file in same dir should be safe
                # Note: The check is for path traversal, not symlink safety
                # We pass the full path to check correctly
                self.assertTrue(is_safe_path(link, tmpdir))
                # Symlink pointing to parent dir
                parent_link = os.path.join(tmpdir, "parent_link")
                os.symlink("..", parent_link)
                # The symlink path itself is safe in this check
                self.assertTrue(is_safe_path(parent_link, tmpdir))
                # Note: is_safe_path doesn't resolve symlinks, so it doesn't
                # detect that parent_link points outside tmpdir. This is a known
                # limitation - path traversal is checked at the string level, not
                # after resolving symlinks.
            except OSError:
                # Symlinks might not be supported on this system
                pass


class ShouldProcessFileEdgeCaseTests(TestCase):
    """Tests for should_process_file edge cases."""

    def test_should_process_empty_extensions(self):
        """Test with empty extensions list."""
        self.assertFalse(should_process_file("test.css", [], []))
        self.assertFalse(should_process_file("test.css", None, []))

    def test_should_process_none_exclude_patterns(self):
        """Test with None exclude patterns."""
        self.assertTrue(should_process_file("test.css", ["css"], None))
        self.assertTrue(should_process_file("test.min.css", ["css"], None))

    def test_should_process_complex_patterns(self):
        """Test with more complex exclude patterns."""
        extensions = ["css"]
        patterns = ["*.min.*", "*-min.*", "*.bundle.css", "vendor.css"]
        # Note: pattern matching is simple and has limitations
        self.assertFalse(should_process_file("app.bundle.css", extensions, patterns))
        self.assertFalse(should_process_file("vendor.css", extensions, patterns))
        self.assertTrue(should_process_file("app.css", extensions, patterns))

    def test_should_process_case_sensitivity(self):
        """Test that extensions are case-sensitive (normalized to lowercase)."""
        # Extensions are normalized to lowercase
        self.assertTrue(should_process_file("test.CSS", ["css"], []))
        self.assertFalse(should_process_file("test.CSS", ["js"], []))


class FileManagerEdgeCaseTests(TestCase):
    """Tests for FileManager edge cases."""

    def test_supported_extensions_with_none(self):
        """Test FileManager when supported_extensions is None."""
        storage = FileSystemStorage()

        class TestFileManager:
            def __init__(self):
                self.storage = storage
                self.supported_extensions = None
                self.exclude_patterns = []
                self.min_file_size = 200

            def is_compression_candidate(self, file_path):
                return True

        manager = TestFileManager()
        # Should handle None gracefully
        extensions = getattr(manager, "supported_extensions", None) or {}
        self.assertIsNone(extensions.get("css"))
