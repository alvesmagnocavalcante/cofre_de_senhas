# syntax=docker/dockerfile:1

# Instala as dependências em uma camada separada.
FROM ghcr.io/astral-sh/uv:0.11.33 AS uv
FROM python:3.12-slim-bookworm AS builder

COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable
RUN .venv/bin/python manage.py collectstatic --noinput

# Executa somente com os arquivos necessários em produção.
FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system cofre && useradd --system --gid cofre --home-dir /app cofre
WORKDIR /app
COPY --from=builder --chown=cofre:cofre /app /app

USER cofre
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os,socket; socket.create_connection(('127.0.0.1', int(os.getenv('PORT', '8000'))), 2).close()"]

CMD ["gunicorn", "app.wsgi:application", "--config", "gunicorn.conf.py"]
