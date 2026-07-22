---
paths:
  - "orchestrator/config/**/*"
  - "agentic_team/config/**/*"
  - "orchestrator/infra/config_manager.py"
---

# Configuration Rules

- Config files are YAML at `*/config/agents.yaml`
- Agent config fields: type, enabled, command/endpoint, role, timeout, offline, capabilities
- Workflow config: list of steps with agent + task/role, or dict with steps key
- Settings: max_iterations, output_dir, reports_dir, create_reports, offline, fallback
- Agentic team config is under the `agentic_team` key in agents.yaml
- Use `ConfigManager` and `AppSettings` (Pydantic) for programmatic access
- Never hardcode paths — use `Path` objects and config values
