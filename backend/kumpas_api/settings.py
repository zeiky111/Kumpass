import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "signtext",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "kumpas_api.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "kumpas_api.wsgi.application"

USE_POSTGRES = os.getenv("USE_POSTGRES", "False").lower() == "true"

if USE_POSTGRES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "kumpas_db"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
            "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files (user uploads)
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Allow frontend pages during development, including file:// origin.
CORS_ALLOW_ALL_ORIGINS = True
# Allow local file:// pages to make cross-origin requests during development.
# django-cors-headers checks the literal "null" origin for file:// contexts.
CORS_ALLOWED_ORIGINS = [
    "null",
    "https://kumpass-frontend.onrender.com",
]
# Allow credentials (cookies) in CORS requests
CORS_ALLOW_CREDENTIALS = True

# Trust local frontend dev servers for CSRF origin checks during development.
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:5501",
    "http://localhost:5501",
    "http://127.0.0.1:5502",
    "http://localhost:5502",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "https://kumpass-frontend.onrender.com",
]

# Session configuration - loaded from environment variables
SESSION_ENGINE = os.getenv("SESSION_ENGINE", "django.contrib.sessions.backends.db")
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "604800"))  # 7 days in seconds
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = os.getenv("SESSION_COOKIE_HTTPONLY", "True").lower() == "true"  # Prevent JavaScript access to session cookies
SESSION_COOKIE_SAMESITE = "None"  # Required for cross-site cookie sharing between Render frontend and backend
SESSION_EXPIRE_AT_BROWSER_CLOSE = os.getenv("SESSION_EXPIRE_AT_BROWSER_CLOSE", "True").lower() == "true"  # Clear session when browser closes
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "sessionid")  # Name of the session cookie
SESSION_SAVE_EVERY_REQUEST = os.getenv("SESSION_SAVE_EVERY_REQUEST", "False").lower() == "true"  # Save session on every request

# Must match the session cookie settings above -- without these, browsers
# silently drop the csrftoken cookie on cross-site requests between the
# Render frontend and backend domains, causing "CSRF cookie not set" on login.
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "None"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

# Email configuration - uses environment variables (or console backend by default)
# Render blocks outbound SMTP ports (25/465/587) on its network, so
# django's SMTP backend fails with "Network is unreachable" there
# regardless of credentials. Whenever RESEND_API_KEY is set, force the
# Resend HTTP API backend (plain HTTPS, which Render allows) even if an
# old EMAIL_BACKEND=...smtp.EmailBackend is still sitting in the
# environment from a previous config -- that stale SMTP setting is exactly
# what silently overrode this before. Falls back to SMTP if EMAIL_BACKEND
# is set and no Resend key is present, or console output for local dev.
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
if RESEND_API_KEY:
    EMAIL_BACKEND = "signtext.email_backend.ResendEmailBackend"
else:
    EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Kumpas <no-reply@kumpas.local>")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"
# Without this, smtplib has no socket timeout and can hang indefinitely if
# the SMTP host is unreachable/blocked, taking the whole request (and the
# gunicorn worker) down with it until Render's gateway kills it at 30s.
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))

# Note: For Gmail you'll typically need to create an App Password and set
# EMAIL_HOST_USER and EMAIL_HOST_PASSWORD. Alternatively keep the default
# console backend for local development which prints emails to the server console.
