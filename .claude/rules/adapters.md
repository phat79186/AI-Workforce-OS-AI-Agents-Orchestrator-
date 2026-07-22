---
paths:
  - "orchestrator/adapters/**/*.py"
  - "agentic_team/adapters/**/*.py"
---

# Adapter Development Rules

- All adapters extend `BaseAdapter` and implement `execute_task()` and `is_available()`
- CLI adapters use `CLICommunicator` for subprocess management — never call `subprocess` directly
- HTTP adapters (Ollama, LlamaCpp) use `httpx` for async support
- Return `AgentResponse(success=bool, output=str)` — never raise on agent failure
- `is_available()` uses `shutil.which()` for CLI tools, HTTP health check for local servers
- Adapter resolution is by `type` field in config, not by agent name
- The two adapter directories (`orchestrator/adapters/`, `agentic_team/adapters/`) are independent copies
