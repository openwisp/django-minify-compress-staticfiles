from django.conf import settings


def get_setting(name, default=None):
    """Get setting with MINICOMPRESS_ prefix."""
    return getattr(settings, f"MINICOMPRESS_{name}", default)


DEFAULT_SETTINGS = {
    "ENABLED": True,
    "MINIFY_FILES": True,
    "BROTLI_COMPRESSION": True,
    "GZIP_COMPRESSION": True,
    "MIN_FILE_SIZE": 200,
    "COMPRESSION_LEVEL_GZIP": 9,
    "COMPRESSION_LEVEL_BROTLI": 11,
    "PRESERVE_COMMENTS": True,
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
    ],
}
