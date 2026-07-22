---
paths:
  - ".github/**/*"
  - "Dockerfile"
  - "docker-compose.yml"
  - "Makefile"
  - "Jenkinsfile"
  - ".gitlab-ci.yml"
  - ".circleci/**/*"
---

# CI/CD Rules

- GitHub Actions workflow at `.github/workflows/ci.yml`
- CI runs: lint → test → Docker build → GHCR publish → summary
- Tests in CI exclude integration and slow markers: `-m "not integration and not slow"`
- Docker image: multi-stage build, published to `ghcr.io`
- Pre-commit hooks: trailing-whitespace, black, isort, flake8, mypy, bandit, pyupgrade
- All CI job names and step names use emoji prefixes
