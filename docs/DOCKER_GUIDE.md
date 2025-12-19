# Docker Guide for cribl-hc

This guide covers running cribl-hc in Docker containers for isolated, reproducible deployments.

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Build the image
docker-compose build

# Run interactive TUI
docker-compose run --rm cribl-hc tui

# Configure a deployment
docker-compose run --rm cribl-hc config set prod \
  --url https://main-myorg.cribl.cloud \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET

# Run health check
docker-compose run --rm cribl-hc analyze health --deployment prod

# View results
ls -l reports/
```

### Using Docker CLI

```bash
# Build the image
docker build -t cribl-hc:latest .

# Run with volume mounts
docker run -it --rm \
  -v cribl-hc-data:/home/criblhc/.cribl-hc \
  -v $(pwd)/reports:/app/reports \
  cribl-hc:latest --help
```

## Docker Image Details

### Multi-Stage Build

The Dockerfile uses a multi-stage build for optimal image size:

**Stage 1: Builder**
- Installs build dependencies (gcc, g++)
- Builds Python wheels for all dependencies
- ~500 MB intermediate image

**Stage 2: Runtime**
- Python 3.11-slim base (~150 MB)
- Installs only runtime dependencies from wheels
- Final image: ~250 MB
- Runs as non-root user `criblhc`

### Image Specifications

- **Base Image**: `python:3.11-slim`
- **Python Version**: 3.11
- **User**: `criblhc` (non-root, UID varies)
- **Working Directory**: `/app`
- **Entrypoint**: `cribl-hc` CLI
- **Default Command**: `--help`

### Security Features

- ✅ Non-root user execution
- ✅ Minimal base image (slim variant)
- ✅ Multi-stage build (no build tools in final image)
- ✅ Health check included
- ✅ No secrets in image layers
- ✅ Read-only filesystem compatible

## Volume Mounts

### Credentials Storage

**Path**: `/home/criblhc/.cribl-hc`

Store encrypted credentials persistently:

```bash
# Using named volume (recommended)
docker run -it --rm \
  -v cribl-hc-credentials:/home/criblhc/.cribl-hc \
  cribl-hc:latest config set prod --url https://cribl.example.com --token TOKEN

# Using bind mount
docker run -it --rm \
  -v ~/.cribl-hc:/home/criblhc/.cribl-hc \
  cribl-hc:latest config list
```

### Reports Output

**Path**: `/app/reports`

Save analysis reports to host:

```bash
docker run -it --rm \
  -v cribl-hc-credentials:/home/criblhc/.cribl-hc \
  -v $(pwd)/reports:/app/reports \
  cribl-hc:latest analyze health --deployment prod --export json
```

Reports will be saved to `./reports/` on your host machine.

## Common Usage Patterns

### Interactive TUI Mode

Run the full TUI interface:

```bash
# Docker Compose
docker-compose run --rm cribl-hc tui

# Docker CLI
docker run -it --rm \
  -v cribl-hc-credentials:/home/criblhc/.cribl-hc \
  -v $(pwd)/reports:/app/reports \
  cribl-hc:latest tui
```

**Note**: Requires TTY (`-t`) and stdin (`-i`) for interactive navigation.

### Credential Management

```bash
# Set credentials with bearer token
docker-compose run --rm cribl-hc config set prod \
  --url https://cribl.example.com \
  --token YOUR_BEARER_TOKEN

# Set credentials with OAuth (recommended for Cribl.Cloud)
docker-compose run --rm cribl-hc config set prod \
  --url https://main-myorg.cribl.cloud \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET

# List configured deployments
docker-compose run --rm cribl-hc config list

# View specific deployment
docker-compose run --rm cribl-hc config get prod

# Test connection
docker-compose run --rm cribl-hc test-connection prod
```

### Health Check Analysis

```bash
# Run full health check
docker-compose run --rm cribl-hc analyze health --deployment prod

# Run specific analyzers
docker-compose run --rm cribl-hc analyze health \
  --deployment prod \
  --analyzers config,worker

# Export results to JSON
docker-compose run --rm cribl-hc analyze health \
  --deployment prod \
  --export json \
  --output-file prod_health_check

# Results saved to ./reports/prod_health_check.json
```

### List Available Analyzers

```bash
docker-compose run --rm cribl-hc list analyzers
```

## Networking Considerations

### Accessing Local Cribl Instances

If your Cribl Stream is running on the host machine:

**Option 1: Use host network (Linux only)**

```yaml
# docker-compose.yml
services:
  cribl-hc:
    network_mode: host
```

**Option 2: Use host.docker.internal (Docker Desktop)**

```bash
docker-compose run --rm cribl-hc config set local \
  --url http://host.docker.internal:9000 \
  --token YOUR_TOKEN
```

**Option 3: Use host IP address**

```bash
# Get host IP
ip addr show docker0 | grep inet

docker-compose run --rm cribl-hc config set local \
  --url http://172.17.0.1:9000 \
  --token YOUR_TOKEN
```

### Accessing Remote Cribl Instances

For Cribl.Cloud or remote deployments, no special configuration needed:

```bash
docker-compose run --rm cribl-hc config set cloud \
  --url https://main-myorg.cribl.cloud \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET
```

## Environment Variables

Configure behavior via environment variables:

```yaml
# docker-compose.yml
services:
  cribl-hc:
    environment:
      # Logging
      - LOG_LEVEL=debug  # debug, info, warning, error
      - STRUCTLOG_FORMAT=json  # json or console

      # Output
      - NO_COLOR=1  # Disable colored output
      - FORCE_COLOR=1  # Force colored output

      # API
      - CRIBL_HC_TIMEOUT=60  # API timeout in seconds
      - CRIBL_HC_MAX_RETRIES=5  # Max API retry attempts
```

Or pass via CLI:

```bash
docker run -it --rm \
  -e LOG_LEVEL=debug \
  -e NO_COLOR=1 \
  cribl-hc:latest analyze health --deployment prod
```

## Building Custom Images

### Build Arguments

```bash
# Specify Python version
docker build --build-arg PYTHON_VERSION=3.12 -t cribl-hc:py312 .

# Build with specific platform
docker build --platform linux/amd64 -t cribl-hc:amd64 .
docker build --platform linux/arm64 -t cribl-hc:arm64 .
```

### Multi-Platform Builds

```bash
# Setup buildx (one-time)
docker buildx create --name multiplatform --use

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t cribl-hc:latest \
  --push \
  .
```

### Tagging Strategy

```bash
# Version tag
docker build -t cribl-hc:1.0.0 .

# Latest tag
docker build -t cribl-hc:latest .

# Development tag
docker build -t cribl-hc:dev .
```

## CI/CD Integration

### GitLab CI Example

```yaml
# .gitlab-ci.yml
build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t cribl-hc:$CI_COMMIT_SHA .
    - docker tag cribl-hc:$CI_COMMIT_SHA cribl-hc:latest
    - docker push cribl-hc:latest

health-check:
  stage: test
  image: cribl-hc:latest
  script:
    - cribl-hc version
    - cribl-hc list analyzers
```

### GitHub Actions Example

```yaml
# .github/workflows/docker.yml
name: Docker Build

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: docker build -t cribl-hc:latest .

      - name: Test image
        run: |
          docker run --rm cribl-hc:latest version
          docker run --rm cribl-hc:latest list analyzers
```

## Automated Health Checks

### Scheduled Analysis with Cron

```yaml
# docker-compose.cron.yml
version: '3.8'

services:
  cribl-hc-cron:
    image: cribl-hc:latest
    volumes:
      - cribl-hc-credentials:/home/criblhc/.cribl-hc
      - ./reports:/app/reports
    entrypoint: ["/bin/bash", "-c"]
    command:
      - |
        while true; do
          cribl-hc analyze health --deployment prod --export json
          sleep 3600  # Run every hour
        done
```

### Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cribl-health-check
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cribl-hc
            image: cribl-hc:latest
            args:
              - analyze
              - health
              - --deployment
              - prod
              - --export
              - json
            volumeMounts:
            - name: credentials
              mountPath: /home/criblhc/.cribl-hc
            - name: reports
              mountPath: /app/reports
          volumes:
          - name: credentials
            secret:
              secretName: cribl-hc-credentials
          - name: reports
            persistentVolumeClaim:
              claimName: cribl-hc-reports
          restartPolicy: OnFailure
```

## Troubleshooting

### Permission Issues

If you see permission errors:

```bash
# Check container user
docker run --rm cribl-hc:latest id

# Run as specific UID (if needed)
docker run --rm --user 1000:1000 cribl-hc:latest version
```

### Network Connectivity

Test if container can reach Cribl API:

```bash
# Test DNS resolution
docker run --rm cribl-hc:latest \
  bash -c "nslookup main-myorg.cribl.cloud"

# Test HTTPS connectivity
docker run --rm cribl-hc:latest \
  bash -c "curl -v https://main-myorg.cribl.cloud/api/v1/version"
```

### Credential Storage Issues

Verify credentials are persisted:

```bash
# List volume contents
docker run --rm \
  -v cribl-hc-credentials:/data \
  busybox ls -la /data

# Check credentials file
docker run --rm \
  -v cribl-hc-credentials:/home/criblhc/.cribl-hc \
  cribl-hc:latest config list
```

### TUI Not Working

Ensure TTY and stdin are enabled:

```bash
# Correct (with -it flags)
docker run -it --rm cribl-hc:latest tui

# Incorrect (missing -it)
docker run --rm cribl-hc:latest tui  # Won't work
```

## Best Practices

### 1. Use Named Volumes for Credentials

```bash
# Good: Named volume
docker run -v cribl-hc-credentials:/home/criblhc/.cribl-hc cribl-hc:latest

# Bad: Anonymous volume (lost on container removal)
docker run -v /home/criblhc/.cribl-hc cribl-hc:latest
```

### 2. Always Use --rm for One-Off Commands

```bash
# Good: Auto-cleanup
docker-compose run --rm cribl-hc config list

# Bad: Leaves stopped containers
docker-compose run cribl-hc config list
```

### 3. Store Reports on Host

```bash
# Mount reports directory
docker run -v $(pwd)/reports:/app/reports cribl-hc:latest analyze health ...

# Reports accessible on host
ls -l reports/
```

### 4. Use docker-compose for Consistency

```bash
# Easier and more reproducible
docker-compose run --rm cribl-hc analyze health --deployment prod

# vs complex docker run command
docker run -it --rm \
  -v cribl-hc-credentials:/home/criblhc/.cribl-hc \
  -v $(pwd)/reports:/app/reports \
  cribl-hc:latest analyze health --deployment prod
```

### 5. Version Your Images

```bash
# Tag with version numbers
docker build -t cribl-hc:1.0.0 .
docker tag cribl-hc:1.0.0 cribl-hc:latest

# Use specific versions in production
docker run cribl-hc:1.0.0 analyze health --deployment prod
```

## Docker Image Size Optimization

Current image sizes:
- **Builder stage**: ~500 MB
- **Final runtime image**: ~250 MB

To reduce further:

```dockerfile
# Use alpine (smaller but may have compatibility issues)
FROM python:3.11-alpine

# Remove unnecessary files
RUN find /usr/local -type d -name '__pycache__' -exec rm -rf {} + && \
    find /usr/local -type f -name '*.pyc' -delete
```

## Security Scanning

Scan the image for vulnerabilities:

```bash
# Using Trivy
trivy image cribl-hc:latest

# Using Docker Scout
docker scout cves cribl-hc:latest

# Using Snyk
snyk container test cribl-hc:latest
```

## Summary

Docker deployment provides:
- ✅ **Isolated environment** (no Python/dependency conflicts)
- ✅ **Reproducible builds** (same image everywhere)
- ✅ **Easy CI/CD integration** (automated health checks)
- ✅ **Portable** (run on any Docker-enabled system)
- ✅ **Secure** (non-root user, minimal attack surface)

For most users, **docker-compose is the recommended approach** for its simplicity and consistency.

## Next Steps

1. Build the image: `docker-compose build`
2. Configure credentials: `docker-compose run --rm cribl-hc config set ...`
3. Run health check: `docker-compose run --rm cribl-hc analyze health ...`
4. View results: `ls -l reports/`

For production deployments, consider Kubernetes CronJobs or scheduled container runs for automated monitoring.
