# Multi-stage Dockerfile for cribl-hc
# Optimized for small image size and security

# Stage 1: Builder
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies and build wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels .

# Stage 2: Runtime
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r criblhc && useradd -r -g criblhc criblhc

# Set working directory
WORKDIR /app

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/src ./src

# Install runtime dependencies only
RUN pip install --no-cache-dir --no-index --find-links=/wheels cribl-health-check && \
    rm -rf /wheels

# Create directories for credentials and reports
RUN mkdir -p /home/criblhc/.cribl-hc /app/reports && \
    chown -R criblhc:criblhc /home/criblhc /app/reports

# Switch to non-root user
USER criblhc

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/criblhc

# Volume for persistent credential storage
VOLUME ["/home/criblhc/.cribl-hc", "/app/reports"]

# Default command shows help
ENTRYPOINT ["cribl-hc"]
CMD ["--help"]

# Health check (optional - checks if CLI is working)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=1 \
    CMD cribl-hc version || exit 1

# Labels
LABEL org.opencontainers.image.title="Cribl Health Check" \
      org.opencontainers.image.description="Comprehensive health checking tool for Cribl Stream deployments" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="Cribl Health Check Project" \
      org.opencontainers.image.licenses="MIT"
