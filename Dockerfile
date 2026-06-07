FROM python:3.11-slim

LABEL org.opencontainers.image.title="Exocortex"
LABEL org.opencontainers.image.description="Exocortex — sensor-aware memory and prediction engine"
LABEL org.opencontainers.image.source="https://github.com/SuperInstance/exocortex"

WORKDIR /app

# Install system deps for any native extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Install exocortex (adjust if publishing to PyPI)
# For now: copy project and install
COPY . /app
RUN pip install --no-cache-dir -e .

# Default config via environment
ENV EXOCORTEX_HOST=0.0.0.0
ENV EXOCORTEX_PORT=9000
ENV EXOCORTEX_DB_URL=http://surrealdb:8000

EXPOSE 9000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:9000/api/v1/capabilities || exit 1

CMD ["uvicorn", "exocortex.main:app", "--host", "0.0.0.0", "--port", "9000"]
