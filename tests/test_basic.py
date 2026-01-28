import os
import tempfile
from unittest import mock

from django.test import TestCase, override_settings

from django_minify_compress_staticfiles.conf import DEFAULT_SETTINGS, get_setting
from django_minify_compress_staticfiles.storage import MinicompressStorage
from django_minify_compress_staticfiles.utils import (
    FileManager,
    generate_file_hash,
    should_process_file,
)


class BasicTests(TestCase):
    """Basic tests to ensure that package loads correctly."""

    def test_import_storage(self):
        """Test that storage class can be imported."""
        self.assertTrue(callable(MinicompressStorage))

    def test_import_utils(self):
        """Test that utility functions can be imported."""
        self.assertTrue(callable(FileManager))

    def test_import_conf(self):
        """Test that configuration can be imported."""
        self.assertTrue(callable(get_setting))
        self.assertIsInstance(DEFAULT_SETTINGS, dict)

    def test_file_manager_instantiation(self):
        """Test that file manager can be instantiated."""
        from django.core.files.storage import FileSystemStorage

        storage = FileSystemStorage()
        manager = FileManager(storage)
        self.assertIsNotNone(manager)

    def test_generate_file_hash(self):
        """Test file hash generation."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            hash_value = generate_file_hash(temp_path, length=12)
            self.assertEqual(len(hash_value), 12)
            self.assertIsInstance(hash_value, str)
        finally:
            os.unlink(temp_path)

    def test_should_process_file(self):
        """Test file processing logic."""
        # CSS files should be processed
        self.assertTrue(should_process_file("test.css", {"css": True}, []))

        # JS files should be processed
        self.assertTrue(should_process_file("test.js", {"js": True}, []))

        # Excluded patterns should be skipped
        self.assertFalse(
            should_process_file("test.min.css", {"css": True}, ["*.min.*"])
        )
        self.assertFalse(should_process_file("test-min.js", {"js": True}, ["*-min.*"]))

        # Unsupported extensions should be skipped
        self.assertFalse(should_process_file("test.png", {"css": True}, []))

    def test_default_settings_structure(self):
        """Test that default settings have expected structure."""
        self.assertIn("MINIFY_FILES", DEFAULT_SETTINGS)
        self.assertIn("GZIP_COMPRESSION", DEFAULT_SETTINGS)
        self.assertIn("BROTLI_COMPRESSION", DEFAULT_SETTINGS)
        self.assertIn("SUPPORTED_EXTENSIONS", DEFAULT_SETTINGS)
        self.assertIn("EXCLUDE_PATTERNS", DEFAULT_SETTINGS)

        # Check supported extensions
        extensions = DEFAULT_SETTINGS["SUPPORTED_EXTENSIONS"]
        self.assertIn("css", extensions)
        self.assertIn("js", extensions)

        # Check exclude patterns
        patterns = DEFAULT_SETTINGS["EXCLUDE_PATTERNS"]
        self.assertIn("*.min.*", patterns)

    def test_supported_extensions_comprehensive(self):
        """Test supported file types."""
        extensions = DEFAULT_SETTINGS["SUPPORTED_EXTENSIONS"]

        # Text-based files that should be minified
        self.assertIn("css", extensions)
        self.assertIn("js", extensions)

        # Files that should be compressed
        self.assertIn("txt", extensions)
        self.assertIn("json", extensions)
        self.assertIn("html", extensions)
        self.assertIn("htm", extensions)
        self.assertIn("xml", extensions)
        self.assertIn("svg", extensions)
        self.assertIn("md", extensions)
        self.assertIn("rst", extensions)

    def test_default_settings_values(self):
        """Test default setting values."""
        self.assertEqual(DEFAULT_SETTINGS["MINIFY_FILES"], True)
        self.assertEqual(DEFAULT_SETTINGS["GZIP_COMPRESSION"], True)
        self.assertEqual(DEFAULT_SETTINGS["BROTLI_COMPRESSION"], True)
        self.assertEqual(DEFAULT_SETTINGS["MIN_FILE_SIZE"], 200)
        self.assertEqual(DEFAULT_SETTINGS["COMPRESSION_LEVEL_GZIP"], 9)
        self.assertEqual(DEFAULT_SETTINGS["COMPRESSION_LEVEL_BROTLI"], 11)
        self.assertEqual(DEFAULT_SETTINGS["PRESERVE_COMMENTS"], True)

    def test_storage_class_structure(self):
        """Test storage class has required methods."""
        # Check that storage class has the expected methods
        self.assertTrue(hasattr(MinicompressStorage, "post_process"))
        self.assertTrue(hasattr(MinicompressStorage, "process_minification"))
        self.assertTrue(hasattr(MinicompressStorage, "process_compression"))

    @override_settings(MINICOMPRESS_ENABLED=False)
    def test_settings_override(self):
        """Test that settings can be overridden."""
        from django.conf import settings

        # The override should work
        self.assertFalse(getattr(settings, "MINICOMPRESS_ENABLED", True))


if __name__ == "__main__":
    import unittest

    unittest.main()
