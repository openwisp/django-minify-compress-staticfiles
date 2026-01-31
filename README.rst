Django Minify Compress StaticFiles
==================================

.. image:: https://github.com/openwisp/django-minify-compress-staticfiles/workflows/CI/badge.svg
    :target: https://github.com/openwisp/django-minify-compress-staticfiles/actions
    :alt: CI build status

.. image:: https://coveralls.io/repos/github/openwisp/django-minify-compress-staticfiles/badge.svg?branch=main
    :target: https://coveralls.io/github/openwisp/django-minify-compress-staticfiles?branch=main
    :alt: Coverage

.. image:: https://badge.fury.io/py/django-minify-compress-staticfiles.svg
    :target: https://badge.fury.io/py/django-minify-compress-staticfiles
    :alt: PyPI Version

.. image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
    :target: https://opensource.org/licenses/BSD-3-Clause
    :alt: License

A modern Django package for minifying and compressing static files during
``collectstatic``. This package provides a drop-in replacement for
unmaintained static file compression solutions with feature parity and
improved maintainability.

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

``MINICOMPRESS_COMPRESSION_LEVEL_GZIP``
    Gzip compression level (default: ``9``)

``MINICOMPRESS_COMPRESSION_LEVEL_BROTLI``
    Brotli compression quality (default: ``11``)

``MINICOMPRESS_PRESERVE_COMMENTS``
    Preserve bang comments in CSS/JS (default: ``True``)

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
