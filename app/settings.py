import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


# Leitura das variáveis de ambiente.
def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() == "true"


DEBUG = env_bool("DJANGO_DEBUG", True)
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-development-only-change-me"
)
ALLOWED_HOSTS = [
    host for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if host
]

# Aplicações e processamento das requisições.
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "gerenciador.axes_config.AxesPortugueseConfig",
    "gerenciador",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

# Autenticação protegida contra tentativas repetidas.
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "app.urls"
WSGI_APPLICATION = "app.wsgi.application"

# Templates.
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
                "gerenciador.context_processors.administration_access",
            ]
        },
    }
]

# PostgreSQL por URL, com SQLite apenas para desenvolvimento local.
DATABASE_URL = os.environ.get("DATABASE_URL")
DATABASES = {
    "default": (
        dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=int(os.environ.get("DATABASE_CONN_MAX_AGE", "60")),
            conn_health_checks=True,
        )
        if DATABASE_URL
        else {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    )
}

# Banco SQLite usado somente durante a migração de dados.
if os.environ.get("LEGACY_SQLITE_PATH"):
    DATABASES["legacy"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ["LEGACY_SQLITE_PATH"],
    }

# Validação completa do certificado quando a CA da Aiven for fornecida.
if DATABASE_URL and os.environ.get("DATABASE_CA_CERT"):
    DATABASES["default"].setdefault("OPTIONS", {}).update(
        {
            "sslmode": "verify-full",
            "sslrootcert": os.environ["DATABASE_CA_CERT"],
        }
    )

# Regras das contas e senhas de acesso.
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "vault:list"
LOGOUT_REDIRECT_URL = "login"

# Bloqueio temporário após falhas de login.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_USE_ATTEMPT_EXPIRATION = True
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_ENABLE_RETRY_AFTER_HEADER = True
AXES_LOCKOUT_TEMPLATE = "registration/locked_out.html"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# A primeira chave cifra; as demais permitem ler dados antigos.
VAULT_ENCRYPTION_KEYS = os.environ.get("VAULT_ENCRYPTION_KEYS", "")

# Exigências adicionais do ambiente de produção.
if not DEBUG:
    if not os.environ.get("DJANGO_SECRET_KEY"):
        raise RuntimeError("DJANGO_SECRET_KEY é obrigatória em produção.")
    if not VAULT_ENCRYPTION_KEYS:
        raise RuntimeError("VAULT_ENCRYPTION_KEYS é obrigatória em produção.")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    if env_bool("DJANGO_TRUST_PROXY_SSL_HEADER"):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Saída local ou envio SMTP em produção.
MAILERS = {
    "default": {
        "BACKEND": (
            "django.core.mail.backends.console.EmailBackend"
            if DEBUG
            else "django.core.mail.backends.smtp.EmailBackend"
        ),
        "OPTIONS": {}
        if DEBUG
        else {
            "host": os.environ.get("EMAIL_HOST", "localhost"),
            "port": int(os.environ.get("EMAIL_PORT", "587")),
            "username": os.environ.get("EMAIL_HOST_USER"),
            "password": os.environ.get("EMAIL_HOST_PASSWORD"),
            "use_tls": env_bool("EMAIL_USE_TLS", True),
        },
    },
}
