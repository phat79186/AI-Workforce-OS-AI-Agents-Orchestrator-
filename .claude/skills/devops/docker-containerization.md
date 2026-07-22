# Skill: Docker Containerization

Build secure, efficient Docker images and compose configurations.

## Capabilities
- Multi-stage builds
- Layer optimization
- Security hardening
- Docker Compose patterns
- Health checks
- Resource limits

## Patterns

### Multi-Stage Build
```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Runtime stage
FROM python:3.11-slim as runtime

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies only
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

EXPOSE 8000

CMD ["python", "-m", "orchestrator.ui.app"]
```

### Optimized Layer Caching
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code last (changes frequently)
COPY . .

CMD ["python", "main.py"]
```

### Docker Compose for Development
```yaml
version: '3.8'

services:
  orchestrator:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=DEBUG
      - DATABASE_URL=sqlite:///data/orchestrator.db
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M
    restart: unless-stopped

  mcp-server:
    build:
      context: ./mcp_server
    ports:
      - "8001:8001"
    depends_on:
      orchestrator:
        condition: service_healthy
    environment:
      - ORCHESTRATOR_URL=http://orchestrator:8000

volumes:
  data:
```

### Security Scanning
```dockerfile
# .hadolint.yaml
ignored:
  - DL3008  # Pin versions in apt-get

# Scan with trivy
# trivy image myimage:latest

# Scan with docker scout
# docker scout cves myimage:latest
```

### .dockerignore
```
# Git
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
.pytest_cache
.coverage
htmlcov

# Virtual environments
venv
.venv
env

# IDE
.idea
.vscode
*.swp

# Build artifacts
dist
build
*.egg-info

# Local config
.env
*.local

# Tests (not needed in production)
tests/
```

## Checklist
- [ ] Multi-stage build for smaller images
- [ ] Non-root user in production
- [ ] Health check defined
- [ ] Resource limits set
- [ ] No secrets in image
- [ ] .dockerignore excludes unnecessary files
- [ ] Pinned base image versions
- [ ] Security scanning in CI
- [ ] Layer caching optimized
