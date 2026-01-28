####################################
 Django Minify Compress StaticFiles
####################################

|Build Status| |Coverage| |PyPI Version| |License|

A modern Django package for minifying and compressing static files during
``collectstatic``. This package provides a drop-in replacement for
unmaintained static file compression solutions with feature parity and
improved maintainability.

**********
 Features
**********

- **CSS/JS Minification**: Uses ``rjsmin`` and ``rcssmin`` for fast
  minification
- **Dual Compression**: Gzip and Brotli compression support
- **Django Integration**: Seamless integration with Django's static file
  system
- **Selective Processing**: Only processes appropriate file types
- **Hashed Filenames**: Maintains Django's manifest system
- **Configurable**: Fine-grained control over processing options

**************
 Installation
**************

Install from PyPI:

.. code-block:: bash

    pip install django-minify-compress-staticfiles

If you need brotli compression:

.. code-block:: bash

    pip install django-minify-compress-staticfiles[brotli]

***************
 Configuration
***************

Update your static files storage:

.. code-block:: python

    STATICFILES_STORAGE = "django_minify_compress_staticfiles.storage.MinicompressStorage"

**********
 Settings
**********

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

*******
 Usage
*******

Run ``collectstatic`` as usual:

.. code-block:: bash

    python manage.py collectstatic --noinput

The package will automatically: - Minify CSS and JavaScript files - Create
``.gz`` and ``.br`` compressed versions - Update Django's manifest with
minified file paths - Skip already processed files and patterns

**********************
 Supported File Types
**********************

**Minification**: CSS, JavaScript

**Compression**: CSS, JS, TXT, XML, JSON, SVG, MD, RST, HTML, HTM

Files matching ``*.min.*`` or ``*-min.*`` patterns are excluded from
processing.

**************
 Dependencies
**************

**Required**: - Django >= 4.2 - Python >= 3.10

**Optional**: - ``rjsmin`` >= 1.2.0 (for JS minification) - ``rcssmin`` >=
1.1.0 (for CSS minification) - ``brotli`` >= 1.0.0 (for Brotli
compression)

*********
 License
*********

BSD 3-Clause License. See ``LICENSE`` file for details.

**************
 Contributing
**************

Contributions are welcome! Please see the `OpenWISP contributing
guidelines`_ for more information.

.. _openwisp contributing guidelines: https://github.com/openwisp/openwisp-utils/blob/main/CONTRIBUTING.rst

*********
 Support
*********

- Documentation_
- `Issue Tracker`_
- `OpenWISP Community`_

.. _documentation: https://openwisp.io/docs/stable/

.. _issue tracker: https://github.com/openwisp/django-minify-compress-staticfiles/issues

.. _openwisp community: https://openwisp.io/community/

.. |Build Status| image:: https://github.com/openwisp/django-minify-compress-staticfiles/workflows/CI/badge.svg
   :target: https://github.com/openwisp/django-minify-compress-staticfiles/actions
.. |Coverage| image:: https://coveralls.io/repos/github/openwisp/django-minify-compress-staticfiles/badge.svg?branch=main
   :target: https://coveralls.io/github/openwisp/django-minify-compress-staticfiles?branch=main
.. |PyPI Version| image:: https://badge.fury.io/py/django-minify-compress-staticfiles.svg
   :target: https://badge.fury.io/py/django-minify-compress-staticfiles
.. |License| image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
   :target: https://opensource.org/licenses/BSD-3-Clause
