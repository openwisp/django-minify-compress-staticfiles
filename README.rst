Django Minify Compress StaticFiles
==================================

.. image:: https://github.com/openwisp/django-minify-compress-staticfiles/workflows/CI/badge.svg
    :target: https://github.com/openwisp/django-minify-compress-staticfiles/actions
    :alt: CI build status

.. image:: https://coveralls.io/repos/github/openwisp/django-minify-compress-staticfiles/badge.svg?branch=master
    :target: https://coveralls.io/github/openwisp/django-minify-compress-staticfiles?branch=master
    :alt: Coverage

.. image:: https://badge.fury.io/py/django-minify-compress-staticfiles.svg
    :target: https://badge.fury.io/py/django-minify-compress-staticfiles
    :alt: PyPI Version

.. image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
    :target: https://opensource.org/licenses/BSD-3-Clause
    :alt: License

A modern Django package for minifying and compressing static files during
``collectstatic`` with minimal configuration.

Features
--------

- **CSS/JS Minification**: Uses ``rjsmin`` and ``rcssmin`` for fast
  minification
- **Dual Compression**: Gzip and Brotli compression support
- **Django Integration**: Seamless integration with Django's static file
  system
- **Selective Processing**: Only processes appropriate file types
- **Hashed Filenames**: Maintains Django's manifest system
- **Configurable**: Fine-grained control over processing options

Installation
------------

Install from PyPI:

.. code-block:: bash

    pip install django-minify-compress-staticfiles

Configuration
-------------

For **Django 4.2+**, update your ``STORAGES`` setting:

.. code-block:: python

    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django_minify_compress_staticfiles.storage.MinicompressStorage",
        },
    }

For **Django < 4.2**, use the legacy setting:

.. code-block:: python

    STATICFILES_STORAGE = "django_minify_compress_staticfiles.storage.MinicompressStorage"

Settings
--------

All settings use the ``MINICOMPRESS_`` prefix:

``MINICOMPRESS_ENABLED``
    Enable/disable processing (default: ``True``)

``MINICOMPRESS_MINIFY_FILES``
    Enable CSS/JS minification (default: ``True``)

``MINICOMPRESS_GZIP_COMPRESSION``
    Enable Gzip compression (default: ``True``)

``MINICOMPRESS_BROTLI_COMPRESSION``
    Enable Brotli compression (default: ``True``)

``MINICOMPRESS_MIN_FILE_SIZE``
    Minimum file size for compression in bytes (default: ``200``)

``MINICOMPRESS_MAX_FILE_SIZE``
    Maximum file size for processing in bytes (default: ``10485760``,
    i.e., 10MB) Files larger than this are skipped to prevent memory
    exhaustion. Adjust based on your available memory and security
    requirements.

``MINICOMPRESS_MAX_FILES_PER_RUN``
    Maximum number of files to process per ``collectstatic`` run (default:
    ``1000``) Prevents CPU and memory exhaustion when processing large
    numbers of files. Increase only if you have verified your system can
    handle it.

``MINICOMPRESS_COMPRESSION_LEVEL_GZIP``
    Gzip compression level (default: ``6``, range: 0-9) Level 6 provides a
    good balance between compression ratio and CPU usage. Higher values
    (8-9) consume significantly more CPU with diminishing returns. Lower
    values (0-5) are faster but produce larger compressed files.

``MINICOMPRESS_COMPRESSION_LEVEL_BROTLI``
    Brotli compression quality (default: ``4``, range: 0-11) Level 4
    offers excellent compression with reasonable CPU usage. Higher values
    (8-11) can cause severe CPU spikes during ``collectstatic``. Lower
    values (0-3) are faster but less effective compression.

``MINICOMPRESS_PRESERVE_COMMENTS``
    Preserve bang comments in CSS/JS (default: ``True``)

``MINICOMPRESS_SUPPORTED_EXTENSIONS``
    Dictionary of file extensions to process (default: css, js, txt, xml,
    json, svg, md, rst, html, htm)

``MINICOMPRESS_EXCLUDE_PATTERNS``
    List of glob patterns to exclude from processing (default:
    ``["*.min.*", "*-min.*", "*.gz", "*.br", "*.zip"]``) Pre-compressed
    files (e.g., ``.gz``, ``.br``, ``.zip``) are excluded by default to
    prevent double-compression and security issues.

Usage
-----

Run ``collectstatic`` as usual:

.. code-block:: bash

    python manage.py collectstatic --noinput

The package will automatically:

- Minify CSS and JavaScript files
- Create ``.gz`` and ``.br`` compressed versions
- Update Django's manifest with minified file paths
- Skip already processed files and patterns

Supported File Types
--------------------

**Minification**: CSS, JavaScript

**Compression**: CSS, JS, TXT, XML, JSON, SVG, MD, RST, HTML, HTM

Files matching ``*.min.*`` or ``*-min.*`` patterns are excluded from
processing.

Security Considerations
-----------------------

The package includes several security features to protect against common
attacks:

**Path Traversal Protection**
    All file paths are validated to prevent directory traversal attacks.
    Files outside the static root directory cannot be read or written.

**Memory Exhaustion Prevention**
    ``MAX_FILE_SIZE`` limits the maximum file size that will be processed,
    preventing attackers from causing memory exhaustion with extremely
    large files.

**CPU Exhaustion Prevention**
    Compression levels and file processing limits prevent CPU exhaustion
    attacks. Default compression values (Gzip: 6, Brotli: 4) provide good
    performance without causing excessive CPU usage.

**Compression Bomb Protection**
    Already compressed files (e.g., ``.gz``, ``.br``, ``.zip``) are
    excluded from processing by default to prevent recursive compression
    that could cause CPU exhaustion.

**SHA-256 Hashing**
    File hashes use SHA-256 instead of MD5 for better security, though
    this is primarily for cache invalidation rather than cryptographic
    security.

Recommended Settings for Production
-----------------------------------

For production deployments with high security requirements:

.. code-block:: python

    MINICOMPRESS_MAX_FILE_SIZE = 2097152  # 2MB
    MINICOMPRESS_MAX_FILES_PER_RUN = 500
    MINICOMPRESS_COMPRESSION_LEVEL_GZIP = 6
    MINICOMPRESS_COMPRESSION_LEVEL_BROTLI = 4

For development environments with faster builds:

.. code-block:: python

    MINICOMPRESS_COMPRESSION_LEVEL_GZIP = 1
    MINICOMPRESS_COMPRESSION_LEVEL_BROTLI = 0
    MINICOMPRESS_BROTLI_COMPRESSION = False  # Disable for faster builds

Dependencies
------------

**Required**:

- Django >= 4.2
- Python >= 3.10
- ``brotli`` >= 1.0.0
- ``rjsmin`` >= 1.2.0
- ``rcssmin`` >= 1.1.0

License
-------

BSD 3-Clause License. See ``LICENSE`` file for details.

Contributing
------------

Contributions are welcome! Please see the `OpenWISP contributing
guidelines`_ for more information.

.. _openwisp contributing guidelines: https://openwisp.io/docs/stable/developer/contributing.html

Support
-------

- `Issue Tracker`_
- `OpenWISP Support`_

.. _issue tracker: https://github.com/openwisp/django-minify-compress-staticfiles/issues

.. _openwisp support: https://openwisp.org/support/
