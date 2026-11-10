"""Settings for the demo site: a tiny project for running the module while it's built.

Development only. It is not part of the installed package.

Database: SQLite in demo/db.sqlite3 by default. For Postgres, set DATABASE_URL:
    DATABASE_URL=postgres://app:app@localhost:5432/capy_demo uv run python demo/manage.py migrate
"""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent  # the demo/ folder

SECRET_KEY = "demo-only-not-secret"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_tailwind_cli",  # demo only: builds demo/static/css/tailwind.css
    "capy_theme",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "demo_site.urls"
WSGI_APPLICATION = "demo_site.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en"

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Tailwind CSS v4 standalone CLI (downloaded to demo/.django_tailwind_cli/ on first run)
# with the daisyUI 5 plugin files in demo/tailwind/.
TAILWIND_CLI_VERSION = "4.3.4"
TAILWIND_CLI_SRC_CSS = "tailwind/source.css"  # relative to demo/
TAILWIND_CLI_DIST_CSS = "css/tailwind.css"  # relative to demo/static/
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# capy-theme: show the theme showcase (/theme/showcase/) inside the demo's own
# page, with its navbar, instead of the module's standalone page.
CAPY_THEME_BASE_TEMPLATE = "base.html"
