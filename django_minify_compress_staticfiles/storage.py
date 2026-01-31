import gzip
import io
import json
import logging
import os
from pathlib import Path

import brotli
import rcssmin
import rjsmin
from django.contrib.staticfiles.storage import ManifestFilesMixin, StaticFilesStorage
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible

from .conf import DEFAULT_SETTINGS, get_setting
from .utils import FileManager, generate_file_hash, is_safe_path

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
                preserve_comments = get_setting(
                    "PRESERVE_COMMENTS", DEFAULT_SETTINGS["PRESERVE_COMMENTS"]
                )
                if preserve_comments is None:
                    preserve_comments = True
                return rcssmin.cssmin(
                    content,
                    keep_bang_comments=bool(preserve_comments),
                )
            except Exception as e:
                logger.error(f"CSS minification failed for {file_type}: {e}")
                return content
        elif file_type == "js" and rjsmin:
            try:
                preserve_comments = get_setting(
                    "PRESERVE_COMMENTS", DEFAULT_SETTINGS["PRESERVE_COMMENTS"]
                )
                if preserve_comments is None:
                    preserve_comments = True
                return rjsmin.jsmin(
                    content,
                    keep_bang_comments=bool(preserve_comments),
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
        max_files = (
            get_setting("MAX_FILES_PER_RUN", DEFAULT_SETTINGS["MAX_FILES_PER_RUN"])
            or 1000
        )
        processed_count = 0

        for path in paths:
            if processed_count >= max_files:
                logger.warning(f"Reached maximum file processing limit ({max_files})")
                break
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
                    path_bytes = path.encode("utf-8") if isinstance(path, str) else path
                    content_bytes = (
                        minified_content.encode("utf-8")
                        if isinstance(minified_content, str)
                        else minified_content
                    )
                    file_hash = generate_file_hash(path_bytes + content_bytes)
                    # Create minified path: dir/name.min.hash.ext
                    path_obj = Path(path)
                    parent = path_obj.parent
                    stem = path_obj.stem
                    suffix = path_obj.suffix
                    minified_filename = f"{stem}.min.{file_hash}{suffix}"
                    if parent and str(parent) != ".":
                        minified_path = str(parent / minified_filename)
                    else:
                        minified_path = minified_filename

                    # Save minified content
                    self._write_file_content(
                        minified_path, minified_content, is_text=True
                    )
                    minified_files[path] = minified_path
                    processed_count += 1
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
        max_files = (
            get_setting("MAX_FILES_PER_RUN", DEFAULT_SETTINGS["MAX_FILES_PER_RUN"])
            or 1000
        )
        processed_count = 0

        for path in paths:
            if processed_count >= max_files:
                logger.warning(f"Reached maximum file processing limit ({max_files})")
                break
            if not self.should_process_compression(path):
                continue
            try:
                content = self._read_file_content(path)
                if content is None:
                    continue
                # Get relative path for storage operations
                # If path is absolute, convert to a relative path while preserving directory structure
                if os.path.isabs(path):
                    path_obj = Path(path)
                    parts = path_obj.parts
                    # parts[0] is the root/drive (e.g., "/" or "C:\\"); join the remaining parts
                    if len(parts) > 1:
                        relative_path = os.path.join(*parts[1:])
                    else:
                        # Fallback: if for some reason there are no extra parts, use the basename
                        relative_path = os.path.basename(path)
                else:
                    relative_path = path
                # Process Gzip compression
                if get_setting(
                    "GZIP_COMPRESSION", DEFAULT_SETTINGS["GZIP_COMPRESSION"]
                ):
                    gzipped_path = f"{relative_path}.gz"
                    gzipped_content = self.gzip_compress(content)
                    self._write_file_content(
                        gzipped_path, gzipped_content, is_text=False
                    )
                    compressed_files.setdefault(path, []).append(gzipped_path)
                # Process Brotli compression
                if get_setting(
                    "BROTLI_COMPRESSION", DEFAULT_SETTINGS["BROTLI_COMPRESSION"]
                ):
                    brotli_path = f"{relative_path}.br"
                    brotli_content = self.brotli_compress(content)
                    self._write_file_content(brotli_path, brotli_content, is_text=False)
                    compressed_files.setdefault(path, []).append(brotli_path)
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to compress {path}: {e}")
                continue
        return compressed_files

    def _read_file_content(self, path):
        """Read file content using storage methods."""
        if not is_safe_path(path):
            logger.warning(f"Skipping unsafe path: {path}")
            return None
        max_size = (
            get_setting("MAX_FILE_SIZE", DEFAULT_SETTINGS["MAX_FILE_SIZE"]) or 10485760
        )
        # Try storage methods first
        if self.exists(path):
            with self.open(path) as f:
                content = f.read()
                if isinstance(content, bytes) and len(content) > max_size:
                    logger.warning(f"File too large, skipping: {path}")
                    return None
                return content
        # Fallback to local filesystem
        if os.path.exists(path):
            try:
                file_size = os.path.getsize(path)
                if file_size > max_size:
                    logger.warning(f"File too large, skipping: {path}")
                    return None
                with open(path, "rb") as f:
                    return f.read()
            except OSError as e:
                logger.error(f"Failed to read file {path}: {e}")
                return None
        return None

    def _write_file_content(self, path, content, is_text=True):
        """Write file content using storage methods."""
        if not is_safe_path(path):
            logger.warning(f"Skipping unsafe path for writing: {path}")
            return
        self.save(path, ContentFile(content))

    def gzip_compress(self, content):
        """Compress content using gzip."""
        buffer = io.BytesIO()
        level = (
            get_setting(
                "COMPRESSION_LEVEL_GZIP", DEFAULT_SETTINGS["COMPRESSION_LEVEL_GZIP"]
            )
            or 6
        )
        # Clamp level to valid range (0-9)
        level = max(0, min(9, level))
        with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=level) as gz_file:
            if isinstance(content, str):
                content = content.encode("utf-8")
            gz_file.write(content)
        return buffer.getvalue()

    def brotli_compress(self, content):
        """Compress content using brotli."""
        level = (
            get_setting(
                "COMPRESSION_LEVEL_BROTLI", DEFAULT_SETTINGS["COMPRESSION_LEVEL_BROTLI"]
            )
            or 4
        )
        # Clamp level to valid range (0-11)
        level = max(0, min(11, level))
        if isinstance(content, str):
            content = content.encode("utf-8")
        return brotli.compress(content, quality=level)


@deconstructible
class MinicompressStorage(
    MinificationMixin, CompressionMixin, ManifestFilesMixin, StaticFilesStorage
):
    """Main storage class combining all minification and compression functionality."""

    def post_process(self, paths, dry_run=False, **options):
        """Post-process collected static files."""
        # First, let the parent classes do their work (creates manifest with hashed names)
        yield from super().post_process(paths, dry_run=dry_run, **options)
        if dry_run:
            return
        # Get the list of processed paths from the manifest or use original paths
        # Read manifest to get processed (hashed) paths
        processed_paths = []
        try:
            if hasattr(self, "read_manifest"):
                manifest_json = self.read_manifest()
                if manifest_json:
                    manifest = json.loads(manifest_json)
                    processed_paths = list(manifest.get("paths", {}).values())
        except Exception:
            pass
        # If no paths from manifest, use original paths
        if not processed_paths:
            processed_paths = list(paths.keys())
        # Process minification
        minified_files = self.process_minification(processed_paths)
        # Yield minified files back to Django
        for original, minified in minified_files.items():
            yield original, minified, True
        # Update paths to include minified files for compression
        all_paths = processed_paths + list(minified_files.values())
        # Process compression
        self.process_compression(all_paths)
        # Update manifest with minified file paths
        if minified_files:
            self._update_manifest(minified_files)

    def _update_manifest(self, minified_files):
        """Update manifest with minified file paths.

        minified_files is a dict where: - key: the path that was minified
        (hashed path from ManifestFilesMixin) - value: the minified
        version path
        """
        try:
            # Read existing manifest using Django's method
            manifest_json = self.read_manifest()
            if manifest_json:
                manifest = json.loads(manifest_json)
            else:
                manifest = {}

            if "paths" not in manifest:
                manifest["paths"] = {}

            # Update paths to point to minified versions
            # minified_files has: {hashed_path: minified_hashed_path}
            # manifest["paths"] has: {original_path: hashed_path}
            # We need to find which original_path points to our hashed_path,
            # then update it to point to minified_hashed_path
            for hashed_path, minified_path in minified_files.items():
                # Normalize paths
                hashed_relative = hashed_path
                if os.path.isabs(hashed_path):
                    path_obj = Path(hashed_path)
                    parts = path_obj.parts
                    if len(parts) > 1:
                        hashed_relative = os.path.join(*parts[1:])
                    else:
                        hashed_relative = os.path.basename(hashed_path)

                minified_relative = minified_path
                if os.path.isabs(minified_path):
                    path_obj = Path(minified_path)
                    parts = path_obj.parts
                    if len(parts) > 1:
                        minified_relative = os.path.join(*parts[1:])
                    else:
                        minified_relative = os.path.basename(minified_path)

                # Find which original path maps to this hashed path
                for original_path, current_path in manifest["paths"].items():
                    if current_path == hashed_relative:
                        # Update to point to minified version
                        manifest["paths"][original_path] = minified_relative
                        break

            # Save updated manifest - delete old one first to avoid stale data
            if self.exists(self.manifest_name):
                self.delete(self.manifest_name)
            new_manifest_contents = json.dumps(manifest).encode("utf-8")
            self.save(self.manifest_name, ContentFile(new_manifest_contents))
        except Exception as e:
            logger.error(f"Failed to update manifest: {e}")
