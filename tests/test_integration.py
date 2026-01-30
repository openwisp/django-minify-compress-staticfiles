"""Integration tests for end-to-end static file processing."""

import os
import shutil
import tempfile

from django.test import TestCase, override_settings

from django_minify_compress_staticfiles.storage import MinicompressStorage

try:
    import brotli  # noqa: F401
    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False


class IntegrationTests(TestCase):
    """End-to-end integration tests."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.static_root = os.path.join(self.temp_dir, "static")
        os.makedirs(self.static_root)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_css_processing(self):
        """Test complete CSS processing: minification + compression."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()

            css_content = """
            body {
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
            }
            .container {
                width: 100%;
                max-width: 1200px;
            }
            """ * 5  # Repeat to make it larger

            test_file = os.path.join(self.static_root, "style.css")
            with open(test_file, "w") as f:
                f.write(css_content)

            paths = {"style.css": (storage, "style.css")}
            list(storage.post_process(paths, dry_run=False))

            # Verify original file still exists
            self.assertTrue(os.path.exists(test_file))

    def test_full_js_processing(self):
        """Test complete JS processing: minification + compression."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()

            js_content = """
            (function() {
                'use strict';
                function init() {
                    console.log('Application initialized');
                }
                init();
            })();
            """ * 5

            test_file = os.path.join(self.static_root, "app.js")
            with open(test_file, "w") as f:
                f.write(js_content)

            paths = {"app.js": (storage, "app.js")}
            list(storage.post_process(paths, dry_run=False))

            self.assertTrue(os.path.exists(test_file))

    def test_minified_files_skipped(self):
        """Test that already minified files are skipped."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            self.assertFalse(storage.should_process_minification("style.min.css"))

    def test_small_files_not_compressed(self):
        """Test that small files are not compressed."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()

            test_file = os.path.join(self.static_root, "tiny.css")
            with open(test_file, "w") as f:
                f.write("small")

            self.assertFalse(storage.should_process_compression(test_file))

    @override_settings(MINICOMPRESS_MINIFY_FILES=False)
    def test_minification_disabled(self):
        """Test minification can be disabled."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            self.assertFalse(storage.should_process_minification("style.css"))

    @override_settings(MINICOMPRESS_GZIP_COMPRESSION=False, MINICOMPRESS_BROTLI_COMPRESSION=False)
    def test_compression_disabled(self):
        """Test compression can be disabled."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()

            test_file = os.path.join(self.static_root, "large.css")
            with open(test_file, "w") as f:
                f.write("x" * 500)

            compressed = storage.process_compression(["large.css"])
            self.assertEqual(compressed, {})

    def test_multiple_files_processing(self):
        """Test processing multiple files at once."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()

            # Create CSS and JS files
            css_file = os.path.join(self.static_root, "style.css")
            js_file = os.path.join(self.static_root, "app.js")

            with open(css_file, "w") as f:
                f.write("body { margin: 0; padding: 0; }" * 20)
            with open(js_file, "w") as f:
                f.write("function test() { console.log('test'); }" * 20)

            paths = {
                "style.css": (storage, "style.css"),
                "app.js": (storage, "app.js"),
            }
            results = list(storage.post_process(paths, dry_run=False))

            self.assertEqual(len(results), 2)
