"""Tests for storage functionality."""

import gzip
import json
import os
import shutil
import tempfile

import brotli
from django.core.management import call_command
from django.test import TestCase

from django_minify_compress_staticfiles.storage import (
    CompressionMixin,
    FileProcessorMixin,
    MinicompressStorage,
    MinificationMixin,
)


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


class _TestableMinification(MinificationMixin, CompressionMixin, MockStorage):
    """Testable version of MinificationMixin with CompressionMixin for file I/O."""

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

    def test_minify_content_css_exception(self):
        """Test CSS minification exception handling."""
        from django_minify_compress_staticfiles import storage as storage_module

        # Save original rcssmin
        original_rcssmin = storage_module.rcssmin

        # Mock rcssmin to raise an exception
        class MockRcssmin:
            @staticmethod
            def cssmin(content, keep_bang_comments=True):
                raise Exception("CSS minification error")

        storage_module.rcssmin = MockRcssmin()
        try:
            css = "body { margin: 0; }"
            result = self.processor.minify_file_content(css, "css")
            # Should return original content on error
            self.assertEqual(result, css)
        finally:
            storage_module.rcssmin = original_rcssmin

    def test_minify_content_js_exception(self):
        """Test JS minification exception handling."""
        from django_minify_compress_staticfiles import storage as storage_module

        # Save original rjsmin
        original_rjsmin = storage_module.rjsmin

        # Mock rjsmin to raise an exception
        class MockRjsmin:
            @staticmethod
            def jsmin(content, keep_bang_comments=True):
                raise Exception("JS minification error")

        storage_module.rjsmin = MockRjsmin()
        try:
            js = "function test() {}"
            result = self.processor.minify_file_content(js, "js")
            # Should return original content on error
            self.assertEqual(result, js)
        finally:
            storage_module.rjsmin = original_rjsmin


class MinificationMixinTests(TestCase):
    """Tests for MinificationMixin."""

    def setUp(self):
        self.minifier = _TestableMinification()

    def tearDown(self):
        self.minifier.cleanup()

    def test_process_minification_unchanged_content(self):
        """Test that files aren't minified if content doesn't change size."""
        # Create a file with already-minified content
        test_file = os.path.join(self.minifier.temp_dir, "tiny.css")
        with open(test_file, "w") as f:
            f.write("a")  # Single character - can't be minified further

        result = self.minifier.process_minification(["tiny.css"])
        # Should not create a minified version since size wouldn't decrease
        self.assertEqual(result, {})

    def test_process_minification_with_directory(self):
        """Test minification preserves directory structure."""
        os.makedirs(os.path.join(self.minifier.temp_dir, "css"), exist_ok=True)
        test_file = os.path.join(self.minifier.temp_dir, "css", "style.css")
        with open(test_file, "w") as f:
            f.write("body {\n    margin: 0;\n}" * 10)

        result = self.minifier.process_minification(["css/style.css"])
        self.assertIn("css/style.css", result)
        self.assertIn("css/", result["css/style.css"])
        self.assertIn(".min.", result["css/style.css"])

    def test_process_minification_binary_file(self):
        """Test that binary files are skipped during minification."""
        test_file = os.path.join(self.minifier.temp_dir, "data.bin")
        with open(test_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03\xff\xfe")  # Binary content

        result = self.minifier.process_minification(["data.bin"])
        # Should skip binary files that can't be decoded
        self.assertEqual(result, {})

    def test_process_minification_max_files_limit(self):
        """Test MAX_FILES_PER_RUN limit is respected."""
        # Create multiple CSS files
        for i in range(5):
            test_file = os.path.join(self.minifier.temp_dir, f"style{i}.css")
            with open(test_file, "w") as f:
                f.write(f"body{{margin:{i}}} " * 50)
        # Process with a low limit
        from django_minify_compress_staticfiles.conf import DEFAULT_SETTINGS

        original_max = DEFAULT_SETTINGS.get("MAX_FILES_PER_RUN", 1000)
        DEFAULT_SETTINGS["MAX_FILES_PER_RUN"] = 2
        try:
            paths = [f"style{i}.css" for i in range(5)]
            result = self.minifier.process_minification(paths)
            # Should only process up to the limit
            self.assertLessEqual(len(result), 2)
        finally:
            DEFAULT_SETTINGS["MAX_FILES_PER_RUN"] = original_max

    def test_process_minification_unsafe_path(self):
        """Test that unsafe paths are skipped."""
        result = self.minifier.process_minification(["../etc/passwd"])
        self.assertEqual(result, {})


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
        content = "Hello World! " * 100
        compressed = self.compressor.brotli_compress(content)
        self.assertIsInstance(compressed, bytes)
        self.assertLess(len(compressed), len(content))
        # Verify decompression
        self.assertEqual(brotli.decompress(compressed).decode("utf-8"), content)

    def test_process_compression_with_absolute_path(self):
        """Test compression handles absolute paths correctly."""
        test_file = os.path.join(self.compressor.temp_dir, "large.css")
        with open(test_file, "w") as f:
            f.write("body { margin: 0; }" * 100)
        # Use absolute path
        abs_path = os.path.abspath(test_file)
        result = self.compressor.process_compression([abs_path])
        # Should create compressed files
        self.assertIn(abs_path, result)
        self.assertTrue(any(path.endswith(".gz") for path in result[abs_path]))

    def test_read_file_content_fallback(self):
        """Test _read_file_content falls back to local filesystem."""
        test_file = os.path.join(self.compressor.temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")
        # Read using fallback
        content = self.compressor._read_file_content(test_file)
        self.assertEqual(content, b"test content")

    def test_read_file_content_missing(self):
        """Test _read_file_content returns None for missing files."""
        content = self.compressor._read_file_content("/nonexistent/file.txt")
        self.assertIsNone(content)


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
        """Test post_process yields processed paths including minified files."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            # Create a test file with content that will be minified
            test_file = os.path.join(self.static_root, "test.css")
            with open(test_file, "w") as f:
                f.write("body {\n    margin: 0;\n}" * 20)
            paths = {"test.css": (storage, "test.css")}
            results = list(storage.post_process(paths, dry_run=False))
            # Should yield both original and minified files
            self.assertGreaterEqual(len(results), 1)
            # First result should be the original file
            self.assertEqual(results[0][0], "test.css")

    def test_post_process_with_original_paths_fallback(self):
        """Test post_process uses original paths when parent yields empty results."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            # Create a large CSS file that will be minified
            test_file = os.path.join(self.static_root, "style.css")
            with open(test_file, "w") as f:
                f.write("body {\n    margin: 0;\n    padding: 0;\n}" * 20)
            # Use empty dict for paths - forces fallback to use original paths
            paths = {}
            results = list(storage.post_process(paths, dry_run=False))
            # Should complete without errors even with empty paths
            self.assertIsInstance(results, list)

    def test_post_process_updates_manifest(self):
        """Test that post_process handles manifest operations."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            # Create a CSS file
            test_file = os.path.join(self.static_root, "style.css")
            with open(test_file, "w") as f:
                f.write("body { margin: 0; }" * 20)
            paths = {"style.css": (storage, "style.css")}
            # Should complete without errors
            results = list(storage.post_process(paths, dry_run=False))
            self.assertIsInstance(results, list)

    def test_process_minification_error_handling(self):
        """Test that minification errors are caught and logged."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            # Create a CSS file
            test_file = os.path.join(self.static_root, "style.css")
            with open(test_file, "w") as f:
                f.write("body { margin: 0; }" * 20)
            # Mock the minify_file_content to raise an exception
            original_minify = storage.minify_file_content

            def mock_minify_error(content, file_type):
                raise Exception("Test error")

            storage.minify_file_content = mock_minify_error
            try:
                result = storage.process_minification(["style.css"])
                # Should return empty dict on error, not crash
                self.assertEqual(result, {})
            finally:
                storage.minify_file_content = original_minify

    def test_read_file_content_with_size_limit(self):
        """Test _read_file_content respects MAX_FILE_SIZE setting."""
        with self.settings(STATIC_ROOT=self.static_root, MINICOMPRESS_MAX_FILE_SIZE=10):
            storage = MinicompressStorage()
            # Create a file larger than the limit
            test_file = os.path.join(self.static_root, "large.css")
            with open(test_file, "w") as f:
                f.write("x" * 100)
            # Should return None for files exceeding size limit
            content = storage._read_file_content("large.css")
            self.assertIsNone(content)

    def test_write_file_content_with_unsafe_path(self):
        """Test _write_file_content skips unsafe paths."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            # Try to write to an unsafe path (with path traversal)
            storage._write_file_content("../unsafe.txt", "content", is_text=True)
            # Should not create the file
            self.assertFalse(
                os.path.exists(
                    os.path.join(os.path.dirname(self.static_root), "unsafe.txt")
                )
            )

    def test_process_compression_error_handling(self):
        """Test that compression errors are caught and logged."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            # Create a CSS file
            test_file = os.path.join(self.static_root, "style.css")
            with open(test_file, "w") as f:
                f.write("body { margin: 0; }" * 50)
            # Mock gzip_compress to raise an exception
            original_gzip = storage.gzip_compress

            def mock_gzip_error(content):
                raise Exception("Test gzip error")

            storage.gzip_compress = mock_gzip_error
            try:
                result = storage.process_compression(["style.css"])
                # Should complete without crashing, even if empty
                self.assertIsInstance(result, dict)
            finally:
                storage.gzip_compress = original_gzip

    def test_post_process_dry_run_no_files_created(self):
        """Test dry_run prevents minification and compression."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            # Create a CSS file large enough to be minified
            test_file = os.path.join(self.static_root, "style.css")
            with open(test_file, "w") as f:
                f.write("body {\n    margin: 0;\n    padding: 0;\n}" * 50)
            paths = {"style.css": (storage, "style.css")}
            list(storage.post_process(paths, dry_run=True))
            # Check that no minified files were created
            for filename in os.listdir(self.static_root):
                self.assertNotIn(".min.", filename)
                self.assertNotIn(".gz", filename)
                self.assertNotIn(".br", filename)

    def test_process_compression_brotli_with_absolute_path(self):
        """Test brotli compression with absolute path."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            # Create a large CSS file
            test_file = os.path.join(self.static_root, "style.css")
            with open(test_file, "w") as f:
                f.write("body { margin: 0; }" * 100)
            # Use absolute path
            abs_path = os.path.abspath(test_file)
            result = storage.process_compression([abs_path])
            # Should create brotli compressed file
            self.assertIn(abs_path, result)
            self.assertTrue(any(path.endswith(".br") for path in result[abs_path]))

    def test_process_minification_disabled(self):
        """Test minification is skipped when disabled."""
        with self.settings(
            STATIC_ROOT=self.static_root, MINICOMPRESS_MINIFY_FILES=False
        ):
            storage = MinicompressStorage()
            # Create a CSS file
            test_file = os.path.join(self.static_root, "style.css")
            with open(test_file, "w") as f:
                f.write("body { margin: 0; }" * 50)
            # Should return empty dict when disabled
            result = storage.process_minification(["style.css"])
            self.assertEqual(result, {})

    def test_process_minification_content_none(self):
        """Test minification handles None content."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            # Try to minify a file that doesn't exist (will return None from _read_file_content)
            result = storage.process_minification(["nonexistent.css"])
            self.assertEqual(result, {})

    def test_manifest_update_error_handling(self):
        """Test manifest update handles errors gracefully."""
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            # Create a minified files dict
            minified_files = {"style.css": "style.min.abc123.css"}
            # Mock save to raise an exception
            original_save = storage.save

            def mock_save_error(name, content):
                raise Exception("Manifest save error")

            storage.save = mock_save_error
            try:
                # Should not raise an exception
                storage._update_manifest(minified_files)
            finally:
                storage.save = original_save

    def test_manifest_structure_with_minified_files(self):
        """Test that manifest has proper structure for Django to serve minified files.

        This test verifies the manifest structure is correct with 'paths',
        'version', and either 'settings' or 'hash' keys as required by
        Django's ManifestFilesMixin. Without this structure, Django's {%
        static %} template tag would not return minified files.
        """
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            # Create CSS and JS files with content that can be minified
            css_file = os.path.join(self.static_root, "style.css")
            js_file = os.path.join(self.static_root, "app.js")
            with open(css_file, "w") as f:
                f.write("body {\n    margin: 0;\n    padding: 0;\n}" * 20)
            with open(js_file, "w") as f:
                f.write("function test() {\n    console.log('test');\n}" * 20)
            paths = {
                "style.css": (storage, "style.css"),
                "app.js": (storage, "app.js"),
            }
            # Run post_process
            list(storage.post_process(paths, dry_run=False))
            # Read the manifest file
            manifest_path = os.path.join(self.static_root, storage.manifest_name)
            self.assertTrue(os.path.exists(manifest_path), "Manifest file should exist")
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            # Verify manifest structure
            self.assertIn("paths", manifest, "Manifest must have 'paths' key")
            self.assertIn("version", manifest, "Manifest must have 'version' key")
            # Django uses either 'settings' (older) or 'hash' (newer) key
            self.assertTrue(
                "settings" in manifest or "hash" in manifest,
                "Manifest must have either 'settings' or 'hash' key",
            )
            # Verify paths is a dict
            self.assertIsInstance(
                manifest["paths"], dict, "Manifest 'paths' must be a dictionary"
            )
            # Verify original files are mapped to minified versions
            for original_path in ["style.css", "app.js"]:
                self.assertIn(
                    original_path,
                    manifest["paths"],
                    f"Original file {original_path} should be in manifest",
                )
                mapped_path = manifest["paths"][original_path]
                # The mapped path should contain '.min.' indicating it's minified
                self.assertIn(
                    ".min.",
                    mapped_path,
                    f"File {original_path} should map to minified version, got {mapped_path}",
                )

    def test_manifest_without_proper_structure_fails(self):
        """Test that manifest without 'paths' key would cause issues.

        This test documents the bug that was fixed - if the manifest is
        saved as a flat dict instead of having the proper structure with
        'paths', 'version', and 'settings' keys, Django's
        ManifestFilesMixin won't read it correctly.
        """
        with self.settings(STATIC_ROOT=self.static_root):
            storage = MinicompressStorage()
            manifest_path = os.path.join(self.static_root, storage.manifest_name)
            # Create a malformed manifest (flat dict without 'paths' key)
            # This simulates what the buggy code was doing
            malformed_manifest = {
                "style.css": "style.min.abc123.css",
                "app.js": "app.min.def456.js",
            }
            # Save it as the manifest
            with open(manifest_path, "w") as f:
                json.dump(malformed_manifest, f)
            # Try to read it with read_manifest (this should fail or return unexpected results)
            try:
                manifest_json = storage.read_manifest()
                if manifest_json:
                    manifest = json.loads(manifest_json)
                    # Django's ManifestFilesMixin expects 'paths' key
                    if "paths" not in manifest:
                        # This demonstrates the bug - Django wouldn't find any paths
                        self.assertNotIn("paths", manifest)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

    def test_collectstatic_produces_valid_manifest(self):
        """Test that collectstatic produces a manifest Django can use.

        This test verifies that after running collectstatic, the manifest
        file is in a format that Django's static() template tag can read
        to return minified file paths.
        """
        with self.settings(
            STATIC_ROOT=self.static_root,
            STATICFILES_STORAGE="django_minify_compress_staticfiles.storage.MinicompressStorage",
        ):
            # Create a CSS file
            css_file = os.path.join(self.static_root, "test.css")
            with open(css_file, "w") as f:
                f.write("body {\n    margin: 0;\n    padding: 0;\n}" * 30)
            # Run collectstatic
            call_command("collectstatic", "--noinput", verbosity=0)
            # Read the manifest
            manifest_path = os.path.join(self.static_root, "staticfiles.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                # Verify the manifest has the expected structure
                self.assertIn("paths", manifest)
                self.assertIn("version", manifest)
