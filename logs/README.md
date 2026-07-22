# 📋 Logs Directory

Runtime log output for all AI Coding Tools services. Contents are **git-ignored** — only this README and `.gitkeep` are tracked.

## Overview

Every service writes structured logs here during execution. Logs are the primary diagnostic tool for debugging agent behavior, tracking task progress, and auditing system activity.

## Services That Write Logs

| Service | Log Pattern | Port | Description |
|---------|-------------|------|-------------|
| **Orchestrator** | `orchestrator_*.log` | 5001 | Multi-agent task coordination |
| **Agentic Team** | `agentic_team_*.log` | 5002 | Role-based team collaboration |
| **MCP Server** | `mcp_server_*.log` | 8000 | Model Context Protocol tools |
| **Context Dashboard** | `dashboard_*.log` | 5003 | Graph visualization backend |

## Log Architecture

```mermaid
flowchart TD
    subgraph Services
        O[Orchestrator :5001]
        A[Agentic Team :5002]
        M[MCP Server :8000]
        D[Context Dashboard :5003]
    end

    subgraph "Logging Pipeline"
        SL[structlog Processor]
        FH[File Handler]
        JH[Journal / stdout]
    end

    subgraph "logs/"
        OF[orchestrator_*.log]
        AF[agentic_team_*.log]
        MF[mcp_server_*.log]
        DF[dashboard_*.log]
    end

    O --> SL
    A --> SL
    M --> SL
    D --> SL
    SL --> FH --> OF & AF & MF & DF
    SL --> JH
```

## Log Format

All services use **structlog** for structured JSON logging:

```json
{
  "timestamp": "2026-04-04T21:00:00.000Z",
  "level": "info",
  "event": "task_executed",
  "service": "orchestrator",
  "agent": "claude",
  "task_id": "abc-123",
  "duration_ms": 1450,
  "status": "success"
}
```

## Log Levels

```mermaid
graph LR
    D[DEBUG] --> I[INFO] --> W[WARNING] --> E[ERROR] --> C[CRITICAL]
    style D fill:#6c757d,color:#fff
    style I fill:#0d6efd,color:#fff
    style W fill:#ffc107,color:#000
    style E fill:#dc3545,color:#fff
    style C fill:#6f42c1,color:#fff
```

| Level | Use |
|-------|-----|
| `DEBUG` | Agent prompts, adapter I/O, internal state |
| `INFO` | Task start/complete, agent selection, workflow steps |
| `WARNING` | Rate limits, fallback routing, retries |
| `ERROR` | Agent failures, timeout, connection errors |
| `CRITICAL` | Service crash, data corruption, security events |

## Configuration

Set log level via environment variable:

```bash
export LOG_LEVEL=INFO          # Default
export LOG_LEVEL=DEBUG         # Verbose (development)
```

In production (Docker/K8s/systemd), logs also go to **stdout/journal** for aggregation by Prometheus, Grafana Loki, or ELK.

## Retention

- **Development**: Logs accumulate until manually cleared
- **Production (Docker)**: Managed by Docker log driver (`json-file`, `max-size: 10m`, `max-file: 5`)
- **Production (K8s)**: Collected by node-level log agents (Fluentd/Fluent Bit)
- **Systemd**: Managed by `journald` (`journalctl -u ai-orchestrator`)

## Useful Commands

```bash
# Tail orchestrator logs
tail -f logs/orchestrator_*.log | python -m json.tool

# Search for errors across all logs
grep '"level":"error"' logs/*.log

# Count events by level
grep -oh '"level":"[a-z]*"' logs/*.log | sort | uniq -c | sort -rn
```
