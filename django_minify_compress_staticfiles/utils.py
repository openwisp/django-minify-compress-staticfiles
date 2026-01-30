import hashlib
import logging
import os
import re
from pathlib import Path

from django.utils.functional import cached_property

from .conf import DEFAULT_SETTINGS, get_setting

logger = logging.getLogger(__name__)


def generate_file_hash(content_or_path, length=12):
    """Generate MD5 hash of file content or raw bytes.


    Returns:
        A hex string of the specified length
    """
    try:
        if isinstance(content_or_path, bytes):
            # Direct content hash
            return hashlib.md5(content_or_path).hexdigest()[:length]
        elif isinstance(content_or_path, str):
            # File path - read and hash
            with open(content_or_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()[:length]
        else:
            logger.error(f"Unsupported type for hash generation: {type(content_or_path)}")
            return ""
    except (OSError, IOError) as e:
        logger.error(f"Failed to generate hash for {content_or_path}: {e}")
        return ""


def create_hashed_filename(original_path, hash_value):
    """Create filename with hash inserted before extension."""
    path = Path(original_path)
    parent = path.parent
    stem = path.stem
    suffix = path.suffix

    # If already has hash, replace it
    hash_pattern = r"\.[a-f0-9]{12}$"
    if re.search(hash_pattern, stem):
        stem = re.sub(hash_pattern, "", stem)

    new_filename = f"{stem}.{hash_value}{suffix}"
    # Preserve directory structure
    if parent and str(parent) != '.':
        return str(parent / new_filename)
    return new_filename


def normalize_extension(extension):
    """Normalize file extension for processing."""
    return extension.lower().lstrip(".")


def should_process_file(file_path, supported_extensions, exclude_patterns):
    """Check if file should be processed for minification/compression."""
    path = Path(file_path)
    ext = normalize_extension(path.suffix)

    # Check extension
    if not supported_extensions or ext not in supported_extensions:
        return False

    # Check exclude patterns
    filename = path.name
    for pattern in exclude_patterns or []:
        # Handle simple glob patterns
        if pattern == "*.min.*" and ".min." in filename:
            return False
        elif pattern == "*-min.*" and "-min." in filename:
            return False
        elif pattern.startswith("*") and filename.endswith(pattern[1:]):
            return False
        elif filename.endswith(pattern):
            return False

    return True


def get_file_size(file_path):
    """Get file size in bytes."""
    try:
        return os.path.getsize(file_path)
    except (OSError, IOError) as e:
        logger.error(f"Failed to get file size for {file_path}: {e}")
        return 0


class FileManager:
    """Helper class for managing file operations."""

    def __init__(self, storage):
        self.storage = storage

    @cached_property
    def supported_extensions(self):
        """Get supported file extensions from settings."""
        result = get_setting(
            "SUPPORTED_EXTENSIONS", DEFAULT_SETTINGS["SUPPORTED_EXTENSIONS"]
        )
        return result or {}

    @cached_property
    def exclude_patterns(self):
        """Get exclude patterns from settings."""
        result = get_setting("EXCLUDE_PATTERNS", DEFAULT_SETTINGS["EXCLUDE_PATTERNS"])
        return result or []

    @cached_property
    def min_file_size(self):
        """Get minimum file size for compression."""
        result = get_setting("MIN_FILE_SIZE", DEFAULT_SETTINGS["MIN_FILE_SIZE"])
        return result or 200

    def should_process(self, file_path):
        """Check if file should be processed."""
        extensions = getattr(self, "supported_extensions", None) or {}
        if hasattr(extensions, "keys"):
            extensions = list(extensions.keys())
        elif isinstance(extensions, dict):
            extensions = list(extensions.keys())
        else:
            extensions = extensions or []
        return should_process_file(
            file_path, extensions, getattr(self, "exclude_patterns", None) or []
        )

    def is_compression_candidate(self, file_path):
        """Check if file is candidate for compression (size check)."""
        min_size = getattr(self, "min_file_size", None) or 200
        # Try to get full path from storage first
        if hasattr(self.storage, 'path'):
            try:
                full_path = self.storage.path(file_path)
                return get_file_size(full_path) >= min_size
            except Exception:
                pass
        return get_file_size(file_path) >= min_size
