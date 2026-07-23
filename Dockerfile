# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install the application (runtime dependencies only). Copying the full source
# first keeps the build simple and correct for a setuptools src-less layout.
COPY . .
RUN pip install --upgrade pip && pip install .

# Run database migrations, then start the API server.
ENTRYPOINT ["./docker-entrypoint.sh"]
EXPOSE 8000
