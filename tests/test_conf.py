"""Tests for configuration module."""

from django.test import TestCase, override_settings

from django_minify_compress_staticfiles.conf import DEFAULT_SETTINGS, get_setting


class GetSettingTests(TestCase):
    """Tests for get_setting function."""

    def test_get_default_value(self):
        """Test getting default value when setting not defined."""
        result = get_setting("NONEXISTENT_SETTING", "default_value")
        self.assertEqual(result, "default_value")

    @override_settings(MINICOMPRESS_ENABLED=False)
    def test_get_overridden_value(self):
        """Test getting overridden setting value."""
        result = get_setting("ENABLED", True)
        self.assertFalse(result)

    @override_settings(MINICOMPRESS_MIN_FILE_SIZE=500)
    def test_get_custom_values(self):
        """Test getting custom setting values."""
        self.assertEqual(get_setting("MIN_FILE_SIZE", 200), 500)


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
        self.assertEqual(DEFAULT_SETTINGS["COMPRESSION_LEVEL_GZIP"], 9)
        self.assertEqual(DEFAULT_SETTINGS["COMPRESSION_LEVEL_BROTLI"], 11)

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
