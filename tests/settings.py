SECRET_KEY = "test-secret-key-for-testing-only"
DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django_minify_compress_staticfiles",
]

STATIC_URL = "/static/"
STATIC_ROOT = "test_staticfiles"

USE_TZ = True
