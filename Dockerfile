# Multi-stage Dockerfile for Cribl Health Check
# Supports both CLI and Web GUI modes

# Stage 1: Builder - Build Python dependencies
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies and build wheel
RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -e .

# Stage 2: Runtime - Minimal production image
FROM python:3.11-slim

LABEL maintainer="cribl-hc"
LABEL description="Cribl Health Check CLI and Web API"
LABEL version="1.0.0"

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash criblhc

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dist from builder
COPY --from=builder /build/dist /tmp/dist

# Install cribl-hc
RUN pip install --no-cache-dir /tmp/dist/*.whl && \
    rm -rf /tmp/dist

# Create directories for credentials and reports
RUN mkdir -p /home/criblhc/.cribl-hc /app/reports && \
    chown -R criblhc:criblhc /home/criblhc /app

# Switch to non-root user
USER criblhc

# Expose port for web API
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/criblhc

# Volume for persistent credential storage
VOLUME ["/home/criblhc/.cribl-hc", "/app/reports"]

# Health check for web API mode
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command: Run web API server
# Can be overridden to run CLI commands
CMD ["python", "-m", "uvicorn", "cribl_hc.api.app:app", "--host", "0.0.0.0", "--port", "8080"]

# Usage examples:
#
# Web API mode (default):
#   docker run -p 8080:8080 -v cribl-hc-data:/home/criblhc/.cribl-hc cribl-hc
#
# CLI mode:
#   docker run -v cribl-hc-data:/home/criblhc/.cribl-hc cribl-hc cribl-hc --help
#   docker run -v cribl-hc-data:/home/criblhc/.cribl-hc cribl-hc cribl-hc analyze prod
#
# Interactive shell:
#   docker run -it -v cribl-hc-data:/home/criblhc/.cribl-hc cribl-hc bash
