# Multi-stage Production Dockerfile for AI Coding Tools
# Supports two independent systems: orchestrator (port 5001) and agentic_team (port 5002)

# ─────────────────────────────────────────────
# Stage 1: Builder — install all Python deps
# ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

LABEL maintainer="DevOps Team"
LABEL version="2.0.0"
LABEL description="AI Coding Tools — Builder Stage"

WORKDIR /build

# Build-time system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the dependency manifests first (layer-cache friendly)
COPY requirements.txt .
COPY pyproject.toml .
COPY setup.py .

# Install all Python deps into the user site for later copy
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user -r requirements.txt

# ─────────────────────────────────────────────
# Stage 2: Runtime — minimal production image
# ─────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="DevOps Team"
LABEL version="2.0.0"
LABEL description="AI Coding Tools — Production Runtime"

# Runtime environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=5001 \
    LOG_LEVEL=INFO \
    ENVIRONMENT=production

# Non-root user with fixed UID/GID for predictable K8s securityContext
RUN groupadd -r -g 1000 appuser && \
    useradd -r -u 1000 -g appuser -m -s /bin/bash appuser

WORKDIR /app

# Runtime system deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Pull Python packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# ── Application source (both self-contained systems + MCP server) ──
COPY --chown=appuser:appuser orchestrator/   ./orchestrator/
COPY --chown=appuser:appuser agentic_team/   ./agentic_team/
COPY --chown=appuser:appuser mcp_server/     ./mcp_server/
COPY --chown=appuser:appuser context_dashboard/ ./context_dashboard/
COPY --chown=appuser:appuser scripts/          ./scripts/

# ── Root-level entry points and manifests ──
COPY --chown=appuser:appuser ai-orchestrator     ./ai-orchestrator
COPY --chown=appuser:appuser ai-agentic-team     ./ai-agentic-team
COPY --chown=appuser:appuser setup.py            ./setup.py
COPY --chown=appuser:appuser pyproject.toml      ./pyproject.toml
COPY --chown=appuser:appuser requirements.txt    ./requirements.txt
COPY --chown=appuser:appuser README.md           ./README.md
COPY --chown=appuser:appuser LICENSE             ./LICENSE

# Make CLI entry points executable
RUN chmod +x ai-orchestrator ai-agentic-team

# Runtime writable directories
RUN mkdir -p \
    /app/output \
    /app/workspace \
    /app/reports \
    /app/sessions \
    /app/logs \
    /app/tmp \
    /home/appuser/.ai-orchestrator \
    /home/appuser/.agentic-team \
    && chown -R appuser:appuser /app

# Lock down source trees; config files inside each subsystem are read-only
RUN chmod -R 755 /app/orchestrator /app/agentic_team && \
    find /app/orchestrator/config  -name "*.yaml" -exec chmod 444 {} + 2>/dev/null || true && \
    find /app/agentic_team/config  -name "*.yaml" -exec chmod 444 {} + 2>/dev/null || true

USER appuser

ENV PATH="/home/appuser/.local/bin:${PATH}"

# orchestrator UI on 5001, agentic team UI on 5002, context dashboard on 5003, MCP server on 8000
EXPOSE 5001
EXPOSE 5002
EXPOSE 5003
EXPOSE 8000

# Health check targets orchestrator by default; override via HEALTHCHECK_PORT for agentic_team
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5001}/health || exit 1

# Persistent data lives outside the image
VOLUME ["/app/workspace", "/app/sessions", "/app/logs", "/app/output", "/home/appuser/.ai-orchestrator", "/home/appuser/.agentic-team"]

# Default: run the orchestrator UI.
# Override CMD in docker-compose / K8s to run agentic_team/ui/app.py instead.
ENTRYPOINT ["python"]
CMD ["orchestrator/ui/app.py"]
