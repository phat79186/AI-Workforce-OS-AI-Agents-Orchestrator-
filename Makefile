.PHONY: help install install-dev \
        test test-orchestrator test-agentic test-unit test-integration test-coverage \
        lint lint-orchestrator lint-agentic \
        format format-all prettier-format \
        type-check security security-orchestrator security-agentic \
        clean build \
        docker-build docker-up docker-down docker-run docker-run-agentic \
        run-ui run-agentic-ui \
        shell agentic-shell \
        docs pre-commit

# ── Help ───────────────────────────────────────────────────────────────────────
help:
	@echo "Available targets:"
	@echo ""
	@echo "  Dependencies"
	@echo "    install              Install production dependencies"
	@echo "    install-dev          Install dev dependencies and pre-commit hooks"
	@echo ""
	@echo "  Testing"
	@echo "    test                 Run full test suite (pytest tests/)"
	@echo "    test-orchestrator    Run orchestrator-specific tests"
	@echo "    test-agentic         Run agentic_team-specific tests"
	@echo "    test-unit            Run unit tests only"
	@echo "    test-integration     Run integration tests only"
	@echo "    test-coverage        Run tests with HTML coverage report"
	@echo ""
	@echo "  Code Quality"
	@echo "    lint                 Lint all Python source"
	@echo "    lint-orchestrator    Lint orchestrator/ only"
	@echo "    lint-agentic         Lint agentic_team/ only"
	@echo "    format               Format with black + isort"
	@echo "    prettier-format      Format JS/CSS/HTML with Prettier"
	@echo "    format-all           Run Python + Prettier formatting"
	@echo "    type-check           Run mypy on both subsystems"
	@echo "    security             Run bandit + safety on everything"
	@echo "    security-orchestrator Run bandit on orchestrator/"
	@echo "    security-agentic     Run bandit on agentic_team/"
	@echo ""
	@echo "  Build"
	@echo "    clean                Remove build artifacts and caches"
	@echo "    build                Build distribution packages"
	@echo ""
	@echo "  Docker"
	@echo "    docker-build         Build the Docker image"
	@echo "    docker-up            Start both services with docker compose"
	@echo "    docker-down          Stop and remove containers"
	@echo "    docker-run           Run orchestrator UI container on port 5001"
	@echo "    docker-run-agentic   Run agentic team UI container on port 5002"
	@echo ""
	@echo "  Run locally"
	@echo "    run-ui               Start orchestrator UI  (orchestrator/ui/app.py)"
	@echo "    run-agentic-ui       Start agentic team UI  (agentic_team/ui/app.py)"
	@echo "    shell                Start orchestrator CLI shell"
	@echo "    agentic-shell        Start agentic team CLI shell"
	@echo ""
	@echo "  MCP Server"
	@echo "    run-mcp              Start MCP server (stdio, for Claude Desktop)"
	@echo "    run-mcp-http         Start MCP server (HTTP, port 8000)"
	@echo ""
	@echo "  Misc"
	@echo "    docs                 Build Sphinx documentation"
	@echo "    pre-commit           Run pre-commit hooks on all files"

# ── Dependencies ───────────────────────────────────────────────────────────────
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# ── Testing ────────────────────────────────────────────────────────────────────
test:
	python -m pytest tests/ --override-ini="addopts=" -q --timeout=30

test-orchestrator:
	python -m pytest tests/test_orchestrator.py tests/test_ui_backend.py \
	               tests/test_adapters.py tests/test_adapter_execution.py \
	               tests/test_cli_communicator.py tests/test_shell.py \
	               --override-ini="addopts=" -q --timeout=30

test-agentic:
	python -m pytest tests/test_agentic_team_engine.py tests/test_agentic_ui_backend.py \
	               --override-ini="addopts=" -q --timeout=30

test-unit:
	python -m pytest tests/ -m "unit or not integration" \
	               --override-ini="addopts=" -q --timeout=30

test-integration:
	python -m pytest tests/ -m integration \
	               --override-ini="addopts=" -q --timeout=30

test-coverage:
	python -m pytest tests/ --override-ini="addopts=" -q --timeout=30 \
	               --cov=orchestrator --cov=agentic_team \
	               --cov-report=term-missing --cov-report=html

# ── Code Quality ───────────────────────────────────────────────────────────────
lint:
	flake8 orchestrator/ agentic_team/ tests/ --max-line-length=120
	pylint orchestrator/ agentic_team/ --fail-under=7.0 || true

lint-orchestrator:
	flake8 orchestrator/ tests/test_orchestrator.py tests/test_ui_backend.py \
	       --max-line-length=120
	pylint orchestrator/ --fail-under=7.0 || true

lint-agentic:
	flake8 agentic_team/ tests/test_agentic_team_engine.py tests/test_agentic_ui_backend.py \
	       --max-line-length=120

format:
	black orchestrator/ agentic_team/ tests/
	isort orchestrator/ agentic_team/ tests/

prettier-format:
	npm run format

format-all: format prettier-format

type-check:
	mypy orchestrator/ agentic_team/ --ignore-missing-imports

security:
	bandit -r orchestrator/ agentic_team/ -c pyproject.toml
	safety check --json

security-orchestrator:
	bandit -r orchestrator/ -c pyproject.toml

security-agentic:
	bandit -r agentic_team/ -c pyproject.toml

# ── Build ──────────────────────────────────────────────────────────────────────
clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	rm -rf build dist .coverage htmlcov .pytest_cache .mypy_cache

build: clean
	python -m build

# ── Docker ─────────────────────────────────────────────────────────────────────
docker-build:
	docker build -t ai-coding-tools:latest .

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

# Run just the orchestrator UI container (port 5001)
docker-run:
	docker run -it --rm \
	  -e PORT=5001 \
	  -p 5001:5001 \
	  ai-coding-tools:latest \
	  orchestrator/ui/app.py

# Run just the agentic team UI container (port 5002)
docker-run-agentic:
	docker run -it --rm \
	  -e PORT=5002 \
	  -e AGENTIC_UI_BACKEND_PORT=5002 \
	  -p 5002:5002 \
	  ai-coding-tools:latest \
	  agentic_team/ui/app.py

# ── Run locally ─────────────────────────────────────────────────────────────────
run-ui:
	python orchestrator/ui/app.py

run-agentic-ui:
	python agentic_team/ui/app.py

shell:
	./ai-orchestrator shell

agentic-shell:
	./ai-agentic-team shell

# ── MCP Server ─────────────────────────────────────────────────────────────────
run-mcp:
	python -m mcp_server.server

run-mcp-http:
	python -m mcp_server.server --transport http --port 8000

# ── Misc ───────────────────────────────────────────────────────────────────────
docs:
	cd docs && make html

pre-commit:
	pre-commit run --all-files

# Run everything in sequence (CI-style)
all: format lint type-check test-coverage security
