---
name: sequential-thinking
description: Structured, iterative, and reflective multi-step reasoning with thought revision and hypothesis branching. Imported from GitHub modelcontextprotocol/servers.
---

# Sequential Thinking Skill

Imported and integrated from **[modelcontextprotocol/servers (sequentialthinking)](https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking)** / `@modelcontextprotocol/server-sequential-thinking`.

Sequential Thinking gives AI agents a structured, reflective, and step-by-step reasoning framework to tackle complex problems. Rather than outputting a single-shot response, the agent maintains an internal reasoning trajectory where each thought is an explicit step that can be validated, dynamically extended, revised, or branched into alternative hypotheses.

---

## When to Use

- **Multi-Step Problem Decomposition**: Breaking down complex architectural, refactoring, or algorithmic challenges into discrete, verifiable sub-steps.
- **Dynamic Plan Adaptation**: Adjusting the estimated number of steps (`totalThoughts`) as new constraints or edge cases emerge.
- **Thought Revision**: Recognizing a flawed assumption or error in earlier logic and explicitly marking a step as a revision (`isRevision=True`, `revisesThought=N`).
- **Hypothesis Branching**: Forking off alternative solution candidates (`branchFromThought=N`, `branchId="alt-design"`) to compare trade-offs before committing.
- **Audit Trail & Observability**: Generating clear, inspectable summaries of how a design decision or bug diagnosis was reached.

---

## Core Thought Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `thought` | `str` | Yes | The current step's reasoning or analysis text. |
| `thoughtNumber` | `int` | Yes | 1-based index of the current reasoning step. |
| `totalThoughts` | `int` | Yes | Estimated total number of thoughts required (dynamically adjustable). |
| `nextThoughtNeeded`| `bool` | Yes | `True` if more reasoning steps are needed; `False` on the concluding thought. |
| `isRevision` | `bool` | No | `True` if this step modifies or invalidates an earlier step. |
| `revisesThought` | `int` | No | The 1-based step index being revised (required if `isRevision` is `True`). |
| `branchFromThought`| `int` | No | The 1-based step index to branch from. |
| `branchId` | `str` | No | Unique identifier for the alternative branch (e.g. `"redis-cache-strategy"`). |
| `needsMoreThoughts`| `bool` | No | Signal that initial scope was underestimated and more steps are expected. |
| `resetSession` | `bool` | No | Clear previous thought history to start a fresh reasoning problem. |

---

## Usage Modes

### 1. In-Process Python Usage (`ExternalEcosystemHub`)

```python
from orchestrator.integrations import ExternalEcosystemHub

hub = ExternalEcosystemHub()
engine = hub.sequential_thinking

# Step 1: Initial problem framing
step1 = engine.process_thought(
    thought="Analyze high concurrency bottleneck in websocket broker.",
    thought_number=1,
    total_thoughts=3,
    next_thought_needed=True,
)

# Step 2: Branching alternative hypothesis
step2_branch = engine.process_thought(
    thought="Hypothesis B: Memory pressure caused by unbounded client queues.",
    thought_number=2,
    total_thoughts=3,
    next_thought_needed=True,
    branch_from_thought=1,
    branch_id="memory-leak-check",
)

# Step 3: Concluding thought
step3 = engine.process_thought(
    thought="Solution: Introduce backpressure with sliding token bucket per client socket.",
    thought_number=3,
    total_thoughts=3,
    next_thought_needed=False,
)

print(engine.get_summary())
```

### 2. Native AI Workforce OS MCP Server

This repository's built-in MCP server (`ai-mcp-server` / `mcp_server.server`) exposes both:
- `sequentialthinking` (official camelCase schema)
- `sequential_thinking` (snake_case alias)

Start server:
```bash
python -m mcp_server.server
```

Clients can invoke:
```json
{
  "name": "sequentialthinking",
  "arguments": {
    "thought": "Evaluate database isolation levels for inventory deduction.",
    "thoughtNumber": 1,
    "totalThoughts": 3,
    "nextThoughtNeeded": true
  }
}
```

### 3. External MCP Server Configuration (NPX or Docker)

For external IDEs (Claude Desktop, Cursor, Codex) connecting to the upstream GitHub package:

#### Via NPX (`claude_desktop_config.json` / `mcp.json`):
```json
{
  "mcpServers": {
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    }
  }
}
```

#### Via Docker:
```json
{
  "mcpServers": {
    "sequentialthinking": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "mcp/sequentialthinking"]
    }
  }
}
```

---

## Verification & Testing

Run the automated test suite for Sequential Thinking:
```bash
python -m pytest tests/test_sequential_thinking.py --override-ini="addopts=" -v
```
