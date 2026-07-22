---
description: Run system health checks and generate a health report
disable-model-invocation: false
---

Run health checks for the orchestrator system:

1. Execute the health checker:
```python
python3 -c "
from orchestrator.observability.health import HealthChecker
from orchestrator.observability.report_generator import ReportGenerator
import json

checker = HealthChecker()
results = checker.run_all_checks()
print(json.dumps(results, indent=2, default=str))

gen = ReportGenerator(reports_dir='./reports')
path = gen.generate_health_report(health_results=results)
print(f'\nReport saved: {path}')
"
```

2. Summarize the health status, highlighting any degraded or unhealthy checks.
