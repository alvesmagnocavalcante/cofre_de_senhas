# ---------- Stage 1: builder ----------
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Necessário apenas se alguma dependência compila extensões nativas (ex.: psycopg2 sem -binary)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Camada de dependências (só invalida quando pyproject.toml/uv.lock mudam)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Código da aplicação + instalação do projeto
COPY . .
RUN uv sync --frozen --no-dev

# Gera os estáticos e o manifest do WhiteNoise.
# Os valores abaixo existem só durante o build e não vão para a imagem final.
RUN DJANGO_DEBUG=false \
    DJANGO_SECRET_KEY=build-only-valor-descartavel-nao-usar-em-producao-0123456789 \
    DJANGO_ALLOWED_HOSTS=localhost \
    VAULT_ENCRYPTION_KEYS="$(/app/.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
    /app/.venv/bin/python manage.py collectstatic --noinput

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PORT=8000 \
    HOME=/app \
    XDG_RUNTIME_DIR=/run/gunicorn \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# libpq5 só é necessário se usar psycopg/psycopg2 com PostgreSQL
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system cofre \
    && useradd --system --gid cofre --home-dir /app cofre \
    && install -d -o cofre -g cofre -m 0700 /run/gunicorn

WORKDIR /app

COPY --from=builder --chown=cofre:cofre /app /app

USER cofre

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os,socket; socket.create_connection(('127.0.0.1', int(os.getenv('PORT', '8000'))), 2).close()"]

CMD ["gunicorn", "app.wsgi:application", "--config", "gunicorn.conf.py"]
