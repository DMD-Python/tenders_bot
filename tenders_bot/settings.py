import os
from pathlib import Path
from dotenv import load_dotenv
from tenders_bot.settings_utils import env_or_err, try_load_env_file

# Определяет путь к корневой папке проекта Django
BASE_DIR = Path(__file__).resolve().parent.parent

# Загрузка переменных окружения
env_files = ["app.env", "db.env", "email.env"]
for file in env_files:
    try_load_env_file(BASE_DIR / "environments" / file)

# Безопасность проекта
# Значение берется из файла environments/app.env
SECRET_KEY = env_or_err("SECRET_KEY")

# В продакшене отключить отладку
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Установленные приложения проекта
INSTALLED_APPS = [
    "django.contrib.admin",
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "tenders_bot.apps.TendersConfig",
    "adminsortable2",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

#URL- и WSGI-конфигурация
ROOT_URLCONF = 'tenders_bot.urls'
WSGI_APPLICATION = 'tenders_bot.wsgi.application'

# Настройки и подключение к базе данных
DATABASES = {
    'default': {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": env_or_err("DATABASE_HOST"),
        "PORT": env_or_err("DATABASE_PORT"),
        "NAME": env_or_err("DATABASE_NAME"),
        "USER": env_or_err("DATABASE_USER"),
        "PASSWORD": env_or_err("DATABASE_PASSWORD"),
        "OPTIONS": {
            "options": f'-c search_path="{env_or_err("DATABASE_SCHEMA")}" -c statement_timeout=30000',
            "connect_timeout": 10,
        },
        "CONN_MAX_AGE": 0,
    }
}

# Шаблоны
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Аутентификация
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Локализация
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# Статические и медиа-файлы
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "files")

# Настройки email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env_or_err("EMAIL_HOST")
EMAIL_PORT = int(env_or_err("EMAIL_PORT", 465))
EMAIL_USE_SSL = env_or_err("EMAIL_USE_SSL", False, True)
EMAIL_USE_TLS = env_or_err("EMAIL_USE_TLS", True, True)
EMAIL_HOST_USER = env_or_err("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env_or_err("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = env_or_err("DEFAULT_FROM_EMAIL")
MAIL_FEEDBACK_TO = env_or_err("MAIL_FEEDBACK_TO").split(",")

# Ограничения на подгружаемые файлы
MAX_FILE_SIZE_MB = 3  # MB
MAX_TOTAL_SIZE_MB = 15  # MB
# Доп настройки
ID_FORMAT = "GKE-{id}"
TELEGRAM_TOKEN = env_or_err("TELEGRAM_TOKEN")
TELEBOT_NUM_THREADS = int(env_or_err("TELEBOT_NUM_THREADS", 10))

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Логирование (поставить на INFO - уровень логирования, отключит DEBUG)
LOG_LEVEL = "DEBUG"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname} {asctime} {module} {process:d} {thread:d}] {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{asctime}::{name}::{levelname}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "django": {
            "handlers": ["console"],
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "tenders_bot": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}