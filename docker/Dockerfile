# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# Copy project configuration and source code
COPY pyproject.toml ./
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Install dependencies
# TODO: Consider using uv/pdm/poetry for better dependency management
# For now, install dependencies from pyproject.toml using pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e .

# Expose port
EXPOSE 8000

# Health check (simple HTTP check - will fail if API is down, but Modbus connection issues won't fail it)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

# Run the application
# TODO: Update to use gunicorn with uvicorn workers for production
# CMD ["gunicorn", "-c", "docker/gunicorn_conf.py", "app:app"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
