"""DevOps utility MCP tools for infrastructure and deployment."""

import json
import re
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context


async def generate_dockerfile(
    ctx: Context,
    language: str,
    framework: Optional[str] = None,
    port: int = 8000,
) -> Dict[str, Any]:
    """Generate a Dockerfile for a project.

    Args:
        ctx: MCP context
        language: Programming language (python, node, go, java)
        framework: Optional framework (flask, fastapi, express, gin)
        port: Port to expose

    Returns:
        Generated Dockerfile content and recommendations.
    """
    templates: Dict[str, Dict[str, Any]] = {
        "python": {
            "base": "python:3.11-slim",
            "install": "pip install --no-cache-dir -r requirements.txt",
            "cmd": "python app.py",
        },
        "node": {
            "base": "node:20-alpine",
            "install": "npm ci --only=production",
            "cmd": "node index.js",
        },
        "go": {
            "base": "golang:1.21-alpine",
            "install": "go mod download",
            "cmd": "./app",
        },
        "java": {
            "base": "eclipse-temurin:17-jdk-alpine",
            "install": "./mvnw package -DskipTests",
            "cmd": "java -jar target/*.jar",
        },
    }

    framework_overrides: Dict[str, Dict[str, str]] = {
        "flask": {"cmd": "gunicorn -w 4 -b 0.0.0.0:{port} app:app"},
        "fastapi": {"cmd": "uvicorn app:app --host 0.0.0.0 --port {port}"},
        "express": {"cmd": "node server.js"},
        "gin": {"cmd": "./server"},
    }

    template = templates.get(language, templates["python"])
    cmd = template["cmd"]

    if framework and framework in framework_overrides:
        cmd = framework_overrides[framework].get("cmd", cmd)

    cmd = cmd.format(port=port)

    dockerfile = f"""# Auto-generated Dockerfile
FROM {template["base"]}

WORKDIR /app

# Copy dependency files first for better caching
COPY requirements.txt* package*.json* go.* pom.xml* ./

# Install dependencies
RUN {template["install"]}

# Copy application code
COPY . .

# Expose port
EXPOSE {port}

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:{port}/health || exit 1

# Run application
CMD {cmd}
"""

    return {
        "dockerfile": dockerfile,
        "recommendations": [
            "Use multi-stage builds for smaller images",
            "Add .dockerignore file",
            "Pin dependency versions",
            "Run as non-root user",
            "Use specific image tags instead of latest",
        ],
        "security_notes": [
            "Scan image for vulnerabilities",
            "Don't include secrets in image",
            "Use read-only filesystem where possible",
        ],
    }


async def generate_docker_compose(
    ctx: Context,
    services: List[str],
    include_db: Optional[str] = None,
    include_cache: bool = False,
) -> Dict[str, Any]:
    """Generate a docker-compose.yml file.

    Args:
        ctx: MCP context
        services: List of service names
        include_db: Database to include (postgres, mysql, mongodb)
        include_cache: Include Redis cache

    Returns:
        Generated docker-compose.yml content.
    """
    compose: Dict[str, Any] = {
        "version": "3.8",
        "services": {},
        "networks": {"app-network": {"driver": "bridge"}},
        "volumes": {},
    }

    # Add main services
    for i, service in enumerate(services):
        compose["services"][service] = {
            "build": f"./{service}" if len(services) > 1 else ".",
            "ports": [f"{8000 + i}:8000"],
            "environment": ["NODE_ENV=production"],
            "networks": ["app-network"],
            "restart": "unless-stopped",
        }

    # Add database
    if include_db:
        db_configs: Dict[str, Dict[str, Any]] = {
            "postgres": {
                "image": "postgres:15-alpine",
                "environment": [
                    "POSTGRES_USER=app",
                    "POSTGRES_PASSWORD=secret",
                    "POSTGRES_DB=appdb",
                ],
                "volumes": ["postgres-data:/var/lib/postgresql/data"],
                "healthcheck": {
                    "test": ["CMD-SHELL", "pg_isready -U app"],
                    "interval": "10s",
                    "timeout": "5s",
                    "retries": 5,
                },
            },
            "mysql": {
                "image": "mysql:8.0",
                "environment": [
                    "MYSQL_ROOT_PASSWORD=secret",
                    "MYSQL_DATABASE=appdb",
                    "MYSQL_USER=app",
                    "MYSQL_PASSWORD=secret",
                ],
                "volumes": ["mysql-data:/var/lib/mysql"],
            },
            "mongodb": {
                "image": "mongo:6.0",
                "environment": [
                    "MONGO_INITDB_ROOT_USERNAME=app",
                    "MONGO_INITDB_ROOT_PASSWORD=secret",
                ],
                "volumes": ["mongo-data:/data/db"],
            },
        }

        if include_db in db_configs:
            compose["services"]["db"] = db_configs[include_db]
            compose["services"]["db"]["networks"] = ["app-network"]
            compose["volumes"][f"{include_db}-data"] = {}

            # Add depends_on to services
            for service in services:
                compose["services"][service]["depends_on"] = ["db"]

    # Add cache
    if include_cache:
        compose["services"]["redis"] = {
            "image": "redis:7-alpine",
            "command": "redis-server --appendonly yes",
            "volumes": ["redis-data:/data"],
            "networks": ["app-network"],
        }
        compose["volumes"]["redis-data"] = {}

    import yaml

    try:
        compose_yaml = yaml.dump(compose, default_flow_style=False, sort_keys=False)
    except ImportError:
        compose_yaml = json.dumps(compose, indent=2)

    return {
        "docker_compose": compose_yaml,
        "files_needed": [
            "Dockerfile for each service",
            ".env file for secrets",
            ".dockerignore",
        ],
        "commands": {
            "start": "docker-compose up -d",
            "stop": "docker-compose down",
            "logs": "docker-compose logs -f",
            "rebuild": "docker-compose up -d --build",
        },
    }


async def generate_ci_config(
    ctx: Context,
    platform: str = "github",
    language: str = "python",
    include_deploy: bool = False,
) -> Dict[str, Any]:
    """Generate CI/CD configuration file.

    Args:
        ctx: MCP context
        platform: CI platform (github, gitlab, jenkins)
        language: Programming language
        include_deploy: Include deployment step

    Returns:
        Generated CI configuration.
    """
    configs: Dict[str, str] = {}

    if platform == "github":
        config = """name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: pytest --cov=./ --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  lint:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install linters
        run: pip install flake8 black isort mypy

      - name: Run linters
        run: |
          flake8 .
          black --check .
          isort --check .
"""
        if include_deploy:
            config += """
  deploy:
    needs: [test, lint]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to production
        run: echo "Add deployment steps here"
"""
        configs["github"] = config

    elif platform == "gitlab":
        config = """stages:
  - test
  - lint
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip/

test:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - pytest --cov=./ --cov-report=xml
  coverage: '/TOTAL.*\\s+(\\d+%)/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

lint:
  stage: lint
  image: python:3.11
  script:
    - pip install flake8 black isort
    - flake8 .
    - black --check .
    - isort --check .
"""
        if include_deploy:
            config += """
deploy:
  stage: deploy
  only:
    - main
  script:
    - echo "Add deployment steps here"
"""
        configs["gitlab"] = config

    elif platform == "jenkins":
        config = """pipeline {
    agent any

    environment {
        PYTHON_VERSION = '3.11'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup') {
            steps {
                sh 'python -m pip install --upgrade pip'
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Test') {
            steps {
                sh 'pip install pytest pytest-cov'
                sh 'pytest --cov=./ --cov-report=xml'
            }
            post {
                always {
                    junit 'test-results.xml'
                    cobertura coberturaReportFile: 'coverage.xml'
                }
            }
        }

        stage('Lint') {
            steps {
                sh 'pip install flake8 black'
                sh 'flake8 .'
                sh 'black --check .'
            }
        }
    }
}
"""
        configs["jenkins"] = config

    return {
        "platform": platform,
        "config": configs.get(platform, ""),
        "filename": {
            "github": ".github/workflows/ci.yml",
            "gitlab": ".gitlab-ci.yml",
            "jenkins": "Jenkinsfile",
        }.get(platform, "ci.yml"),
    }


async def analyze_deployment_config(ctx: Context, config_path: str) -> Dict[str, Any]:
    """Analyze deployment configuration for issues and improvements.

    Args:
        ctx: MCP context
        config_path: Path to deployment config file

    Returns:
        Analysis with recommendations.
    """
    issues: List[Dict[str, str]] = []
    recommendations: List[str] = []

    try:
        with open(config_path, encoding="utf-8") as f:
            content = f.read()

        # Check for common issues
        checks = [
            (r"latest", "Using 'latest' tag - pin specific versions"),
            (r"password.*=.*['\"][^'\"]+['\"]", "Hardcoded password detected"),
            (r"privileged:\s*true", "Privileged container - security risk"),
            (r"root", "Running as root user"),
            (r"host.*network", "Using host network mode"),
        ]

        lines = content.splitlines()
        for pattern, message in checks:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({"line": str(i), "issue": message, "content": line.strip()[:60]})

        # Generate recommendations
        if "healthcheck" not in content.lower():
            recommendations.append("Add health checks for containers")
        if "resources" not in content.lower() and "limits" not in content.lower():
            recommendations.append("Add resource limits (CPU/memory)")
        if "restart" not in content.lower():
            recommendations.append("Add restart policy")

        return {
            "file": config_path,
            "issues": issues,
            "recommendations": recommendations,
            "score": max(0, 100 - len(issues) * 10),
        }

    except Exception as e:
        return {"error": str(e)}


async def check_environment_config(ctx: Context, env_file: str = ".env.example") -> Dict[str, Any]:
    """Check environment configuration for completeness.

    Args:
        ctx: MCP context
        env_file: Path to environment file

    Returns:
        Environment configuration analysis.
    """
    try:
        with open(env_file, encoding="utf-8") as f:
            content = f.read()

        env_vars: List[Dict[str, Any]] = []
        categories: Dict[str, List[str]] = {
            "database": [],
            "api_keys": [],
            "auth": [],
            "other": [],
        }

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key = line.split("=")[0].strip()
                has_value = len(line.split("=")) > 1 and line.split("=")[1].strip()

                env_vars.append(
                    {
                        "key": key,
                        "has_default": bool(has_value),
                        "is_secret": any(
                            s in key.lower() for s in ["password", "secret", "key", "token"]
                        ),
                    }
                )

                # Categorize
                key_lower = key.lower()
                if any(s in key_lower for s in ["db", "database", "postgres", "mysql"]):
                    categories["database"].append(key)
                elif any(s in key_lower for s in ["api", "key", "token"]):
                    categories["api_keys"].append(key)
                elif any(s in key_lower for s in ["auth", "jwt", "session"]):
                    categories["auth"].append(key)
                else:
                    categories["other"].append(key)

        return {
            "file": env_file,
            "variables": env_vars,
            "categories": categories,
            "secrets_count": sum(1 for v in env_vars if v["is_secret"]),
            "recommendations": [
                "Never commit .env files with real values",
                "Use .env.example for documentation",
                "Consider using a secrets manager for production",
            ],
        }

    except FileNotFoundError:
        return {"error": f"File not found: {env_file}"}
    except Exception as e:
        return {"error": str(e)}


def register_devops_tools(mcp: Any) -> None:
    """Register DevOps tools with MCP server."""
    mcp.tool()(generate_dockerfile)
    mcp.tool()(generate_docker_compose)
    mcp.tool()(generate_ci_config)
    mcp.tool()(analyze_deployment_config)
    mcp.tool()(check_environment_config)


# Aliases for backward compatibility
analyze_dockerfile = generate_dockerfile
analyze_compose_file = generate_docker_compose
check_ci_config = generate_ci_config
analyze_env_config = check_environment_config


async def generate_deploy_checklist(
    ctx: Context, environment: str = "production"
) -> Dict[str, Any]:
    """Generate deployment checklist.

    Args:
        ctx: MCP context
        environment: Target environment

    Returns:
        Deployment checklist with tasks.
    """
    checklist = {
        "environment": environment,
        "pre_deployment": [
            "Run all tests and ensure they pass",
            "Update dependencies to latest stable versions",
            "Review and update configuration for target environment",
            "Backup production database",
            "Check disk space and resources",
            "Review recent changes and commits",
        ],
        "deployment": [
            "Build production Docker images",
            "Tag images with version number",
            "Push images to registry",
            "Update Kubernetes manifests",
            "Apply configuration changes",
            "Deploy with rolling update strategy",
            "Monitor deployment progress",
        ],
        "post_deployment": [
            "Verify health checks are passing",
            "Check application logs for errors",
            "Run smoke tests",
            "Monitor metrics and alerts",
            "Verify database migrations completed",
            "Test critical user flows",
            "Update documentation",
        ],
        "rollback_plan": [
            "Keep previous version images available",
            "Document rollback procedure",
            "Maintain database backup",
            "Have team members on standby",
        ],
    }

    if environment == "production":
        checklist["additional_checks"] = [
            "Get approval from stakeholders",
            "Schedule maintenance window",
            "Notify users of deployment",
            "Prepare incident response plan",
        ]

    return checklist
