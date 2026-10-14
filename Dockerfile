FROM python:3.14-slim

WORKDIR /app

# add this by claude so it can run
ENV PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=never 

# Create non-root user early so we can own /app
RUN useradd --create-home appuser && chown appuser:appuser /app

# Install uv (fast Python package manager)
RUN pip install uv

# Copy dependency files first (Docker layer caching)
COPY --chown=appuser:appuser pyproject.toml .
COPY --chown=appuser:appuser uv.lock* .


# switch to non-root user before installing deps (so .venv is owned by appuser)
USER appuser

# Install dependencies (production only), added no-install-project by claude to run this
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY --chown=appuser:appuser app/ app/

# Expose port
EXPOSE 8000

# Health check
# HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
#     CMD curl -f http://localhost:8000/health || exit 1

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1


# Run uvicorn directly from venv (avoids uv re-syncing at runtime)
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]