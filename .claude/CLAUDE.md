# AI Coding Tools Orchestrator — Project Instructions

## Commands
- Install: `pip install -r requirements.txt`
- Test (unit): `python -m pytest tests/ --override-ini="addopts=" -q --timeout=30 -m "not integration and not slow"`
- Test (all): `python -m pytest tests/ --override-ini="addopts=" -q --timeout=30`
- Test (single): `python -m pytest tests/test_<name>.py -q --override-ini="addopts=" --timeout=30`
- Lint: `flake8 orchestrator/ agentic_team/ tests/ --max-line-length=120 --exclude=__pycache__,.git,*.egg-info`
- Format: `black orchestrator/ agentic_team/ tests/`
- Import sort: `isort orchestrator/ agentic_team/ tests/`
- Type check: `mypy orchestrator/ agentic_team/ --ignore-missing-imports`
- Security scan: `bandit -r orchestrator/ agentic_team/ -c pyproject.toml`
- Run orchestrator shell: `./ai-orchestrator shell`
- Run agentic team shell: `./ai-orchestrator agentic-shell`
- Start Web UI: `python orchestrator/ui/app.py` (port 5001)
- Start Agentic UI: `python agentic_team/ui/app.py` (port 5002)
- Start MCP server: `python -m mcp_server.server`

## Architecture
Two self-contained systems — **zero shared code**:
- `orchestrator/` — step-based workflow engine (implement → review → refine)
- `agentic_team/` — free-communication team runtime (PM, Architect, Dev, QA, DevOps)
- `mcp_server/` — optional FastMCP 3.x server exposing both engines (10 tools, 2 resources)

Each system has its own adapters, config, CLI, and UI. Never import between them.

## Key Directories
- `orchestrator/config/agents.yaml` — agents, workflows, settings, agentic_team roles
- `orchestrator/core/engine.py` — main orchestration engine
- `orchestrator/adapters/` — Claude, Codex, Gemini, Copilot, Ollama, llama.cpp adapters
- `orchestrator/observability/` — metrics, logging, health, report generation
- `agentic_team/engine.py` — role-based communication engine
- `reports/` — auto-generated JSON reports + HTML dashboard
- `tests/` — 311+ tests (pytest), markers: unit, integration, slow, security, agentic_team

## Rules
- Python 3.8+ compatibility required
- Use type hints (Pydantic for models, dataclasses for simple structs)
- Black formatting, 120-char line limit
- Tests go in `tests/test_<module>.py` — match existing patterns
- Mark tests requiring CLI tools as `@pytest.mark.integration`
- Never import between `orchestrator/` and `agentic_team/`
- Keep pre-commit hooks passing: trailing whitespace, black, isort, flake8, mypy, bandit
- When adding features to one system, check if the other needs a parallel addition
