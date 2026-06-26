"""Django settings for HR Vidnova."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-change-me")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "http://localhost:5178,http://127.0.0.1:5178").split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.access",
    "apps.employees",
    "apps.skud",
    "apps.leave",
    "apps.knowledge",
    "apps.dashboard",
    "apps.selfservice",
    "apps.integrations",
    "apps.assets",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if os.getenv("DB_ENGINE", "postgres") == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "NAME": os.getenv("DB_NAME", "hr_vidnova"),
            "USER": os.getenv("DB_USER", "hr_vidnova"),
            "PASSWORD": os.getenv("DB_PASSWORD", "hr_vidnova_pass"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        }
    }

if env_bool("FOTOPACIENTS_DB_ENABLED", False):
    fotopacients_db_name = os.getenv("FOTOPACIENTS_DB_NAME", "").strip()
    if fotopacients_db_name:
        DATABASES["fotopacients"] = {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": os.getenv("FOTOPACIENTS_DB_HOST", "localhost"),
            "PORT": os.getenv("FOTOPACIENTS_DB_PORT", "5432"),
            "NAME": fotopacients_db_name,
            "USER": os.getenv("FOTOPACIENTS_DB_USER", ""),
            "PASSWORD": os.getenv("FOTOPACIENTS_DB_PASSWORD", ""),
            "CONN_MAX_AGE": int(os.getenv("FOTOPACIENTS_DB_CONN_MAX_AGE", "60")),
        }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "uk"
TIME_ZONE = os.getenv("TIME_ZONE", "Europe/Kyiv")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5178,http://127.0.0.1:5178").split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False

# Behind a TLS-terminating reverse proxy (nginx / Cloudflare tunnel): trust the
# forwarded scheme so request.is_secure() works and secure cookies / CSRF over
# https are accepted.
if env_bool("USE_X_FORWARDED_PROTO", not DEBUG):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
HR_PUBLIC_READ_API = env_bool("HR_PUBLIC_READ_API", DEBUG)
HR_PUBLIC_WRITE_API = env_bool("HR_PUBLIC_WRITE_API", False)
HR_BOT_API_SECRET = os.getenv("HR_BOT_API_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
HR_TELEGRAM_SENDER_BACKEND = os.getenv("HR_TELEGRAM_SENDER_BACKEND", "telegram_bot_api")
HR_LOGIN_CODE_TTL_SECONDS = int(os.getenv("HR_LOGIN_CODE_TTL_SECONDS", "300"))
HR_LOGIN_CODE_MAX_ATTEMPTS = int(os.getenv("HR_LOGIN_CODE_MAX_ATTEMPTS", "5"))
HR_LOGIN_CODE_REQUEST_LIMIT_PER_MINUTE = int(os.getenv("HR_LOGIN_CODE_REQUEST_LIMIT_PER_MINUTE", "5"))

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 50,
}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_TRACK_STARTED = True
CELERY_TIMEZONE = TIME_ZONE

SKUD_UPROX_BASE_URL = os.getenv("SKUD_UPROX_BASE_URL", "")
SKUD_ZKTECO_DEVICE_IP = os.getenv("SKUD_ZKTECO_DEVICE_IP", "")
SKUD_SYNC_ENABLED = env_bool("SKUD_SYNC_ENABLED", False)

# CMMS (vidnova-cmms) integration — assets + responsible person
CMMS_API_BASE_URL = os.getenv("CMMS_API_BASE_URL", "")
# Browser-facing CMMS URL for asset photos (signed /uploads links)
CMMS_PUBLIC_URL = os.getenv("CMMS_PUBLIC_URL", "https://cmms.vidnova.com")
CMMS_API_USERNAME = os.getenv("CMMS_API_USERNAME", "")
CMMS_API_PASSWORD = os.getenv("CMMS_API_PASSWORD", "")
CMMS_API_TIMEOUT = int(os.getenv("CMMS_API_TIMEOUT", "20"))

PEOPLEFORCE_API_BASE_URL = os.getenv("PEOPLEFORCE_API_BASE_URL", "https://app.peopleforce.io/api/public/v3")
PEOPLEFORCE_API_KEY = os.getenv("PEOPLEFORCE_API_KEY", "")
PEOPLEFORCE_TIMEOUT_SECONDS = int(os.getenv("PEOPLEFORCE_TIMEOUT_SECONDS", "30"))
PEOPLEFORCE_WEB_COOKIE = os.getenv("PEOPLEFORCE_WEB_COOKIE", "")
PEOPLEFORCE_COMPAT_API_KEY = os.getenv("PEOPLEFORCE_COMPAT_API_KEY", "")
PEOPLEFORCE_TIMESHEET_START_DATE = os.getenv("PEOPLEFORCE_TIMESHEET_START_DATE", "2022-01-01")
PEOPLEFORCE_DOCUMENT_DOWNLOAD_TIMEOUT_SECONDS = int(os.getenv("PEOPLEFORCE_DOCUMENT_DOWNLOAD_TIMEOUT_SECONDS", "30"))
