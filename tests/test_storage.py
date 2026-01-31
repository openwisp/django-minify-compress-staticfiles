"""Tests for storage functionality."""

import gzip
import os
import shutil
import tempfile

from django.test import TestCase

from django_minify_compress_staticfiles.storage import (
    CompressionMixin,
    FileProcessorMixin,
    MinicompressStorage,
    MinificationMixin,
)

try:
    import brotli

    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False


class MockStorage:
    """Mock storage for testing mixins."""

    def __init__(self):
        self.saved_files = {}
        self.temp_dir = tempfile.mkdtemp()

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

        # Normalize data to bytes so we can always write in binary mode.
        if isinstance(data, str):
            data = data.encode("utf-8")
        elif isinstance(data, bytearray):
            data = bytes(data)
        elif not isinstance(data, bytes):
            # Fallback: convert to string then encode.
            data = str(data).encode("utf-8")
        with open(full_path, "wb") as f:
            f.write(data)
        self.saved_files[path] = full_path
        return path

    def path(self, name):
        return os.path.join(self.temp_dir, name)

    def cleanup(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class _TestableFileProcessor(FileProcessorMixin, MockStorage):
    """Testable version of FileProcessorMixin."""

    pass


class _TestableMinification(MinificationMixin, MockStorage):
    """Testable version of MinificationMixin."""

    pass


class _TestableCompression(CompressionMixin, MockStorage):
    """Testable version of CompressionMixin."""

    pass


class FileProcessorMixinTests(TestCase):
    """Tests for FileProcessorMixin."""

    def setUp(self):
        self.processor = _TestableFileProcessor()

    def tearDown(self):
        self.processor.cleanup()

    def test_get_file_type(self):
        """Test getting file type from path."""
        self.assertEqual(self.processor._get_file_type("style.css"), "css")
        self.assertEqual(self.processor._get_file_type("app.js"), "js")
        self.assertEqual(self.processor._get_file_type("/path/to/style.css"), "css")

    def test_should_process_minification(self):
        """Test minification eligibility checks."""
        self.assertTrue(self.processor.should_process_minification("style.css"))
        self.assertTrue(self.processor.should_process_minification("app.js"))
        self.assertFalse(self.processor.should_process_minification("style.min.css"))
        self.assertFalse(self.processor.should_process_minification("data.json"))

    def test_minify_content(self):
        """Test CSS and JS minification."""
        css = "body {\n    margin: 0;\n    padding: 0;\n}"
        minified_css = self.processor.minify_file_content(css, "css")
        self.assertIn("body{", minified_css)
        self.assertLess(len(minified_css), len(css))

        js = "function hello() {\n    console.log('Hello');\n}"
        minified_js = self.processor.minify_file_content(js, "js")
        self.assertLess(len(minified_js), len(js))

        # Unknown type returns original
        txt = "some content"
        self.assertEqual(self.processor.minify_file_content(txt, "txt"), txt)


class CompressionMixinTests(TestCase):
    """Tests for CompressionMixin."""

    def setUp(self):
        self.compressor = _TestableCompression()

    def tearDown(self):
        self.compressor.cleanup()

    def test_gzip_compress(self):
        """Test gzip compression."""
        content = "Hello World! " * 100
        compressed = self.compressor.gzip_compress(content)
        self.assertIsInstance(compressed, bytes)
        self.assertLess(len(compressed), len(content))
        # Verify decompression
        self.assertEqual(gzip.decompress(compressed).decode("utf-8"), content)

    def test_brotli_compress(self):
        """Test brotli compression."""
        if not HAS_BROTLI:
            self.skipTest("Brotli not installed")

        content = "Hello World! " * 100
        compressed = self.compressor.brotli_compress(content)
        self.assertIsInstance(compressed, bytes)
        self.assertLess(len(compressed), len(content))
        # Verify decompression
        import brotli  # noqa: F811

        self.assertEqual(brotli.decompress(compressed).decode("utf-8"), content)


class MinicompressStorageTests(TestCase):
    """Tests for MinicompressStorage class."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.static_root = os.path.join(self.temp_dir, "static")
        os.makedirs(self.static_root)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_storage_instantiation(self):
        """Test storage can be instantiated with required methods."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            self.assertTrue(hasattr(storage, "post_process"))
            self.assertTrue(hasattr(storage, "process_minification"))
            self.assertTrue(hasattr(storage, "process_compression"))
            self.assertTrue(hasattr(storage, "file_manager"))

    def test_post_process_dry_run(self):
        """Test post_process with dry_run can be called without side effects."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            result = list(storage.post_process({}, dry_run=True))
            self.assertIsInstance(result, list)

    def test_post_process_yields_paths(self):
        """Test post_process yields processed paths."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()

            # Create a test file
            test_file = os.path.join(self.static_root, "test.css")
            with open(test_file, "w") as f:
                f.write("body { margin: 0; }")

            paths = {"test.css": (storage, "test.css")}
            results = list(storage.post_process(paths, dry_run=False))

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0][0], "test.css")
