---
description: Generate all report types (execution, performance, workflow, health, config audit, HTML dashboard)
disable-model-invocation: true
argument-hint: [type]
---

Generate reports for the orchestrator system.

If `$ARGUMENTS` specifies a type (health, config, performance, workflow, dashboard, all), generate that type.
Default is "all".

```python
python3 -c "
import yaml
from orchestrator.observability.report_generator import ReportGenerator

with open('orchestrator/config/agents.yaml') as f:
    config = yaml.safe_load(f)

gen = ReportGenerator(reports_dir='./reports')
paths = gen.seed_reports(config=config)
for p in paths:
    print(f'  Generated: {p}')
print(f'\n{len(paths)} reports generated in reports/')
"
```

Report which files were generated and their sizes.
