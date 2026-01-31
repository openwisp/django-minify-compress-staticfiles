import os

from setuptools import find_packages, setup

HERE = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(HERE, "README.rst"), encoding="utf-8") as f:
    LONG_DESCRIPTION = f.read()

setup(
    name="django-minify-compress-staticfiles",
    version="1.0.0",
    description="Django package for minifying and compressing static files",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/x-rst",
    author="OpenWISP",
    author_email="support@openwisp.io",
    url="https://github.com/openwisp/django-minify-compress-staticfiles",
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    install_requires=[
        "rjsmin>=1.2.0",
        "rcssmin>=1.1.0",
        "brotli>=1.0.0",
    ],
    extras_require={
        "test": [
            "openwisp-utils[qa]~=1.2.2",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 4.2",
        "Framework :: Django :: 5.0",
        "Framework :: Django :: 5.1",
        "Framework :: Django :: 5.2",
        "Framework :: Django :: 6.0",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Site Management",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="django staticfiles minification compression optimization",
    python_requires=">=3.10",
    zip_safe=False,
)
