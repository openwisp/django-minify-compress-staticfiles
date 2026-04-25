from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

_UNSET = object()

DEFAULT_SETTINGS = {
    "ENABLED": True,
    "MINIFY_FILES": True,
    "BROTLI_COMPRESSION": True,
    "GZIP_COMPRESSION": True,
    "MIN_FILE_SIZE": 200,
    "MAX_FILE_SIZE": 10485760,
    "COMPRESSION_LEVEL_GZIP": 6,
    "COMPRESSION_LEVEL_BROTLI": 4,
    "PRESERVE_COMMENTS": True,
    "MAX_FILES_PER_RUN": 1000,
    "SUPPORTED_EXTENSIONS": {
        "css": True,
        "js": True,
        "txt": True,
        "xml": True,
        "json": True,
        "svg": True,
        "md": True,
        "rst": True,
        "html": True,
        "htm": True,
    },
    "EXCLUDE_PATTERNS": [
        "*.min.*",
        "*-min.*",
        "*.gz",
        "*.br",
        "*.zip",
    ],
}


def get_setting(name):
    """Get a MINICOMPRESS_* setting, falling back to DEFAULT_SETTINGS.

    An explicit None value is treated the same as unset.
    """
    value = getattr(settings, f"MINICOMPRESS_{name}", _UNSET)
    if value is _UNSET or value is None:
        return DEFAULT_SETTINGS.get(name)
    return value


def validate_settings():
    """Raise ImproperlyConfigured for settings that must be positive integers."""
    for name in ("MIN_FILE_SIZE", "MAX_FILE_SIZE"):
        value = get_setting(name)
        if value is not None and value <= 0:
            raise ImproperlyConfigured(
                f"MINICOMPRESS_{name} must be a positive integer, got {value!r}."
            )
