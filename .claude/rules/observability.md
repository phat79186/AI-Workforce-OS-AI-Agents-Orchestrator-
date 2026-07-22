---
paths:
  - "orchestrator/observability/**/*.py"
  - "reports/**/*"
---

# Observability & Reports Rules

- Metrics use `prometheus_client` — Counter, Histogram, Gauge, Summary
- Use the global singleton: `get_metrics_collector()` from `orchestrator.observability.metrics`
- Reports go to `reports/` directory as JSON + HTML dashboard
- `ReportGenerator` auto-generates execution reports when `create_reports: true` in config
- Health checks are in `health.py` — `HealthChecker.run_all_checks()` returns structured results
- Structured logging via `structlog` — use `get_logger(__name__)` not `logging.getLogger`
- Report INDEX.json is the catalog — `_update_index()` maintains it automatically
