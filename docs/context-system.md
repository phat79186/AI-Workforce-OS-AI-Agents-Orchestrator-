# Graph Context System

The Graph Context System provides persistent memory capabilities for AI agents, enabling them to learn from past conversations, tasks, and mistakes. This enterprise-grade system uses a graph database with hybrid search (BM25 + semantic) for intelligent context retrieval.

## Overview

The context system stores and retrieves information using:
- **Graph Database**: SQLite with FTS5 for full-text search
- **Embeddings**: Sentence-transformers (all-MiniLM-L6-v2) for semantic similarity
- **Hybrid Search**: Reciprocal Rank Fusion (RRF) combining keyword and semantic search
- **Node Types**: Conversations, Tasks, Mistakes, Patterns, Decisions, Code Snippets, Preferences

## Architecture

```
orchestrator/context/
├── __init__.py          # Module exports
├── schemas.py           # Node and edge type definitions
├── graph_store.py       # SQLite graph database with FTS5
├── embeddings.py        # Sentence-transformer embeddings
├── bm25_index.py        # BM25 keyword search
├── hybrid_search.py     # RRF fusion search
└── memory_manager.py    # High-level API
```

## Node Types

### ConversationNode
Stores past conversations with context.
```python
ConversationNode(
    id="conv-123",
    content="Discussion about authentication implementation",
    timestamp=datetime.now(timezone.utc),
    metadata={"topic": "auth", "user": "developer"}
)
```

### TaskNode
Records completed tasks with outcomes.
```python
TaskNode(
    id="task-456",
    content="Implemented JWT authentication",
    timestamp=datetime.now(timezone.utc),
    task_description="Build login system",
    outcome="completed",
    success=True,
    metadata={"duration": 3600, "engine": "orchestrator"}
)
```

### MistakeNode
Logs errors and their corrections for learning.
```python
MistakeNode(
    id="mistake-789",
    content="Used wrong endpoint format",
    timestamp=datetime.now(timezone.utc),
    error_description="API returned 404",
    context="When trying to fetch user data",
    correction="Use /api/v1/users instead of /api/users"
)
```

### PatternNode
Stores recognized code patterns.
```python
PatternNode(
    id="pattern-101",
    content="Repository pattern for data access",
    timestamp=datetime.now(timezone.utc),
    pattern_type="design_pattern",
    examples=["UserRepository", "OrderRepository"]
)
```

### DecisionNode
Records architectural decisions.
```python
DecisionNode(
    id="decision-202",
    content="Use PostgreSQL for primary database",
    timestamp=datetime.now(timezone.utc),
    decision="PostgreSQL over MySQL",
    rationale="Better JSON support and performance"
)
```

## Edge Types

- **RELATED_TO**: General relationship between nodes
- **CAUSED_BY**: Error causation (mistake → cause)
- **FIXED_BY**: Solution relationship (mistake → fix)
- **SIMILAR_TO**: Semantic similarity
- **DEPENDS_ON**: Dependency relationship
- **PRECEDED_BY**: Temporal ordering
- **FOLLOWED_BY**: Temporal ordering (inverse)
- **LEARNED_FROM**: Learning source
- **REFERENCES**: Reference relationship
- **CONTAINS**: Containment relationship
- **PRODUCED_BY**: Production relationship
- **USED_IN**: Usage relationship

## Usage

### Python API

```python
from orchestrator.context import MemoryManager

# Initialize the memory manager
manager = MemoryManager()

# Store a conversation
conv_id = manager.store_conversation(
    content="Discussed REST API design patterns",
    metadata={"topic": "api-design"}
)

# Store a completed task
task_id = manager.store_task(
    task_description="Implement user authentication",
    outcome="completed",
    success=True,
    metadata={"duration_seconds": 120}
)

# Log a mistake for learning
mistake_id = manager.log_mistake(
    error_description="Forgot to validate input",
    context="User registration endpoint",
    correction="Add input validation middleware"
)

# Search for relevant context
results = manager.search("authentication JWT tokens", limit=5)
for result in results:
    print(f"Node: {result.node.id}, Score: {result.score}")

# Get formatted context for injection into prompts
context = manager.get_relevant_context("how to implement login", limit=5)
print(context)

# Link related nodes
manager.link_nodes(task_id, conv_id, EdgeType.RELATED_TO)
```

### MCP Tools

The context system is exposed via MCP tools:

```yaml
# Store a conversation
store_conversation:
  content: "User requested REST API implementation"
  metadata: '{"project": "api-gateway"}'

# Search context
search_context:
  query: "REST API best practices"
  limit: 10

# Log a mistake
log_mistake:
  error_description: "SQL injection vulnerability found"
  context: "User search endpoint"
  correction: "Use parameterized queries"

# Get relevant context
get_relevant_context:
  query: "database optimization"
  limit: 5
```

## Search Capabilities

### BM25 Search
Keyword-based search using BM25 algorithm:
```python
results = manager.bm25_search("python authentication", limit=10)
```

### Semantic Search
Embedding-based similarity search:
```python
results = manager.semantic_search("user login system", limit=10)
```

### Hybrid Search (Recommended)
Combines BM25 and semantic search using Reciprocal Rank Fusion:
```python
results = manager.search("authentication best practices", limit=10)
```

## Integration

### Orchestrator Engine
The orchestrator automatically stores tasks in context after execution:
```python
from orchestrator.core import OrchestratorEngine

engine = OrchestratorEngine()
result = engine.execute_task("Build user auth system")
# Task automatically stored in context
```

### Agentic Team Engine
The agentic team also stores task results:
```python
from agentic_team import AgenticTeamEngine

engine = AgenticTeamEngine()
result = engine.execute_task("Implement payment processing")
# Task automatically stored with team metadata
```

## Configuration

### Database Location
Default: `~/.orchestrator/context.db`

Override via environment variable:
```bash
export ORCHESTRATOR_CONTEXT_DB=/path/to/context.db
```

### Embedding Model
Default: `all-MiniLM-L6-v2` (384 dimensions)

Override in code:
```python
from orchestrator.context import EmbeddingGenerator
generator = EmbeddingGenerator(model_name="all-mpnet-base-v2")
```

## Performance

- **Storage**: SQLite with WAL mode for concurrent access
- **Indexing**: FTS5 for full-text search, vector index for embeddings
- **Caching**: In-memory BM25 index for fast keyword search
- **Thread Safety**: Thread-local database connections

## Best Practices

1. **Store meaningful context**: Focus on learnable outcomes, not every conversation
2. **Log mistakes promptly**: Record errors with context and corrections
3. **Link related nodes**: Create edges to build a knowledge graph
4. **Use hybrid search**: Combines keyword precision with semantic understanding
5. **Periodic cleanup**: Remove old, irrelevant context to maintain performance

## Troubleshooting

### Missing embeddings
Install sentence-transformers:
```bash
pip install sentence-transformers
```

### Database locked
The context system uses WAL mode. If you see locking issues:
```python
# Ensure connections are closed properly
manager.close()
```

### Search returning no results
Check that nodes are indexed after storage. The hybrid search automatically indexes new nodes.
