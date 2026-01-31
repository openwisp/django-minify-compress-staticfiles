"""Tests for security features and edge cases."""

import gzip
import json
import os
import shutil
import tempfile
from unittest.mock import patch

import brotli
from django.core.files.storage import FileSystemStorage
from django.test import TestCase, override_settings

from django_minify_compress_staticfiles.storage import (
    CompressionMixin,
    MinicompressStorage,
    MinificationMixin,
)
from django_minify_compress_staticfiles.utils import FileManager, is_safe_path


class _TestableSecurityMinification(MinificationMixin, CompressionMixin):
    """Testable version for security tests."""

    def __init__(self, temp_dir=None):
        self.temp_dir = temp_dir or tempfile.mkdtemp()
        self.saved_files = {}
        self.file_manager = FileManager(self)

    def exists(self, path):
        return path in self.saved_files or os.path.exists(
            os.path.join(self.temp_dir, path)
        )

    def open(self, path, mode="rb"):
        full_path = os.path.join(self.temp_dir, path)
        return open(full_path, mode)

    def save(self, path, content):
        full_path = os.path.join(self.temp_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        if hasattr(content, "read"):
            data = content.read()
        else:
            data = content
        if isinstance(data, str):
            data = data.encode("utf-8")
        with open(full_path, "wb") as f:
            f.write(data)
        self.saved_files[path] = full_path
        return path

    def path(self, name):
        return os.path.join(self.temp_dir, name)

    def cleanup(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class PathTraversalTests(TestCase):
    """Tests for path traversal protection."""

    def test_is_safe_path_with_dots(self):
        """Test that paths with .. are rejected."""
        self.assertFalse(is_safe_path("../etc/passwd"))
        self.assertFalse(is_safe_path("../../etc/passwd"))
        self.assertFalse(is_safe_path("./../etc/passwd"))

    def test_is_safe_path_normal(self):
        """Test that normal paths are accepted."""
        self.assertTrue(is_safe_path("static/css/style.css"))
        self.assertTrue(is_safe_path("style.css"))
        self.assertTrue(is_safe_path("deep/nested/path/to/file.txt"))

    def test_is_safe_path_with_base_dir(self):
        """Test path validation with base directory."""
        # Create a real temp directory for testing
        with tempfile.TemporaryDirectory() as base:
            # Test paths that are relative to base
            abs_safe_path = os.path.join(base, "css", "style.css")
            abs_unsafe_path = os.path.join(base, "..", "etc", "passwd")

            self.assertTrue(is_safe_path(abs_safe_path, base))
            self.assertFalse(is_safe_path(abs_unsafe_path, base))
            self.assertTrue(
                is_safe_path(os.path.join(base, "subdir", "file.txt"), base)
            )


class FileSizeLimitTests(TestCase):
    """Tests for file size limits."""

    def setUp(self):
        self.minifier = _TestableSecurityMinification()

    def tearDown(self):
        self.minifier.cleanup()

    def test_max_file_size_enforced(self):
        """Test that files exceeding MAX_FILE_SIZE are skipped."""
        # Create a file larger than default MAX_FILE_SIZE (10MB)
        large_file = os.path.join(self.minifier.temp_dir, "large.css")
        with open(large_file, "wb") as f:
            f.write(b"body { margin: 0; }" * 1000000)

        result = self.minifier.process_minification(["large.css"])
        # Should skip large file
        self.assertEqual(result, {})

    def test_file_within_size_limit(self):
        """Test that files within MAX_FILE_SIZE are processed."""
        small_file = os.path.join(self.minifier.temp_dir, "small.css")
        with open(small_file, "w") as f:
            f.write("body {\n    margin: 0;\n    padding: 0;\n}" * 100)

        result = self.minifier.process_minification(["small.css"])
        # Should process small file
        self.assertIn("small.css", result)


class MaxFilesPerRunTests(TestCase):
    """Tests for MAX_FILES_PER_RUN limit."""

    def setUp(self):
        self.minifier = _TestableSecurityMinification()
        # Create multiple CSS files
        for i in range(5):
            test_file = os.path.join(self.minifier.temp_dir, f"style{i}.css")
            with open(test_file, "w") as f:
                f.write("body {\n    margin: 0;\n}" * 10)

    def tearDown(self):
        self.minifier.cleanup()

    @override_settings(MINICOMPRESS_MAX_FILES_PER_RUN=2)
    def test_max_files_limit_minification(self):
        """Test that only MAX_FILES_PER_RUN files are minified."""
        paths = [f"style{i}.css" for i in range(5)]
        result = self.minifier.process_minification(paths)
        # Should only process 2 files
        self.assertEqual(len(result), 2)

    @override_settings(MINICOMPRESS_MAX_FILES_PER_RUN=2)
    def test_max_files_limit_compression(self):
        """Test that only MAX_FILES_PER_RUN files are compressed."""
        paths = [f"style{i}.css" for i in range(5)]
        result = self.minifier.process_compression(paths)
        # Should only process 2 files
        self.assertEqual(len(result), 2)


class MinificationEdgeCaseTests(TestCase):
    """Tests for minification edge cases."""

    def setUp(self):
        self.minifier = _TestableSecurityMinification()

    def tearDown(self):
        self.minifier.cleanup()

    def test_minification_with_none_preserve_comments(self):
        """Test minification when PRESERVE_COMMENTS is None."""
        # Patch get_setting to return None to test the branch
        with patch(
            "django_minify_compress_staticfiles.storage.get_setting", return_value=None
        ):
            css = "/* comment */ body { margin: 0; }"
            result = self.minifier.minify_file_content(css, "css")
            self.assertIsInstance(result, str)

    def test_minification_css_exception(self):
        """Test CSS minification exception handling."""
        # Force an exception by passing non-string content
        with patch(
            "django_minify_compress_staticfiles.storage.rcssmin"
        ) as mock_rcssmin:
            mock_rcssmin.cssmin.side_effect = Exception("CSS minification error")
            result = self.minifier.minify_file_content("body { }", "css")
            # Should return original content on error
            self.assertEqual(result, "body { }")

    def test_minification_js_exception(self):
        """Test JS minification exception handling."""
        with patch("django_minify_compress_staticfiles.storage.rjsmin") as mock_rjsmin:
            mock_rjsmin.jsmin.side_effect = Exception("JS minification error")
            result = self.minifier.minify_file_content("function() {}", "js")
            # Should return original content on error
            self.assertEqual(result, "function() {}")


class CompressionEdgeCaseTests(TestCase):
    """Tests for compression edge cases."""

    def setUp(self):
        self.compressor = _TestableSecurityMinification()

    def tearDown(self):
        self.compressor.cleanup()

    def test_gzip_compress_with_string(self):
        """Test gzip compression with string input."""
        content = "Hello World" * 100
        result = self.compressor.gzip_compress(content)
        self.assertIsInstance(result, bytes)
        decompressed = gzip.decompress(result).decode("utf-8")
        self.assertEqual(decompressed, content)

    def test_brotli_compress_with_string(self):
        """Test brotli compression with string input."""
        content = "Hello World" * 100
        result = self.compressor.brotli_compress(content)
        self.assertIsInstance(result, bytes)
        decompressed = brotli.decompress(result).decode("utf-8")
        self.assertEqual(decompressed, content)

    def test_compression_level_clamping(self):
        """Test that compression levels are clamped to valid ranges."""
        with override_settings(
            MINICOMPRESS_COMPRESSION_LEVEL_GZIP=999,
            MINICOMPRESS_COMPRESSION_LEVEL_BROTLI=999,
        ):
            # Should not raise error with invalid levels
            content = "test" * 100
            gzipped = self.compressor.gzip_compress(content)
            brotlied = self.compressor.brotli_compress(content)
            self.assertIsInstance(gzipped, bytes)
            self.assertIsInstance(brotlied, bytes)

    def test_compression_with_negative_level(self):
        """Test compression with negative levels."""
        with override_settings(
            MINICOMPRESS_COMPRESSION_LEVEL_GZIP=-1,
            MINICOMPRESS_COMPRESSION_LEVEL_BROTLI=-1,
        ):
            content = "test" * 100
            gzipped = self.compressor.gzip_compress(content)
            brotlied = self.compressor.brotli_compress(content)
            self.assertIsInstance(gzipped, bytes)
            self.assertIsInstance(brotlied, bytes)


class AbsolutePathTests(TestCase):
    """Tests for absolute path handling."""

    def setUp(self):
        self.compressor = _TestableSecurityMinification()

    def tearDown(self):
        self.compressor.cleanup()

    def test_compression_with_absolute_path(self):
        """Test compression handles absolute paths correctly."""
        # Create file in temp dir
        test_file = os.path.join(self.compressor.temp_dir, "test.css")
        with open(test_file, "w") as f:
            f.write("body { margin: 0; }" * 100)

        # Use absolute path
        abs_path = os.path.abspath(test_file)
        result = self.compressor.process_compression([abs_path])
        # Should create compressed files
        self.assertIn(abs_path, result)

    def test_compression_absolute_path_root_only(self):
        """Test compression with absolute path that has only root."""
        # This is an edge case where Path.parts has only one element
        # It should fallback to basename
        test_file = os.path.join(self.compressor.temp_dir, "test.css")
        with open(test_file, "w") as f:
            f.write("body { margin: 0; }" * 100)

        result = self.compressor.process_compression([test_file])
        self.assertIn(test_file, result)


class UnsafePathTests(TestCase):
    """Tests for unsafe path handling."""

    def setUp(self):
        self.processor = _TestableSecurityMinification()

    def tearDown(self):
        self.processor.cleanup()

    def test_read_file_unsafe_path(self):
        """Test that unsafe paths are rejected when reading."""
        result = self.processor._read_file_content("../etc/passwd")
        self.assertIsNone(result)

    def test_write_file_unsafe_path(self):
        """Test that unsafe paths are rejected when writing."""
        # Should not raise error, just return without writing
        self.processor._write_file_content("../etc/passwd", b"test", is_text=False)
        # File should not exist
        self.assertFalse(
            os.path.exists(os.path.join(self.processor.temp_dir, "etc", "passwd"))
        )

    def test_write_file_relative_unsafe_path(self):
        """Test that relative unsafe paths are rejected."""
        self.processor._write_file_content("../../test.txt", b"test", is_text=False)
        # Should not write file
        self.assertEqual(self.processor.saved_files, {})


class FileManagerExtensionTests(TestCase):
    """Tests for FileManager with different extension types."""

    def test_should_process_with_supported_extensions(self):
        """Test should_process with supported extensions."""
        storage = FileSystemStorage()
        manager = FileManager(storage)

        # Test with CSS and JS files (should process)
        self.assertTrue(manager.should_process("style.css"))
        self.assertTrue(manager.should_process("app.js"))
        # Test with unsupported extension
        self.assertFalse(manager.should_process("image.png"))


class ManifestUpdateTests(TestCase):
    """Tests for manifest update functionality."""

    def test_update_manifest_original_not_in_manifest(self):
        """Test manifest update when original path not in manifest."""
        # Test the branch where original not in manifest (line 347)
        # We'll patch _update_manifest to test this specific branch
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create storage with STATIC_ROOT set
            with override_settings(STATIC_ROOT=temp_dir):
                storage = MinicompressStorage()

            # Create an existing manifest with some entries
            manifest_path = os.path.join(temp_dir, "staticfiles.json")
            with open(manifest_path, "w") as f:
                json.dump({"existing.css": "existing.min.abc123.css"}, f)

            # Update with files where original not in manifest
            minified_files = {"new.css": "new.min.xyz789.css"}

            # Call _update_manifest
            storage._update_manifest(minified_files)

            # Manifest should have original entry but not new one
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            self.assertIn("existing.css", manifest)
            self.assertNotIn("new.css", manifest)


class OSExceptionHandlingTests(TestCase):
    """Tests for OSError handling in file operations."""

    def setUp(self):
        self.processor = _TestableSecurityMinification()

    def tearDown(self):
        self.processor.cleanup()

    def test_read_file_oserror(self):
        """Test OSError handling when reading file via filesystem fallback."""
        # Test the fallback path that uses os.path.getsize (lines 227-238)
        # We need to mock storage methods to return False
        original_exists = self.processor.exists

        def mock_exists(_path):
            # Return False to force fallback to filesystem
            return False

        self.processor.exists = mock_exists
        try:
            # Create a file in the temp dir
            test_file = os.path.join(self.processor.temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")

            # Now mock os.path.getsize to raise OSError
            with patch("os.path.getsize", side_effect=OSError("Permission denied")):
                result = self.processor._read_file_content(test_file)
                self.assertIsNone(result)
        finally:
            self.processor.exists = original_exists


class BinaryFileHandlingTests(TestCase):
    """Tests for binary file handling during minification."""

    def setUp(self):
        self.minifier = _TestableSecurityMinification()

    def tearDown(self):
        self.minifier.cleanup()

    def test_minification_with_binary_content(self):
        """Test that binary content is handled correctly."""
        # Create a file with bytes that will fail UTF-8 decode
        test_file = os.path.join(self.minifier.temp_dir, "binary.css")
        with open(test_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03\xff\xfe")

        result = self.minifier.process_minification(["binary.css"])
        # Should skip binary file
        self.assertEqual(result, {})

    def test_minification_bytes_content(self):
        """Test minification when content is bytes."""
        # rcssmin and rjsmin handle both str and bytes
        result = self.minifier.minify_file_content(b"body { margin: 0; }", "css")
        # Should return bytes when given bytes
        self.assertIsInstance(result, bytes)
        self.assertIn(b"margin", result)


class CompressionNoneContentTests(TestCase):
    """Tests for handling None content during compression."""

    def setUp(self):
        self.compressor = _TestableSecurityMinification()

    def tearDown(self):
        self.compressor.cleanup()

    def test_compression_with_none_content(self):
        """Test that None content is skipped during compression."""
        test_file = os.path.join(self.compressor.temp_dir, "test.css")
        with open(test_file, "w") as f:
            f.write("body { margin: 0; }")

        # Mock _read_file_content to return None
        with patch.object(self.compressor, "_read_file_content", return_value=None):
            result = self.compressor.process_compression([test_file])
            # Should skip files with None content
            self.assertEqual(result, {})
