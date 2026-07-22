# Contributing to AI Workforce OS

Thank you for your interest in contributing to **AI Workforce OS**! We welcome contributions from developers, AI researchers, local AI enthusiasts, and open-source contributors.

---

## 1. Development Setup

### Prerequisites
- **Python 3.8+** (Python 3.10 to 3.14 fully supported)
- **Git**
- **Ollama** (Optional, for local LLM execution: `ollama run qwen2.5-coder:7b`)

### Quick Setup Commands
```bash
# Clone repository
git clone https://github.com/hoangsonww/AI-Agents-Orchestrator.git
cd AI-Agents-Orchestrator

# Create virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 2. Running Tests

We maintain a strict **100% test pass policy** (614+ unit & integration tests passing).

```bash
# Run unit & integration test suite (excluding slow/integration CLI marks)
python -m pytest tests/ -o addopts="" -m "not integration and not slow"

# Run specific module tests
python -m pytest tests/test_v4_organization.py -o addopts=""
python -m pytest tests/test_real_obsidian_integration.py -o addopts=""
```

---

## 3. Code Style & Standards

- **Formatting**: `black` (120 character line length)
- **Imports**: `isort`
- **Linting**: `flake8`
- **Type Annotations**: Python 3.8+ type hints required for all public methods and functions.
- **Documentation**: Keep comments and docstrings intact. Do not delete existing comments unless explicitly requested.

```bash
# Format code
black --line-length 120 .
isort .
flake8
```

---

## 4. Pull Request Process

1. **Fork the Repository**: Create a topic branch from `main` (`feature/your-feature-name` or `bugfix/issue-description`).
2. **Write Unit Tests**: Ensure new features or bug fixes include pytest unit tests under `tests/`.
3. **Verify Test Suite**: Run `pytest` to confirm 0 failures.
4. **Submit PR**: Open a Pull Request on GitHub with a clear description of changes and rationale.

---

## 5. Security & Vulnerability Reporting

If you discover a security vulnerability, please report it via GitHub Security Advisories or contact the maintainers directly. Do not report security vulnerabilities in public issues.
