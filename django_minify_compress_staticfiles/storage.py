import gzip
import io
import logging
import os
from pathlib import Path

import rcssmin
import rjsmin
from django.contrib.staticfiles.storage import ManifestFilesMixin
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

from .conf import DEFAULT_SETTINGS, get_setting
from .utils import FileManager, create_hashed_filename, generate_file_hash

try:
    import brotli
except ImportError:
    brotli = None

logger = logging.getLogger(__name__)


class FileProcessorMixin:
    """Mixin providing file processing capabilities."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_manager = FileManager(self)

    def should_process_minification(self, path):
        """Check if file should be minified."""
        if not get_setting("MINIFY_FILES", DEFAULT_SETTINGS["MINIFY_FILES"]):
            return False
        if not self.file_manager.should_process(path):
            return False
        return self._get_file_type(path) in ["css", "js"]

    def should_process_compression(self, path):
        """Check if file should be compressed."""
        if not self.file_manager.should_process(path):
            return False
        return self.file_manager.is_compression_candidate(path)

    def _get_file_type(self, path):
        """Get file type from path."""
        return Path(path).suffix.lower().lstrip(".")

    def minify_file_content(self, content, file_type):
        """Minify file content based on type."""
        if file_type == "css" and rcssmin:
            try:
                return rcssmin.cssmin(
                    content,
                    keep_bang_comments=get_setting(
                        "PRESERVE_COMMENTS", DEFAULT_SETTINGS["PRESERVE_COMMENTS"]
                    ),
                )
            except Exception as e:
                logger.error(f"CSS minification failed for {file_type}: {e}")
                return content
        elif file_type == "js" and rjsmin:
            try:
                return rjsmin.jsmin(
                    content,
                    keep_bang_comments=get_setting(
                        "PRESERVE_COMMENTS", DEFAULT_SETTINGS["PRESERVE_COMMENTS"]
                    ),
                )
            except Exception as e:
                logger.error(f"JS minification failed: {e}")
                return content
        return content


class MinificationMixin(FileProcessorMixin):
    """Mixin for handling CSS/JS minification."""

    def process_minification(self, paths):
        """Process minification for given paths."""
        if not get_setting("MINIFY_FILES", DEFAULT_SETTINGS["MINIFY_FILES"]):
            return {}
        minified_files = {}

        for path in paths:
            if not self.should_process_minification(path):
                continue
            try:
                content = self._read_file_content(path)
                if content is None:
                    continue
                # Only process text files
                if isinstance(content, bytes):
                    try:
                        content = content.decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                file_type = self._get_file_type(path)
                minified_content = self.minify_file_content(content, file_type)

                # Only save if minification reduced size
                if len(minified_content) < len(content):
                    # Generate hash and new filename
                    file_hash = generate_file_hash(
                        path.encode("utf-8") + minified_content.encode("utf-8")
                    )
                    minified_path = create_hashed_filename(path, file_hash).replace(
                        f".{file_type}", f".min.{file_hash}.{file_type}"
                    )

                    # Save minified content
                    self._write_file_content(
                        minified_path, minified_content, is_text=True
                    )
                    minified_files[path] = minified_path
            except Exception as e:
                logger.error(f"Failed to minify {path}: {e}")
                continue
        return minified_files


class CompressionMixin(FileProcessorMixin):
    """Mixin for handling Gzip/Brotli compression."""

    def process_compression(self, paths):
        """Process compression for given paths."""
        if not (
            get_setting("GZIP_COMPRESSION", DEFAULT_SETTINGS["GZIP_COMPRESSION"])
            or get_setting("BROTLI_COMPRESSION", DEFAULT_SETTINGS["BROTLI_COMPRESSION"])
        ):
            return {}
        compressed_files = {}

        for path in paths:
            if not self.should_process_compression(path):
                continue
            try:
                content = self._read_file_content(path)
                if content is None:
                    continue
                # Process Gzip compression
                if get_setting(
                    "GZIP_COMPRESSION", DEFAULT_SETTINGS["GZIP_COMPRESSION"]
                ):
                    gzipped_path = f"{path}.gz"
                    gzipped_content = self.gzip_compress(content)
                    self._write_file_content(
                        gzipped_path, gzipped_content, is_text=False
                    )
                    compressed_files.setdefault(path, []).append(gzipped_path)
                # Process Brotli compression
                if (
                    get_setting(
                        "BROTLI_COMPRESSION", DEFAULT_SETTINGS["BROTLI_COMPRESSION"]
                    )
                    and brotli
                ):
                    brotli_path = f"{path}.br"
                    brotli_content = self.brotli_compress(content)
                    self._write_file_content(brotli_path, brotli_content, is_text=False)
                    compressed_files.setdefault(path, []).append(brotli_path)
            except Exception as e:
                logger.error(f"Failed to compress {path}: {e}")
                continue
        return compressed_files

    def _read_file_content(self, path):
        """Read file content using available storage methods."""
        # Try storage methods first
        if hasattr(self, "exists") and hasattr(self, "open"):
            if self.exists(path):
                with self.open(path) as f:
                    return f.read()
        # Fallback to local filesystem
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
        return None

    def _write_file_content(self, path, content, is_text=True):
        """Write file content using available storage methods."""
        if hasattr(self, "save") and ContentFile is not None:
            mode = "w" if is_text else "wb"
            self.save(path, ContentFile(content))
        else:
            # Fallback to local filesystem
            if hasattr(self, "path"):
                full_path = self.path(path)
            else:
                full_path = path
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            mode = "w" if is_text else "wb"
            encoding = "utf-8" if is_text else None
            with open(full_path, mode, encoding=encoding) as f:
                f.write(content)

    def gzip_compress(self, content):
        """Compress content using gzip."""
        buffer = io.BytesIO()
        level = (
            get_setting(
                "COMPRESSION_LEVEL_GZIP", DEFAULT_SETTINGS["COMPRESSION_LEVEL_GZIP"]
            )
            or 9
        )
        with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=level) as gz_file:
            if isinstance(content, str):
                content = content.encode("utf-8")
            gz_file.write(content)
        return buffer.getvalue()

    def brotli_compress(self, content):
        """Compress content using brotli."""
        if not brotli:
            return None
        level = (
            get_setting(
                "COMPRESSION_LEVEL_BROTLI", DEFAULT_SETTINGS["COMPRESSION_LEVEL_BROTLI"]
            )
            or 11
        )
        if isinstance(content, str):
            content = content.encode("utf-8")
        return brotli.compress(content, quality=level)


@deconstructible
class MinicompressStorage(
    ManifestFilesMixin, MinificationMixin, CompressionMixin, Storage
):
    """Main storage class combining all minification and compression functionality."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def post_process(self, paths, dry_run=False, **options):
        """Post-process collected static files."""
        if dry_run:
            return
        # Process minification first
        minified_files = self.process_minification(paths.keys())
        # Update paths to include minified files for compression
        all_paths = list(paths.keys()) + list(minified_files.values())
        # Process compression
        self.process_compression(all_paths)
        # Update manifest with minified file paths
        if hasattr(self, "manifest") and minified_files:
            self._update_manifest(minified_files)
        # Yield processed files for Django's collectstatic
        for path in paths:
            yield path, None, None

    def _update_manifest(self, minified_files):
        """Update manifest with minified file paths."""
        try:
            # Read existing manifest
            if hasattr(self, "exists") and self.exists(self.manifest_name):
                with self.open(self.manifest_name) as f:
                    import json

                    manifest = json.load(f)
            else:
                manifest = {}
            # Update paths to point to minified versions
            for original, minified in minified_files.items():
                if original in manifest:
                    manifest[original] = minified
            # Save updated manifest
            if hasattr(self, "save"):
                self.save(
                    self.manifest_name,
                    ContentFile(json.dumps(manifest, indent=2, sort_keys=True)),
                )
        except Exception as e:
            logger.error(f"Failed to update manifest: {e}")
