"""The smallest Django project that can run this module's tests.

It stands in for "any project that installs the module". If the module only
works inside one particular project, these tests fail.

Database: SQLite in memory by default, no setup needed. To test against
Postgres (for Postgres-only features), set DATABASE_URL:
    DATABASE_URL=postgres://app:app@localhost:5432/module_tests uv run pytest
"""

import os

import dj_database_url

SECRET_KEY = "tests-only-not-secret"
DEBUG = False
ALLOWED_HOSTS = ["testserver"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "capy_theme",
    # Django REST Framework and drf-spectacular, so the API can be tested in DRF
    # mode and in the generated API docs. Projects don't need them.
    "rest_framework",
    "drf_spectacular",
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Stricter than DRF's own default, to prove the theme API stays public.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "tests.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "capy_theme.context_processors.theme",
            ],
        },
    },
]

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite://:memory:")
DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}

USE_TZ = True
STATIC_URL = "static/"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast tests
