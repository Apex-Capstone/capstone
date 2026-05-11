# APEX FastAPI backend — production-oriented image (Poetry, Python 3.11).
# Render and local Poetry workflows are unchanged; this file is for Docker only.

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Match local docs: imports resolve from backend/src as top-level packages (config, controllers, …).
    PYTHONPATH=src \
    POETRY_VERSION=1.8.5 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/opt/poetry/bin:$PATH"

WORKDIR /app

# curl: Poetry installer / optional debugging.
# libpq5: runtime for some PostgreSQL client scenarios (psycopg2-binary wheels are usually self-contained).
# gcc + libpq-dev: fallback if a wheel is missing and pip must compile (keeps image reasonably small vs full build-essential).
#
# ffmpeg is NOT installed to keep the image smaller. Optional acoustic tone analysis (AudioToneAdapter) uses ffmpeg
# to decode non-WAV uploads; without ffmpeg, tone metadata is skipped for those formats (WAV still works).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        libpq5 \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 - \
    && poetry --version

# Layer dependency install: copy only manifests first.
# Add and COPY poetry.lock when available for reproducible installs (`poetry lock` in backend/).
COPY pyproject.toml ./

# Install main dependencies only (no dev group).
RUN poetry install --no-root --only main

# Application source and Alembic config.
COPY alembic.ini ./
COPY src ./src
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
