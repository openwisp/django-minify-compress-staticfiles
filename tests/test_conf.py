"""Tests for configuration module."""

from django.test import TestCase, override_settings

from django_minify_compress_staticfiles.conf import DEFAULT_SETTINGS, get_setting


class GetSettingTests(TestCase):
    """Tests for get_setting function."""

    def test_get_default_value(self):
        """Test getting default value when setting not defined."""
        self.assertEqual(get_setting("ENABLED"), True)
        self.assertIsNone(get_setting("NONEXISTENT_SETTING"))

    @override_settings(MINICOMPRESS_ENABLED=False)
    def test_get_overridden_value(self):
        """Test getting overridden setting value."""
        self.assertFalse(get_setting("ENABLED"))

    @override_settings(MINICOMPRESS_MIN_FILE_SIZE=500)
    def test_get_custom_values(self):
        """Test getting custom setting values."""
        self.assertEqual(get_setting("MIN_FILE_SIZE"), 500)

    def test_none_value_falls_back_to_default(self):
        """Explicit None is treated as unset and returns the default for all types."""
        with override_settings(MINICOMPRESS_ENABLED=None):
            self.assertEqual(get_setting("ENABLED"), DEFAULT_SETTINGS["ENABLED"])
        with override_settings(MINICOMPRESS_MIN_FILE_SIZE=None):
            self.assertEqual(
                get_setting("MIN_FILE_SIZE"), DEFAULT_SETTINGS["MIN_FILE_SIZE"]
            )
        with override_settings(MINICOMPRESS_COMPRESSION_LEVEL_GZIP=None):
            self.assertEqual(
                get_setting("COMPRESSION_LEVEL_GZIP"),
                DEFAULT_SETTINGS["COMPRESSION_LEVEL_GZIP"],
            )
        with override_settings(MINICOMPRESS_SUPPORTED_EXTENSIONS=None):
            self.assertEqual(
                get_setting("SUPPORTED_EXTENSIONS"),
                DEFAULT_SETTINGS["SUPPORTED_EXTENSIONS"],
            )


class DefaultSettingsTests(TestCase):
    """Tests for DEFAULT_SETTINGS dictionary."""

    def test_required_settings_exist(self):
        """Test all required settings exist with correct defaults."""
        # Boolean settings
        self.assertTrue(DEFAULT_SETTINGS["ENABLED"])
        self.assertTrue(DEFAULT_SETTINGS["MINIFY_FILES"])
        self.assertTrue(DEFAULT_SETTINGS["GZIP_COMPRESSION"])
        self.assertTrue(DEFAULT_SETTINGS["BROTLI_COMPRESSION"])
        self.assertTrue(DEFAULT_SETTINGS["PRESERVE_COMMENTS"])

        # Numeric settings
        self.assertEqual(DEFAULT_SETTINGS["MIN_FILE_SIZE"], 200)
        self.assertEqual(DEFAULT_SETTINGS["MAX_FILE_SIZE"], 10485760)
        self.assertEqual(DEFAULT_SETTINGS["COMPRESSION_LEVEL_GZIP"], 6)
        self.assertEqual(DEFAULT_SETTINGS["COMPRESSION_LEVEL_BROTLI"], 4)

    def test_supported_extensions(self):
        """Test SUPPORTED_EXTENSIONS has required types."""
        extensions = DEFAULT_SETTINGS["SUPPORTED_EXTENSIONS"]
        self.assertIn("css", extensions)
        self.assertIn("js", extensions)
        self.assertIn("html", extensions)

    def test_exclude_patterns(self):
        """Test EXCLUDE_PATTERNS has minified file patterns."""
        patterns = DEFAULT_SETTINGS["EXCLUDE_PATTERNS"]
        self.assertIn("*.min.*", patterns)
        self.assertIn("*-min.*", patterns)
        self.assertIn("*swagger-ui-*", patterns)
