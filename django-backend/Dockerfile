# ─────────────────────────────────────────────
#  Stage 1: dependency builder
# ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Keeps Python from generating .pyc files and forces stdout/stderr to be unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install only the C-level build deps needed to compile psycopg2 (if ever switched
# from psycopg2-binary) and other potential native extensions.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install into an isolated prefix so the final stage can copy cleanly
RUN pip install --upgrade pip \
    && pip install --prefix=/install -r requirements.txt


# ─────────────────────────────────────────────
#  Stage 2: final runtime image
# ─────────────────────────────────────────────
FROM python:3.12-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Tell Django where to find settings
    DJANGO_SETTINGS_MODULE=raktakosh.settings \
    # Gunicorn tuning (can be overridden at runtime)
    GUNICORN_WORKERS=3 \
    GUNICORN_THREADS=2 \
    PORT=8080

WORKDIR /app

# Runtime system libs only (libpq for psycopg2 at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from the builder stage
COPY --from=builder /install /usr/local

# Create a non-root user for security
RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --no-create-home appuser

# Copy project source (respects .dockerignore)
COPY --chown=appuser:appgroup . .

# Collect static files at build time so no DB is needed at startup
# SECRET_KEY is a dummy value used only for this build step
RUN SECRET_KEY=build-time-dummy \
    DATABASE_URL=sqlite:///dummy.db \
    python manage.py collectstatic --noinput --clear \
    && rm -f dummy.db

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE ${PORT}

# Health-check: hits Django's admin URL (always available) via the loopback interface
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/admin/')" || exit 1

# Start Gunicorn; worker count and threads can be tuned via env vars
CMD gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers "${GUNICORN_WORKERS}" \
    --threads "${GUNICORN_THREADS}" \
    --worker-class gthread \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    raktakosh.wsgi:application
