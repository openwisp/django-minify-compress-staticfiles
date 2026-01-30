"""Tests for utility functions."""

import os
import tempfile

from django.test import TestCase

from django_minify_compress_staticfiles.utils import (
    FileManager,
    create_hashed_filename,
    generate_file_hash,
    get_file_size,
    normalize_extension,
    should_process_file,
)


class GenerateFileHashTests(TestCase):
    """Tests for generate_file_hash function."""

    def test_hash_from_bytes(self):
        """Test hash generation from bytes."""
        content = b"test content"
        hash1 = generate_file_hash(content)
        hash2 = generate_file_hash(content)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 12)

    def test_hash_from_file(self):
        """Test hash generation from file path."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test content for file")
            temp_path = f.name
        try:
            hash_value = generate_file_hash(temp_path)
            self.assertEqual(len(hash_value), 12)
        finally:
            os.unlink(temp_path)

    def test_hash_edge_cases(self):
        """Test hash with custom length, different content, and error cases."""
        # Custom length
        self.assertEqual(len(generate_file_hash(b"test", length=8)), 8)
        # Different content produces different hashes
        self.assertNotEqual(generate_file_hash(b"a"), generate_file_hash(b"b"))
        # Nonexistent file returns empty string
        self.assertEqual(generate_file_hash("/nonexistent/file.txt"), "")
        # Invalid type (non-bytes, non-path object) returns empty string
        self.assertEqual(generate_file_hash(object()), "")


class CreateHashedFilenameTests(TestCase):
    """Tests for create_hashed_filename function."""

    def test_filename_with_and_without_path(self):
        """Test filename creation with hash."""
        # Basic filename
        result = create_hashed_filename("style.css", "abc123def456")
        self.assertEqual(result, "style.abc123def456.css")

        # Filename with path - should preserve directory
        result = create_hashed_filename("css/main/style.css", "abc123def456")
        self.assertIn("css/main/", result)
        self.assertIn("abc123def456", result)


class UtilityFunctionsTests(TestCase):
    """Tests for normalize_extension and get_file_size."""

    def test_normalize_extension(self):
        """Test extension normalization."""
        self.assertEqual(normalize_extension(".CSS"), "css")
        self.assertEqual(normalize_extension("JS"), "js")

    def test_get_file_size(self):
        """Test getting file size."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test content here")
            temp_path = f.name
        try:
            self.assertEqual(get_file_size(temp_path), 17)
        finally:
            os.unlink(temp_path)
        # Nonexistent file returns 0
        self.assertEqual(get_file_size("/nonexistent/file.txt"), 0)


class ShouldProcessFileTests(TestCase):
    """Tests for should_process_file function."""

    def test_supported_extensions(self):
        """Test supported and unsupported extensions."""
        self.assertTrue(should_process_file("test.css", ["css"], []))
        self.assertTrue(should_process_file("test.js", ["js"], []))
        self.assertFalse(should_process_file("test.png", ["css"], []))
        self.assertFalse(should_process_file("test.css", [], []))
    def test_exclude_patterns(self):
        """Test exclude patterns."""
        self.assertFalse(should_process_file("jquery.min.css", ["css"], ["*.min.*"]))
        self.assertFalse(should_process_file("app-min.js", ["js"], ["*-min.*"]))
        self.assertTrue(should_process_file("test.css", ["css"], None))


class FileManagerTests(TestCase):
    """Tests for FileManager class."""

    def setUp(self):
        """Set up test fixtures."""
        from django.core.files.storage import FileSystemStorage
        self.storage = FileSystemStorage()
        self.manager = FileManager(self.storage)

    def test_properties(self):
        """Test FileManager properties."""
        self.assertIn("css", self.manager.supported_extensions)
        self.assertIn("*.min.*", self.manager.exclude_patterns)
        self.assertEqual(self.manager.min_file_size, 200)

    def test_should_process(self):
        """Test should_process method."""
        self.assertTrue(self.manager.should_process("style.css"))
        self.assertFalse(self.manager.should_process("style.min.css"))

    def test_is_compression_candidate(self):
        """Test compression candidate check."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"x" * 300)  # Large file
            large_path = f.name
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"x" * 10)  # Small file
            small_path = f.name
        try:
            self.assertTrue(self.manager.is_compression_candidate(large_path))
            self.assertFalse(self.manager.is_compression_candidate(small_path))
        finally:
            os.unlink(large_path)
            os.unlink(small_path)
