# Context Graph Builder Skill

Build, maintain, and enrich the project's context graph as you work.
This skill runs automatically — agents should follow these guidelines
during every task execution to incrementally improve the context graph.

## When to Build Context

**Always** update the graph when you:
- Complete a task (success or failure)
- Discover a code pattern or anti-pattern
- Make an architectural decision
- Encounter and fix an error
- Learn a user preference (coding style, framework choice, etc.)
- Modify files in the project

**Build from scratch** when:
- The user provides a `--project` path for the first time
- The user requests `rescan` or `rebuild context`
- The graph is empty for the active project

## How to Build Context

### 1. Project Registration (First Use)

When a project path is provided, the system auto-scans to create:
- A `PROJECT` node (root anchor for the project graph)
- `FILE` nodes for each directory
- `PATTERN` nodes for detected languages, frameworks, and structure
- `DECISION` nodes for detected CI/CD, testing, and infrastructure choices
- `CONTAINS` / `RELATED_TO` edges linking them all

### 2. Incremental Updates During Operation

After each task execution, store context:

```python
# After completing a task
manager.store_task(
    task_description="What was done",
    outcome="The result",
    success=True,
    agents_involved=["claude", "codex"],
    files_modified=["src/auth.py"],
    project_id=project_id,  # Scope to current project
)

# When you discover a useful pattern
manager.store_pattern(
    pattern_name="Error Handling Convention",
    pattern_type="convention",
    description="This project uses Result types instead of exceptions",
    examples=["def fetch_user(...) -> Result[User, Error]: ..."],
    languages=["python"],
)

# When you encounter and fix a bug
manager.log_mistake(
    error_type="import_error",
    error_message="Circular import between auth and users modules",
    context_description="When refactoring the auth module",
    correction="Moved shared types to a common.types module",
    prevention_strategy="Keep shared types in dedicated modules",
    severity="medium",
)

# When an architectural decision is made
manager.store_decision(
    decision_title="Use PostgreSQL over MongoDB",
    decision_description="Chose relational DB for strong consistency",
    rationale="ACID transactions needed for payment processing",
    alternatives_considered=["MongoDB", "CockroachDB"],
)
```

### 3. Build from Scratch

To fully rebuild a project's context graph:

```python
# Delete existing graph for the project
manager.delete_project_graph(project_id)

# Re-register and scan
manager.register_project("/path/to/project")
```

Or via CLI:
```bash
ai-orchestrator run "analyze project" --project /path/to/project
```

## Multi-Project Isolation

Each project gets a unique `project_id` derived from its absolute path.
All nodes created within a project session carry that `project_id`.
This ensures:

- Graphs from different projects never mingle
- Searching within a project only returns its own context
- Deleting a project's graph doesn't affect others
- The dashboard can filter by project

When no project is configured, nodes have `project_id=""` (global scope).
Global nodes are shared across all contexts — use for universal patterns.

## What Makes Good Context

**DO store:**
- Concrete patterns discovered in the codebase
- Specific error messages and their fixes
- Architectural decisions with rationale
- File modification history per task
- User's coding preferences (naming, style, framework choices)

**DON'T store:**
- Raw LLM outputs verbatim (summarize instead)
- Temporary debugging artifacts
- Sensitive credentials or secrets
- Duplicate information already in the graph

## Triggering

This skill activates automatically through the engine integration.
Both the Orchestrator and Agentic Team engines:
1. Auto-register projects on startup if `PROJECT_PATH` is set
2. Store task results after each execution
3. Log mistakes on failures
4. Pass `project_id` to scope all context operations
