# Examples

Runnable examples for both the **Orchestrator** and **Agentic Team** systems.

## Prerequisites

```bash
# From project root
pip install -r requirements.txt

# Ensure at least one CLI tool is available
which claude codex gemini
```

## Orchestrator Examples

| File | What It Shows |
|------|---------------|
| [`orchestrator/basic_usage.py`](orchestrator/basic_usage.py) | Run a task through the default workflow (codex → gemini → claude) |
| [`orchestrator/custom_workflow.py`](orchestrator/custom_workflow.py) | Choose specific workflows (quick, review-only, thorough) |
| [`orchestrator/with_fallback.py`](orchestrator/with_fallback.py) | Cloud-to-local fallback when agents are unreachable |
| [`orchestrator/programmatic_adapters.py`](orchestrator/programmatic_adapters.py) | Use individual adapters directly without the workflow engine |
| [`orchestrator/metrics_and_health.py`](orchestrator/metrics_and_health.py) | Health checks, Prometheus metrics, caching, circuit breaker |

```bash
python examples/orchestrator/basic_usage.py
python examples/orchestrator/custom_workflow.py
python examples/orchestrator/programmatic_adapters.py
```

## Agentic Team Examples

| File | What It Shows |
|------|---------------|
| [`agentic_team/basic_usage.py`](agentic_team/basic_usage.py) | Run a task with multi-role team collaboration |
| [`agentic_team/with_callbacks.py`](agentic_team/with_callbacks.py) | Real-time turn-by-turn monitoring via callbacks |
| [`agentic_team/custom_team_config.py`](agentic_team/custom_team_config.py) | Inspect and validate team role-to-agent mappings |
| [`agentic_team/decision_parsing.py`](agentic_team/decision_parsing.py) | How the decision parser extracts routing from LLM output |

```bash
python examples/agentic_team/basic_usage.py
python examples/agentic_team/with_callbacks.py
python examples/agentic_team/decision_parsing.py
```

## CLI Examples

```bash
# Orchestrator interactive shell
./ai-orchestrator shell

# Agentic team interactive shell
./ai-orchestrator agentic-shell

# Single task execution
./ai-orchestrator run "Build a calculator" --workflow default

# Offline mode
./ai-orchestrator run "Build a REST API" --offline
```

## Sample Task Ideas

See [`sample_tasks.md`](sample_tasks.md) for a comprehensive list of tasks to try.
