# ⚡ Quickstart

Get up and running in under 2 minutes. Our two flagship systems, **Orchestrator** and **Agentic Team**, can be accessed via CLI shells, web UIs, or Docker. Both engines leverage your configured AI tools to execute tasks, build context graphs, and accelerate over time.

## Prerequisites

- **Python 3.8+**
- **pip**
- At least one AI tool installed: `claude`, `codex`, `gemini`, `ollama`, or `llama.cpp`

## Install

```bash
git clone https://github.com/hoangsonww/AI-Agents-Orchestrator.git
cd AI-Agents-Orchestrator
pip install -e ".[dev]"
```

## Run

### Option A: CLI Shells (recommended)

```bash
# Orchestrator — multi-agent workflows
make shell

# Agentic Team — role-based collaboration
make agentic-shell
```

On startup you'll be prompted for an optional project path:

```
Enter project path (absolute or relative, Enter to skip): /path/to/your/project
```

This gives agents full codebase awareness. Skip it to work in task-only mode.

> **Tip:** Set `PROJECT_PATH=/your/project` as an env var to skip the prompt.

### Option B: Web UIs

```bash
make run-ui              # Orchestrator  → http://127.0.0.1:5001
make run-agentic-ui      # Agentic Team  → http://127.0.0.1:5002
python -m context_dashboard  # Dashboard → http://127.0.0.1:5003
```

### Option C: Docker (all services)

```bash
make docker-build && make docker-up
```

## (Optional) Seed Context Graphs

Pre-populate graphs with generic best-practice knowledge:

```bash
python scripts/seed_context_graphs.py
```

## (Optional) MCP Server

Expose tools to Claude Desktop or other MCP clients:

```bash
make run-mcp-http    # HTTP → http://127.0.0.1:8000
make run-mcp         # stdio (for Claude Desktop)
```

## Key Commands (inside CLI shell)

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/agents` | List available AI agents |
| `/workflows` | List workflow templates |
| `/switch <agent>` | Switch active agent |
| `/project [path]` | Show or change project path |
| `/context` | View current context graph |
| `/exit` | Exit the shell |

## What Happens

1. You type a task → agents execute it using your configured AI tools
2. Context graphs build automatically as agents work
3. If a project path is set, agents scan the codebase and store project knowledge
4. Future tasks benefit from accumulated context — agents get faster over time

## Next Steps

- [README.md](README.md) — Full documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design
- [FEATURES.md](FEATURES.md) — Complete feature list
- [SETUP.md](SETUP.md) — Detailed setup & configuration
