# Security Guide

Security architecture and hardening measures for both systems.

## Overview

Both the Orchestrator and Agentic Team implement defense-in-depth security:

| Layer | Implementation |
|-------|---------------|
| Input validation | `InputValidator` — length limits, dangerous pattern detection |
| Rate limiting | `TokenBucketRateLimiter` — configurable per-key rate limits |
| Secret management | `SecretManager` — env-based loading, masked logging |
| Audit logging | `AuditLogger` — append-only logs with 0600 permissions |
| Path traversal | `/api/files/` endpoint validates paths against workspace root |
| Session isolation | Per-client session state with thread-safe locking |
| CORS | Configurable via `CORS_ALLOWED_ORIGINS` environment variable |
| Secret keys | Generated with `os.urandom(32)` — never hardcoded |
| File permissions | Session files and audit logs created with `0o600` |
| Subprocess safety | `shlex.quote()` for shell arguments; no `shell=True` |

## Input Validation

The `InputValidator` class (in `orchestrator/security_module/security.py`) validates:

```python
from orchestrator.security_module import InputValidator

# Task validation — checks length and dangerous patterns
task = InputValidator.validate_task("Build a REST API")

# Workflow name — alphanumeric + hyphens/underscores only
name = InputValidator.validate_workflow_name("my-workflow")

# File path — prevents traversal attacks
path = InputValidator.validate_file_path(
    "src/main.py",
    allowed_root=Path("./workspace"),
)
```

### Dangerous Patterns Blocked

- `rm -rf`
- `curl ... | bash`
- `wget ... | sh`
- `> /dev/` (device writes)
- `format C:` (Windows)
- `del /F` (Windows)

### Length Limits

| Field | Max Length |
|-------|-----------|
| Task description | 50,000 chars |
| Workflow name | 100 chars |
| Agent name | 50 chars |
| File path | 4,096 chars |
| Client ID | 128 chars |

## Rate Limiting

```python
from orchestrator.security_module import TokenBucketRateLimiter

limiter = TokenBucketRateLimiter(rate=60, window=60)  # 60 req/min
limiter.check_limit("user_123")  # Raises RateLimitError if exceeded
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `FLASK_SECRET_KEY` | Orchestrator Flask session key |
| `FLASK_SECRET_KEY_AGENTIC` | Agentic Team Flask session key |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins |
| `FLASK_DEBUG` | Set to `true` only in development |

## Production Checklist

- [ ] Set `FLASK_SECRET_KEY` and `FLASK_SECRET_KEY_AGENTIC` to strong random values
- [ ] Set `CORS_ALLOWED_ORIGINS` to your specific domains
- [ ] Set `FLASK_DEBUG=false`
- [ ] Enable rate limiting in config
- [ ] Review audit logs regularly (`logs/audit.log`)
- [ ] Run with non-root user (Dockerfile uses UID 1000)
- [ ] Use TLS termination at load balancer/ingress level

## Defense-in-Depth Security Layers

The following diagram illustrates how every incoming request passes through multiple security layers before reaching the execution engine. Each layer independently validates and can reject the request.

```mermaid
flowchart TD
    REQ["Incoming Request<br/>(REST API / WebSocket / CLI)"] --> CORS

    subgraph layer1["Layer 1: Transport Security"]
        CORS["CORS Policy<br/>CORS_ALLOWED_ORIGINS"]
        SESSION["Session Isolation<br/>Per-client state + thread-safe lock"]
        SECRET_KEY["Flask Secret Key<br/>os.urandom(32)"]
    end

    CORS --> IV

    subgraph layer2["Layer 2: Input Validation"]
        IV["InputValidator"]
        IV_TASK["Task length check<br/>(max 50,000 chars)"]
        IV_PATTERN["Dangerous pattern scan<br/>(rm -rf, curl|bash, etc.)"]
        IV_NAME["Name format check<br/>[a-zA-Z0-9_-]"]
        IV_PATH["Path traversal prevention<br/>resolve against workspace root"]
        IV --> IV_TASK --> IV_PATTERN --> IV_NAME --> IV_PATH
    end

    IV_PATH --> RL

    subgraph layer3["Layer 3: Rate Limiting"]
        RL["TokenBucketRateLimiter<br/>Per-key: 60 req / 60s window"]
    end

    RL --> SM

    subgraph layer4["Layer 4: Secret Masking"]
        SM["SecretManager<br/>Load API_KEY_*, SECRET_*,<br/>TOKEN_*, PASSWORD_*"]
        SM_MASK["Mask secrets in all<br/>log output and responses"]
        SM --> SM_MASK
    end

    SM_MASK --> AL

    subgraph layer5["Layer 5: Audit Logging"]
        AL["AuditLogger<br/>JSON-line events to logs/audit.log"]
        AL_PERM["File permissions: 0o600<br/>Append-only"]
        AL --> AL_PERM
    end

    AL_PERM --> EXEC

    subgraph layer6["Layer 6: Subprocess Safety"]
        EXEC["Agent Execution"]
        SHLEX["shlex.quote() all arguments"]
        NO_SHELL["No shell=True"]
        EXEC --> SHLEX
        EXEC --> NO_SHELL
    end

    IV_TASK -->|"length exceeded"| R400["400 Bad Request"]
    IV_PATTERN -->|"dangerous pattern"| R400
    IV_NAME -->|"invalid format"| R400
    IV_PATH -->|"traversal detected"| R403["403 Forbidden"]
    RL -->|"rate exceeded"| R429["429 Too Many Requests"]

    style layer1 fill:#3498db20,stroke:#3498db
    style layer2 fill:#e74c3c20,stroke:#e74c3c
    style layer3 fill:#e67e2220,stroke:#e67e22
    style layer4 fill:#8e44ad20,stroke:#8e44ad
    style layer5 fill:#27ae6020,stroke:#27ae60
    style layer6 fill:#2c3e5020,stroke:#2c3e50
    style R400 fill:#e74c3c,color:#fff
    style R403 fill:#e74c3c,color:#fff
    style R429 fill:#e74c3c,color:#fff
```
