"""
Django settings for rick-and-morty-explorer-api project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-rick-and-morty-explorer-portfolio-dev-key",
)

DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,testserver").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "drf_spectacular",
    # Local apps
    "explorer",
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

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASE_NAME = os.getenv("DATABASE_NAME", "db.sqlite3")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / DATABASE_NAME if not os.path.isabs(DATABASE_NAME) else Path(DATABASE_NAME),
    }
}

# External Rick and Morty Public API Settings
RICK_AND_MORTY_API_BASE_URL = os.getenv(
    "RICK_AND_MORTY_API_BASE_URL",
    "https://rickandmortyapi.com/api",
).rstrip("/")

RICK_AND_MORTY_API_TIMEOUT = float(os.getenv("RICK_AND_MORTY_API_TIMEOUT", "5"))

# Cache Configuration with configurable TTL
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "rick-and-morty-explorer-cache",
        "TIMEOUT": CACHE_TTL_SECONDS,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "explorer.exception_handler.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Rick and Morty Explorer API",
    "DESCRIPTION": (
        "API própria desenvolvida com Django e Django REST Framework que consome a API pública "
        "de Rick and Morty (`https://rickandmortyapi.com/api`), oferece filtros, paginação, "
        "cache configurável, persistência resiliente de favoritos em SQLite (personagens e episódios) "
        "e análise estatística com Pandas."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CONTACT": {
        "name": "Rick and Morty Explorer API Portfolio",
    },
    "TAGS": [
        {"name": "Characters", "description": "Consulta e filtragem de personagens na API pública com cache e fallback local."},
        {"name": "Favorites", "description": "Gerenciamento de personagens favoritos persistidos no SQLite."},
        {"name": "Favorite Episodes", "description": "Listagem e gerenciamento de episódios favoritos no SQLite."},
        {"name": "Statistics", "description": "Análise estatística e agregações dos favoritos utilizando Pandas."},
        {"name": "Health", "description": "Verificação de saúde e conectividade da API."},
    ],
}
