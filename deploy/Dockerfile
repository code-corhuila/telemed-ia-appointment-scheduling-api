# syntax=docker/dockerfile:1.7

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml ./
COPY src ./src
COPY apps ./apps

RUN useradd -r -u 1001 app && chown -R app /app
USER app

ENV PYTHONPATH=/app/src:/app
EXPOSE 8080

CMD ["python", "-m", "apps.api"]
