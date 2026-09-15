FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PORT=8000 \
    HOME=/app \
    XDG_RUNTIME_DIR=/run/gunicorn \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system cofre \
    && useradd --system --gid cofre --home-dir /app cofre \
    && install -d -o cofre -g cofre -m 0700 /run/gunicorn

WORKDIR /app

COPY --from=builder --chown=cofre:cofre /app /app

USER cofre

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os,socket; socket.create_connection(('127.0.0.1', int(os.getenv('PORT', '8000'))), 2).close()"]

CMD ["gunicorn", "app.wsgi:application", "--config", "gunicorn.conf.py"]
